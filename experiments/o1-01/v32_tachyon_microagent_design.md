# V32 TachyonMicroAgent Adaptive Allocator Design

Status: design report only. No miner, wire, proof, scheduler, or live-state code is modified by this document.

## Purpose

TachyonMicroAgent is a proposed V32 scheduler-policy component for Janus/V31/V32. It observes existing scoreboard, ratebook, DualLock, tail, HPS, reject, and cooldown telemetry and emits scheduler lane weights.

It must not hash, submit shares, build headers, alter Stratum messages, or touch proof format. Its only runtime authority is allocation of scheduler weight among existing strategy/lane/cfg choices.

## Hard Boundaries

- No wire byte changes.
- No header assembly changes.
- No nonce endian changes.
- No extranonce2 handling changes.
- No prevhash mirror changes.
- No TruthGate changes.
- No submit gate changes.
- No accepted proof format changes.
- No live miner state patching.
- Python remains the primary implementation.
- CUDA is optional only as a future scoring backend, never as a mining backend.

## Existing V31 Anchors

The V31 code already separates scheduler telemetry from wire construction:

- `StrategyRateBook` tracks per-lane checked hashes, accepted shares, rejects, best_z, and z24/z28/z30/z32/z33 tail counts.
- `TailTracker` writes high-z candidate telemetry.
- `DualLockMemory` tracks the fixed DualLock lane family.
- `normalized_lane_weights(args)` provides current static lane weights.
- `choose_v31_task(...)` selects one scheduler lane and returns `(strategy, sector, cfg, lane)`.
- `EnduranceOracle.dashboard(...)` publishes dashboard JSON and already contains a `v31_duallock_oracle` diagnostics block.
- `scripts/analyze_v31_io.py` reads dashboard, DualLock memory, strategy rates, proof filenames, and reports health/tail metrics.

Tachyon should sit between telemetry and lane selection. It should replace only the static weight calculation when explicitly enabled.

## Proposed Class

```python
class TachyonMicroAgent:
    def __init__(
        self,
        backend: str = "python",
        min_explore_ratio: float = 0.08,
        max_promote_ratio: float = 0.55,
        decay: float = 0.985,
        min_mh_for_strong_promotion: float = 512.0,
        min_accepted_for_strong_promotion: int = 64,
    ) -> None:
        ...

    def observe(
        self,
        top_strategy_scoreboard: list[dict],
        strategy_rates: dict,
        dual_lock_memory: dict,
        tail_counts: dict,
        hps_ewma: float,
        reject_rate: float,
        cooldown: bool,
    ) -> None:
        ...

    def decide(self) -> dict:
        ...
```

`backend="python"` is the default. `backend="cuda"` is accepted only as a placeholder; if no CUDA scoring backend exists, Tachyon silently falls back to Python.

## Inputs

Tachyon consumes existing telemetry only:

- `top_strategy_scoreboard`
- `strategy_rates`
- `dual_lock_memory`
- tail counts by threshold
- per-lane attempts, checked hashes, accepted shares, rejects, submitted shares, and best_z
- `hps_ewma`
- reject rate
- cooldown state

No input may be raw private key material, pool credentials, Stratum wire bytes, or proof payload mutation data.

## Outputs

Tachyon emits a pure scheduler-policy decision:

- normalized weights per `strategy/lane/cfg`
- exploration ratio
- optional prune/restore hints
- JSON diagnostics for dashboard

Suggested decision schema:

```json
{
  "enabled": true,
  "backend": "python",
  "weights": {
    "linear/linear_proof/canonical": 0.32,
    "zim_reverse/dual_lock:zim_reverse_s6/canonical": 0.18
  },
  "explore_ratio": 0.10,
  "confidence": "moderate",
  "top_lanes": [],
  "prune_hints": [],
  "restore_hints": [],
  "last_decision_reason": "stable low reject rate; promoted lanes with sustained z30+/MH"
}
```

## Scoring

The score should prioritize sustained proof productivity, not one lucky tail:

```text
base =
  0.30 * accepted_per_mh_norm +
  0.18 * z28_per_mh_norm +
  0.20 * z30_per_mh_norm +
  0.16 * z32_per_mh_norm +
  0.10 * z33_per_mh_norm +
  0.06 * z35_per_mh_norm

score = confidence * base - reject_penalty - cooldown_penalty
```

Recommended confidence gate:

```text
sample_confidence = min(1.0, sqrt(mh / min_mh_for_strong_promotion))
accepted_confidence = min(1.0, accepted / min_accepted_for_strong_promotion)
confidence = min(sample_confidence, accepted_confidence)
```

Tail metrics should be normalized against a robust baseline such as the current lane median or best stable baseline. A single z36 should contribute to diagnostics but should not dominate score unless the lane also has sufficient z30+/MH, z32+/MH, or z33+/MH support.

Reject penalty:

```text
lane_reject_rate = rejected / max(1, submitted)
reject_penalty = clamp((lane_reject_rate - global_reject_rate) * 4.0, 0.0, 0.35)
```

If global reject rate rises above policy threshold or cooldown is true, Tachyon should increase exploration floor only conservatively and prefer known stable canonical lanes.

## Overfit Guards

- Keep a minimum exploration floor, for example 8-12 percent.
- Cap any single lane promotion, for example at 55 percent.
- Decay old observations gradually.
- Require minimum MH and accepted samples before strong promotion.
- Do not promote solely because of one z36+ hit.
- Penalize high reject contribution.
- Restore low-weight lanes periodically to test drift.
- Keep random baseline visible as a calibration lane.

## Scheduler Integration

V32 should introduce a new slot, not rewrite V31 behavior:

1. Add `V32_TACHYON_AGENT = None` near existing scheduler telemetry globals.
2. Add CLI flags:
   - `--enable-tachyon-agent`
   - `--tachyon-backend {python,cuda}`
   - `--tachyon-min-explore-ratio`
   - `--tachyon-min-mh-for-promotion`
3. Instantiate Tachyon after `StrategyRateBook`, `TailTracker`, and `DualLockMemory`.
4. Add `tachyon_lane_weights(args, fallback_weights)` that returns fallback static weights unless enabled and healthy.
5. Modify the V32 task chooser only at the lane-weight selection point.
6. Keep returned tuple shape `(strategy, sector, cfg, lane)` unchanged.

This means Tachyon changes only probability mass over existing scheduler choices.

## Dashboard Additions

Add these fields under a new V32 diagnostics block:

```json
{
  "v32_tachyon_microagent": {
    "tachyon_enabled": true,
    "tachyon_backend": "python",
    "tachyon_top_lanes": [],
    "tachyon_explore_ratio": 0.1,
    "tachyon_confidence": "moderate",
    "tachyon_last_decision_reason": "stable allocation"
  }
}
```

Also preserve `wire_change_required=false` in the existing wire diagnostics.

## Analyzer Additions

The analyzer should report:

- per-lane `accepted/MH`
- per-lane `z28+/MH`
- per-lane `z30+/MH`
- per-lane `z32+/MH`
- per-lane `z33+/MH`
- per-lane `z35+/MH`
- Tachyon selected lanes and weights
- comparison of Tachyon selected lanes vs actual rare-tail output
- whether Tachyon over-promoted a lane with low sample confidence

## CUDA Policy

CUDA is a future scoring backend only:

- Default backend is `python`.
- `backend="cuda"` may be accepted as a placeholder.
- No hard dependency on `torch`, `cupy`, or `numba`.
- If CUDA is unavailable, scoring falls back silently to Python.
- CUDA must never perform mining, hashing, header construction, Stratum submission, or proof mutation.

## Confidence Policy

Claim level should remain conservative:

- Weak: one lane has a lucky high tail but no stable MH-normalized support.
- Moderate: lane beats baseline by more than 25 percent on z30+/MH or z32+/MH with enough MH and accepted samples.
- Strong: repeated A/B runs show stable superiority across accepted/MH and high-tail/MH while reject rate remains low and wire is frozen.

Current V31 evidence supports designing Tachyon as an allocator candidate. It does not support any claim that SHA-256 is broken or that mining profit is guaranteed.

## V32 Backlog Section

### TachyonMicroAgent adaptive allocator

Add a scheduler-only micro-agent that observes V31/V32 scoreboard, strategy ratebook, DualLock memory, and accepted proof tail statistics. It emits normalized lane weights, exploration ratio, prune/restore hints, and dashboard diagnostics. It must preserve all wire, header, nonce, extranonce2, prevhash, TruthGate, submit gate, and proof-format invariants. Python is the default backend; CUDA is a future optional scoring backend only.
