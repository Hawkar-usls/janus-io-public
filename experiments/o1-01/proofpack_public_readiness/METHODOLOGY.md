# Methodology

Janus is evaluated as a proof-oriented lottery mining research framework. The core measurement unit is an accepted proof file, not an inherited dashboard counter.

## Clean Proof Count

Clean IO proof count is the number of accepted proof files matching:

```text
accepted_20*_z*_nonce0x*.json
```

`accepted_index.json` is excluded from this file count.

Dashboard `accepted` may include imported or inherited state. It is useful for operational context, but clean IO accepted count should be derived from accepted proof files.

## Tail Counts

Tail counts are threshold counts over accepted proofs:

- z23+
- z24+
- z25+
- z26+
- z28+
- z30+
- z32+
- z33+
- z34+
- z35+
- z36+
- z37+

The maximum proof archive z is the maximum `zbits` seen across saved accepted proofs. Dashboard `best_z` may reflect a live or rolling session view and can differ from archive max.

## Rate Metrics

When checked-hash data is available, report:

- accepted/MH
- z28+/MH
- z30+/MH
- z32+/MH
- z33+/MH
- z35+/MH
- reject rate

These metrics should be compared only across runs with similar pool difficulty, submit gate, hardware, worker count, and wire policy.

## Interpretation Limits

Single rare events are not sufficient evidence for a scheduler advantage. A z36 proof is valuable corpus evidence, but a public advantage claim requires repeated A/B tests and stable MH-normalized outperformance.

Do not claim SHA-256 weakness. Do not claim guaranteed mining profit.
