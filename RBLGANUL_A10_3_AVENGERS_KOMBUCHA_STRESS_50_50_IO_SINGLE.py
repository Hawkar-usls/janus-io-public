#!/usr/bin/env python3
"""A10.3 Avengers wrapper: JANUS vs randomized mirror with stress Kombucha.

This file intentionally reuses the audited A9.11 wire/mining implementation and
patches only the scheduler-side KombuchaMemory class before entering main().

Wire policy stays frozen:
- no header construction changes
- no target / submit gate changes
- no Stratum behavior changes
- no accepted proof format changes

The "stress molecule" is an algorithmic metaphor: a slowly decaying scheduler
pressure signal. It is not a medical, biological, or chemistry instruction.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import random
import sys
from typing import Any, Dict, Iterable, List, Tuple

import RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE as base


A10_VERSION = "Rblganul A10.3 Avengers Kombucha Stress Strict 50_50 IO SINGLE 20260608"
A10_SENTINEL = "RBLGANUL_A10_3_AVENGERS_KOMBUCHA_STRESS_50_50_IO_SINGLE_20260608"
A10_DEFAULT_RUN_NAME = "A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE"


DEFAULT_RENAMES = {
    "csv_log": (
        "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_lab.csv",
        "rblganul_a10_3_avengers_kombucha_stress_50_50_lab.csv",
    ),
    "lockbox": (
        "a9_11_v32_active_triune_sovereign_gate_50_50_lockbox.json",
        "a10_3_avengers_kombucha_stress_50_50_lockbox.json",
    ),
    "session_summary": (
        "session_summary_a9_11_v32_active_triune_sovereign_gate_50_50.json",
        "session_summary_a10_3_avengers_kombucha_stress_50_50.json",
    ),
    "janus_brain": (
        "rblganul_a9_11_v32_best_brain.json",
        "rblganul_a10_3_avengers_kombucha_stress_best_brain.json",
    ),
    "proof_dashboard": (
        "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_dashboard.json",
        "rblganul_a10_3_avengers_kombucha_stress_50_50_dashboard.json",
    ),
    "stride_memory": (
        "rblganul_a9_11_v32_zim_stride_memory.json",
        "rblganul_a10_3_avengers_kombucha_stress_zim_stride_memory.json",
    ),
    "strategy_rates": (
        "rblganul_a9_11_v32_strategy_rates.json",
        "rblganul_a10_3_avengers_kombucha_stress_strategy_rates.json",
    ),
    "tail_events": (
        "rblganul_a9_11_v32_tail_events.jsonl",
        "rblganul_a10_3_avengers_kombucha_stress_tail_events.jsonl",
    ),
    "rare_tail_timing_dashboard": (
        "rblganul_a9_11_v32_rare_tail_timing_summary.json",
        "rblganul_a10_3_avengers_kombucha_stress_rare_tail_timing_summary.json",
    ),
    "rare_tail_timing_events": (
        "rblganul_a9_11_v32_rare_tail_timing_z32_plus.jsonl",
        "rblganul_a10_3_avengers_kombucha_stress_rare_tail_timing_z32_plus.jsonl",
    ),
    "rare_tail_timing_csv": (
        "rblganul_a9_11_v32_rare_tail_timing_z32_plus.csv",
        "rblganul_a10_3_avengers_kombucha_stress_rare_tail_timing_z32_plus.csv",
    ),
    "janus_glyph_summary": (
        "rblganul_a9_11_v32_janus_glyph_summary.json",
        "rblganul_a10_3_avengers_kombucha_stress_janus_glyph_summary.json",
    ),
    "janus_glyph_events": (
        "rblganul_a9_11_v32_janus_glyph_events.jsonl",
        "rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.jsonl",
    ),
    "janus_glyph_csv": (
        "rblganul_a9_11_v32_janus_glyph_events.csv",
        "rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.csv",
    ),
    "dual_lock_memory": (
        "rblganul_a9_11_v32_dual_lock_memory.json",
        "rblganul_a10_3_avengers_kombucha_stress_dual_lock_memory.json",
    ),
    "a9_accounting_dashboard": (
        "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_accounting.json",
        "rblganul_a10_3_avengers_kombucha_stress_50_50_accounting.json",
    ),
    "witchhunter_dashboard": (
        "rblganul_a9_11_v32_witchhunter_dark_tail.json",
        "rblganul_a10_3_avengers_kombucha_stress_witchhunter_dark_tail.json",
    ),
    "witchhunter_events": (
        "rblganul_a9_11_v32_witchhunter_dark_tail_events.jsonl",
        "rblganul_a10_3_avengers_kombucha_stress_witchhunter_dark_tail_events.jsonl",
    ),
}


def _same_default(value: Any, old_name: str) -> bool:
    try:
        return str(value or "").replace("\\", "/").rstrip("/").split("/")[-1] == old_name
    except Exception:
        return False


class AvengersStressKombuchaMemory(base.KombuchaMemory):
    """Scheduler-only stress adapter layered over A9.11 KombuchaMemory.

    The molecule is deliberately "hard to digest": accepted shares reduce it,
    but do not erase it. Mirror pressure and rare-tail gaps raise it. Rejects
    raise acidity but batch sizing remains guarded by the original reject logic.
    """

    def __init__(self, strategies: Iterable[str], sectors: int, cfg_names: Iterable[str]):
        super().__init__(strategies, sectors, cfg_names)
        self.stress_molecule = 0.12
        self.stress_floor = 0.08
        self.stress_ceiling = 0.62
        self.stress_decay = 0.9985
        self.stress_choices = 0
        self.janus_best_z = 0
        self.mirror_best_z = 0
        self.janus_z32_hits = 0
        self.mirror_z32_hits = 0
        self.last_stress_reason = "warmup"

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(value)))

    @staticmethod
    def _lane_group(lane: Any) -> str:
        name = str(lane or "")
        if name == "randomized_traversal_mirror":
            return "mirror"
        if name.startswith("janus_") or name == "janus_dispatcher":
            return "janus"
        return "other"

    def _apply_stress_pressure(self, delta: float, reason: str) -> None:
        value = self.stress_molecule * self.stress_decay + float(delta)
        self.stress_molecule = self._clamp(value, self.stress_floor, self.stress_ceiling)
        if reason:
            self.last_stress_reason = reason

        # Feed only scheduler instincts. Keep acidity as the brake.
        brake = 1.0 - min(0.65, self.acidity * 0.35)
        self.brew = self._clamp(max(self.brew, 0.035 + self.stress_molecule * 0.40 * brake), 0.03, 0.48)
        self.carbonation = self._clamp(max(self.carbonation, 0.62 + self.stress_molecule * 0.28 * brake), 0.35, 1.0)

    def update_result(self, r: Any) -> None:
        super().update_result(r)
        group = self._lane_group(getattr(r, "lane", ""))
        z = int(getattr(r, "best_z", 0) or 0)

        if group == "mirror":
            self.mirror_best_z = max(self.mirror_best_z, z)
            if z >= 32:
                self.mirror_z32_hits += 1
        elif group == "janus":
            self.janus_best_z = max(self.janus_best_z, z)
            if z >= 32:
                self.janus_z32_hits += 1

        best_gap = max(0, self.mirror_best_z - self.janus_best_z)
        tail_gap = max(0, self.mirror_z32_hits - self.janus_z32_hits)

        pressure = 0.0
        reason = ""
        if group == "mirror" and z >= 32:
            pressure += 0.010
            reason = "mirror_z32_pressure"
        elif group == "mirror" and z >= 30:
            pressure += 0.004
            reason = "mirror_z30_pressure"
        if best_gap >= 2:
            pressure += min(0.018, 0.004 * best_gap)
            reason = "mirror_best_gap"
        if tail_gap > 0:
            pressure += min(0.020, 0.003 * tail_gap)
            reason = "mirror_tail_gap"
        if group == "janus" and z >= 32:
            pressure -= 0.018
            reason = "janus_tail_relief"
        elif group == "janus" and z >= 30:
            pressure -= 0.006
            reason = "janus_z30_relief"

        self._apply_stress_pressure(pressure, reason)

    def on_submit_result(self, accepted: bool) -> None:
        super().on_submit_result(accepted)
        if accepted:
            # Non-digestible stress: success cools it, but leaves a small memory.
            self.stress_molecule = self._clamp(
                self.stress_floor + (self.stress_molecule - self.stress_floor) * 0.88,
                self.stress_floor,
                self.stress_ceiling,
            )
            self.last_stress_reason = "accepted_relief_nonzero_memory"
        else:
            self.stress_molecule = self._clamp(self.stress_molecule + 0.018, self.stress_floor, self.stress_ceiling)
            self.last_stress_reason = "reject_acid_guard"

    def _stress_choice(self, rng: random.Random, cfgs: List[Any]) -> Tuple[str, int, Any]:
        choices: List[Tuple[float, str, int, Any]] = []
        for st in self.strategies:
            for sec in range(self.sectors):
                for cfg in cfgs:
                    s: Dict[str, float] = self.stats[(st, sec, cfg.name)]
                    checked = max(0.0, float(s.get("checked", 0.0) or 0.0))
                    best_z = max(0.0, float(s.get("best_z", 0.0) or 0.0))
                    score = max(0.05, float(s.get("score", 1.0) or 1.0))
                    coverage_bonus = 1.0 / (1.0 + checked / 5_000_000.0)
                    tail_bonus = max(0.0, best_z - 24.0) / 16.0
                    canonical_bias = 1.08 if cfg.name == "canonical" else 0.95
                    weight = canonical_bias * (0.55 * score + 1.35 * coverage_bonus + 0.45 * tail_bonus)
                    choices.append((max(0.01, weight), st, sec, cfg))
        total = sum(x[0] for x in choices) or 1.0
        pick = rng.random() * total
        acc = 0.0
        for weight, st, sec, cfg in choices:
            acc += weight
            if acc >= pick:
                self.stress_choices += 1
                return st, sec, cfg
        _, st, sec, cfg = choices[-1]
        self.stress_choices += 1
        return st, sec, cfg

    def choose(self, rng: random.Random, cfgs: List[Any], round_id: int, worker_id: int) -> Tuple[str, int, Any]:
        if int(round_id or 0) >= 4:
            chance = min(0.30, 0.035 + self.stress_molecule * 0.32)
            if rng.random() < chance:
                return self._stress_choice(rng, cfgs)
        return super().choose(rng, cfgs, round_id, worker_id)

    def next_batch(self, base_batch: int, accepted: int, rejected: int) -> int:
        raw = super().next_batch(base_batch, accepted, rejected)
        if rejected > 0 and accepted == 0:
            return raw
        factor = 1.0 + min(0.18, self.stress_molecule * 0.24)
        return max(10_000, min(2_000_000, int(raw * factor)))

    def line(self, next_batch: int) -> str:
        return (
            f"{super().line(next_batch)} "
            f"stress_molecule={self.stress_molecule:.3f} "
            f"stress_choices={self.stress_choices} "
            f"janus_best={self.janus_best_z} mirror_best={self.mirror_best_z} "
            f"janus_z32={self.janus_z32_hits} mirror_z32={self.mirror_z32_hits} "
            f"reason={self.last_stress_reason}"
        )


_original_parse_args = base.parse_args


def parse_args_with_a10_defaults() -> argparse.Namespace:
    args = _original_parse_args()
    if getattr(args, "io_run_name", "") == "A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_AFTER_A9_10":
        args.io_run_name = A10_DEFAULT_RUN_NAME
    for attr, (old_name, new_name) in DEFAULT_RENAMES.items():
        if hasattr(args, attr) and _same_default(getattr(args, attr), old_name):
            setattr(args, attr, new_name)
    return args


def install() -> None:
    base.VERSION = A10_VERSION
    base.SENTINEL = A10_SENTINEL
    base.KombuchaMemory = AvengersStressKombuchaMemory
    base.parse_args = parse_args_with_a10_defaults


def main() -> None:
    install()
    base.main()


if __name__ == "__main__":
    # Keep Windows ProcessPoolExecutor happy when this wrapper is the entrypoint.
    mp.freeze_support()
    try:
        main()
    except KeyboardInterrupt:
        base.log("done", "Interrupted by operator; writing session summary")
        try:
            base.write_session_summary(base.SESSION_STATE.get("summary_path", "session_summary.json"))
        except Exception:
            pass
        sys.exit(130)
