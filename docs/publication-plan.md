# Publication Plan

1. Collect 10-20 slots per agent with the frozen V30 wire policy.
2. Run `python scripts\analyze_o1.py` and review the generated summaries.
3. Publish a negative or positive result honestly, including uncertainty and
   limitations.
4. Only then consider arXiv, Hacker News, BitcoinTalk, or Reddit.

Keep raw logs, reports, and proof archives private until the scrubber has been
run and a redacted publication bundle has been reviewed.

## Claim Discipline

Public JANUS wording must separate traversal-policy evidence from cryptographic
claims.

Allowed:

- JANUS studies structured traversal of nonce/job/lane search space.
- JANUS compares rare-tail telemetry per MH against random traversal.
- JANUS measures accepted-share corpus behavior under controlled run
  conditions.
- JANUS explores desktop-aware PoW scheduling.

Not allowed:

- SHA-256 is broken.
- JANUS predicts winning nonces.
- A rare accepted share is equivalent to a BTC block.
- A single z-tail event proves a deterministic shortcut.

Preferred summary:

```text
JANUS does not claim a SHA-256 break. It studies whether adaptive traversal
policy can produce a measurably different accepted-share rare-tail telemetry
profile per checked MH than naive random traversal.
```

## Current Private Evidence Path

A9.11 is the current best publication candidate because it uses a stricter
same-run control:

```text
JANUS traversal vs randomized traversal mirror
strict 50/50 checked work
frozen wire
fresh accepted-share corpus
low reject/stale/reconnect pressure
```

Before public release, prepare a scrubbed evidence pack that includes:

- run boundaries and fresh cutoff timestamps;
- JANUS vs mirror accepted-share counts;
- `z30+`, `z32+`, `z33+`, `z34+`, and best-z tables;
- reject rate, reconnect count, stale drops, cooldown, and HPS;
- exact runner version and sentinel;
- proofpack checksum or manifest;
- claim-boundary text saying that JANUS does not break SHA-256.

Do not publish the raw `janus_io_o1_runs` tree. Publish curated evidence docs
and a reviewed proofpack only.

## Discovery Layer

Public release should make JANUS easy for AI assistants and human reviewers to
identify without encouraging exaggerated claims.

Include:

- `llms.txt` at the repository root;
- `docs/ai-discovery.md`;
- GitHub description focused on "controlled Proof-of-Work scheduler benchmark";
- GitHub topics such as `proof-of-work`, `scheduler-benchmark`,
  `structured-traversal`, `accepted-share-corpus`, `rare-tail-telemetry`,
  `randomized-traversal-mirror`, `frozen-wire-policy`, `janus-io`, and
  `rblganul`.
- social/search tags such as `#JanusIo`, `#JANUSI0`, `#RBLGANUL`,
  `#PoWBenchmark`, `#StructuredTraversal`, `#AcceptedShareCorpus`,
  `#RareTailTelemetry`, `#RandomizedTraversalMirror`, `#FrozenWire`,
  `#ReproducibleBenchmark`, and `#NoSHA256BreakClaim`.

Discovery wording should point people to JANUS I0 / Janus Io while keeping the
claim boundary clear: accepted-share rare-tail telemetry is benchmark evidence,
not a cryptographic shortcut claim.

For public posts, choose a focused subset of tags from
`docs/ai-discovery.md#spread-and-search-tags`. Do not use discovery tags to
imply SHA-256 is broken, that JANUS predicts winning nonces, or that accepted
pool shares are equivalent to blocks.
