# V32 TachyonMicroAgent Patch Proposal

Status: proposal only. This document does not patch the live miner.

## Scope

Create a V32 scheduler-only allocator slot named `TachyonMicroAgent`. The patch should be reviewable line by line and must not touch wire construction, submit behavior, proof serialization, or live state.

## Files

Suggested files for a later patch:

- `RBLGANUL_V32_TACHYON_ORACLE_IO_SINGLE.py`
- `scripts/analyze_v31_io.py` or a new `scripts/analyze_v32_tachyon.py`
- `experiments/o1-01/v32_tachyon_microagent_design.md`

Do not modify live V31 proof archives, dashboards, memory files, or session files.

## Minimal Code Changes

1. Add a new pure-Python class:

```python
class TachyonMicroAgent:
    ...
```

2. Add a global:

```python
V32_TACHYON_AGENT = None
```

3. Add CLI flags:

```python
p.add_argument("--enable-tachyon-agent", action="store_true", default=False)
p.add_argument("--tachyon-backend", choices=("python", "cuda"), default="python")
p.add_argument("--tachyon-min-explore-ratio", type=float, default=0.10)
p.add_argument("--tachyon-min-mh-for-promotion", type=float, default=512.0)
```

4. Add a scheduler-only wrapper:

```python
def tachyon_or_static_lane_weights(args, fallback):
    if not getattr(args, "enable_tachyon_agent", False):
        return fallback
    if V32_TACHYON_AGENT is None:
        return fallback
    return V32_TACHYON_AGENT.decide().get("lane_weights", fallback)
```

5. In the V32 task chooser, use Tachyon only where static lane weights are currently used. The returned task shape must remain unchanged.

6. Extend dashboard JSON with:

```json
"v32_tachyon_microagent": {
  "tachyon_enabled": false,
  "tachyon_backend": "python",
  "tachyon_top_lanes": [],
  "tachyon_explore_ratio": 0.1,
  "tachyon_confidence": "weak",
  "tachyon_last_decision_reason": "disabled"
}
```

7. Extend analyzer output with per-lane tail/MH and Tachyon selection diagnostics.

## Safe Merge Conditions

- `python -m py_compile` passes for the V32 script.
- Analyzer runs offline against copied artifacts.
- Dashboard still reports `wire_change_required=false`.
- Accepted proof format is unchanged.
- Submit gate policy is unchanged.
- No new dependency is required for default Python backend.

## Explicit Non-Goals

- No Stratum reconnect change in this patch.
- No CUDA mining backend.
- No hash kernel replacement.
- No proof artifact rewrite.
- No public performance claim without A/B data.
