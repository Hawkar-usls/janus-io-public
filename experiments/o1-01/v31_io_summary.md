# V31 IO Summary

Generated: 2026-05-27T15:06:19+00:00
Input root: `janus_io_o1_runs\A5_V31_AFTER_V30_IMPORT`

## Main status

| Metric | Value |
|---|---:|
| Accepted | 15327 |
| Rejected | 39 |
| Submitted | 14369 |
| Reject rate total | 0.002714176351868606 |
| Best z | 33 |
| Clean IO accepted/proof files | 12919 |
| HPS last | 2645224 |
| HPS EWMA | 2519766 |
| Best HPS EWMA | 2891812 |
| Accepted/MH | 10.938487047335475 |
| Round | 570 |
| Uptime seconds | 827.0539903640747 |
| Written UTC | 2026-05-27T15:06:15Z |

## Clean IO-run interpretation

Do not treat dashboard `accepted - imported_accepted` as pure new IO accepted. The dashboard accepted counter is inherited/imported state. The clean IO-run accepted/proof count is the number of accepted proof files in this IO output directory.

| Metric | Value |
|---|---:|
| Imported accepted | 2027 |
| Imported rejected | 8 |
| Imported submitted | 1419 |
| Imported best z | 32 |
| Clean IO accepted/proofs | 12919 |
| Clean IO/dashboard best z | 33 |
| Dashboard accepted minus import | 13300 |
| Dashboard rejected minus import | 31 |
| Dashboard submitted minus import | 12950 |
| Reject/proof hint | 0.002400 |

## Endurance

| Field | Value |
|---|---:|
| Cooldown | False |
| Cooldown rounds left | 0 |
| Batch factor | 1.0744386561490502 |
| Last reason | stable |
| Pruned replacements | 60 |
| Sector lock hits | 107 |
| Total checked | 1401199264 |

## ProofMind

| Field | Value |
|---|---:|
| Mode | HUNT |
| Mode strength | 0.985 |
| Hunger | 0.025872678676926088 |
| Elite | 468 |
| Bad | 13 |
| Best z seen | 36 |
| Best combo | `linear/s5/canonical/a-1` |

## Wire lock

| Invariant | Value |
|---|---:|
| nonce submit big-endian uint32 hex | True |
| nonce header little-endian bytes | True |
| prevhash word reverse | True |
| extranonce2 little-endian | True |
| wire change required | False |

## DualLock memory



| Lane | Attempts/Observations | Accepted | Best z | Source |
|---|---:|---:|---:|---|
| `linear_s6` | 50460 | 1069 | 31 | `dual_lock_memory` |
| `zim_reverse_s6` | 43971 | 899 | 32 | `dual_lock_memory` |
| `knight_s11` | 31684 | 679 | 34 | `dual_lock_memory` |

## Top strategy scoreboard

| Strategy | Accepted | Best z | Observations | Last HPS |
|---|---:|---:|---:|---:|
| `zim_reverse/s6/canonical` | 40 | 28 | 2113 | 160220 |
| `linear/s6/canonical` | 17 | 28 | 1455 | 161122 |
| `linear/s0/canonical` | 15 | 27 | 729 | 163469 |
| `knight/s11/canonical` | 14 | 29 | 896 | 163332 |
| `linear/s7/canonical` | 10 | 27 | 257 | 157688 |
| `linear/s3/canonical` | 9 | 33 | 694 | 165938 |
| `linear/s9/canonical` | 7 | 26 | 273 | 159497 |
| `linear/s4/canonical` | 6 | 27 | 243 | 157046 |
| `linear/s10/canonical` | 6 | 26 | 237 | 158824 |
| `linear/s1/canonical` | 6 | 24 | 254 | 165954 |

## Tail counts from proof filenames

| Threshold | Count |
|---|---:|
| z24+ | 6516 |
| z25+ | 3338 |
| z26+ | 1693 |
| z28+ | 408 |
| z30+ | 91 |
| z32+ | 24 |
| z33+ | 16 |

## Latest proofs

| Modified | File |
|---|---|
| 2026-05-27T18:06:11 | `accepted_2026-05-27_15-06-11_z24_nonce0x8f2d969c_job6a16078a0000088e.json` |
| 2026-05-27T18:06:05 | `accepted_2026-05-27_15-06-05_z23_nonce0x7ef43ce3_job6a16078a0000088e.json` |
| 2026-05-27T18:05:55 | `accepted_2026-05-27_15-05-55_z23_nonce0x8d266b93_job6a16078a0000088e.json` |
| 2026-05-27T18:05:50 | `accepted_2026-05-27_15-05-50_z25_nonce0x043f436e_job6a16078a0000088e.json` |
| 2026-05-27T18:05:41 | `accepted_2026-05-27_15-05-41_z26_nonce0x8dde901f_job6a16078a0000088d.json` |
| 2026-05-27T18:05:39 | `accepted_2026-05-27_15-05-39_z23_nonce0x8af82a79_job6a16078a0000088d.json` |
| 2026-05-27T18:05:37 | `accepted_2026-05-27_15-05-37_z27_nonce0x0d0fd85a_job6a16078a0000088d.json` |
| 2026-05-27T18:05:34 | `accepted_2026-05-27_15-05-34_z23_nonce0x8c3c149a_job6a16078a0000088d.json` |
| 2026-05-27T18:05:30 | `accepted_2026-05-27_15-05-30_z23_nonce0x88c5e555_job6a16078a0000088d.json` |
| 2026-05-27T18:05:26 | `accepted_2026-05-27_15-05-26_z23_nonce0x8a597365_job6a16078a0000088d.json` |
| 2026-05-27T18:05:23 | `accepted_2026-05-27_15-05-23_z23_nonce0xf59539de_job6a16078a0000088d.json` |
| 2026-05-27T18:05:21 | `accepted_2026-05-27_15-05-21_z23_nonce0xfd071ea7_job6a16078a0000088c.json` |
| 2026-05-27T18:05:06 | `accepted_2026-05-27_15-05-06_z23_nonce0xfb3eaf03_job6a16078a0000088c.json` |
| 2026-05-27T18:05:03 | `accepted_2026-05-27_15-05-03_z24_nonce0xc06db92a_job6a16078a0000088c.json` |
| 2026-05-27T18:04:44 | `accepted_2026-05-27_15-04-44_z23_nonce0x8f9b0668_job6a16078a0000088c.json` |

## Decision

`KEEP RUNNING` if accepted grows and rejected does not grow fast. Wire remains frozen.
