"""VAB sound banks (Sony 'pBAV' header + VAG sample bodies) inside PAC entries."""
import struct


def parse(d, at=0):
    """Return (header_len, [sample sizes in bytes], body_offset) for a VAB header at `at`.
    Layout: 0x20 header, 0x800 program table, 0x200 per program of tones, then 256 u16 sizes (x8)."""
    assert d[at:at + 4] == b'pBAV'
    ps, ts, vs = struct.unpack_from('<HHH', d, at + 0x12)  # programs, tones, vag count
    sizes_off = at + 0x20 + 0x800 + ps * 0x200
    sizes = [struct.unpack_from('<H', d, sizes_off + 2 * i)[0] * 8 for i in range(1, vs + 1)]
    hdr = sizes_off + 0x200 - at
    return hdr, sizes, at + hdr


def samples(d, at=0):
    hdr, sizes, body = parse(d, at)
    out, o = [], body
    for n in sizes:
        out.append((o, d[o:o + n])); o += n
    return out
