"""Run the skill's emu.py on macOS: the Intel PCSX-Redux build segfaults under Rosetta with -no-ui,
so drop that flag (a window opens, everything else is unchanged). Same arguments as emu.py."""
import os, runpy, subprocess, sys

SKILL = os.environ.get('TRANSLATE_SKILL', os.path.expanduser('~/.claude/skills/translate-retro-game'))
EMU = os.path.join(SKILL, 'scripts', 'emu.py')

_popen = subprocess.Popen
subprocess.Popen = lambda cmd, *a, **k: _popen([c for c in cmd if c != '-no-ui'], *a, **k)
sys.argv[0] = EMU
runpy.run_path(EMU, run_name='__main__')
