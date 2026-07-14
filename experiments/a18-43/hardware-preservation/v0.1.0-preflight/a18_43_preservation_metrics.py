#!/usr/bin/env python3
"""Pure, deterministic A18.43 preservation metrics.

No miner control and no hardware writes occur in this module.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from typing import Any, Iterable

SCHEMA = "JANUS/A18.43/preservation-metrics/v0.1.0"


def _numbers(values: Iterable[Any]) -> list[float]:
    return [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))]


def trapezoid_integral(samples: list[dict[str, Any]], value_key: str) -> float | None:
    rows = sorted(
        [(float(r["t_monotonic"]), float(r[value_key])) for r in samples
         if isinstance(r.get("t_monotonic"), (int, float)) and isinstance(r.get(value_key), (int, float))],
        key=lambda x: x[0],
    )
    if len(rows) < 2:
        return None
    total = 0.0
    for (t0, v0), (t1, v1) in zip(rows, rows[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        total += dt * (v0 + v1) / 2.0
    return total


def thermal_degree_seconds(samples: list[dict[str, Any]], value_key: str, threshold_c: float) -> float | None:
    transformed = []
    for row in samples:
        value = row.get(value_key)
        if isinstance(value, (int, float)):
            transformed.append({"t_monotonic": row.get("t_monotonic"), "excess": max(0.0, float(value) - threshold_c)})
    return trapezoid_integral(transformed, "excess")


def derived_cpu_percent(samples: list[dict[str, Any]], logical_cpus: int) -> float | None:
    rows = sorted(
        [(float(r["t_monotonic"]), float(r["process_tree_cpu_seconds_total"])) for r in samples
         if isinstance(r.get("t_monotonic"), (int, float)) and isinstance(r.get("process_tree_cpu_seconds_total"), (int, float))],
        key=lambda x: x[0],
    )
    if len(rows) < 2 or logical_cpus <= 0:
        return None
    elapsed = rows[-1][0] - rows[0][0]
    cpu_delta = rows[-1][1] - rows[0][1]
    if elapsed <= 0 or cpu_delta < 0:
        return None
    return 100.0 * cpu_delta / (elapsed * logical_cpus)


def coefficient_of_variation(values: Iterable[Any]) -> float | None:
    rows = _numbers(values)
    if len(rows) < 2:
        return None
    mean = statistics.fmean(rows)
    if mean == 0:
        return None
    return statistics.pstdev(rows) / abs(mean)


def waste_summary(counts: dict[str, Any]) -> dict[str, Any]:
    useful = int(counts.get("useful_completed_batches") or 0)
    fields = [
        "post_target_overflow_batches", "stale_batches", "duplicate_batches",
        "reconnect_invalidated_batches", "queue_overshoot_batches",
        "shutdown_latency_batches", "unaccountable_batches",
    ]
    waste = {field: int(counts.get(field) or 0) for field in fields}
    total_waste = sum(waste.values())
    all_work = useful + total_waste
    return {
        "schema": SCHEMA,
        "useful_completed_batches": useful,
        "waste_batches": waste,
        "total_waste_batches": total_waste,
        "all_accounted_batches": all_work,
        "useful_work_fraction": (useful / all_work) if all_work else None,
        "waste_work_fraction": (total_waste / all_work) if all_work else None,
    }


def claim_readiness(sensor_types: set[str], stable_identity: bool, sample_count: int) -> dict[str, Any]:
    thermal = "Temperature" in sensor_types and "Load" in sensor_types and stable_identity and sample_count >= 20
    energy = thermal and "Power" in sensor_types
    fan = thermal and ("Fan" in sensor_types or "Control" in sensor_types)
    return {
        "thermal_challenge_ready": thermal,
        "direct_energy_claim_ready": energy,
        "fan_wear_metrics_ready": fan,
        "energy_claim_block_reason": None if energy else "NO_STABLE_POWER_SENSOR_OR_BASELINE",
        "hardware_lifetime_claim_ready": False,
        "hardware_lifetime_claim_block_reason": "REQUIRES_LONGITUDINAL_DEVICE_HEALTH_HISTORY",
    }


def self_test() -> int:
    power = [
        {"t_monotonic": 0.0, "power": 100.0},
        {"t_monotonic": 1.0, "power": 100.0},
        {"t_monotonic": 2.0, "power": 200.0},
    ]
    assert abs((trapezoid_integral(power, "power") or 0) - 250.0) < 1e-9
    temps = [
        {"t_monotonic": 0.0, "temp": 70.0},
        {"t_monotonic": 1.0, "temp": 80.0},
        {"t_monotonic": 2.0, "temp": 80.0},
    ]
    assert abs((thermal_degree_seconds(temps, "temp", 75.0) or 0) - 7.5) < 1e-9
    cpu = [
        {"t_monotonic": 0.0, "process_tree_cpu_seconds_total": 10.0},
        {"t_monotonic": 2.0, "process_tree_cpu_seconds_total": 18.0},
    ]
    assert abs((derived_cpu_percent(cpu, 4) or 0) - 100.0) < 1e-9
    w = waste_summary({"useful_completed_batches": 8, "post_target_overflow_batches": 2})
    assert w["total_waste_batches"] == 2 and abs(w["useful_work_fraction"] - 0.8) < 1e-9
    r = claim_readiness({"Temperature", "Load", "Power", "Fan"}, True, 30)
    assert r["thermal_challenge_ready"] and r["direct_energy_claim_ready"] and r["fan_wear_metrics_ready"]
    print(json.dumps({"schema": SCHEMA, "status": "PASS", "tests": 5}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    return self_test() if args.self_test else 0


if __name__ == "__main__":
    raise SystemExit(main())
