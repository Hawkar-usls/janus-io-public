#!/usr/bin/env python3
"""Read-only OpenHardwareMonitor WMI sensor probe for JANUS A18.43."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

from a18_43_preservation_metrics import claim_readiness

SCHEMA = "JANUS/A18.43/hardware-sensor-probe/v0.1.0"
NAMESPACE = "root/OpenHardwareMonitor"
SENSOR_CLASS = "Sensor"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def normalize_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []
    rows = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        rows.append({
            "name": item.get("Name"),
            "identifier": item.get("Identifier"),
            "parent": item.get("Parent"),
            "sensor_type": item.get("SensorType"),
            "value": item.get("Value"),
            "min": item.get("Min"),
            "max": item.get("Max"),
            "index": item.get("Index"),
        })
    rows.sort(key=lambda r: (str(r.get("sensor_type")), str(r.get("identifier"))))
    return rows


def query_windows_sensors(timeout_seconds: float = 15.0) -> list[dict[str, Any]]:
    if platform.system() != "Windows":
        raise RuntimeError("WINDOWS_REQUIRED_FOR_OPENHARDWAREMONITOR_WMI")
    script = r"""
$ErrorActionPreference = 'Stop'
try {
  $rows = @(Get-CimInstance -Namespace 'root/OpenHardwareMonitor' -ClassName 'Sensor' -ErrorAction Stop |
    Select-Object Name,Identifier,Parent,SensorType,Value,Min,Max,Index)
} catch {
  $rows = @(Get-WmiObject -Namespace 'root\OpenHardwareMonitor' -Class 'Sensor' -ErrorAction Stop |
    Select-Object Name,Identifier,Parent,SensorType,Value,Min,Max,Index)
}
$rows | ConvertTo-Json -Depth 4 -Compress
""".strip()
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()[-1200:]
        raise RuntimeError(f"OPENHARDWAREMONITOR_WMI_QUERY_FAILED: {tail}")
    text = completed.stdout.strip()
    if not text:
        return []
    return normalize_rows(json.loads(text))


def inventory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sensor_type = str(row.get("sensor_type") or "UNKNOWN")
        by_type.setdefault(sensor_type, []).append({
            "name": row.get("name"), "identifier": row.get("identifier"),
            "parent": row.get("parent"), "index": row.get("index"),
            "initial_value": row.get("value"),
        })
    return {
        "schema": "JANUS/A18.43/sensor-inventory/v0.1.0",
        "generated_at_utc": utc_now(),
        "provider": "OpenHardwareMonitor",
        "namespace": NAMESPACE,
        "sensor_count": len(rows),
        "sensor_types": sorted(by_type),
        "sensors_by_type": by_type,
    }


def run_probe(output_dir: Path, duration_seconds: float, interval_seconds: float) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples_path = output_dir / "HARDWARE_SAMPLES.jsonl"
    samples_path.unlink(missing_ok=True)
    first = query_windows_sensors()
    if not first:
        raise RuntimeError("OPENHARDWAREMONITOR_RETURNED_NO_SENSORS")
    first_ids = tuple(str(r.get("identifier")) for r in first)
    inv = inventory(first)
    atomic_json(output_dir / "SENSOR_INVENTORY.json", inv)
    started = time.monotonic()
    sample_count = 0
    identity_stable = True
    changed_values = 0
    previous = {str(r.get("identifier")): r.get("value") for r in first}
    while True:
        rows = query_windows_sensors()
        now = time.monotonic()
        ids = tuple(str(r.get("identifier")) for r in rows)
        identity_stable = identity_stable and ids == first_ids
        current = {str(r.get("identifier")): r.get("value") for r in rows}
        changed_values += sum(1 for key, value in current.items() if key in previous and value != previous[key])
        previous = current
        append_jsonl(samples_path, {
            "schema": "JANUS/A18.43/hardware-sample/v0.1.0",
            "ts_utc": utc_now(), "t_monotonic": now,
            "sample_index": sample_count, "sensors": rows,
        })
        sample_count += 1
        if now - started >= duration_seconds:
            break
        time.sleep(max(0.05, interval_seconds))
    types = set(inv["sensor_types"])
    readiness = claim_readiness(types, identity_stable, sample_count)
    if readiness["direct_energy_claim_ready"]:
        status = "PASS_ENERGY_AND_THERMAL_SENSOR_BASELINE"
    elif readiness["thermal_challenge_ready"]:
        status = "PARTIAL_THERMAL_ONLY_NO_DIRECT_POWER_SENSOR"
    else:
        status = "FAIL_CLOSED_INSUFFICIENT_SENSOR_BASELINE"
    report = {
        "schema": SCHEMA,
        "generated_at_utc": utc_now(),
        "status": status,
        "platform": platform.platform(),
        "python": sys.version,
        "provider": "OpenHardwareMonitor",
        "namespace": NAMESPACE,
        "sample_count": sample_count,
        "duration_seconds": time.monotonic() - started,
        "interval_seconds_requested": interval_seconds,
        "sensor_identity_stable": identity_stable,
        "changed_value_observations": changed_values,
        "sensor_types": sorted(types),
        "claim_readiness": readiness,
        "no_miner_launched": True,
        "no_hardware_control_performed": True,
        "outputs": {
            "inventory": str(output_dir / "SENSOR_INVENTORY.json"),
            "samples": str(samples_path),
        },
    }
    atomic_json(output_dir / "A18_43_PREFLIGHT_REPORT.json", report)
    return report


def self_test() -> int:
    mock = normalize_rows({"Name":"GPU Core","Identifier":"/gpu/0/temperature/0","Parent":"/gpu/0","SensorType":"Temperature","Value":55.0,"Min":40.0,"Max":60.0,"Index":0})
    assert len(mock) == 1 and mock[0]["sensor_type"] == "Temperature"
    inv = inventory(mock)
    assert inv["sensor_count"] == 1 and inv["sensor_types"] == ["Temperature"]
    print(json.dumps({"schema": SCHEMA, "status": "PASS", "tests": 2}, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "output"))
    parser.add_argument("--duration-seconds", type=float, default=15.0)
    parser.add_argument("--interval-seconds", type=float, default=0.5)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        report = run_probe(Path(args.output).resolve(), args.duration_seconds, args.interval_seconds)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["status"].startswith("PASS") or report["status"].startswith("PARTIAL") else 4
    except Exception as exc:
        output = Path(args.output).resolve()
        failure = {
            "schema": SCHEMA, "generated_at_utc": utc_now(),
            "status": "FAIL_CLOSED", "error": str(exc),
            "no_miner_launched": True, "no_hardware_control_performed": True,
            "recovery": [
                "Run OpenHardwareMonitor.exe as Administrator.",
                "Keep OpenHardwareMonitor running during PREFLIGHT_ONLY.",
                "Verify that CPU/GPU sensors are enabled.",
                "Run PREFLIGHT_ONLY.cmd again."
            ]
        }
        atomic_json(output / "A18_43_PREFLIGHT_REPORT.json", failure)
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
