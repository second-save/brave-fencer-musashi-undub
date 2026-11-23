# Brave Fencer Musashi undub (US disc + Japanese voices)

## How it works
- Voices are XA clips in the 10 `.STR` files (not FMV): 8-channel stereo (ST01, OPEN) or 16-channel mono banks.
- EXE (`SLUS_007.26` @0x5AE9C, JP `SLPS_014.90` @0x5A038): 10 bank records of 0x48 bytes
  `{slot table ptr, 8ch flag, u32 group_start[16]}`; slot = `{vol, flags, u16 length}` per group x 16.
  Bank order: ST01 ST02 SHOPS01 OPEN END ST03 ST04 ST05 OUT ST06. Player: `func_80036AF8` (BFM-decomp).
- Voice id = `0x4000 | bank<<9 | (group*2+half)<<4 | ch`, written inline in dialogue text as
  `05|08|0A|16, 0B, flags, id` inside LZSS overlays of `SC0x.CD`/`MAIN.CD`.
- Both versions pack clips by length, so ids differ: `tools/align.py` pairs US/JP boxes (difflib on
  language-independent tokens), `data/voice_map.json`. Mapped pairs' lengths correlate ~0.85.
- `tools/build.py` keeps the US layout (no script/text edits), puts the paired JP clip in each US slot
  (JP slot vol/flags/length too), re-interleaves, appends new STRs after Track 1, patches EXE table,
  ISO dir, PVD size and the `.DA` file LBAs (audio tracks move back). Unpaired slots are emptied
  (silent): the JP game leaves those boxes unvoiced (the US dub voiced more lines).
- Files are found by name at runtime, so moving them is safe.

## Commands
```
python3 tools/extract_root.py US_T1.bin work/us; python3 tools/extract_root.py JP_T1.bin work/jp
python3 tools/align.py work/us work/jp data/voice_map.json
python3 tools/build.py US_T1.bin JP_T1.bin data/voice_map.json "build/Brave Fencer Musashi (USA) (Track 1).bin"
python3 tools/verify.py BUILT_T1.bin US_T1.bin JP_T1.bin data/voice_map.json
xdelta3 -e -9 -s US_T1.bin BUILT_T1.bin dist/...xdelta
```
Emulator QA (macOS): `tools/emu_mac.py` (skill emu.py without `-no-ui`; Intel PCSX-Redux segfaults
headless under Rosetta). Use `--bios .../Resources/share/pcsx-redux/resources/openbios.bin` (SCPH5500
gives black frames), `--sav work/qa/card1.mcd` (`tools/blank_mcd.py`), PS1 key names (`cross`).
`--debugger` aborts on this build; `tools/lua/voice_log.lua` polls the voice id at 0x800A6430 instead.

## Status (2026-11-23)
- v1 (English fallback) tested by user: works, "only partially in Japanese".
- v2 19:36: gap-fill pairing (857/894 text ids), unpaired slots silenced: 855 JP, 105 silent, no English.
  Patch 75 MB, re-apply verified, smoke + opening route ok. User: works.
- v3: title FMV (LOGOA/B) audio = JP (US video kept), MAIN.CD sound banks sub 2/3/4 = JP (title/New Game
  shouts; JP bodies padded to US size). Stage banks (SC0x) still have ~330 English voice samples (NPC/boss
  shouts); some JP bodies are larger there, so entries would move: not done.
