# Security and responsible disclosure

JANUS I0 is experimental research software. Public repository content should be
safe to review offline and should not expose operational mining credentials or
private infrastructure.

## Report privately

Use a private channel to report:

- pool credentials, worker identifiers, tokens, private keys, or private
  endpoints committed to the repository;
- a path traversal, unsafe cleanup, command injection, or arbitrary file-write
  issue;
- a way to bypass runtime identity checks or evidence-chain validation;
- an instrumentation change that silently alters hashing, nonce traversal,
  verification, wire, or submit semantics;
- a reproducible cryptographic weakness that could affect real systems.

Do not include working secrets in a public issue. Revoke exposed credentials
before discussing remediation publicly.

## Cryptographic findings

A possible SHA-256 or protocol weakness must not be tested covertly against a
public pool or deployed for advantage. Preserve evidence, reproduce it in an
offline or reduced environment, separate implementation bugs from primitive
behavior, and use responsible disclosure to affected maintainers.

## Public issues are appropriate for

- documentation errors;
- broken offline analysis commands;
- schema inconsistencies in already-sanitized artifacts;
- reproducibility questions that do not expose private operational data;
- requests for clearer claim boundaries.

## Supported security properties

The project may provide:

- expected-file digest checks;
- deterministic instrumentation manifests;
- linked evidence records;
- privacy-pattern scans;
- guarded temporary-directory cleanup;
- fail-closed decisions when required evidence is missing.

These controls reduce risk but are not a complete sandbox, formal verification,
legal chain of custody, or production security certification.

## Disclosure boundary

A hash-chain pass means the preserved committed sequence is internally
consistent relative to its chain contract. It does not independently establish
source truth, clock correctness, acquisition completeness, or operator honesty.
