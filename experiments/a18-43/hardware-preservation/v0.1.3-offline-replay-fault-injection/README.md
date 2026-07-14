# A18.43 V0.1.3 — Offline Evidence Replay & Fault Injection

This stage validates the analysis laboratory before the next live run.

It has two independent layers:

1. **Hardware evidence replay** — corrected sensor mapping, joule integration, thermal metrics, dropout handling, and 13 hardware-evidence fault scenarios.
2. **Undina wave-semantics replay** — frozen A18.42 distinctions between wave, crest, valley, foam, and tail, tested against 15 deterministic control-trace faults.

A18.42 is not finished in the sense of being discarded. It is frozen as the control mechanism used by A18.43:

```text
Native Flow Gate
→ OPEN / HOLD / DRAIN / clean valley / REOPEN
→ separate old foam from new crest
→ count post-target tail
→ align hardware telemetry
→ compare CONTINUOUS / SHAM / NATIVE preservation cost
```

Validated offline result:

- real hardware evidence replay: PASS;
- hardware fault expectations: 13/13 PASS;
- wave fault expectations: 15/15 PASS;
- CPU Package energy replayed: 884.0816777189305 J;
- GPU and wall-energy claims remain blocked.

Synthetic faults validate the analyzer only. They do not prove physical energy saving, hardware-life extension, a useful Wave Pump, SHA-256 predictability, mining advantage, or profitability.
