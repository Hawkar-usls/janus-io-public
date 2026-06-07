# Benchmark Plan

The public benchmark plan should compare scheduler policies without changing wire behavior.

## Baselines

Required comparison families:

- Random pure baseline.
- Linear pure baseline.
- Zim-only baseline.
- Janus full baseline.
- DualLock baseline.
- Future TachyonMicroAgent allocator.
- Optional NerdMiner-like baseline, if implemented as a local scheduler policy.

## Metrics

Report:

- clean accepted proof count;
- accepted/MH;
- z28+/MH;
- z30+/MH;
- z32+/MH;
- z33+/MH;
- z35+/MH;
- max proof z;
- reject rate;
- cooldown state;
- wire_change_required.

## Claim Threshold

Do not make public advantage claims from one lucky tail. A candidate advantage should require repeated A/B runs and stable improvement, for example:

- more than 15 percent accepted/MH improvement over strong linear baseline;
- more than 25 percent z30+/MH improvement over best baseline;
- reject rate remaining below 0.5 percent;
- `wire_change_required=false` throughout.

## Recommended Next A/B

Run fixed-duration or fixed-MH windows for random, linear, Zim, Janus, DualLock, and Tachyon. Keep pool difficulty, workers, hardware, submit gate, and wire policy fixed.
