# O1-01 Methodology

O1-01 is a sequential-slot benchmark for Janus Io scheduler behavior. Each slot
runs one agent profile, then the next profile runs under the same machine,
network, pool endpoint, and advertised difficulty target.

The comparison target is `A3_JANUS_FULL` against:

- `A0_RANDOM_PURE`
- `A1_LINEAR_PURE`
- `A2_ZIM_ONLY`
- `A4_DUAL_LOCK_TEST`

Use normalization by MH so accepted shares and z-threshold observations are
compared against work performed, not only elapsed wall time. Wall time remains
useful for operational context, but it is not sufficient when hash rate varies.

The primary rates are `accepted_per_MH`, `z24_per_MH`, `z28_per_MH`,
`z30_per_MH`, and `z32_per_MH`. Report `reject_rate`, `hps_mean`, and `hps_std`
alongside those rates so scheduler differences are not confused with throughput
or pool-response artifacts.

P-values require multiple slots per agent because single slots are dominated by
PoW variance, pool timing, network jitter, and hardware scheduling noise. Treat
early O1-01 results as descriptive until each agent has enough repeated slots
for a real statistical comparison.
