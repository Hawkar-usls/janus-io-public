# Rblganul / Janus V31 IO Full Project Audit For ChatGPT

Report timestamp: 2026-05-26T12:55:51Z.

This report is a read-only project audit and lab analysis of the live V31 IO mining experiment. It intentionally avoids private absolute paths, secrets, worker labels, account identifiers, and raw credential values. Paths are repo-relative. The running miner, wire logic, proofs, live dashboards, session state, and GitHub state were not modified.

## Executive Verdict

V31 IO is live, productive, and currently healthy. The clean IO-run evidence is the accepted proof file count, not `accepted - imported_accepted`, because dashboard accepted/rejected/submitted counters include inherited V30 state. As of the latest analyzer snapshot, V31 IO has:

| Metric | Value |
|---|---:|
| clean IO accepted proof files | 1,757 |
| dashboard accepted total | 4,162 |
| dashboard rejected total | 14 |
| dashboard submitted total | 3,179 |
| total reject rate | 0.004403900597672224 |
| reject/proof hint | 0.003415 |
| best_z | 32 |
| hps_ewma | 2,890,343 |
| best_hps_ewma | 3,075,745 |
| batch_factor | 1.35 |
| cooldown | false |
| wire_change_required | false |

Decision: **KEEP RUNNING**.

Public upload decision: **not safe yet**. The run is still live, the worktree contains untracked live artifacts and modified raw evidence, and targeted scrubber checks still find local-path and wallet/worker-like identifiers. Prepare a clean, reviewed, redacted patch after the run.

## Scope And Evidence Sources

Primary live run directory: `janus_io_o1_runs/A5_V31_AFTER_V30_IMPORT`.

Commands run first:

```powershell
python scripts\analyze_v31_io.py
Get-Content experiments\o1-01\v31_io_summary.md
```

Additional read-only audit checks included:

- `git status --short`
- `.gitignore` review
- repo file listing via `rg --files`
- live artifact directory listing
- targeted scrubber dry-run with no finding samples printed
- source hash checks for the IO miner script and analyzer
- read-only source search for the known `DualLockMemory.save(force=True)` wart

Generated audit outputs:

- `experiments/o1-01/rblganul_full_project_audit_for_chatgpt.md`
- `experiments/o1-01/rblganul_full_project_audit_for_chatgpt.json`

## What Has Already Been Achieved

1. V31 IO output path is working.
   The run is writing into `janus_io_o1_runs/A5_V31_AFTER_V30_IMPORT`, including dashboard, session summary, strategy rates, DualLock memory, CSV lab telemetry, and accepted proof files.

2. Clean IO proof production is strong.
   Clean accepted proof files reached 1,757 at the report snapshot and continued to grow during observation windows.

3. High-tail evidence exists.
   The clean IO proof filename tail counters show sustained z24-z30 production and one z32+ proof.

4. Wire policy is still frozen.
   The analyzer reports canonical wire invariants as true and `wire_change_required=false`.

5. Reject behavior is controlled.
   Dashboard total reject rate is about 0.44%; the clean reject/proof hint is about 0.34%. Rejected is not growing faster than proofs.

6. DualLock lanes are active.
   DualLock memory and top strategy scoreboard both show the intended `linear/s6`, `zim_reverse/s6`, and `knight/s11` lanes producing accepted shares and tails.

7. Analyzer interpretation has been corrected.
   `scripts/analyze_v31_io.py` now treats proof file count as clean IO-run accepted/proof count, excludes `accepted_index.json`, keeps imported counters as inherited diagnostics, stabilizes tail thresholds, and falls back from DualLock memory to `top_strategy_scoreboard` if lane memory is zeroed or schema-mismatched.

## Current Metrics

Analyzer snapshot: `experiments/o1-01/v31_io_summary.md`, generated at 2026-05-26T12:55:51Z from dashboard written at 2026-05-26T12:55:46Z.

| Category | Metric | Value |
|---|---|---:|
| dashboard | accepted | 4,162 |
| dashboard | rejected | 14 |
| dashboard | submitted | 3,179 |
| dashboard | total reject rate | 0.004403900597672224 |
| clean IO | accepted proofs | 1,757 |
| clean IO | best_z | 32 |
| clean IO | dashboard accepted minus imported accepted | 2,135 |
| clean IO | dashboard rejected minus imported rejected | 6 |
| clean IO | dashboard submitted minus imported submitted | 1,760 |
| clean IO | reject/proof hint | 0.003415 |
| performance | hps_last | 2,873,847 |
| performance | hps_ewma | 2,890,343 |
| performance | best_hps_ewma | 3,075,745 |
| endurance | batch_factor | 1.35 |
| endurance | cooldown | false |
| endurance | cooldown_rounds_left | 0 |
| endurance | sector_lock_hits | 509 |
| endurance | total_checked | 10,724,980,064 |
| wire | wire_change_required | false |

Imported V30 baseline used only as inherited context:

| Metric | Value |
|---|---:|
| imported accepted | 2,027 |
| imported rejected | 8 |
| imported submitted | 1,419 |
| imported best_z | 32 |

Interpretation: `accepted - imported_accepted` is not clean IO accepted. It is only a diagnostic inherited-counter delta. Clean IO accepted equals accepted proof files in the A5 proof directory.

## Tail Evidence

Tail counts from accepted proof filenames:

| Threshold | Count |
|---|---:|
| z24+ | 912 |
| z25+ | 491 |
| z26+ | 233 |
| z28+ | 50 |
| z30+ | 10 |
| z32+ | 1 |
| z33+ | 0 |

Observed exact z distribution during the audit window showed proof files across z23-z32, including one z32 proof. This is accepted-share proof telemetry, not evidence of a SHA-256 shortcut or block discovery.

## DualLock Evidence

DualLock memory:

| Lane | Attempts/Observations | Accepted | Best z | Source |
|---|---:|---:|---:|---|
| `linear_s6` | 6,461 | 146 | 29 | `dual_lock_memory` |
| `zim_reverse_s6` | 5,726 | 109 | 30 | `dual_lock_memory` |
| `knight_s11` | 4,038 | 98 | 29 | `dual_lock_memory` |

Top strategy scoreboard:

| Strategy | Accepted | Best z | Observations |
|---|---:|---:|---:|
| `zim_reverse/s6/canonical` | 280 | 31 | 13,937 |
| `linear/s6/canonical` | 222 | 32 | 9,959 |
| `knight/s11/canonical` | 142 | 31 | 6,151 |
| `linear/s0/canonical` | 116 | 31 | 5,217 |
| `linear/s3/canonical` | 107 | 31 | 5,104 |

Interpretation: DualLock lanes are active and productive. The scoreboard currently gives stronger strategy-level evidence than lane memory alone because scoreboard acceptance totals aggregate by strategy/cfg key.

## Wire And Safety Evidence

The live analyzer reports these wire invariants:

| Invariant | Value |
|---|---:|
| nonce submit big-endian uint32 hex | true |
| nonce header little-endian bytes | true |
| prevhash word reverse | true |
| extranonce2 little-endian | true |
| wire_change_required | false |

Existing docs also state the frozen V30 wire policy: scheduler experiments may change traversal policy, task allocation, and analysis, but must not change accepted V30 wire behavior. V31 IO remains inside that policy from observed evidence.

## Code And Tooling Snapshot

Source files relevant to the later clean patch:

| File | SHA-256 |
|---|---|
| `RBLGANUL_V31_DUALLOCK_ORACLE_IO_SINGLE.py` | `31676D6FE1D6D04D31684462753E12F6433DFC431924AF5E4BBC930341AC7B9A` |
| `scripts/analyze_v31_io.py` | `4CF8EEA309DC779BD89D2AECEAD0D5C78B50D205F775D73ABBFA8CDC2BA8038F` |

Notable code facts from read-only search:

- IO miner script sentinel: `RBLGANUL_V31_DUALLOCK_ORACLE_IO_SINGLE_20260526_IOPATH`.
- IO miner script version: `Rblganul V31 DualLock Oracle IO SINGLE 20260526_IOPATH`.
- Known non-fatal wart queued for post-run cleanup: `DualLockMemory.save()` accepts no `force` parameter, but the IO script has a `V31_DUALLOCK_MEMORY.save(force=True)` call site. Do not patch during the live run.
- Analyzer line count is about 275 lines and includes the corrected clean-proof interpretation and DualLock scoreboard fallback.

## What Is Still Unproven

1. No Proof-of-Work break is proven.
   z-bit tails and accepted shares are rare-event telemetry, not cryptographic shortcut evidence.

2. No mainnet block discovery is proven.
   The evidence is accepted shares at pool target, not a found Bitcoin block.

3. Statistical advantage is not yet proven.
   Current V31 IO evidence is productive, but it still needs longer controlled comparisons against random and fixed baselines using normalized MH, confidence intervals, and rejection-adjusted rates.

4. Third-party reproducibility is not proven.
   Public reproduction requires a clean runner, redacted configuration, documented environment, and reproducible analysis commands.

5. Publication readiness is not proven.
   The worktree still contains raw and live artifacts plus scrubber findings. Public upload must wait for cleanup.

6. Long-run endurance is still in progress.
   `cooldown=false`, `wire_change_required=false`, and low reject rates are good, but the run should continue to collect a longer segment.

## GitHub / Public Release Risk

Current worktree state is not publication-clean.

Read-only `git status --short` showed:

- modified launcher and historical raw O1 artifacts;
- untracked V31 scripts and analyzer;
- untracked A4/A5 run directories;
- untracked live reports under `experiments/o1-01/`;
- untracked local file `statCM.txt`.

`.gitignore` currently excludes:

- `janus_io_o1_runs/**/*.log`
- `janus_io_o1_runs/**/raw_log.txt`
- `janus_io_o1_runs/**/proofs/`
- `experiments/**/logs/`
- `experiments/**/proofs/*`
- common Python/cache/secret file patterns.

However, `.gitignore` does not currently exclude all live JSON/CSV/state files such as A5 dashboards, session summaries, lockboxes, memory files, strategy rates, lab CSVs, and tail event logs. Those showed up as untracked artifacts and must not be committed accidentally.

Targeted scrubber dry-run, with finding samples suppressed, found:

| Rule | Count | Location category |
|---|---:|---|
| `windows_path` | 4 | prior handoff/report text |
| `wallet_or_worker` | 4 | V31 script defaults / worker-like labels |

Security notes already warn that raw artifacts may contain wallet-like worker labels, local paths, pool/job metadata, and proof metadata. Public docs should use placeholders and summaries rather than raw local paths or worker labels.

## Required Cleanup Before GitHub

Do these only after the live run is no longer at risk, and do not commit raw live artifacts.

1. Review and sanitize source defaults.
   Replace worker-like labels, pool credentials, local paths, and operational identifiers with placeholders or environment-driven config.

2. Fix the post-run DualLock memory wart.
   Change the `DualLockMemory.save()` signature or call site so `save(force=True)` is valid. Verify without touching wire behavior.

3. Decide the exact clean patch scope.
   Allowed later patch candidates:
   - `RBLGANUL_V31_DUALLOCK_ORACLE_IO_SINGLE.py`
   - `scripts/analyze_v31_io.py`
   - sanitized docs/report summary under `experiments/o1-01/`

4. Exclude or remove live artifacts from staging.
   Do not commit:
   - `janus_io_o1_runs/A5_V31_AFTER_V30_IMPORT/proofs/`
   - `accepted_index.json`
   - live dashboards
   - session summaries
   - lockboxes
   - strategy/memory files
   - lab CSVs
   - tail event logs
   - raw logs
   - stale-drop/last-accepted/last-candidate/last-reject files

5. Run scrubber checks.
   Use the existing scrubber before any public action. Review any `.redacted` copies manually; do not assume automated redaction is enough.

6. Verify `git status --short`.
   Only intended source/analyzer/docs files should appear staged. No proofs, live dashboards, raw logs, session state, memory files, lockboxes, local launchers, private paths, or worker labels.

7. Keep wire policy frozen.
   Any code cleanup must not change nonce submit format, header nonce bytes, prevhash word behavior, extranonce2 endianness, canonical header construction, TruthGate, or pool target gate.

## When It Is Safe To Upload Or Open Publicly

The repository can be considered for public upload only when all of these are true:

- the live miner is not dependent on the files being cleaned;
- no running process is writing to the tree selected for publication;
- `wire_change_required=false` remains true in the final run evidence;
- a clean summary exists that uses proof counts correctly;
- raw proof archives and live dashboards/session/memory files are excluded;
- scrubber findings are resolved or explicitly accepted as non-sensitive after manual review;
- all private paths, worker labels, passwords, API keys, private account info, and local launch details are removed or replaced with placeholders;
- `git status --short` shows only the intended clean patch files;
- the README/public docs clearly state that this is scheduler telemetry and not a PoW break;
- the publication bundle has been reviewed from a fresh clone or export.

Current decision: **not safe to publish yet**.

## Recommended Next Steps

1. Continue read-only monitoring while V31 IO is healthy.
2. Append lab observations periodically under `experiments/o1-01/`.
3. Do not patch miner code during the live run.
4. After a longer V31 segment, freeze a summary snapshot and prepare a minimal patch.
5. Run cleanup and scrubber review before any GitHub action.

Current operating recommendation: **KEEP RUNNING**.
