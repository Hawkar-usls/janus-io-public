# A10.3 Avengers Kombucha Stress Molecule

This note defines the A10.3 scheduler-side "stress molecule" layer.

It is an algorithmic metaphor only. It is not a biological, medical, chemical,
or nutrition instruction.

## Purpose

A10 showed that the randomized traversal mirror can temporarily lead JANUS in
rare-tail telemetry. A10.3 keeps that mirror as a strict control arm, but lets
JANUS extract scheduler pressure from the confrontation:

```text
mirror pressure -> persistent stress memory -> controlled disorder -> next safer search order
```

The molecule is deliberately hard to digest. Accepted shares cool it down, but
do not erase it. That preserves a small memory of stress after local success.

## Scope

The stress molecule may influence only scheduler behavior:

- JANUS-side KombuchaMemory exploration pressure;
- JANUS-side structured choice among strategy, sector, and config cells;
- JANUS-side batch expansion within existing caps;
- log lines that expose stress state.

It must not influence:

- SHA-256;
- block header construction;
- nonce wire encoding;
- Stratum submit policy;
- pool target or local submit gate;
- accepted-share proof format;
- randomized traversal mirror purity.

## Current Implementation

The implementation lives in:

```text
RBLGANUL_A10_3_AVENGERS_KOMBUCHA_STRESS_50_50_IO_SINGLE.py
```

It wraps the audited A9.11 runner and monkey-patches only `KombuchaMemory`.
The old A9.11 file remains unchanged.

The stress molecule rises when:

- the randomized traversal mirror produces z30+ or z32+ pressure;
- mirror best_z leads JANUS best_z;
- mirror z32+ count leads JANUS z32+ count;
- rejects appear, which also raises acidity.

It cools when:

- JANUS produces z30+ or z32+ relief;
- accepted shares arrive.

Cooling never drops below a small stress floor.

## Operator Command

The normal launcher remains:

```text
Yaksa .bat
```

Then type:

```text
The Avengers
```

The future run folder defaults to:

```text
A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
```

## Audit Expectations

Expected console marker:

```text
[Rblganul | kombucha] brew=... acidity=... carbonation=... next_batch=... stress_molecule=... stress_choices=... janus_best=... mirror_best=...
```

Expected interpretation:

```text
The randomized traversal mirror remains the control arm.
JANUS learns only from scheduler-side telemetry pressure.
The frozen wire remains frozen.
```
