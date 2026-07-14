# A18.42 V0.3.4.4 — Native Flow Gate BEACON snapshot

Status: `BEACON PASS / CALIBRATION RESULT PENDING`

This directory preserves the public-safe architecture, contracts, build validation,
exact source-file hashes and sanitized live result for:

`JANUS_A18_42_UNDINAS_NATIVE_FLOW_GATE_V0_3_4_4_BEACON_TERMINAL_VALIDATION_HOTFIX`

## Live result

- decision: `PASS_NATIVE_BEACON_VALIDATED`
- completed and sealed batches: `4/4`
- epoch 0: `2 admissions -> 2 completions`
- drained two-phase boundary: `PASS`
- REOPEN epoch 1: `2 new admissions -> 2 completions`
- same miner process: `PASS`
- reconnect delta at both boundaries: `0`
- Observer Barrier: `PASS`
- runtime hash validation: `PASS`
- cleanup: `PASS`
- strict local candidate: `true`

## Claim boundary

This is not a confirmed Wave Pump. Matched sham comparison and replication are
still required. Calibration is authorized; four-matrix discovery remains blocked
until calibration review.

## Privacy boundary

The raw report and raw runtime log are not included because they contain local
filesystem paths and operational pool context. Their SHA-256 bindings are stored
in `BEACON_RESULT_SANITIZED.json`.

## Source preservation

`SOURCE_SNAPSHOT_SHA256.json` binds every non-bytecode file in the operator-held
release archive. The binary archive itself is not added by this connector update.
