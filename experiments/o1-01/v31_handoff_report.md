# V31 Handoff Report

Read-only audit timestamp: 2026-05-26.

Scope note: the expected V31 handoff artifacts were not present in the repository root at audit time. The V31 launcher batch file starts `RBLGANUL_V31_DUALLOCK_ORACLE_SINGLE.py` without CLI overrides, so the expected default output paths are the root-level `rblganul_v31_*` files, `session_summary_v31.json`, `proof_dashboard.json`, `session_summary.json`, and `proofs/accepted_index.json`. None of those files existed during this audit.

## V31 live evidence from pasted logs

Update note: the earlier root-only scan is superseded for live evidence. The V31 script is launched from the repository path, but the live run writes relative artifacts under a local Windows user profile. Read-only inspection found the current V31 dashboard, DualLock memory, tail event log, session summary, lab CSV, and proof index there. No miner process was stopped or restarted, and no miner code, wire bytes, proof files, or live state were modified for this update.

V31 selfcheck and import evidence from pasted logs:

- selfcheck sentinel: `RBLGANUL_V31_DUALLOCK_ORACLE_SINGLE_20260526`
- selfcheck script: `RBLGANUL_V31_DUALLOCK_ORACLE_SINGLE.py`
- selfcheck `sha256_16`: `b636ff78e96b31c7`
- imported V30 baseline: `accepted=2027`, `rejected=8`, `submitted=1419`, `best_z=32`
- seeded brain: `rblganul_v30_best_brain.json -> rblganul_v31_best_brain.json`
- seeded stride memory: `rblganul_v30_zim_stride_memory.json -> rblganul_v31_zim_stride_memory.json`
- wire remains frozen to accepted V26/V27/V28/V29/V30 behavior.

Latest read-only dashboard snapshot from the local `rblganul_v31_duallock_dashboard.json` artifact:

| Field | Value |
|---|---:|
| `written_at_utc` | `2026-05-26T01:31:41Z` |
| `accepted` | 2325 |
| `rejected` | 9 |
| `submitted` | 1718 |
| `reject_rate` | 0.005238649592549476 |
| `best_z` | 33 |
| `round` | 1060 |
| `hps_last` | 2,773,990 |
| `hps_ewma` | 2,775,626 |
| `best_hps_ewma` | 2,983,627 |
| `accepted_per_mh` | 0.8068301822143895 |

V31 segment is now measurable against the imported V30 baseline:

| Segment metric | Value |
|---|---:|
| new accepted since import | 298 |
| new submitted since import | 299 |
| new rejected since import | 1 |
| segment reject rate | 0.0033444816053511705 |
| best_z increase | 32 -> 33 |
| accepted proof filenames at or after V31 start | 299 |

Reject note: early pasted lines showed `rejected=8`, while later pasted/file evidence shows one `REJECT total=9` with `error=Stale` during a job turnover. That is not noncewire evidence and does not justify changing nonce submit endian, prevhash mirror, extranonce2, TruthGate, pool target gate, or batch factor.

Live endurance/oracle state:

- `wire_change_required=false`
- `batch_factor=1.35`
- `cooldown=false`
- `last_reason=stable`
- `pruned_replacements=0`
- `sector_lock_hits=101`
- `total_checked=2,881,647,280`

DualLock memory from the local `rblganul_v31_dual_lock_memory.json` artifact at `2026-05-26T01:31:41Z`:

| Lane | Attempts | Accepted | Best z |
|---|---:|---:|---:|
| `linear_s6` | 1,393 | 24 | 30 |
| `zim_reverse_s6` | 1,145 | 24 | 30 |
| `knight_s11` | 817 | 17 | 27 |

Tail counts from accepted proof filenames at or after the V31 start:

| Threshold | Count |
|---|---:|
| z24+ | 142 |
| z25+ | 78 |
| z26+ | 34 |
| z28+ | 14 |
| z29+ | 7 |
| z30+ | 4 |
| z32+ | 1 |
| z33+ | 1 |

Strongest visible V31 proofs:

| z | Nonce | Job | Lane / strategy | Hash |
|---:|---|---|---|---|
| 33 | `5954b8f0` | `6a0a8e4000005a07` | `janus_dispatcher` / `knight/s4` | `000000004bbc6151f79a891411ae611686e332b00ca878cd6ca56bcf44abeecb` |
| 30 | `935caf7e` | `6a0a8e40000059f3` | `dual_lock:linear_s6` / `linear/s6` | `00000003a7a5304c5f9b0fde6c6f66c69bd40ce1fd6fc4bb0627f1199913f7a7` |
| 30 | `8824bc2b` | `6a0a8e40000059f8` | `dual_lock:zim_reverse_s6` / `zim_reverse/s6` | `0000000312cc6aa75b1863d482304c8ee5dd09deff023333b0b8e39a82f91a4f` |
| 30 | `44174661` | `6a0a8e4000005a0b` | `janus_dispatcher` / `linear/s3` | `00000003149a583e7745a90e3d3228e20d404dfde6ee58578aaf80af7e701e4c` |
| 29 | `d185aa3f` | `6a0a8e40000059fd` | pasted proof / accepted proof file | `000000056a110e10faae8cc8f45999cadf50d77b39da4e81ad55a17448bda8d9` |

The requested proof files for `935caf7e`, `8824bc2b`, and `d185aa3f` were present under the local `proofs/` artifact directory; their recorded hash objects report `target_pass=true`.

Decision: **KEEP RUNNING**. No intervention, no wire change, no nonce/endian/prevhash/extranonce2/TruthGate/pool-gate/batch-factor change.

## 1. Imported V30 Baseline

Observable imported baseline from V31 artifacts:

- accepted: 0 observed
- rejected: 0 observed
- submitted: 0 observed
- best_z: 0 observed

Evidence: `rblganul_v31_strategy_rates.json` was missing, and the default V30 import sources `proof_dashboard.json`, `session_summary.json`, and `proofs/accepted_index.json` were also missing in the current working directory.

Nearest raw O1/V30 context, not counted as a V31 import:

| Source | accepted | rejected | submitted | best_z |
|---|---:|---:|---:|---:|
| `janus_io_o1_runs/A3_JANUS_FULL/a3_janus_full_proof_dashboard.json` | 123 | 1 | 124 | 33 |
| `janus_io_o1_runs/A4_DUAL_LOCK_TEST/a4_dual_lock_test_proof_dashboard.json` | 232 | 0 | 232 | 33 |

## 2. Current V31 Totals

Current V31 totals from V31 artifacts:

- accepted: 0 observed
- rejected: 0 observed
- submitted: 0 observed
- best_z: 0 observed

No root-level V31 dashboard, strategy ratebook, session summary, tail event log, dual-lock memory, CSV, or proof index was available.

## 3. V31 Delta Since Import

- new accepted: 0 observed
- new rejected: 0 observed
- reject rate for new V31 segment: 0.0 observed / not measurable
- new best_z: 0 observed

This does not prove the miner was inactive. It only means the expected V31 handoff artifacts were not available in the current working directory.

## 4. DualLock Lane Status

V31 DualLock ratebook/memory artifacts were missing, so no V31 lane attempts were measurable.

| Lane | attempts | accepted | best_z | Status |
|---|---:|---:|---:|---|
| `linear_s6` | 0 observed | 0 observed | 0 observed | No V31 artifact |
| `zim_reverse_s6` | 0 observed | 0 observed | 0 observed | No V31 artifact |
| `knight_s11` | 0 observed | 0 observed | 0 observed | No V31 artifact |

DualLock leader in the V31 segment: unknown.

Raw O1 fallback context, not V31:

| Lane | accepted | best_z | Interpretation |
|---|---:|---:|---|
| `zim_reverse/s6` | 116 | 29 | Accept-count leader in A4 |
| `linear/s6` | 57 | 33 | Tail leader in A4 |
| `knight/s11` | 60 | 29 | Fixed deep-tail probe lane |

## 5. Strategy Scoreboard

No V31 strategy scoreboard was available because `rblganul_v31_strategy_rates.json` was missing.

Raw O1 fallback context:

Top by accepted in A4:

| Strategy | accepted | best_z |
|---|---:|---:|
| `zim_reverse/s6` | 116 | 29 |
| `knight/s11` | 60 | 29 |
| `linear/s6` | 57 | 33 |

Top by best_z in raw O1 context:

| Source | Strategy | best_z |
|---|---|---:|
| A4 | `linear/s6` | 33 |
| A3 live raw evidence | `knight/s11` | 33 |
| A1 | `linear/s7` | 31 |

Top by accepted/MH cannot be computed for the V31 segment without V31 ratebook/check counters. Any early per-lane accepted/MH from a short V31 run should be marked unstable until multiple slots exist.

## 6. Tail Events

V31 tail event file status: `rblganul_v31_tail_events.jsonl` missing.

V31 observed tail counts:

- z24+: 0 observed
- z28+: 0 observed
- z30+: 0 observed
- z32+: 0 observed

Raw O1 fallback z30+ events, not counted as V31:

| Source | z | Strategy | Sector | Nonce | Hash | Job |
|---|---:|---|---:|---|---|---|
| A3 | 30 | `zim_bandit` | 6 | `9486f314` | `00000003911955c56eed806eb612a5efecb5ebfb587eb8f188e5e1f844807682` | `6a0a8e400000592c` |
| A3 | 31 | `linear` | 9 | `cafcdf42` | `00000001be84fe84134ee49760a5466b546fc2abb9cb89a3ff31176dc3b4dd4e` | `6a0a8e4000005939` |
| A3 | 30 | `random` | 9 | `d3c144e2` | `00000003ffb4ddbc1572a043aa511cfeb5c2f0dc883c203ec486c23592403652` | `6a0a8e400000596b` |
| A3 | 31 | `random` | 6 | `8708c3fc` | `00000001cbdaa7e781e363222ac21233f0fe0b05200dc289c5c5c5eb6767f36d` | `6a0a8e400000599f` |
| A3 | 30 | `linear` | 9 | `cddba4a5` | `00000003d095c2906bd87b5f77110fbcc3bac241e257706675af3cc7ee0c5309` | `6a0a8e40000059a7` |
| A3 | 33 | `knight` | 11 | `f98e2e05` | `000000005e5345b806d3537d1b99e752bee39844221e81e88dbc550589559ca8` | `6a0a8e40000059d4` |
| A4 | 33 | `linear` | 6 | `8390586e` | `0000000040645502acbc5b19d4775264d079c1f276958379fd1f26d9ebb300b9` | `6a0a8e40000059c0` |

## 7. HPS / Endurance

No V31 dashboard or CSV was available, so V31 HPS/endurance status is not measurable.

V31 observed:

- hps mean: not available
- hps recent: not available
- hps max/best: not available
- batch_factor: not available
- cooldown status: not available
- `batch_factor=1.35`: cannot be judged from V31 artifacts

Raw O1 fallback context:

| Source | hps mean | hps recent | hps max/best |
|---|---:|---:|---:|
| A3 CSV | 2737669.52 | 2693573 | 3005398 |
| A4 CSV | 2948537.36 | 2952429 | 3038173 |

The O1 fallback suggests the V30/A4 batch level was tolerable in that run, but it does not prove V31 `batch_factor=1.35` is stable because no V31 HPS artifacts were found.

## 8. Safety

- Reject counter after V31 start: no V31 counter was found, so growth cannot be confirmed or denied.
- `wire_change_required`: false.
- Noncewire failure evidence: none found in the expected V31 handoff artifacts. No `rblganul_v31_endurance_mirror_fail.json` artifact was present in the repository root.
- Wire policy should remain frozen. No evidence in this read-only audit justifies changing nonce submit, header nonce bytes, prevhash word-swap32, extranonce2 endian, TruthGate, or Stratum submit format.

## 9. Recommendation

Status: no measurable V31 handoff segment was found in the expected output files.

Recommended action: no wire action and no proof/log movement. If V31 is still running, keep it running, but verify the terminal output or working directory because the expected root-level V31 artifacts are not being written or are being written elsewhere. If V31 is not running, start it again only when ready, with explicit output paths so the handoff files are unambiguous.

```json
{
  "v31_status": "no_v31_handoff_artifacts_found",
  "wire_change_required": false,
  "new_accepts_since_import": 0,
  "new_rejects_since_import": 0,
  "new_best_z_since_import": 0,
  "dual_lock_leader": "unknown",
  "keep_running": true,
  "recommended_action": "No wire changes. Keep V31 running if it is active, but verify the terminal output or working directory because expected V31 artifacts were not found."
}
```
