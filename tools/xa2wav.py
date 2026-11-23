"""Decode the XA audio of a file on a raw Mode 2 track to WAV (for listening checks).
Usage: xa2wav.py TRACK1.bin LBA SECTORS OUT.wav [CHANNEL]"""
import struct, sys, wave

K = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)]


def decode(sectors, channel=None):
    """Yield (left, right) or (mono,) sample lists per 4-bit XA sector."""
    hist = [[0, 0], [0, 0]]
    stereo = rate = None
    out = []
    for s in sectors:
        if not s[18] & 4 or (channel is not None and s[17] != channel):
            continue
        coding = s[19]
        stereo, rate = coding & 1, 18900 if coding & 4 else 37800
        data = s[24:24 + 2304]
        for g in range(18):
            grp = data[g * 128:(g + 1) * 128]
            for blk in range(8):
                ch = blk & 1 if stereo else 0
                hdr = grp[4 + blk]
                shift, flt = hdr & 15, min(hdr >> 4, 4)
                k0, k1 = K[flt]
                h = hist[ch]
                for i in range(28):
                    nib = (grp[16 + i * 4 + blk // 2] >> (4 * (blk & 1))) & 15
                    v = (nib << 12) - (0x10000 if nib & 8 else 0)
                    v = (v >> shift) + ((h[0] * k0 + h[1] * k1 + 32) >> 6)
                    v = max(-32768, min(32767, v))
                    h[1], h[0] = h[0], v
                    out.append((ch, v))
    if stereo:
        L = [v for c, v in out if c == 0]; R = [v for c, v in out if c == 1]
        return rate, 2, [x for p in zip(L, R) for x in p]
    return rate, 1, [v for _, v in out]


if __name__ == '__main__':
    path, lba, n, dst = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    ch = int(sys.argv[5]) if len(sys.argv) > 5 else None
    f = open(path, 'rb'); f.seek(lba * 2352)
    secs = [f.read(2352) for _ in range(n)]
    rate, nch, pcm = decode(secs, ch)
    w = wave.open(dst, 'wb'); w.setnchannels(nch); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack('<%dh' % len(pcm), *pcm)); w.close()
    print(dst, rate, 'Hz', nch, 'ch', round(len(pcm) / nch / rate, 2), 's')
