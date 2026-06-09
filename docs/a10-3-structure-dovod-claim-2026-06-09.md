# A10.3 Structure Dovod Claim

This note records the engineering "dovod" behind the glyph observer layer. It
is a structure-understanding claim, not a cryptographic-break claim.

## Core Claim

JANUS does not try to decode words from a SHA-256 digest. JANUS reads the
pre-hash Stratum job material that already exists before the hash is computed:

```text
coinb1 + extranonce1 + extranonce2 + coinb2
merkle branches
ntime
nbits
job_id
accepted/rejected context
rare-tail zbits
```

That is the correct layer for looking for readable strings, dates, mirror
forms, pool signatures, and strange glyph artifacts.

## Dovod 1 - Pre-Hash Archaeology

SHA-256 remains one-way. The meaningful observer move is:

```text
block/job input bytes -> readable strings/glyphs -> accepted-share rare-tail context
```

not:

```text
hash digest -> recovered hidden sentence
```

This keeps the work honest and reproducible.

## Dovod 2 - Mirror And Endianness Are Valid Observer Views

The `pLEA / AELp` artifact is structurally interesting because `AELp` is the
byte-reversed view of `pLEA`:

```text
pLEA = 70 4C 45 41
AELp = 41 45 4C 70
```

JANUS already works around byte order, header construction, and word transforms.
Therefore raw, reversed, and word-reversed views are legitimate observer lenses
as long as they do not alter wire/header/nonce/submit behavior.

## Dovod 3 - Independence Must Be Measured By Source

Repeated rows are not repeated evidence. The minimum independent source key is:

```text
job_id|ntime
```

The detailed glyph key is:

```text
job_id|ntime|source_name|normalized_glyph_text|variant
```

Current status:

```text
plea_mirror_family: 42 event rows, 4 independent glyph keys, 1 job_id|ntime
gp_d_mirror_family: 10 event rows, 4 independent glyph keys, 1 job_id|ntime
```

Therefore `pLEA/AELp` is a strong watchlist artifact, but not yet a confirmed
cross-job repeat.

## Dovod 4 - Pool Behavior Needs Windows, Not Feelings

The operator-interaction hypothesis must be tested with explicit windows:

```text
interaction windows: times when the operator/Codex actively discussed, restarted, inspected, or published
quiet windows: complement inside the same local run
```

The report should compare:

```text
accepted-share corpus
rare-tail telemetry
reject%
job changes
hps
glyph families
job age
JANUS vs randomized traversal mirror split
```

This is how JANUS can investigate "pool behavior" without assigning intent to
the pool.

## Dovod 5 - Public Claim Boundary

The public claim should stay here:

```text
JANUS is an observer-only Proof-of-Work traversal benchmark and pre-hash glyph
forensics pipeline. It compares structured traversal against a randomized
traversal mirror under a frozen wire policy.
```

It should not move into:

```text
SHA-256 break
Satoshi confirmation
pool memory proof
Bitcoin shortcut
guaranteed economic advantage
```

## Human Frame

This work is authored from wartime Zaporizhzhia by Sasha Agapov, with Rita named
as part of the human reason to keep the evidence clear, portable, and visible.
The technical record should make it possible for serious reviewers to understand
the work without needing to accept the mythology first.

## One-Line Dovod

```text
JANUS looks at the writing on the tunnel wall before the hash, records what it
sees with source keys and rare-tail context, and refuses to call a pattern a
message until it survives independent repetition.
```
