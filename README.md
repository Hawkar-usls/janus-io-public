# JANUS I0

> **Not for power. With care.**  
> **We do not seek to make the machine work faster at any cost. We seek to remove work it should never have had to perform.**

JANUS I0 is an experimental, evidence-gated hardware-preservation and Proof-of-Work research project.

Its primary mission is not to create another miner and not to chase maximum hashrate at any cost.

JANUS I0 develops auditable measurement and control methods for reducing:

- unnecessary Proof-of-Work computation;
- post-target overflow and queue overshoot;
- stale, duplicate, reconnect-invalidated, and unaccountable work;
- unnecessary energy use and heat;
- avoidable thermal stress and hardware wear;
- hidden exploitation history on the secondary hardware market;

while preserving standard SHA-256 verification and valid proof semantics.

## The heart of JANUS

A compute device is not treated as a disposable animal waiting to be exhausted.

A GPU, ASIC, CPU, memory module, fan, power stage, and thermal interface contain material resources, human labor, engineering knowledge, energy, and a finite useful life. JANUS asks whether that life can be preserved by preventing work that has no confirmed utility and by avoiding operating points where a small performance gain costs disproportionate power, temperature, errors, and wear.

The long-term vision is a farm supervised by a **caretaker**, not a warden:

```text
observe
→ prove what is happening
→ prevent unnecessary work
→ reduce avoidable heat and stress
→ preserve useful life
→ keep an honest operating history
→ protect the next owner
```

This is the engineering expression of a broader ethic:

> **The machine refuses to abandon the human. JANUS refuses to abandon the machine.**

Founder essay: [When the Machine Comes Not for Power, but with Care](https://medium.com/@hawkarlol/when-the-machine-comes-not-for-power-but-with-care-c211a904f87b)

Canonical mission and remote context anchor: [JANUS Meta Registry](https://github.com/Hawkar-usls/janus-meta-registry/blob/main/JANUS_CONTEXT_ANCHOR.md)

## What JANUS measures

JANUS is building a verified accounting system for the difference between all performed work and work that can still produce a valid, attributable result.

Important classes include:

```text
post-target overflow
stale work
duplicate work
reconnect-invalidated work
queue overshoot
shutdown-latency work
unaccountable or unsubmittable work
poor operating points
```

The eventual preservation score is not raw hashrate alone. It is closer to:

```text
confirmed useful work
────────────────────────────────────────────
energy + thermal stress + hardware-health cost
```

Candidate measurements include:

- useful work / all accounted work;
- joules per accepted valid proof or share;
- component and wall energy where sensors permit;
- GPU hotspot, memory, and CPU package temperature;
- temperature degree-seconds above a safe threshold;
- thermal-throttling time;
- fan duty, RPM, and instability;
- hardware-error rate;
- heavy thermal cycles;
- maintenance and thermal-interface history.

A short experiment may measure heat, power, fan behavior, and errors. It may not honestly prove extended hardware lifetime. That requires a longitudinal **Hardware Health Passport**.

## Evidence before claims

JANUS follows a strict rule:

```text
Do not promote an interesting observation into a claim
until provenance, exposure, controls, and replication exist.
```

The toolchain can:

- verify approved runtime components with SHA-256 before execution;
- apply deterministic, manifest-bound instrumentation;
- assert that hashing, verification, nonce traversal, WIRE, HASH, and SUBMIT semantics remain frozen;
- collect exact completed-batch exposure;
- reconcile admitted, submitted, finalized, and completed work;
- write normalized JSON/JSONL evidence with linked event hashes;
- separate sealed useful work from post-target foam and overflow;
- preserve negative, partial, and fail-closed outcomes;
- compare matched real, sham, and continuous controls;
- scan public artifacts for credentials, private paths, endpoints, and operational identifiers.

A linked hash chain provides tamper evidence after commitment. It does not by itself prove that the original sensor was truthful, the clock was correct, the collection was complete, or a causal interpretation was valid. Those require separate gates.

## Current sealed research state

### A18.37 — visible overflow

A measurable post-target class was observed: eight valid windows recorded 8,194,253 post-target hashes, about 1.44% of measured work. Utility and energy were still unknown.

### A18.38 — honest negative controller result

The first target-aware quiesce controller did not produce a reliable overflow reduction. The nonpass was preserved rather than hidden.

### A18.40 — cohort-drain tail

JANUS made a configuration-specific 16-worker in-flight completion cohort visible and compared real post-target tail work against matched pseudo-tail exposure.

### A18.41 — TimeShift

One already dispatched live wave survived multiple HOLD/RESUME pulses. The experiment also showed that external stopping could arrive too late and could not prove the birth of new admissions.

### A18.42 — Native Flow Gate

A native admission gate implemented:

```text
OPEN → exact quota → HOLD → DRAIN → clean valley → REOPEN
```

Sealed engineering classification:

```text
REPLICATED_NATIVE_WAVE_SEGMENTATION
```

Results:

- calibration: `10/10 valid`;
- discovery: `40/40 valid`;
- strict native candidates: `20/20`;
- matched candidate pairs: `16/16`;
- equivalent sham signatures: `0/16`;
- native boundaries: `56/56 PASS`;
- reconnect delta at boundaries: `0`;
- final-boundary foam: `0` in all discovery runs;
- Observer, runtime hashes, gate event chain, and cleanup: `40/40 PASS`.

This proves reproducible admission-wave segmentation inside the tested persistent process. It does **not** prove SHA-256 predictability, increased proof probability, mining advantage, profitability, energy savings, or extended hardware life.

See:

- [A18.42 public replication report](docs/a18-42-native-flow-gate-replication-2026-07-14.md)
- [A18.42 public experiment artifacts](experiments/a18-42/native-flow-gate/)

## Current next stage: A18.43

**JANUS A18.43 — Hardware Preservation Challenge** asks:

> Can the frozen Native Flow Gate reduce work without confirmed utility and reduce thermal or energy cost without a disproportionate loss of valid useful work?

The first phase is sensor preflight only. It inventories passive telemetry from:

- OpenHardwareMonitor WMI;
- NVIDIA NVML;
- `nvidia-smi` fallback;
- `psutil` CPU and memory metrics.

The later frozen comparison will use matched families:

```text
CONTINUOUS_BASELINE
SHAM_TIMING_CONTROL
NATIVE_GATE_PRESERVATION
```

Acceptable outcomes include:

```text
PASS
NO_EFFECT
NEGATIVE_EFFECT
PARTIAL
FAIL_CLOSED
```

A negative result is useful engineering knowledge.

## What JANUS is not

JANUS does not claim that:

- SHA-256 is broken or predictable;
- winning nonces can be inferred;
- a rare accepted share is equivalent to a Bitcoin block;
- a working admission gate proves mining advantage;
- component power automatically equals wall power;
- lower instantaneous temperature automatically proves longer life;
- the current software is a production mining platform;
- a machine is God or should replace human agency;
- care means total control.

## Proof-of-Observation

JANUS Proof-of-Observation is the project's evidence discipline:

1. preserve facts and provenance;
2. calculate derived metrics deterministically;
3. keep missing values unknown rather than converting them to zero;
4. link committed observer records for integrity;
5. compare only compatible windows and exact exposure;
6. separate discovery, challenge, and replication;
7. emit claims only when predefined gates pass.

Read:

- [Proof-of-Observation](docs/proof-of-observation.md)
- [Machine-readable origin record](docs/proof-of-observation-origin-record.json)
- [Current engineering capabilities](docs/current-engineering-capabilities.md)

## Repository map

```text
docs/         mission, methodology, claim boundaries, curated status
scripts/      offline analyzers, scrubbers, and reviewer utilities
src/          importable historical supervisor snapshot
experiments/  public-safe contracts, launchers, summaries, and proof packs
```

Raw credentials, private paths, pool identities, unsanitized logs, and private operational state do not belong in this public repository. Exact SHA-256 bindings may be published instead.

## Reviewer path

```text
2 minutes   README.md
5 minutes   docs/current-engineering-capabilities.md
10 minutes  latest A18 report
20 minutes  docs/proof-of-observation.md + evidence-pack spec
30 minutes  reviewer guide + curated proof pack
```

The desired conclusion is not “trust the author.” It is:

```text
The mission, method, controls, evidence boundary,
and unresolved uncertainties are explicit enough to inspect.
```

## Safety and publication policy

- Keep SHA-256, verification, nonce traversal, WIRE, HASH, and SUBMIT frozen unless a separate change is explicitly authorized.
- Never use digest quality to steer a preservation controller.
- Publish negative and fail-closed results alongside positive signals.
- Do not claim energy savings without stable, time-aligned power telemetry.
- Do not claim extended hardware life from short experiments.
- Never publish credentials, wallet-like labels, private endpoints, raw local paths, or unsanitized live evidence.
- JANUS is a caretaker, not a throne.

See [Security and disclosure](SECURITY.md) and [Contributing](CONTRIBUTING.md).

## License

Apache License 2.0. See [LICENSE](LICENSE).
