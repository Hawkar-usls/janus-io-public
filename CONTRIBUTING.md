# Contributing to JANUS I0

JANUS welcomes documentation, analysis, reproducibility, validation, and
measurement-infrastructure contributions. Changes that affect hashing, proof
verification, scheduling, wire behavior, or live submission require a narrower
review than ordinary repository maintenance.

## Before opening a change

1. Read `README.md` and `docs/current-engineering-capabilities.md`.
2. Preserve the distinction between facts, derived metrics, and claims.
3. Keep missing data as unknown; never silently convert unavailable evidence to
   zero.
4. Do not publish credentials, private endpoints, wallet-like labels, local user
   paths, raw pool payloads, or unsanitized live logs.
5. State whether a change is offline-only, observer-only, shadow-only, or live.

## Change classes

### Documentation and public-safe analysis

Suitable for normal pull requests when they:

- use sanitized artifacts;
- preserve claim boundaries;
- identify source reports and calculation methods;
- report negative and inconclusive results honestly.

### Observer and instrumentation changes

Must document:

- source and output SHA-256 identities;
- deterministic build or patch procedure;
- semantic invariants that are intended to remain unchanged;
- new fields, schemas, and validation rules;
- failure and rollback behavior;
- whether the change can contact a pool or submit work.

### Hashing, verifier, wire, submit, or scheduler changes

Do not combine these with documentation cleanup or evidence publication. They
require explicit authorization, a separate branch, a precise threat model, and
new validation. Public claims must not rely on an unreviewed live-path change.

## Evidence requirements

A strong evidence contribution should include:

- a machine-readable schema identifier;
- provenance and source identity;
- exact exposure or an explicit `DATA_NOT_AVAILABLE` value;
- deterministic derived calculations;
- integrity validation results;
- technical nonpasses and exclusions;
- an explicit claim level;
- a sanitized reviewer summary.

A valid linked ledger is not enough by itself. Acquisition completeness, source
truth, timing, comparability, and independence require separate evidence.

## Pull request checklist

- [ ] No credentials, private paths, endpoints, or unsanitized raw evidence.
- [ ] No unsupported SHA-256, advantage, profit, or energy claim.
- [ ] Facts, metrics, and conclusions are separated.
- [ ] Negative and inconclusive outcomes are retained.
- [ ] Hashes/manifests are updated when runtime artifacts change.
- [ ] Offline self-tests or validators pass where applicable.
- [ ] The README or relevant status document is updated when public behavior
      changes.

## Style

Prefer plain technical language over promotional claims. Use exact values and
state uncertainty. Explain what a control proves and what it does not prove.
