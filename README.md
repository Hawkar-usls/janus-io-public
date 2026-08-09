<div align="center">

# JANUS I0
### Proof-of-Work measurement & hardware-preservation experiments

![Status](https://img.shields.io/badge/status-active%20experimental%20research-2f81f7)
![Scope](https://img.shields.io/badge/evidence-tested%20configurations-6e7681)

`measure first` · `preserve negative results` · `do not infer beyond the tested scope`

</div>

## Abstract

JANUS I0 studies whether avoidable computation, queue overshoot, and thermal load can be measured and reduced **without changing standard SHA-256 verification semantics**.

The project is experimental. Its evidence concerns the tested software/process configurations only.

## Current public status

| Item | Status |
| --- | --- |
| Work accounting / observer tooling | implemented in the published experimental stack |
| A18.42 Native Flow Gate | repeated project runs produced the published wave-segmentation signature |
| Energy savings | **not established** |
| Hardware-life extension | **not established** |
| SHA-256 predictability / weakness | **not claimed** |
| Mining advantage / profitability | **not established** |

Machine-readable status: [`PROJECT_STATUS.json`](PROJECT_STATUS.json)

## Strongest public result — A18.42

The Native Flow Gate used the sequence:

```text
OPEN → exact quota → HOLD → DRAIN → clean valley → REOPEN
```

Published counts:

```text
calibration                  10/10 valid
discovery                    40/40 valid
strict native candidates     20/20
matched candidate pairs      16/16
equivalent sham signatures    0/16
native boundaries            56/56 PASS
```

Within the published A18.42 setup, this supports the narrower engineering conclusion that the gate can produce distinguishable admission-wave segmentation in the tested persistent process.

It does **not** establish lower wall energy, longer hardware life, better mining economics, higher proof probability, or any weakness in SHA-256.

- [A18.42 report](docs/a18-42-native-flow-gate-replication-2026-07-14.md)
- [A18.42 artifacts](experiments/a18-42/native-flow-gate/)

## What is measured

The public toolchain is designed to account for classes such as:

- post-target overflow and queue overshoot;
- stale, duplicate, reconnect-invalidated, or otherwise unusable work;
- admitted, submitted, finalized, and completed work;
- power/thermal telemetry when a stable sensor path is available;
- hardware errors and operating-point quality.

A short experiment can measure these observables. It cannot by itself establish long-term component lifetime.

## Next validation target

The next useful comparison is a matched set of:

```text
CONTINUOUS_BASELINE
SHAM_TIMING_CONTROL
NATIVE_GATE_PRESERVATION
```

with stable, time-aligned power and thermal telemetry. `NO_EFFECT`, `NEGATIVE_EFFECT`, and `FAIL_CLOSED` are valid outcomes.

## Evidence discipline

- Keep SHA-256, verification, target math, and submit semantics fixed unless a separate experiment explicitly changes them.
- Preserve null, negative, and failed runs.
- Keep missing measurements unknown rather than silently treating them as zero.
- Treat hash chains as integrity evidence, not proof that a sensor or clock was truthful.
- Do not promote component telemetry into wall-power claims without a validated measurement path.

Read: [Proof-of-Observation](docs/proof-of-observation.md) · [Current capabilities](docs/current-engineering-capabilities.md)

## Reviewer path

1. [`PROJECT_STATUS.json`](PROJECT_STATUS.json)
2. [A18.42 report](docs/a18-42-native-flow-gate-replication-2026-07-14.md)
3. [A18.42 artifacts](experiments/a18-42/native-flow-gate/)
4. [Proof-of-Observation](docs/proof-of-observation.md)
5. [Security / disclosure](SECURITY.md)
6. [Portfolio maturity/visibility](https://github.com/Hawkar-usls/Janus/blob/main/portfolio-visibility.json)

## Repository map

```text
docs/         methodology, reports and claim boundaries
experiments/  public experiment contracts and proof packs
scripts/      analyzers, scrubbers and reviewer utilities
src/          historical/importable supervisor snapshot
```

## License

Apache-2.0. See [LICENSE](LICENSE).

Presentation follows the account's [public repository standard](https://github.com/Hawkar-usls/Janus/blob/main/docs/PUBLIC_REPOSITORY_PRESENTATION_STANDARD.md). No affiliation with MIT is implied by the presentation style.
