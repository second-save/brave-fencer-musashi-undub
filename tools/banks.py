"""Voice bank tables in the PS-EXE: 10 records of 0x48 bytes {u32 slot_ptr, u32 flags, u32 group_start[16]};
slot table = groups x 16 x u32 {u8 vol, u8 flags, u16 length}. Voice id = 0x4000|bank<<9|half<<4|group<<5|ch."""
import struct
T0 = 0x80010000
REC = {'us': 0x5AE9C, 'jp': 0x5A038}
BANK_FILES = ['ST01', 'ST02', 'SHOPS01', 'OPEN', 'END', 'ST03', 'ST04', 'ST05', 'OUT', 'ST06']

def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def slot_off(exe, rec, vid):
    """File offset of the slot entry a voice id resolves to (mirrors func_80036AF8)."""
    bank, lo, ch = (vid >> 9) & 31, (vid >> 4) & 31, vid & 15
    if lo & 1:
        ch += 4 if exe[rec + bank * 0x48 + 4] else 8
    return u32(exe, rec + bank * 0x48) - T0 + 0x800 + (lo >> 1) * 0x40 + ch * 4

def slot(exe, ver, vid):
    return u32(exe, slot_off(exe, REC[ver], vid))
