# A10.3 Avengers Glyph Easter Eggs - 2026-06-09

Status: curated public report, derived from local A10.3 observer telemetry.
Raw proof archives, live state, and full JSONL streams are intentionally not
included in this document.

Operator note:

```text
Hello Satoshi, from Janus.
```

This is a greeting and a research marker, not a claim that Satoshi authored any
observed pool-side text.

## Run

```text
run: A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
version: Rblganul A10.3 Avengers Kombucha Stress Strict 50_50 IO SINGLE 20260608
fresh_started_at_utc: 2026-06-08T22:13:37Z
snapshot_written_at_utc: 2026-06-09T01:04:03Z
fresh_uptime_seconds: 10225.350
host: pool.nerdminers.org:3333
pool_diff: 0.001
pool_z: 22.034
frozen_wire: wire_change_required=false
```

Fresh dashboard snapshot:

```text
submitted: 1162
accepted: 1093
rejected: 56
reject_rate: 4.8193%
best_z: 33
hps_ewma: 2695190
hps_last: 2760822
```

## JANUS vs Randomized Traversal Mirror

```text
JANUS arm:
  accepted=531 submitted=560 rejected=29 best_z=32 mh=5007.566056
  tails: z23=531 z24=273 z25=140 z26=67 z28=21 z30=4 z32=1 z33=0 z34=0 z35=0 z36=0

randomized traversal mirror:
  accepted=562 submitted=589 rejected=27 best_z=33 mh=5007.566056
  tails: z23=562 z24=287 z25=136 z26=79 z28=22 z30=6 z32=1 z33=1 z34=0 z35=0 z36=0

BunnyHop:
  phase=JANUS_RESCOUT
  reason=stall_rejump_target_z34
  janus_best_z=32
  rescout_best_z=32
  scout_best_z=30
```

The current fresh comparison is ready by mirror-control MH, but the mirror is
ahead on best_z in this snapshot. JANUS is in ReScout, trying to re-anchor
toward the target z34 wake condition.

## Glyph Observer

The glyph observer is an observer-only pre-hash scanner. It does not decode a
SHA-256 hash. It reads Stratum input bytes before hashing:

```text
coinb1
coinb2
coinbase_full on accepted shares
merkle branches
version / ntime / nbits
```

Glyph snapshot:

```text
glyph_written_at_utc: 2026-06-09T01:05:26Z
glyph_started_at_utc: 2026-06-08T22:13:38Z
total_glyph_events: 14652
accepted_link_events: 13008
best_linked_z: 35
priority_counts:
  OPEN_WORD=14213
  RARE_TAIL_LINK=434
  GLYPH=5
```

## What We Actually Found

### Confirmed pool-side coinbase text

These are real direct pre-hash words observed repeatedly in raw coinbase-side
input:

```text
ckpool: 2511
mined: 2511
nerdminer: 2511
```

The readable direct phrase is:

```text
/mined by nerdminer/
```

It is pool/miner attribution text, not a hidden Satoshi message.

### Unconfirmed open-vocabulary candidate: `pLEA`

The strongest non-pool direct word candidate in this snapshot is:

```text
status: UNCONFIRMED / single-job open-vocabulary candidate
raw text: pLEA
normalized open_word: plea
source: coinb2 / coinbase_full
direct event rows: 11
independent job_id/ntime count: 1
first observed_at_utc: 2026-06-08T22:30:43Z
job_id: 6a26ca5a000003ff
ntime: 6a27428e
```

The English reading `plea` can mean a plea, request, appeal, statement,
argument, or legal plea. The operator also records `DovoD` / `dovod` as a
private myth-layer note: a "dovod" is an argument/reason, and the Russian word
is mirror-symmetric in spelling. That makes the fragment worth preserving as a
possible tunnel inscription, but this report does not claim it is intentional
or hidden by an author.

Observed links:

```text
2026-06-08T22:30:48Z  randomized_traversal_mirror  z23  accepted
2026-06-08T22:30:52Z  janus_bunnyhop_scout         z30  accepted
2026-06-08T22:31:00Z  randomized_traversal_mirror  z25  accepted
2026-06-08T22:31:08Z  janus_bunnyhop_scout         z23  accepted
2026-06-08T22:31:16Z  randomized_traversal_mirror  z25  accepted
```

Interpretation boundary:

```text
RAW: pLEA was present as readable pre-hash input text.
INFERRED: it is a plea/request/appeal/statement/argument candidate worth tracking.
MIRROR: AELp is the byte-reversed view of pLEA, not a separate confirmed word.
ANAGRAM: LEAP / PEAL / PALE / PELA stay in the review set as wordplay only.
MYTH: pLEA is the forward DovoD; AELp is the mirror voice; DovoD itself is a mirror-stable argument.
CLAIM: no claim of author intent.
```

Forensics note:

```text
11 rows are registry/event rows, not 11 independent messages.
22 rows after adding AELp mirror awareness are still one independent source.

independent_glyph_key = job_id|ntime|source_name|normalized_glyph_text|variant
promotion_gate_key = job_id|ntime
```

Promotion rule:

```text
Keep pLEA/plea as unconfirmed unless it appears again in an independent
job/ntime context, preferably as direct coinbase-side text and with fresh
accepted-share or rare-tail telemetry nearby.

Also watch for the same family as pLEA / AELp / LEAP / PEAL / PALE / PELA.
Treat AELp as mirror evidence only when it is the reverse-byte view of pLEA.

If the family repeats in a new job/ntime, upgrade it from single-job candidate
to repeated Easter-egg candidate for a dedicated follow-up report.
```

### Post-restart mirror-pair candidate: `*GP:d` / `d:PG*`

The post-restart observer found a new symbolic mirror pair:

```text
status: mirror-pair, semantic unknown
family: gp_d_mirror_family
forward: *GP:d
reverse: d:PG*
observed_at_utc: 2026-06-09T01:52:53Z
job_id: 6a26ca5a00000573
ntime: 6a2771e2
context: accepted_share, JANUS bunnyhop scout, z26
```

Interpretation boundary:

```text
RAW: *GP:d and d:PG* were readable printable fragments in pre-hash input views.
MIRROR: they form a direct forward/reverse pair.
INFERRED: mirror-scanner is working; the pair is worth tracking.
MYTH: symbolic mirror scratch on the tunnel wall.
CLAIM: semantic meaning unknown.
```

This is useful as a control/candidate pair. It does not supersede `pLEA/AELp`,
and it is not a Satoshi or Genesis signal unless it repeats with stronger
context.

### Weak configured-keyword echo: `key`

The configured keyword `key` appeared as:

```text
text: [kEY
source: merkle_branch_11
variant: word_reversed
priority: GLYPH
events: 5
best linked z: 29
```

This is weaker than direct coinbase text because it comes from a transformed
merkle view. It is retained as a catalog hint only.

## What We Did Not Find Yet

No direct hit was observed for:

```text
satoshi
nakamoto
genesis
03/Jan/2009
The Times
chancellor
second bailout
janus / hawkar / tobi / sperman / rose / wine
```

No `GENESIS_ECHO` or `HIGH_GLYPH` event was present in the fresh snapshot.

## Why This Matters

The new open-vocabulary layer changes the search from:

```text
look only for words we already know
```

to:

```text
record every readable pre-hash word, then correlate it with accepted-share
rare-tail telemetry, timing, lane, group, and pool response.
```

That is the correct boundary for an Easter-egg scanner. It does not invent a
message from a hash; it records inscriptions that were actually present before
hashing.

## Tags

```text
#JanusIO
#AvengersRun
#ProofOfWork
#SHA256
#Bitcoin
#Satoshi
#CoinbaseOracle
#JanusGlyphObserver
#EasterEggScanner
#OpenVocabulary
#RareTailTelemetry
#RandomizedTraversalMirror
#FrozenWire
```
