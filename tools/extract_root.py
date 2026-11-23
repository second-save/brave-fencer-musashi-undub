"""Copy the root data files (*.CD and the EXE) of a raw Track 1 into a folder, for align.py.
Usage: extract_root.py TRACK1.bin OUT_DIR"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from build import Disc

disc, out = Disc(sys.argv[1]), sys.argv[2]
os.makedirs(out, exist_ok=True)
for name in disc.files:
    if name.endswith('.CD') or name.startswith(('SLUS', 'SLPS')):
        open(os.path.join(out, name), 'wb').write(disc.read_file(name))
        print(name)
