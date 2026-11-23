"""Raw 2352-byte Mode 2 sectors: address header, EDC and ECC (CD-ROM XA rules)."""

def _tables():
    f, b, edc = [0] * 256, [0] * 256, [0] * 256
    for i in range(256):
        j = (i << 1) ^ (0x11D if i & 0x80 else 0)
        f[i], b[i ^ j] = j, i
        e = i
        for _ in range(8):
            e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
        edc[i] = e
    return f, b, edc

ECC_F, ECC_B, EDC_T = _tables()


def edc(data):
    e = 0
    for x in data:
        e = (e >> 8) ^ EDC_T[(e ^ x) & 0xFF]
    return e.to_bytes(4, 'little')


def _ecc_pq(s, major_count, minor_count, major_mult, minor_inc, dest):
    size = major_count * minor_count
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = s[0xC + index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t; b ^= t; a = ECC_F[a]
        a = ECC_B[ECC_F[a] ^ b]
        s[dest + major] = a
        s[dest + major + major_count] = a ^ b


def set_address(s, lba):
    m, rest = divmod(lba + 150, 75 * 60)
    sec, fr = divmod(rest, 75)
    bcd = lambda v: (v // 10) << 4 | v % 10
    s[0:12] = b'\x00' + b'\xff' * 10 + b'\x00'
    s[12:16] = bytes([bcd(m), bcd(sec), bcd(fr), 2])


def finish(s, lba):
    """Write header, EDC and (Form 1) ECC for a Mode 2 sector whose subheader+data are set."""
    set_address(s, lba)
    if s[18] & 0x20:  # Form 2: EDC over subheader + 2324 bytes
        s[2348:2352] = edc(s[16:2348])
    else:  # Form 1: EDC, then ECC computed with the header zeroed
        s[2072:2076] = edc(s[16:2072])
        hdr = s[12:16]; s[12:16] = b'\0\0\0\0'
        _ecc_pq(s, 86, 24, 2, 86, 0x81C)
        _ecc_pq(s, 52, 43, 86, 88, 0x8C8)
        s[12:16] = hdr
    return s


if __name__ == '__main__':  # self-check: re-encoding real sectors must reproduce them
    import sys
    f = open(sys.argv[1], 'rb')
    for lba in map(int, sys.argv[2:]):
        f.seek(lba * 2352); orig = f.read(2352)
        assert bytes(finish(bytearray(orig), lba)) == orig, lba
    print('ok')
