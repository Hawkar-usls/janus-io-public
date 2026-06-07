# Repository Layout

This repository is split between public-facing project material and private raw
experiment evidence. Keep those boundaries intact when preparing GitHub updates.

## Public Or Curated

- `README.md` gives the high-level scope and safety position.
- `llms.txt` gives AI assistants a compact discovery entrypoint for Janus Io,
  JANUS I0, RBLGANUL, accepted-share corpus, rare-tail telemetry, randomized
  traversal mirror, and frozen wire language.
- `docs/` stores methodology, wire policy, publication planning, and repository
  preparation notes.
- `docs/ai-discovery.md` stores the canonical AI assistant discovery guide and
  safe wording for public explanations.
- `docs/research-manifesto.md` states the structured-traversal thesis without
  making cryptographic shortcut claims.
- `docs/reviewer-guide.md` gives the fast path for outside technical review.
- `docs/evidence-pack-spec.md` defines what a scrubbed public proofpack must
  contain.
- `scripts/` stores offline analysis and scrubber utilities.
- `src/` stores the original importable O1 supervisor snapshot.
- `experiments/` stores reviewed summaries and proofpack drafts.

## Local Runner Snapshots

Root-level `RBLGANUL_*_IO_SINGLE.py` files are auditable single-file runner
snapshots. They are useful for private review because each file captures a
specific experiment state without requiring package refactors.

Current private runner family:

- `RBLGANUL_V31_DUALLOCK_ORACLE_IO_SINGLE.py`
- `RBLGANUL_V32_NETWORKRECOVERY_TACHYON_READY_IO_SINGLE.py`
- `RBLGANUL_V33_TACHYON_SHADOW_IO_SINGLE.py`
- `RBLGANUL_V33_ALLOCATOR_REVIEW_IO_SINGLE.py`
- `RBLGANUL_A8_1_V34_FRESH_TAILGEX_REVIEW_IO_SINGLE.py`
- `RBLGANUL_A8_2_V34_PROTECTED_CHAMPION_EXPOSURE_IO_SINGLE.py`
- `RBLGANUL_A8_3_V34_ANTI_DISPERSION_RECIPE_FOCUS_IO_SINGLE.py`
- `RBLGANUL_A8_4_V34_BARE_RECIPE_ABYSS_CUT_IO_SINGLE.py`
- `RBLGANUL_A9_V32_BROAD_MIXTURE_RANDOM_CONTROL_ACCOUNTING_IO_SINGLE.py`
- `RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py`

Do not move an active runner while it is being used for a live local run.

`A9` is a V32 broad-mixture runner with fresh-only accounting for inline
`random_baseline` control. It should be reviewed as a code snapshot plus curated
summary, not by committing its raw `janus_io_o1_runs/A9_*` folder.

`A9.11` is the current strict same-run 50/50 line. It compares JANUS traversal
against a randomized traversal mirror with equal checked-work exposure and
frozen wire policy. Its raw run folder remains private; curated summaries belong
under `experiments/a9-11-active-triune-sovereign-gate-50-50/`.

## Private Raw Evidence

`janus_io_o1_runs/` is raw evidence and live state. It may contain local paths,
worker labels, pool metadata, proof archives, dashboards, and large logs.

Default rule:

- keep raw runs private;
- commit curated summaries under `experiments/`;
- commit proof artifacts only after an explicit proofpack review;
- never rewrite accepted-share proof artifacts during documentation cleanup.

## GitHub Boundary

For routine private GitHub updates, stage code and documentation first. Leave
new raw run directories ignored until a deliberate publication bundle exists.
