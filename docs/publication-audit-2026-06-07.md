# Publication Audit 2026-06-07

Status: curated publication bundle committed and pushed; public visibility is
blocked by historical raw evidence in Git history.

This audit prepares the repository for a future public GitHub update without
touching the miner, changing the frozen wire, rewriting proof artifacts, or
mixing live run state into curated publication material.

## Checks Already Run

```powershell
python scripts\scrub_secrets.py --limit 120 README.md CHANGELOG.md docs experiments scripts llms.txt *.py *.ps1 *.bat
python -m py_compile <all root RBLGANUL*.py files and scripts/*.py>
```

Result:

- targeted curated scrub: `findings=0`;
- Python syntax checks: passed;
- full-tree scrub was not used as a publication signal because the raw proof
  corpus is intentionally large and should not be scanned as a public staging
  set.

## Current Git Risk Summary

Tracked raw evidence already exists in the repository:

```text
tracked janus_io_o1_runs files: 3759
tracked proof files: 3725
tracked log/jsonl/raw-log files: 11
```

Breakdown:

```text
A3_JANUS_FULL: 1724
A1_LINEAR_PURE: 1069
A0_RANDOM_PURE: 750
A2_ZIM_ONLY: 213
o1_report.md/json and o1_events.jsonl: 3
```

This is the main public-release risk. The next publication commit should not
stage dirty `janus_io_o1_runs/` files. Before opening the repository broadly,
choose one policy:

- keep historical tracked A0-A3 raw evidence visible and publish a clear
  disclaimer; or
- remove tracked raw evidence from the current public tree with a separate
  reviewed cleanup commit while preserving the private local archive.

Do not rewrite Git history unless explicitly chosen as a separate release
operation.

Post-push raw-history scrub:

```text
tracked_raw_scrub findings: 9031
finding classes: local Windows paths, wallet/worker labels
example affected area: janus_io_o1_runs/A0_RANDOM_PURE and proof archives
```

The curated publication commit intentionally excludes dirty/live
`janus_io_o1_runs/` files, but the repository cannot be made public safely while
historical tracked raw evidence remains in reachable Git history. A normal
delete commit would clean the current tree but would not remove old raw evidence
from public history.

## Ignore And Attribute Status

Current protections:

- `janus_io_o1_runs/**/proofs/` is ignored for new files;
- raw logs and A4-A10 live run folders are ignored;
- `experiments/**/proofs/*` is ignored except
  `experiments/o1-01/proofs/README.md`;
- generated `output/` is ignored;
- `.gitattributes` marks raw evidence as generated for GitHub language stats.

This prevents accidental staging of the current A9/A10 raw corpus, but it does
not hide already tracked A0-A3 evidence.

## Candidate Public Stage Set

Safe to stage after the 7000 gate update and one final scrub:

```text
.gitattributes
.gitignore
README.md
llms.txt
docs/*.md
experiments/README.md
experiments/a9-11-active-triune-sovereign-gate-50-50/README.md
experiments/a9-11-active-triune-sovereign-gate-50-50/snapshot-2026-06-07-7000.md
experiments/a9-9-kombucha-cell-microkernel-observer/*.md
experiments/a9-v32-broad-mixture-random-control/README.md
experiments/o1-01/*.md
experiments/o1-01/o1_analysis_summary.md
experiments/o1-01/o1_analysis_summary.json
experiments/o1-01/proofpack_public_readiness/*.md
scripts/*.py
scripts/README.md
RBLGANUL_*.py
```

Stage only after reviewing the final `git diff --cached`. Keep these out of the
normal publication commit:

```text
janus_io_o1_runs/
output/
ST.txt
statCM.txt
Yaksa .bat
JANUS_*_MONITOR*.ps1
MONITOR_*.ps1
CHECK_*.ps1
CODEX_*_AUDIT.md
CODEX_A9_PRE_PHANTOM_SNAPSHOT.md
JANUS_POOLDAY_OMNIOBSERVER_METRICS_PLAN.md
V32_FRESH_EVIDENCE_PACK_AFTER_A8.md
```

Root `CODEX_*.md`, monitor scripts, and pack notes may be useful internally,
but they should stay deferred until separately scrubbed for public narrative
quality and operational detail.

## A9.11 7000-Gate Tasks

Gate status: reached at the local read-only check on 2026-06-07. The curated
publication snapshot now uses:

```text
snapshot_written_at_utc: 2026-06-07T10:05:38Z
fresh accepted-share corpus: 7016
JANUS best_z: 36
randomized traversal mirror best_z: 33
frozen wire: wire_change_required=False
```

Final assembly tasks:

1. Generate a public-safe A9.11 snapshot:

   ```powershell
   python scripts\summarize_a9_11_public_snapshot.py --format markdown
   ```

2. Update:

   ```text
   docs/a9-11-active-triune-sovereign-gate-50-50.md
   experiments/a9-11-active-triune-sovereign-gate-50-50/README.md
   ```

3. Include only summarized values:

   - fresh accepted-share corpus count;
   - JANUS vs randomized traversal mirror accepted counts;
   - best_z and z30+/z32+/z33+/z34+/z35+/z36+/z37+/z38+ tails;
   - reject rate, HPS, cooldown, phase/reason;
   - frozen wire status;
   - WitchHunter dark-tail summary;
   - claim boundary: no SHA-256 break, no nonce-prediction claim.

4. Rerun:

   ```powershell
   python scripts\scrub_secrets.py --limit 120 README.md CHANGELOG.md docs experiments scripts llms.txt *.py *.ps1 *.bat
   python -m py_compile <all staged Python files>
   git diff --check
   git status --short --ignored
   ```

5. Stage curated paths only. Do not stage `janus_io_o1_runs/`.

Completion status:

```text
curated commit: e06f43a Prepare Janus I0 publication bundle
push target: origin/main
push status: completed
repository visibility: still private
```

## Current Verdict

The curated publication bundle is pushed, but the repository is not ready to
open broadly. The remaining blockers are:

- tracked historical raw evidence contains scrub findings and must not be
  exposed accidentally;
- public release needs either an explicit decision to accept historical raw
  exposure, a reviewed history-clean release operation, or a separate clean
  public repository/export;
- repository visibility has not been changed.
