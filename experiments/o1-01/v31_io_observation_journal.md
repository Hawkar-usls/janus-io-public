# V31 IO Observation Journal

Read-only lab notes for the live V31 IO run. This journal only records observations derived from analyzer output and live dashboards; it must not be used to modify miner code, wire logic, proof files, dashboards, session state, memory files, or GitHub history.

## 2026-05-26T12:30:50Z

Source: `python scripts\analyze_v31_io.py` followed by `Get-Content experiments\o1-01\v31_io_summary.md`.

Status snapshot:

| Metric | Value |
|---|---:|
| clean IO proof files | 1,352 |
| dashboard accepted total | 3,760 |
| dashboard rejected total | 14 |
| dashboard submitted total | 2,777 |
| total reject rate | 0.005041411595246669 |
| reject/proof hint | 0.004438 |
| best_z | 32 |
| hps_last | 2,950,792 |
| hps_ewma | 2,869,521 |
| best_hps_ewma | 3,075,745 |
| batch_factor | 1.35 |
| cooldown | false |
| cooldown_rounds_left | 0 |
| wire_change_required | false |
| total_checked | 7,610,269,024 |

Tail counts:

| Threshold | Count |
|---|---:|
| z24+ | 691 |
| z25+ | 378 |
| z26+ | 176 |
| z28+ | 36 |
| z30+ | 6 |
| z32+ | 1 |
| z33+ | 0 |

DualLock lane view:

| Lane | Attempts/Observations | Accepted | Best z | Source |
|---|---:|---:|---:|---|
| `linear_s6` | 5,069 | 115 | 28 | `dual_lock_memory` |
| `zim_reverse_s6` | 4,482 | 91 | 30 | `dual_lock_memory` |
| `knight_s11` | 3,155 | 75 | 29 | `dual_lock_memory` |

Top strategy scoreboard:

| Strategy | Accepted | Best z | Observations |
|---|---:|---:|---:|
| `zim_reverse/s6/canonical` | 195 | 31 | 9,936 |
| `linear/s6/canonical` | 162 | 32 | 7,081 |
| `knight/s11/canonical` | 98 | 29 | 4,366 |
| `linear/s0/canonical` | 85 | 31 | 3,708 |
| `linear/s3/canonical` | 67 | 31 | 3,567 |

Observation:

- Clean IO output is alive: proof count grew from the recent 1,292 monitor snapshot to 1,352.
- Rejected stayed at 14 over the same window, so rejected is not growing faster than proof output.
- `best_z=32` holds, with one clean IO z32+ proof and six z30+ proofs.
- `wire_change_required=false`; wire remains frozen.
- `cooldown=false`; no sustained reject-spike response is active.
- HPS remains normal for this run, around 2.87 MH/s EWMA.

Decision: **KEEP RUNNING**. No miner patch, no wire/proof/live-state touch, no GitHub action.
