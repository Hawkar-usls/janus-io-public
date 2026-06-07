# JANUS Research Manifesto

## One Sentence

JANUS is an attempt to turn Proof-of-Work traversal from blind brute force into
an auditable, measured, feedback-driven search process.

## The Position

JANUS does not claim that SHA-256 is broken.

The claim is different:

```text
The way a miner traverses nonce/job/lane search space can be studied,
structured, measured, and compared against naive random traversal.
```

## Bridge Across Nothing

From the miner's point of view, SHA-256 search space does not expose a human
map. It gives no obvious landmarks, no semantic slope, and no promise that a
single local observation points toward a future rare tail.

JANUS starts from that constraint instead of denying it.

If the inner space is effectively "nothing" to the observer, the only honest
move is to build a bridge from the things that are available:

- pool state;
- job cadence;
- block height and `nbits`;
- pool difficulty;
- network latency and submit acknowledgement time;
- local HPS and desktop load;
- lane and recipe exposure;
- accepted-share rare-tail telemetry;
- random-control comparison.

The project is therefore not a claim that JANUS can see through SHA-256. The
project is a claim that a miner can adapt its traversal process by listening to
every real signal around the hash process.

In this view, the pool is not just a target endpoint. It is part of the
experimental environment. JANUS moves toward the pool by measuring how the pool,
network, machine, and traversal policy behave together.

The purpose of PoolDay and NetPulse is to make this explicit:

```text
PoolDay = job/pool/network context
NetPulse = Stratum timing and transport pressure
Traversal = how JANUS chooses to spend checked MH
Evidence = accepted-share rare-tail telemetry per checked MH
```

Only by joining these layers can the hash process become meaningful enough to
study. Without that context, a miner only sees isolated outcomes. With that
context, JANUS can ask whether a traversal decision was made under a clean pool
window, a stale-risk window, a network-pressure window, or a stable comparison
window.

This matters because most practical miners still treat the search process as a
flat throughput problem:

```text
more hashes
more random walking
more raw pressure
```

JANUS asks whether there is a more rational layer above raw hashing:

```text
lane ecology
sector rotation
job-aware traversal
pool-aware timing
network-aware pressure control
accepted-share rare-tail feedback
desktop-aware pressure control
per-MH comparison against random control
```

## What Counts As Evidence

JANUS evidence is not a single dramatic tail. A high-z accepted share is a
signal, not a conclusion.

Useful evidence requires:

- frozen wire behavior;
- accepted-share proof artifacts;
- checked-MH normalization;
- random-control comparison;
- repeated fresh windows;
- reject, stale, reconnect, cooldown, and NetPulse reporting;
- PoolDay context for job, pool, difficulty, and network windows;
- honest uncertainty.

The key comparison is:

```text
rare-tail telemetry per checked MH
```

not raw event count alone.

## Why A9 Exists

A9 adds built-in accounting around the V32 broad-mixture scheduler:

```text
janus_broad_mixture
random_control
desktop_load_state
accepted-tail per MH
worker-result best-tail per MH
```

This makes the current question testable:

```text
Does structured traversal produce a different accepted-share tail profile
than random traversal under the same machine, pool, wire, and desktop-load
conditions?
```

## Why A10.2 Exists

A10.2 extends the evidence layer with PoolDay and NetPulse:

```text
PoolDay:
  height / nbits / network difficulty / pool diff / job age / clean cadence

NetPulse:
  Stratum RTT / submit ACK latency / socket idle / packet volume /
  pending submit pressure / network pressure
```

This does not make JANUS more mystical. It makes the comparison stricter.

If JANUS appears better than random during a bad network window, that result
must be treated differently from a result produced during a clean stable window.
Likewise, if random control and JANUS are not exposed to the same pool and
network conditions, the comparison is not yet evidence.

The goal is not to force meaning into randomness. The goal is to preserve every
available measurement around the random process so that adaptation has something
real to respond to.

## What JANUS Should Not Say

Do not say:

```text
SHA-256 is broken.
JANUS predicts nonces.
A rare share equals a BTC block.
One z-tail event proves a law.
```

Say:

```text
JANUS investigates whether traversal policy changes the measurable rare-tail
profile of accepted-share PoW telemetry.
```

## Long-Term Direction

If the A9/A9.1 evidence holds, JANUS becomes more than a miner variant. It
becomes a practical research layer for hash-space traversal:

```text
not replacing SHA-256
not bypassing Proof-of-Work
but learning how to walk the search space with structure
```

That is the real project.
