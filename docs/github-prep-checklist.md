# GitHub Prep Checklist

Use this checklist before updating the private GitHub repository.

## Keep Private By Default

- `janus_io_o1_runs/A4_*/` through `janus_io_o1_runs/A9_*/`
- `janus_io_o1_runs/tail_reports/`
- raw `proofs/` archives
- live dashboards, lockboxes, lab CSV files, and tail event streams
- local scratch notes such as `ST.txt` and `statCM.txt`

## Candidate Files For Normal Staging

- root-level runner snapshots after syntax checks
- `docs/*.md`
- `scripts/*.py`
- curated summaries under `experiments/`
- publication/proofpack draft docs after scrub review
- A9 methodology notes under `experiments/a9-v32-broad-mixture-random-control/`
  after they contain only summarized metrics, not raw proof dumps
- A9.11 methodology and evidence drafts after scrub review:
  - `docs/a9-11-active-triune-sovereign-gate-50-50.md`
  - `docs/reviewer-guide.md`
  - `docs/evidence-pack-spec.md`
  - `experiments/a9-11-active-triune-sovereign-gate-50-50/README.md`
  - curated A9.11 proofpack manifests and summaries
- A9.9 curated docs under
  `experiments/a9-9-kombucha-cell-microkernel-observer/`
- `docs/a9-9-kombucha-cell-microkernel-observer.md`
- extraordinary-ability evidence organizer:
  - `docs/extraordinary-ability-evidence-map.md`
- A9.9 runner snapshot only after local worker defaults are redacted or moved
  behind explicit launch arguments; the curated A9.9 docs can be staged first

## Required Local Checks

```powershell
python scripts\scrub_secrets.py --limit 120 README.md CHANGELOG.md docs experiments scripts llms.txt *.py *.ps1 *.bat
python -m py_compile `
  .\RBLGANUL_V31_DUALLOCK_ORACLE_IO_SINGLE.py `
  .\RBLGANUL_V32_NETWORKRECOVERY_TACHYON_READY_IO_SINGLE.py `
  .\RBLGANUL_V33_TACHYON_SHADOW_IO_SINGLE.py `
  .\RBLGANUL_V33_ALLOCATOR_REVIEW_IO_SINGLE.py `
  .\RBLGANUL_A8_1_V34_FRESH_TAILGEX_REVIEW_IO_SINGLE.py `
  .\RBLGANUL_A8_2_V34_PROTECTED_CHAMPION_EXPOSURE_IO_SINGLE.py `
  .\RBLGANUL_A8_3_V34_ANTI_DISPERSION_RECIPE_FOCUS_IO_SINGLE.py `
  .\RBLGANUL_A8_4_V34_BARE_RECIPE_ABYSS_CUT_IO_SINGLE.py `
  .\RBLGANUL_A9_V32_BROAD_MIXTURE_RANDOM_CONTROL_ACCOUNTING_IO_SINGLE.py `
  .\RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py
git status --short --ignored
```

The scrubber is expected to flag raw run artifacts and local identifiers when
run over the entire repository. For publication staging, scan the curated paths
above and keep raw `janus_io_o1_runs/` evidence out of the normal commit.

See `docs/publication-audit-2026-06-07.md` for the current pre-7000 audit
status, staged-path policy, and remaining blockers.

## Do Not Do During Prep

- do not run the miner;
- do not change frozen wire behavior;
- do not enable allocator behavior just for a repo update;
- do not rewrite raw accepted-share proof files;
- do not mix generated reports into raw log folders.
- do not publish cryptographic break claims; phrase JANUS as structured
  traversal and rare-tail telemetry research.
