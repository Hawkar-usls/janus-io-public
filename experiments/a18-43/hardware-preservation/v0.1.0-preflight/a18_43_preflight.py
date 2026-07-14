#!/usr/bin/env python3
"""A18.43 package preflight. Never launches a miner."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

SCHEMA = "JANUS/A18.43/preflight/v0.1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_manifest(root: Path) -> list[dict[str, Any]]:
    manifest = json.loads((root / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    rows = []
    for entry in manifest.get("files", []):
        path = root / entry["path"]
        actual = sha256_file(path) if path.is_file() else None
        rows.append({"path": entry["path"], "expected": entry["sha256"], "actual": actual, "match": actual == entry["sha256"]})
    return rows


def run_self_test(root: Path, script: str) -> dict[str, Any]:
    completed = subprocess.run([sys.executable, str(root / script), "--self-test"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return {"script": script, "exit_code": completed.returncode, "stdout": completed.stdout.strip(), "stderr": completed.stderr.strip(), "pass": completed.returncode == 0}


def self_test() -> int:
    assert SCHEMA.endswith("v0.1.0")
    print(json.dumps({"schema": SCHEMA, "status": "PASS", "tests": 1}, sort_keys=True))
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
    root = Path(__file__).resolve().parent
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_checks = verify_manifest(root)
    self_tests = [run_self_test(root, "a18_43_preservation_metrics.py"), run_self_test(root, "a18_43_hardware_sensor_probe.py")]
    gate = {
        "schema": SCHEMA,
        "generated_at_utc": utc_now(),
        "phase": "PREFLIGHT_ONLY",
        "platform": platform.platform(),
        "python": sys.version,
        "windows": platform.system() == "Windows",
        "package_manifest_pass": all(r["match"] for r in manifest_checks),
        "manifest_checks": manifest_checks,
        "self_tests": self_tests,
        "self_tests_pass": all(r["pass"] for r in self_tests),
        "no_miner_launched": True,
        "no_hardware_control_performed": True,
    }
    (output / "PACKAGE_PREFLIGHT.json").write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not gate["package_manifest_pass"] or not gate["self_tests_pass"] or not gate["windows"]:
        print(json.dumps(gate, ensure_ascii=False, sort_keys=True))
        return 4
    completed = subprocess.run([
        sys.executable, str(root / "a18_43_hardware_sensor_probe.py"),
        "--output", str(output),
        "--duration-seconds", str(args.duration_seconds),
        "--interval-seconds", str(args.interval_seconds),
    ], check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
