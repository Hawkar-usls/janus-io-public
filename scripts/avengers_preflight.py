#!/usr/bin/env python3
"""Run offline Avengers readiness checks.

This script is intentionally passive. It does not start miners, write to NAS,
connect to a pool, or change repository files. If --nas-url is supplied it only
performs a read-only HTTP GET health check.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def check_exists(label: str, path: Path, required: bool = True) -> Dict[str, Any]:
    exists = path.exists()
    return {
        "label": label,
        "path": str(path),
        "required": required,
        "ok": exists or not required,
        "exists": exists,
    }


def check_py_compile(label: str, path: Path) -> Dict[str, Any]:
    result = check_exists(label, path)
    if not result["exists"]:
        return result
    try:
        py_compile.compile(str(path), doraise=True)
        result["ok"] = True
    except py_compile.PyCompileError as exc:
        result["ok"] = False
        result["error"] = str(exc)
    return result


def read_only_get(url: str, timeout: float) -> Dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(2048)
        return {
            "url": url,
            "ok": 200 <= response.status < 300,
            "status": response.status,
            "sample": body.decode("utf-8", errors="replace")[:500],
        }
    except urllib.error.HTTPError as exc:
        body = exc.read(2048)
        return {
            "url": url,
            "ok": False,
            "status": exc.code,
            "sample": body.decode("utf-8", errors="replace")[:500],
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(exc),
        }


def read_only_health(base_url: str, timeout: float) -> Dict[str, Any]:
    paths = ("/health", "/api/status", "/api/swarm/status")
    attempts = [read_only_get(base_url.rstrip("/") + path, timeout) for path in paths]
    return {
        "base_url": base_url,
        "ok": any(attempt["ok"] for attempt in attempts),
        "attempts": attempts,
    }


def build_preflight(i0_root: Path, janus_root: Optional[Path], nas_url: Optional[str], timeout: float) -> Dict[str, Any]:
    i0_root = i0_root.resolve()
    janus_root = (janus_root or (i0_root.parent / "Janus")).resolve()
    checks: List[Dict[str, Any]] = [
        check_exists("A9.11 runner present", i0_root / "RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py"),
        check_exists("A9.11 docs present", i0_root / "docs" / "a9-11-active-triune-sovereign-gate-50-50.md"),
        check_exists("Avengers plan present", i0_root / "docs" / "avengers-integration-plan.md"),
        check_exists("Avengers config example present", i0_root / "avengers" / "avengers_config.example.json"),
        check_exists("NAS Brain present", janus_root / "janus_nas_brain" / "janus_nas_brain.py"),
        check_exists("NAS Brain README present", janus_root / "janus_nas_brain" / "README.md"),
        check_exists("LastSwarm ADV sketch present", janus_root / "LastSwarm" / "ADV_Elite.ino"),
        check_exists("LastSwarm Core2 sketch present", janus_root / "LastSwarm" / "CORE2.ino"),
        check_exists("LastSwarm Yaks sketch present", janus_root / "LastSwarm" / "Yaks_Gate" / "Yaks_Gate.ino"),
        check_py_compile("avengers_corpus_manifest.py compiles", i0_root / "scripts" / "avengers_corpus_manifest.py"),
        check_py_compile("avengers_preflight.py compiles", i0_root / "scripts" / "avengers_preflight.py"),
        check_py_compile("janus_nas_brain.py compiles", janus_root / "janus_nas_brain" / "janus_nas_brain.py"),
    ]
    nas_check = None
    if nas_url:
        nas_check = read_only_health(nas_url, timeout)
        checks.append({
            "label": "NAS Brain read-only health paths",
            "path": nas_url.rstrip("/"),
            "required": False,
            "ok": nas_check["ok"],
            "exists": nas_check["ok"],
            "detail": nas_check,
        })

    hard_failures = [check for check in checks if check.get("required", True) and not check.get("ok")]
    review_findings = [
        "Review Yaks_Gate YG_NAS_BRAIN_URL before device launch: current manifest logic expects NAS Brain on port 5000.",
        "Manual operator must start any benchmark runner; Avengers scripts do not start mining.",
        "Keep randomized traversal mirror enabled for controlled comparisons.",
        "JANUS-first swarm policy: NAS/ESP32 hints may feed JANUS-side priors only, never mirror hints, submit pressure, or wire.",
    ]
    return {
        "codename": "Avengers",
        "generated_at_utc": utc_now(),
        "safety": {
            "starts_miner": False,
            "connects_to_pool": False,
            "writes_to_nas": False,
            "changes_wire": False,
            "nas_check_is_get_only": bool(nas_url),
        },
        "ready_for_offline_manifest": not hard_failures,
        "ready_for_live_private_run": False,
        "manual_launch_required": True,
        "checks": checks,
        "nas_check": nas_check,
        "review_findings": review_findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--i0-root", type=Path, default=Path.cwd())
    parser.add_argument("--janus-root", type=Path)
    parser.add_argument("--nas-url", help="optional read-only NAS Brain base URL")
    parser.add_argument("--output", type=Path, help="optional private output path")
    parser.add_argument("--timeout", type=float, default=1.5)
    args = parser.parse_args()
    report = build_preflight(args.i0_root, args.janus_root, args.nas_url, args.timeout)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
