"""Check a built Track 1: every voice slot with a clip resolves to a whole XA clip, and every
mapped English id now plays exactly the Japanese clip it was paired with.
Usage: verify.py BUILT.bin US.bin JP.bin data/voice_map.json"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from build import Disc, bank_info, clip, vid_of
from banks import BANK_FILES, REC, T0, u32, slot_off

new, us, jp = Disc(sys.argv[1]), Disc(sys.argv[2]), Disc(sys.argv[3])
vmap = {int(a, 16): int(b, 16) for a, b in json.load(open(sys.argv[4]))['map'].items()}
exe, exe_jp = new.read_file('SLUS_007.26'), jp.read_file('SLPS_014.90')
ok = checked = 0
for k, name in enumerate(BANK_FILES):
    _, stride, groups = bank_info(exe, 'us', k)
    _, _, groups_jp = bank_info(exe_jp, 'jp', k)
    for g, gs in enumerate(groups):
        for s in range(stride):
            v = vid_of(k, g, s, stride)
            c = clip(new, new.files[name + '.STR'][0], gs, s, stride)
            j = vmap.get(v)
            if c and j is not None and (j >> 9) & 31 == k:
                jg = (j >> 5) & 15
                jch = (slot_off(exe_jp, REC['jp'], j) - (u32(exe_jp, REC['jp'] + k * 0x48) - T0 + 0x800) - jg * 0x40) // 4
                ref = clip(jp, jp.files[name + '.STR'][0], groups_jp[jg], jch, stride)
                checked += 1
                ok += len(ref) == len(c) and all(a[24:2348] == b[24:2348] for a, b in zip(ref, c))
print(f'{ok}/{checked} mapped slots play the paired Japanese clip')
print('DA files:', {n: v[0] for n, v in new.files.items() if n.endswith('.DA')}, 'vs US', {n: v[0] for n, v in us.files.items() if n.endswith('.DA')})
assert ok == checked
