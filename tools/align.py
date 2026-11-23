"""Pair each English voice id with the Japanese voice id of the same dialogue box.

Usage: align.py US_DIR JP_DIR OUT_JSON   (dirs hold the extracted root files: *.CD + EXE)

Every voiced box in the scripts starts with 05/16 0B <flags> <u16 id>, followed by
02 xx <speaker> <14|18>. Boxes are aligned with difflib two ways (whole game in archive
order, and per voice bank on speaker tokens); when they disagree the pair whose clip
lengths look most alike wins."""
import collections, difflib, hashlib, json, math, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from bfm import cd_subfiles, pac_entries, lzss
from voice_ids import codes
from banks import slot

FILES = ['MAIN', 'SC01', 'SC02', 'SC03', 'SC04', 'SC05', 'SC06', 'SC07']


def boxes(d):
    seen, out = set(), []
    for f in FILES:
        buf = open(f'{d}/{f}.CD', 'rb').read()
        for si, sub in cd_subfiles(buf):
            for pi, t, _, p in pac_entries(sub):
                if t not in (1, 4):
                    continue
                data = lzss(p) if t == 4 else p
                h = hashlib.md5(data).digest()
                if h in seen:  # identical overlays repeat across archives
                    continue
                seen.add(h)
                for off, fl, vid in codes(data):
                    out.append(((vid >> 9) & 31, fl, data[off + 4:off + 8], vid, data[off - 1]))
    return out


def pairs(U, J, key, min_block):
    m = collections.defaultdict(collections.Counter)
    sm = difflib.SequenceMatcher(None, [key(x) for x in U], [key(x) for x in J], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        if n >= min_block:
            for i in range(n):
                m[U[a + i][3]][J[b + i][3]] += 1
    return m


def fill_gaps(U, J, best):
    """Per bank, a run of unpaired US boxes between two paired anchors takes the unpaired JP boxes
    between the anchors' partners, in order, when both runs have the same length."""
    new, taken = {}, set(best.values())
    for b in range(10):
        us = [x for x in U if x[0] == b]
        js = [x for x in J if x[0] == b]
        where = collections.defaultdict(list)
        for i, x in enumerate(js):
            where[x[3]].append(i)
        i = 0
        while i < len(us):
            if us[i][3] in best:
                i += 1
                continue
            k = i
            while k < len(us) and us[k][3] not in best:
                k += 1
            lo = where.get(best[us[i - 1][3]]) if i else [-1]
            hi = where.get(best[us[k][3]]) if k < len(us) else [len(js)]
            spans = [(a, c) for a in lo or [] for c in hi or [] if a < c]
            if spans:
                a, c = min(spans, key=lambda s: s[1] - s[0])
                gap = [x[3] for x in js[a + 1:c] if x[3] not in taken]
                run = [x[3] for x in us[i:k]]
                if len(gap) == len(run):
                    new.update(zip(run, gap))
            i = k
    return new


def main(us_dir, jp_dir, out):
    U, J = boxes(us_dir), boxes(jp_dir)
    eu = open(f'{us_dir}/SLUS_007.26', 'rb').read()
    ej = open(f'{jp_dir}/SLPS_014.90', 'rb').read()
    cand = collections.defaultdict(collections.Counter)
    per_bank = lambda key: [pairs([x for x in U if x[0] == b], [x for x in J if x[0] == b], key, 2) for b in range(10)]
    for m in ([pairs(U, J, lambda x: x[:3], 1)]
              + per_bank(lambda x: (x[2][2], x[2][3]))  # speaker portrait + name-tag byte
              + per_bank(lambda x: (x[4], x[2][2] if x[2][0] == 2 else x[2][0]))):  # box/page start + speaker
        for a, c in m.items():
            cand[a].update(c)
    # most votes wins; ties go to the JP/US length ratio closest to the typical 1.14
    score = lambda a, b: abs(math.log((slot(ej, 'jp', b) >> 16 or 1) / (slot(eu, 'us', a) >> 16 or 1) / 1.14))
    best = {a: min(c, key=lambda b: (-c[b], score(a, b))) for a, c in cand.items()}
    best.update(fill_gaps(U, J, best))
    used = {x[3] for x in U}
    print(f'boxes US {len(U)} JP {len(J)}; US ids {len(used)} mapped {len(best)} unmapped {len(used - set(best))}')
    json.dump({'map': {f'{a:04x}': f'{b:04x}' for a, b in sorted(best.items())},
               'unmapped': [f'{a:04x}' for a in sorted(used - set(best))]}, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:4])
