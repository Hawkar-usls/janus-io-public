# Verify Accepted Proof

This page specifies the verifier expected for the public ProofPack.

## Goal

Given one accepted proof JSON file, reconstruct the submitted candidate enough to verify:

- proof file schema is present;
- header length is 80 bytes;
- double-SHA256 hash matches saved hash fields;
- zbits match the displayed hash;
- target pass is true for the recorded pool/local target;
- submit nonce and header nonce follow documented wire invariants;
- mirror verification is true.

## Verifier Inputs

```text
python scripts/verify_accepted_proof.py path/to/accepted_...json
```

The verifier should not connect to a pool. It should run offline.

## Expected Output

```text
proof: accepted
header_len: 80
hash_match: true
zbits: 36
target_pass: true
wire_invariants: true
```

## Failure Policy

Verifier failures should be explicit and non-destructive. The verifier must not rewrite proof files.
