"""Brave Fencer Musashi containers: .CD TOC -> PAC chain -> LZSS (type 4).
Format notes from BFM-decomp docs/formats.md; this is an independent implementation."""
import struct

SECTOR = 0x800


def cd_subfiles(buf):
    """Yield (index, bytes) for each sub-file of a .CD archive."""
    count = struct.unpack_from('<I', buf, 0)[0]
    for i in range(count):
        rel, length = struct.unpack_from('<II', buf, 8 + 8 * i)
        yield i, buf[rel * SECTOR: rel * SECTOR + length]


def pac_entries(buf):
    """Yield (index, type, header_offset, payload) for a PAC chain; nothing if not a PAC."""
    pos, idx = 0, 0
    while buf[pos:pos + 4] == b'PAC\0':
        typ, last = buf[pos + 4], buf[pos + 5]
        length = struct.unpack_from('<I', buf, pos + 0xC)[0]
        yield idx, typ, pos, buf[pos + SECTOR: pos + length]
        if last:
            return
        pos += (length + SECTOR - 1) & ~(SECTOR - 1)
        idx += 1


def lzss(enc):
    """Game LZSS: 1024 ring, absolute 1-biased positions, pos==0 ends the stream."""
    ring, r, out, flags, p = bytearray(1024), 0, bytearray(), 0, 0
    while p < len(enc):
        flags >>= 1
        if not flags & 0xFF00:
            flags = 0xFF00 | enc[p]; p += 1
        if flags & 1:
            b = enc[p]; p += 1
            out.append(b); ring[r] = b; r = (r + 1) & 0x3FF
        else:
            code = enc[p] | enc[p + 1] << 8; p += 2
            pos = code & 0x3FF
            if pos == 0:
                break
            for i in range((code >> 10) + 2):
                b = ring[(pos - 1 + i) & 0x3FF]
                out.append(b); ring[r] = b; r = (r + 1) & 0x3FF
    return bytes(out)


def overlays(cd_buf):
    """Yield (subfile, pac_index, decompressed bytes) for every type-4 entry."""
    for si, sub in cd_subfiles(cd_buf):
        for pi, typ, _, payload in pac_entries(sub):
            if typ == 4:
                yield si, pi, lzss(payload)
