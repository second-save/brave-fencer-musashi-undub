"""Write a blank, formatted 128 KiB PS1 memory card image. Usage: blank_mcd.py OUT.mcd"""
import sys


def frame(data):
    f = bytearray(data.ljust(127, b'\0'))
    x = 0
    for b in f:
        x ^= b
    return bytes(f + bytes([x]))  # byte 127 = XOR of bytes 0..126


card = bytearray(frame(b'MC'))
for _ in range(15):  # directory: 15 free blocks, no next block
    card += frame(b'\xa0\0\0\0\0\0\0\0\xff\xff')
for _ in range(20):  # broken-sector list: none
    card += frame(b'\xff\xff\xff\xff\0\0\0\0\xff\xff')
card = card.ljust(63 * 128, b'\0') + frame(b'MC')  # frame 63 repeats the header
card = card.ljust(128 * 1024, b'\0')
assert len(card) == 131072 and card[127] == ord('M') ^ ord('C')
open(sys.argv[1], 'wb').write(card)
