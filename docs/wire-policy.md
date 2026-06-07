# Frozen V30 Wire Policy

The V30 mining wire path is frozen for reproducibility. Scheduler experiments
may change traversal policy, task allocation, and analysis, but must not change
accepted V30 wire behavior.

Frozen invariants:

- Canonical Stratum submit nonce is an 8-character big-endian `uint32` hex
  string.
- Header nonce bytes are little-endian.
- `prevhash` uses word-swap32 behavior compatible with accepted shares.
- `extranonce2` is little-endian.
- TruthGate validates the reconstructed pool view before submit.

Do not modify nonce submit format, `prevhash` word-swap behavior,
`extranonce2` endianness, canonical header construction, TruthGate, or accepted
V30 behavior without an explicit wire-policy change request.
