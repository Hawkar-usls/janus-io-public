# O1-01 Analysis Summary

Generated: 2026-05-26T01:41:17Z
Input root: `janus_io_o1_runs`

| Agent | Accepted | Rejected | Best z | MH | accepted/MH | z24/MH | z28/MH | z30/MH | z32/MH | reject rate | hps mean | hps std |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A0_RANDOM_PURE | 185 | 0 | 30 | 1824.681 | 0.101388 | 0.268540 | 0.130982 | 0.045487 | 0.000000 | 0.000000 | 2309577.34 | 175564.22 |
| A1_LINEAR_PURE | 265 | 0 | 31 | 2266.523 | 0.116919 | 0.283694 | 0.158834 | 0.132803 | 0.000000 | 0.000000 | 2960103.49 | 94995.96 |
| A2_ZIM_ONLY | 178 | 4 | 29 | 1813.394 | 0.098158 | 0.259182 | 0.095953 | 0.000000 | 0.000000 | 0.021978 | 2539475.86 | 127455.22 |
| A3_JANUS_FULL | 766 | 2 | 33 | 7082.614 | 0.108152 | 0.276452 | 0.160675 | 0.121989 | 0.024144 | 0.009346 | 2737162.75 | 164707.31 |
| A4_DUAL_LOCK_TEST | 233 | 0 | 33 | 2236.885 | 0.104163 | 0.259736 | 0.183291 | 0.089410 | 0.089410 | 0.000000 | 2947540.22 | 92176.64 |

Rates are normalized by observed or estimated MH. z-threshold rates use best-z samples from lab CSV/log telemetry when available, falling back to accepted proof zbits.
