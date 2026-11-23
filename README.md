# Brave Fencer Musashi (PS1) — Undub

Japanese voices with the English text: the US release of *Brave Fencer Musashi* with the voice acting of the
Japanese original, *Brave Fencer Musashiden* (Square, 1998). No game data included.

## What's Japanese

- **Dialogue voices:** 855 voiced lines in the event scenes now play the Japanese recording. The US dub voiced
  some lines the Japanese game leaves silent; those 105 lines show their English text with no voice, as in the
  original.
- **Title screen video:** the US video (with the US logo), playing the Japanese soundtrack.
- **Title / New Game shouts** and the other voice samples in the system sound banks.

Still English in this beta: about 330 short voice samples in the stage sound banks (NPC and boss shouts).

## Patch

| Patch | Apply to | Result |
|---|---|---|
| `Brave Fencer Musashi (USA) (Track 1) - Japanese voices.xdelta` | `Brave Fencer Musashi (USA) (Track 1).bin` (364,846,944 bytes, SHA-1 `b44f0f0a19936f23b26188b658e13201a6a9c211`, Redump SLUS-00726) | 551,426,400 bytes, SHA-1 `f0a627f8339429641adebfceae1e2ba74cf15c87` |

1. Apply the patch to Track 1 with xdelta3 (`xdelta3 -d -s original.bin patch.xdelta patched.bin`) or a
   GUI such as Delta Patcher.
2. Replace the original Track 1 with the patched file, under the same name, so the `.cue` still finds it.
   Tracks 2–4 and the `.cue` stay unchanged.

The data track grows by about 180 MB (the Japanese audio is added after it); the image still fits on a CD.
Tested in PCSX-Redux. Savestates from the unpatched game won't work: use memory card saves.

## How it works

- Event voices are XA audio clips in the ten `.STR` files, grouped in interleaved channels. A table in the
  EXE lists each bank's groups and slots; each dialogue box names its clip with an inline voice code.
- Both versions packed their clips by length, so the same line has a different id in each. `tools/align.py`
  pairs English and Japanese boxes by their language-independent codes (voice bank, speaker portrait,
  box/page markers); paired clip durations correlate at about 0.85.
- `tools/build.py` keeps the English scripts untouched and rebuilds each voice bank with the paired Japanese
  clip in every English slot, appends the new banks after Track 1 and patches the EXE table, the ISO
  directory and the CD-DA file addresses. It also swaps the title video's audio sectors and the system
  sound banks.
- `tools/verify.py` checks that every slot plays exactly the Japanese clip it was paired with.

`NOTES.md` has the formats and the emulator QA setup.

## Build

Needs both discs (US and Japanese, Redump BIN/CUE) and Python 3:

```
python3 tools/extract_root.py US_TRACK1.bin work/us; python3 tools/extract_root.py JP_TRACK1.bin work/jp
python3 tools/align.py work/us work/jp data/voice_map.json   # optional: data/voice_map.json is included
python3 tools/build.py US_TRACK1.bin JP_TRACK1.bin data/voice_map.json "build/Brave Fencer Musashi (USA) (Track 1).bin"
python3 tools/verify.py "build/Brave Fencer Musashi (USA) (Track 1).bin" US_TRACK1.bin JP_TRACK1.bin data/voice_map.json
```

`extract_root.py` copies each disc's root data files (`*.CD` and the EXE) for the aligner.

## Credits

- [BFM-decomp](https://github.com/Druthulu/BFM-decomp) for the container and LZSS documentation and the
  decompiled voice player.
- CUE's Brave Fencer extractor (romhacking.net) for the original format research.
