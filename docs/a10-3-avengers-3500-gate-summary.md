# A10.3 Avengers 3500-Gate Summary

Status: public-safe curated summary. Raw accepted-share proof JSON and live run
state remain private.

Run:

```text
A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
```

Runner:

```text
Rblganul A10.3 Avengers Kombucha Stress Strict 50_50 IO SINGLE 20260608
```

Final observed checkpoint:

```text
written_at_utc: 2026-06-08T05:27:58Z
fresh accepted-share corpus: 3523
submitted: 3533
rejected: 10
reject%: 0.2830
dashboard best_z: 35
```

The run used strict equal-exposure 50/50 accounting:

```text
JANUS structured traversal + stress Kombucha half
vs
randomized traversal mirror half
same runner
same machine
same pool job stream
same submit policy
same frozen V30 wire
```

## JANUS

```text
accepted: 1761
submitted: 1767
rejected: 6
best_z: 34
checked_mh: 14594.546
accepted_per_mh: 0.120661
tails: z23=1761 z24=888 z25=433 z26=203 z28=42 z30=14 z32=3 z33=2 z34=1 z35=0 z36=0
```

## Randomized Traversal Mirror

```text
accepted: 1762
submitted: 1766
rejected: 4
best_z: 35
checked_mh: 14594.546
accepted_per_mh: 0.120730
tails: z23=1762 z24=894 z25=439 z26=219 z28=42 z30=8 z32=4 z33=1 z34=1 z35=1 z36=0
```

## Runtime State

```text
phase/reason: JANUS_RESCOUT / active_blue_rescout_mirror_z32_gap
ProofMind: HUNT strength=0.985 hunger=0.0342 elite=450 bad=6
BunnyHop broad: accepted=1345 best_z=33
BunnyHop scout: accepted=250 best_z=29
BunnyHop rescout: accepted=166 best_z=34 target_z=34
hps_ewma: 2671608
best_hps_ewma: 2898448
load_state: CLEAN
comparison_gate: READY_FOR_COMPARISON
recommended_min_fresh_proofs: 7000
```

Top lanes at the checkpoint:

```text
random_mirror:linear_proof::random/s6/canonical accepted=123 best_z=35 z35=1
janus_bunnyhop_rescout:linear_proof::linear/s7/canonical accepted=12 best_z=34 z34=1
dual_lock:zim_reverse_s6::zim_reverse/s6/canonical accepted=100 best_z=33 z33=1
janus_bunnyhop_rescout:dual_lock_zim_reverse_s6::zim_reverse/s6/canonical accepted=16 best_z=32 z32=1
random_mirror:linear_proof::random/s4/canonical accepted=119 best_z=32 z32=1
```

## Network And Wire

```text
network_recovery: enabled
socket_alive: true
reconnect_count: 0
failed_connect_count: 0
stale_round_drops: 0
active_job: 6a254aaa000008ac / seq546
wire_change_required: false
```

Frozen V30 wire locks remained unchanged:

```text
extranonce2_little_endian: true
nonce_header_little_endian_bytes: true
nonce_submit_big_endian_uint32_hex: true
prevhash_word_reverse: true
```

## WitchHunter

```text
highest_dark_z: 24
JANUS dark events: 8
mirror dark events: 5
scheduler_effect: observe_only
submit_pressure_changed: false
wire_change_required: false
```

## NAS Corpus Archive

The current A10.3 accepted-share corpus was copied to a private NAS Janus
archive under a local operator path:

```text
<private NAS Janus root>/avengers_corpus/I0_CORPORA_PRIVATE/janus_io_o1_runs/A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
```

This NAS archive is private raw corpus storage. It is not part of the public
GitHub evidence pack and should not be published without a separate scrub and
publication audit.

## Verdict

At the 3500 gate, the randomized traversal mirror held the highest observed
rare tail with `best_z=35` and one `z35+` accepted share. JANUS remained close
in total accepted count and exposure-normalized accepted rate, but its top
accepted rare tail was `best_z=34`.

The meaningful scheduler response is the phase transition into
`JANUS_RESCOUT`, with rescout targeting the mirror gap while the frozen wire
stayed clean. This is a useful negative/pressure checkpoint: JANUS did not beat
the mirror at this gate, but it preserved a clean control comparison and left a
clear next target for the Avengers corpus layer.
