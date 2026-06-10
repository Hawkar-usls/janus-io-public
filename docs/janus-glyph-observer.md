# Janus Glyph Observer

Status: integrated observer layer.

`JanusGlyphObserver` is the Avengers pre-hash data archaeology layer. It does
not try to recover words from a SHA-256 hash. It scans the Stratum job data
that exists before the 80-byte block header is hashed:

```text
coinb1 / coinb2 / full coinbase on accepted shares
merkle branch source bytes
version / ntime / nbits fields
```

The goal is to preserve possible "glyphs" in the tunnel: readable strings,
dates, pool tags, genesis-like echoes, and other unusual input-side patterns.
Those observations are then linked to accepted-share rare-tail telemetry,
timing, and the JANUS-vs-randomized traversal mirror branch.

## Why It Exists

The Bitcoin genesis headline was not decoded from the hash. It was included in
the coinbase script data before hashing. That distinction matters:

```text
wrong: hash -> recover a message
right: pre-hash input data -> record readable strings -> correlate with telemetry
```

JANUS treats this as a forensic catalog, not a proof shortcut. The observer can
help answer questions such as:

- which coinbase/job strings were present near rare accepted tails;
- whether certain pool tags, dates, or script fragments recur around z32+;
- whether a later scheduler experiment is worth designing from accumulated
  evidence.

## Artifacts

A10.3 Avengers runs write A10-prefixed derived artifacts:

```text
rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.jsonl
rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.csv
rblganul_a10_3_avengers_kombucha_stress_janus_glyph_summary.json
```

The A9.11 base runner uses the same filenames with `a9_11_v32` prefixes.

## Event Layers

Each event keeps interpretation separated:

| layer | meaning |
| --- | --- |
| `raw_layer` | literal printable bytes found in the pre-hash input |
| `inferred_layer` | classification tags such as `date_or_timestamp` |
| `myth_layer` | explicitly separate interpretation, never proof |

The observer stores source checksums and short source identifiers instead of
depending on raw byte dumps for public summaries.

## Priority Levels

Every event is scored so the operator can distinguish a real clue candidate
from ordinary readable pool noise:

| priority | meaning |
| --- | --- |
| `GENESIS_ECHO` | exact or dense partial match to `The Times 03/Jan/2009 Chancellor on brink of second bailout for banks` |
| `HIGH_GLYPH` | multiple strong signals such as Satoshi/genesis/date/gate/monetary keywords |
| `RARE_TAIL_LINK` | readable pre-hash string linked to an accepted z32+ rare-tail share |
| `LINEAR_MESSAGE` | readable or symbolic fragment observed in a linear lane/context for SAT3 review |
| `SYMBOL_GLYPH` | symbolic or weird printable glyph candidate in pre-hash input |
| `OPEN_WORD` | open-vocabulary word found in live coinbase/job input |
| `GLYPH` | keyword/date hit without a rare accepted-share link |
| `LOW_CONTEXT` | weak context, usually useful only if it repeats |

High-priority events are logged as:

```text
[Rblganul | glyph_alert] priority=... score=... source=... text='...'
```

The event stream also records `score`, `match_reasons`, `meaning`, and
`exact_genesis_headline`.

## Open Vocabulary And Glyph Capture

The observer is not limited to the fixed keyword list. Each readable span is
also tokenized and shaped into a broad SAT3-ready artifact corpus:

| field | meaning |
| --- | --- |
| `open_words` | any word-like token found in the pre-hash text |
| `unknown_words` | `open_words` that are not part of the configured keyword list |
| `symbol_glyphs` | printable symbol runs such as bracket, slash, colon, marker, or punctuation inscriptions |
| `weird_glyphs` | mixed word/digit/symbol fragments that look structured but are not clean words |
| `mirror_families` | explicit tracked mirror/anagram families such as `plea_mirror_family` or `gp_d_mirror_family` |
| `linear_context` | true when the candidate came from a linear lane or strategy context |

The summary keeps frequency maps:

```text
by_open_word
by_unknown_word
by_symbol_glyph
by_weird_glyph
by_mirror_family
by_direct_open_word
by_direct_unknown_word
by_direct_symbol_glyph
by_direct_weird_glyph
by_direct_mirror_family
linear_context_events
```

This is the broad Easter-egg layer: it tells the operator what words, marks,
inscriptions, and strange printable fragments are actually present before
hashing, even when they are not known clues yet. The intent is not to claim
meaning immediately; it is to preserve everything useful enough for later
SAT3, repetition, timing, and rare-tail analysis.

The `direct` maps count only raw/hex/base64 readings, while the broader maps
also include reversed and 4-byte word-reversed views for hidden-pattern review.
To keep startup bounded, low-z historical proof backfill still focuses on
explicit keywords/dates; the live `stratum_job` and `accepted_share` paths
record open-vocabulary coinbase words and glyph-shape candidates as they
appear.

## Operator Signal Lexicon

In addition to the Genesis/Satoshi vocabulary, the default scanner keeps a
small operator signal lexicon:

```text
janus / jan / tobi / sperman / rose / wine / hawkar
```

Matches from this set are tagged as `janus_operator_signal`. They are treated
as personal review beacons for the Avengers corpus, not as proof of external
intent. If they occur near accepted rare-tail telemetry, the event receives
extra score and is eligible for `glyph_alert` logging.

## PLEA / Mirror Family Watchlist

After the A10.3 glyph snapshot found a single-job `pLEA` fragment, the observer
keeps a narrow watchlist for the same mirror/anagram family:

```text
plea / aelp / leap / peal / pale / pela
```

These matches are tagged as `plea_mirror_family`. The tag is observer-only: it
does not prove intent and does not change scheduling. Its purpose is to make a
future independent repeat easy to find, especially when the same family appears
in a different `job_id`/`ntime`, in direct coinbase-side text, or near accepted
z30+ / z32+ rare-tail telemetry.

For this family, `AELp` is treated as a byte-reversed mirror view of `pLEA`, not
as a separate confirmed word. The operator myth-layer also records `DovoD` /
`dovod`: an argument/reason reading that is mirror-stable in spelling. That
interpretation stays outside RAW and INFERRED until an independent repeat
appears.

## Symbol Mirror Families

The observer also tracks narrow symbolic mirror pairs when they appear in the
pre-hash corpus. The first explicit pair is:

```text
gp_d_mirror_family
forward: *GP:d
reverse: d:PG*
status: mirror-pair, semantic unknown
```

This family is useful as a mirror-scanner health signal and as a candidate for
later SAT3 review. It is not treated as a message unless it repeats across
independent jobs or gains stronger context.

## Independent Glyph Key

Registry row counts are not the same as independent signals. One coinbase can
produce multiple rows through accepted shares, `coinb2`, `coinbase_full`, and
reverse views. For honest forensics, the observer now writes:

```text
independent_glyph_key = job_id|ntime|source_name|normalized_glyph_text|variant
```

The summary exposes:

```text
unique_independent_glyph_keys
independent_glyph_key_formula
independent_by_mirror_family
job_ntime_key_formula
job_ntime_by_mirror_family
```

Promotion rules should use `job_id|ntime` family counts, not raw event row
counts. The full `independent_glyph_key` is more detailed and is useful for
registry deduplication across source and transform views.

Current A10 gate guidance:

```text
accepted-share corpus >= 250 fresh
or 3 independent job_id/ntime hits in plea/key/mirror-family
or JANUS z30+
```

## Search Windows

The observer scans:

- raw printable ASCII windows;
- reversed bytes;
- 4-byte word-reversed bytes;
- hex-as-ASCII windows;
- base64-looking windows that decode to mostly printable text;
- short repeated patterns.

This is still a pre-hash scan. It does not decode SHA-256 output.

## Registry

When `proofs_dir` is available, scored glyph events are also written as derived
registry artifacts under:

```text
proofs/registry/glyph/
```

These registry events are separate from accepted proof JSON and do not rewrite
proof artifacts.

## Boundaries

The observer does not:

- alter SHA-256 or double-SHA256 hashing;
- alter block-header construction;
- alter nonce, extranonce, target, or Stratum submit behavior;
- feed the randomized traversal mirror;
- feed the scheduler in A10.3;
- rewrite accepted proof artifacts.

It is a private corpus lens. Public reports must still scrub raw proof archives
and avoid publishing live pool state unless a curated proofpack is prepared.

## CLI Flags

```text
--janus-glyph-summary
--janus-glyph-events
--janus-glyph-csv
--janus-glyph-min-len
--janus-glyph-accepted-link-min-z
--janus-glyph-keywords
--disable-janus-glyph-observer
```

Default behavior:

```text
scan each Stratum job once for explicit keyword/date matches
link accepted z32+ shares to glyph strings even without keyword hits
write only derived observer telemetry
```

The current keyword set includes Genesis/Satoshi terms, JANUS gate language,
the operator signal lexicon, PoW terms, and quest-language markers used for
human review. Keyword matches are catalog hints, not claims of intent.

## A10 Encoding Archaeology Extension

The A10 Encoding Archaeology runner extends the glyph observer from
open-vocabulary string capture into broader encoding archaeology. It adds:

```text
entropy baseline comparison
mirror-glyph scoring
regex-like glyph scoring
encoded fragment classification
base85/ascii85-style probe metadata
rare-tail accepted link floor configurable down to z28
```

The current public checkpoint is:

```text
docs/a10-encoding-archaeology-status-2026-06-09.md
```

The current A10 claim boundary is:

```text
repeated glyph candidate
rare-tail linked
semantic unconfirmed
frozen wire unchanged
```

The active watchlist is:

```text
main: VV<~ / ~<VV
secondary: KRRO, &&fU
hold: pLEA / AELp / key
```

Promotion still requires independent repeat evidence, especially a new
`job_id` with z28+ context or a new JANUS z32+ event.

## A10 Secret Back/Forth Sidecar

The 2026-06-10 sidecar snapshot adds an observer-only symbol-anchor memory on
top of the glyph stream:

```text
A10_GLYPH_ECOLOGY_SECRET_BACKFORTH_SIDECAR.py
```

It reads `glyph_alert` console lines, rejects known pool boilerplate as
control/background, and writes derived sidecar artifacts:

```text
a10_glyph_ecology_radar.jsonl
a10_glyph_ecology_gates.jsonl
a10_open_sweep_candidates.jsonl
a10_symbol_backforth_shadow.jsonl
a10_symbol_anchor_memory.json
a10_janus_intention_field.json
a10_secret_gratitude.jsonl
```

The sidecar's back/forth layer is a shadow policy only:

```text
goal -> attention_filter -> belief/resistance/gratitude -> forward/backward/mirror motion -> feedback
```

It does not change the miner scheduler yet, does not feed the randomized
traversal mirror, and does not touch wire/header/submit behavior. Current
public note: `docs/a10-secret-backforth-sidecar-2026-06-10.md`.
