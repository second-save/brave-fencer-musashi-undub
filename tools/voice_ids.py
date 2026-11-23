"""List the voice codes in script text, in order: a box/page start byte (05 08 0A 16), 0B, flags, u16 id
(0x4000|bank<<9|...), then a layout/text code (02 09 14)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from bfm import overlays

PAT = re.compile(rb'[\x05\x08\x0a\x16]\x0b(.)(.[\x40-\x53])(?=[\x02\x09\x14])', re.S)

def codes(data):
    return [(m.start() + 1, m.group(1)[0], int.from_bytes(m.group(2), 'little')) for m in PAT.finditer(data)]

if __name__ == '__main__':
    for si, pi, d in overlays(open(sys.argv[1], 'rb').read()):
        c = [x for x in codes(d) if x[2] & 0xC000 == 0x4000]
        print(si, pi, len(c), ' '.join('%04x' % x[2] for x in c))
