"""Build the undub Track 1: English disc, Japanese voice clips.

Usage: build.py US_TRACK1.bin JP_TRACK1.bin data/voice_map.json OUT_TRACK1.bin

For every voice bank (an .STR of interleaved XA channels) the English group/slot layout is kept,
so no script or text changes are needed. Each slot gets the Japanese clip mapped to its voice
id (else the English clip stays), the groups are re-interleaved, the new .STR files are
appended after Track 1, and the EXE bank table, ISO directory and .DA addresses are patched."""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from banks import BANK_FILES, REC, T0, u32, slot_off
from cdsector import finish

RAW = 2352


class Disc:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.files = {}
        pvd = self.data(16)
        self._walk(*struct.unpack_from('<I', pvd, 158), struct.unpack_from('<I', pvd, 166)[0])

    def raw(self, lba):
        self.f.seek(lba * RAW); return self.f.read(RAW)

    def data(self, lba):
        return self.raw(lba)[24:24 + 2048]

    def _walk(self, lba, size):
        for n in range((size + 2047) // 2048):
            d, i = self.data(lba + n), 0
            while i < 2048 and d[i]:
                ln = d[i]
                name = d[i + 33:i + 33 + d[i + 32]].decode('latin1')
                flba, fsize = struct.unpack_from('<I', d, i + 2)[0], struct.unpack_from('<I', d, i + 10)[0]
                # (dir sector lba, offset in sector) is kept so the record can be patched
                if not d[i + 25] & 2:
                    self.files[name.split(';')[0]] = (flba, fsize, lba + n, i)
                i += ln

    def read_file(self, name):
        lba, size, _, _ = self.files[name]
        return b''.join(self.data(lba + i) for i in range((size + 2047) // 2048))[:size]


def bank_info(exe, ver, k):
    rec = REC[ver] + k * 0x48
    stride = 8 if exe[rec + 4] else 16
    starts = [u32(exe, rec + 8 + 4 * i) for i in range(16)]
    groups = [0] + [s for s in starts[1:] if s]
    return rec, stride, groups[:-1]  # the last entry is the file end, not a group


def clip(disc, file_lba, start, ch, stride):
    """Raw sectors of one XA clip: every `stride`-th sector of channel `ch` up to the EOF flag."""
    out, lba = [], file_lba + start + ch
    while True:
        s = disc.raw(lba)
        if not (s[18] & 4 and s[17] == ch):
            assert not out, (file_lba, start, ch, lba)  # a clip must not break off midway
            return None  # slot listed in the table but no clip on disc (unused line)
        out.append(s)
        if s[18] & 0x80:
            return out
        lba += stride


def vid_of(k, g, s, stride):
    half, ch = divmod(s, stride // 2)
    return 0x4000 | k << 9 | ((g << 1) | half) << 4 | ch


def main(us_bin, jp_bin, map_json, out_bin):
    vmap = {int(a, 16): int(b, 16) for a, b in json.load(open(map_json))['map'].items()}
    us, jp = Disc(us_bin), Disc(jp_bin)
    exe_us = bytearray(us.read_file('SLUS_007.26'))
    exe_jp = jp.read_file('SLPS_014.90')
    end = os.path.getsize(us_bin) // RAW
    new_sectors, new_dir = [], {}
    stats = {'jp': 0, 'silenced': 0}
    lba = us.files['ST02.STR'][0]
    while us.raw(lba)[18] & 4:
        lba += 1
    filler = bytearray(us.raw(lba))  # the padding the original files use: a Form 1 zero sector
    for k, name in enumerate(BANK_FILES):
        name += '.STR'
        rec, stride, groups = bank_info(exe_us, 'us', k)
        _, stride_jp, groups_jp = bank_info(exe_jp, 'jp', k)
        assert stride == stride_jp
        out, starts = [], []
        for g, gstart in enumerate(groups):
            clips = {}
            for s in range(stride):
                off = slot_off(exe_us, REC['us'], vid_of(k, g, s, stride))
                if not u32(exe_us, off):
                    continue
                v = vid_of(k, g, s, stride)
                j = vmap.get(v)
                if j is not None and (j >> 9) & 31 == k:
                    jg, jch = (j >> 5) & 15, slot_off(exe_jp, REC['jp'], j)
                    jch = (jch - (u32(exe_jp, REC['jp'] + k * 0x48) - T0 + 0x800) - jg * 0x40) // 4
                    clips[s] = clip(jp, jp.files[name][0], groups_jp[jg], jch, stride)
                    assert clips[s], hex(j)
                    exe_us[off:off + 4] = exe_jp[slot_off(exe_jp, REC['jp'], j):][:4]  # JP vol/flags/length
                    stats['jp'] += 1
                else:  # no Japanese line here (the JP game leaves the box unvoiced): silence the slot
                    exe_us[off:off + 4] = bytes(4)  # empty slot: the player returns early, a running clip goes on
                    stats['silenced'] += 1
            starts.append(len(out))
            rows = max((len(c) for c in clips.values() if c), default=1)
            for r in range(rows):
                for s in range(stride):
                    c = clips.get(s)
                    if c and r < len(c):
                        sec = bytearray(c[r]); sec[17] = sec[21] = s  # channel byte, both subheader copies
                        out.append(sec)
                    else:
                        out.append(bytearray(filler))
        for g, st in enumerate(starts[1:] + [len(out)], start=1):  # table holds group ends
            struct.pack_into('<I', exe_us, rec + 8 + 4 * g, st)
        new_dir[name] = (end + len(new_sectors), len(out) * 2048)
        new_sectors += out
    grow = len(new_sectors)
    print(f"slots: {stats['jp']} Japanese, {stats['silenced']} silenced (no Japanese line); +{grow} sectors")

    with open(us_bin, 'rb') as src, open(out_bin, 'wb') as dst:
        while chunk := src.read(RAW * 4096):
            dst.write(chunk)
        for i, s in enumerate(new_sectors):
            dst.write(finish(s, end + i))

    def patch_sector(f, lba, fn):
        f.seek(lba * RAW); s = bytearray(f.read(RAW)); fn(s); f.seek(lba * RAW); f.write(finish(s, lba))

    def both(s, o, v):
        struct.pack_into('<I', s, o, v); struct.pack_into('>I', s, o + 4, v)

    with open(out_bin, 'r+b') as f:
        for name, (lba, size, dlba, doff) in us.files.items():
            if name in new_dir:
                nl, ns = new_dir[name]
            elif name.endswith('.DA'):  # audio tracks move back by the sectors added to Track 1
                nl, ns = lba + grow, size
            else:
                continue
            patch_sector(f, dlba, lambda s: (both(s, 24 + doff + 2, nl), both(s, 24 + doff + 10, ns)))
        patch_sector(f, 16, lambda s: both(s, 24 + 80, struct.unpack_from('<I', s, 24 + 80)[0] + grow))
        elba = us.files['SLUS_007.26'][0]
        for i in range(len(exe_us) // 2048):
            patch_sector(f, elba + i, lambda s: s.__setitem__(slice(24, 2072), exe_us[i * 2048:(i + 1) * 2048]))
        title_audio(f, us, jp)
        main_vabs(f, us, jp)


def title_audio(f, us, jp):
    """Title FMVs: keep the US video, put the JP soundtrack in the US audio sectors (same interleave;
    the JP track is shorter and the US tail it leaves in place is silence)."""
    for name in ('LOGOA.STR', 'LOGOB.STR'):
        def audio(disc):
            lba, size = disc.files[name][:2]
            return [l for l in range(lba, lba + (size + 2047) // 2048) if disc.raw(l)[18] & 4]
        ua, ja = audio(us), audio(jp)
        for ul, jl in zip(ua, ja):
            src = jp.raw(jl)
            assert src[19] == us.raw(ul)[19]  # same XA coding (stereo 37.8 kHz)
            f.seek(ul * RAW); s = bytearray(f.read(RAW))
            s[24:2348] = src[24:2348]  # audio data only; the US subheader (EOF flags) stays
            f.seek(ul * RAW); f.write(finish(s, ul))
        print(f'{name}: {min(len(ua), len(ja))} of {len(ua)} audio sectors now Japanese')


def main_vabs(f, us, jp):
    """MAIN.CD sound banks (title / New Game shouts): JP header + JP sample body padded to the US size,
    so no entry moves. Only banks whose bodies differ are touched."""
    sys.path.insert(0, os.path.dirname(__file__))
    from bfm import cd_subfiles, pac_entries
    lba = us.files['MAIN.CD'][0]
    orig = us.read_file('MAIN.CD')
    new = bytearray(orig)
    subs_jp = dict(cd_subfiles(jp.read_file('MAIN.CD')))
    for si, sub in cd_subfiles(orig):
        rel = struct.unpack_from('<I', orig, 8 + 8 * si)[0] * 2048
        ue, je = list(pac_entries(sub)), list(pac_entries(subs_jp[si]))
        bank = False  # a type-3 sample body belongs to the pBAV header before it
        for (pi, t, hoff, p), (_, tj, _, q) in zip(ue, je):
            bank = p[:4] == b'pBAV' if t == 2 else bank and t == 3
            if bank and p != q and t == tj:
                assert len(q) <= len(p), (si, pi)
                o = rel + hoff + 0x800
                new[o:o + len(p)] = q + bytes(len(p) - len(q))
                print(f'MAIN.CD sub {si} entry {pi} type {t}: Japanese ({len(q)} bytes in {len(p)})')
    for i in range(len(orig) // 2048):
        if new[i * 2048:(i + 1) * 2048] != orig[i * 2048:(i + 1) * 2048]:
            f.seek((lba + i) * RAW); s = bytearray(f.read(RAW))
            s[24:2072] = new[i * 2048:(i + 1) * 2048]
            f.seek((lba + i) * RAW); f.write(finish(s, lba + i))


if __name__ == '__main__':
    main(*sys.argv[1:5])
