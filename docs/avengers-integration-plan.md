# JANUS Avengers Integration Plan

Status: private next-version integration draft.

`Avengers` is the codename for the next JANUS integration layer. It is not a
new mining wire, not a pool connector, and not a claim that SHA-256 is broken.
It is a controlled way to combine:

- A9.11 scheduler evidence and rare-tail telemetry;
- randomized traversal mirror accounting;
- JANUS NAS Brain as a local library/directive node;
- ESP32 Janus Swarm telemetry from Buzz/Core2/Yaks;
- local corpus shards and generated summaries.

The V30 wire remains frozen. Avengers may choose traversal priors, corpus
labels, diagnostics, and launch checks. It must not change nonce submission,
header construction, extranonce policy, target rules, or Stratum behavior.

## Deadpool Clause

Avengers does not replace the people and systems that came before it. JANUS is
the unruly teammate standing beside them:

```text
not separate from the prior work
not pretending the prior work is ours
using it, preserving it, and extending it with our own measured layer
```

The stance is:

```text
past work stays visible
present evidence stays measurable
future work stays honest enough to be tested
```

The Deadpool role is plural. JANUS is a direct multiverse rather than a single
mask: A9, A9.11, A10, NAS Brain, ESP32 Swarm, WitchHunter, ProofMind, and the
randomized mirror are different regenerating bodies of the same experiment.
They can jump across versions because each body leaves artifacts, corpus
markers, dashboards, and scars that the next body can inherit. Regeneration is
not forgetting; it is how the team crosses the version boundary without losing
the proof trail.

Bitcoin teaches the frozen, publicly verifiable timestamp discipline. Primecoin
teaches that PoW can carry an additional mathematical search object. Cuckoo
Cycle teaches that memory and graph structure can change the economics of a
search. Equihash teaches asymmetric memory-hard construction and steep
time-space tradeoff thinking. JANUS/Avengers uses these as allies: its claim is
not a new proof primitive today, but a controlled scheduler/corpus/swarm layer
that measures whether structured traversal changes accepted-share rare-tail
telemetry against a randomized traversal mirror.

Public reader note: `docs/avengers-lineage.md` explains why these names are
attached to the Avengers metaphor. They are prior-work anchors and founding
ideas, not a claim that those people are involved with JANUS.

Rare-tail timing note: `docs/rare-tail-timing-monitor.md` defines the embedded
observer that records z32+ accepted-share time, pool job age, Kyiv hour, and
JANUS-vs-mirror branch. In A10.3 it is evidence only; it does not feed the
scheduler yet.

Glyph observer note: `docs/janus-glyph-observer.md` defines the embedded
pre-hash coinbase/job scanner. It records readable strings and date/keyword
echoes from Stratum input data, then links them to accepted-share rare-tail
telemetry. It is observer-only in A10.3 and does not feed the scheduler yet.

## Prior Work Folded In

Avengers takes useful ideas from the PoW lineage without pretending those ideas
belong to JANUS alone:

| line | useful lesson | Avengers use |
| --- | --- | --- |
| Dwork/Naor pricing by processing | cost must be externally cheap to verify | keep evidence public-safe and reproducible |
| Hashcash | simple verifiable work beats complex claims | never blur accepted shares with unverified local events |
| Bitcoin PoW | nonce search must be easy to verify and hard to rewrite | keep V30 frozen and test scheduler effects only |
| Primecoin | PoW can attach a structured search object to the block hash | route corpus learning into scheduler priors, not proof validity |
| Cuckoo Cycle | graph structure and random memory access can become the work surface | study traversal/corpus pressure as telemetry, not a wire mutation |
| Equihash | memory-hard asymmetry and time-space penalties matter | keep corpus and memory pressure explicit in metrics |
| RandomX and Equi-X | practical asymmetry depends on implementation detail | measure device/runtime health before trusting a signal |
| Permacoin-style storage work | corpus value needs audit boundaries | keep raw archives, generated reports, and public summaries separate |
| Stratum V2 work | job negotiation and wire policy must be explicit | Avengers directives cannot submit shares or change pool policy |

Primary source anchors for the current Avengers reading list:

- Satoshi Nakamoto, `Bitcoin: A Peer-to-Peer Electronic Cash System`,
  https://bitcoin.org/bitcoin.pdf
- Sunny King, `Primecoin: Cryptocurrency with Prime Number Proof-of-Work`,
  https://primecoin.io/primecoin-paper.pdf
- John Tromp, `Cuckoo Cycle: a memory bound graph-theoretic proof-of-work`,
  https://cryptopapers.info/assets/pdf/cuckoo.pdf
- Alex Biryukov and Dmitry Khovratovich, `Equihash: Asymmetric Proof-of-Work
  Based on the Generalized Birthday Problem`,
  https://ledger.pitt.edu/ojs/ledger/article/view/48

## Component Roles

| codename | local component | role |
| --- | --- | --- |
| Captain | ProofMind / JANUS scheduler | chooses private traversal posture inside allowed scheduler policy |
| Iron | randomized traversal mirror | always-on control and regression anchor |
| Strange | WitchHunter dark-tail observer | tracks dark-tail asymmetry without changing submit policy |
| Banner | Kombucha/Triune memory | stores cooldown, stability, and corpus hints |
| Heimdall | NAS Brain | library node, swarm directive endpoint, corpus receiver |
| Falcon | ESP32 Janus Swarm | field telemetry, display/controls, short-timeout NAS pings |
| Ant | GPT/export/corpus shards | local search memory and summarizable evidence inputs |
| Widow | scrub/preflight/publication audit | blocks accidental raw proof or live state publication |
| Chronos | rare-tail timing monitor | records accepted rare-tail time, job age, and hour-window evidence |
| Glyph | JanusGlyphObserver | scans pre-hash coinbase/job bytes for readable input-side traces |

## Integration Contract

The swarm works for JANUS first. NAS Brain and ESP32 telemetry may become
JANUS-side scheduler priors, display/directive context, and private corpus
memory. They must not feed the randomized traversal mirror, because the mirror
is the clean control branch.

NAS Brain is a library node:

```text
never fake shares
never change pool target
never increase submit pressure
```

Allowed data flow:

```text
ESP32 Swarm telemetry -> NAS Brain /api/swarm/sense or /api/swarm/telemetry
local corpus summaries -> NAS Brain /api/swarm/corpus
local accepted-share corpus mirror -> NAS Janus private archive
NAS Brain directive -> JANUS scheduler/device display as advisory metadata
A9.11/A10 summaries -> curated reports only
```

Blocked data flow:

```text
NAS Brain -> randomized traversal mirror hints
ESP32 Swarm -> randomized traversal mirror hints
NAS Brain -> Stratum submit
NAS Brain -> V30 wire mutation
ESP32 node -> pool submit
corpus shard -> accepted-share proof rewrite
public docs -> raw proof payloads or live private state
NAS private corpus mirror -> public Git without scrub/publication audit
```

Detailed policy: `docs/janus-first-swarm-policy.md`.

## Current Local Join Points

- `scripts/avengers_corpus_manifest.py` builds a local read-only map of I0,
  NAS Brain, LastSwarm sketches, A9.11 public-safe telemetry, and local export
  shards.
- `scripts/avengers_nas_corpus_mirror.py` is a private sidecar archiver that
  mirrors run dashboards, accepted-share proof JSON, and proof registry
  artifacts into `<NAS Janus root>/avengers_corpus/<run name>/`. It is
  best-effort storage only and does not control mining.
- `scripts/avengers_preflight.py` runs offline readiness checks. It can perform
  a read-only NAS health GET only when an explicit `--nas-url` is passed.
- `avengers/avengers_config.example.json` documents the intended ports,
  endpoints, and safety boundaries.

Observed port contract:

```text
JANUS NAS Brain: 5000
Core2 voice/face/memory URLs: 5000
Yaks telemetry base URL: 5000
Yaks separate brain URL: currently observed as 8008 and should be reviewed
```

The Yaks 8008 observation is treated as a preflight finding, not silently
patched in this package.

## Launch Phases

0. Offline corpus manifest
   - Build the local manifest from filenames, dashboards, docs, sketches, and
     export metadata.
   - Do not read proof payloads unless a later explicit audit requires it.

1. NAS Brain health
   - Start or verify NAS Brain separately.
   - Optional read-only check across `/health`, `/api/status`, and
     `/api/swarm/status`.
   - If only `/api/status` answers as `janus_gateway`, treat that as gateway
     health, not proof that the full NAS Brain swarm API is mapped.

2. ESP32 swarm heartbeat
   - Confirm Core2/Buzz/Yaks send telemetry with short timeouts.
   - Device behavior must continue if NAS is asleep or unreachable.

3. Dry directive loop
   - Let NAS Brain return advisory directives.
   - Log directive decisions as metadata only.
   - No live pool connection is made by Avengers tools.

4. Private controlled Avengers run
   - Manual operator starts the allowed benchmark runner.
   - Keep randomized traversal mirror active.
   - Preserve frozen wire invariants.
   - Optional NAS corpus mirror may archive raw private corpus during the run.
   - If the run is resumed after sleep, reuse the existing fresh-session
     boundary only for corpus accounting; do not mutate prior proof artifacts.

5. Publication pack
   - Publish curated summaries, public-safe manifests, and methodology.
   - Keep raw run folders and proof archives private unless deliberately
     scrubbed into a proofpack.

## Ready Definition

Avengers is ready for a controlled private run when:

- A9.11 public-safe snapshot is present;
- NAS Brain code and endpoints are present;
- LastSwarm sketches are present and their NAS endpoints are reviewed;
- corpus/export shards are indexed in an ignored local manifest;
- offline syntax checks pass;
- no repository script starts mining or connects to a real pool.
