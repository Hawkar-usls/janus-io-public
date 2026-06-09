#!/usr/bin/env python3
"""Build a passive JANUS-first Swarm advisory snapshot.

This script is read-only by default. It does not start miners, connect to a
pool, write to NAS, change wire policy, or feed the randomized traversal mirror.
If --nas-url is supplied it performs GET-only checks.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


A10_RUN_GLOB = "A10_AVENGERS_KOMBUCHA_STRESS*"
A10_ACCOUNTING = "rblganul_a10_3_avengers_kombucha_stress_50_50_accounting.json"
A10_DASHBOARD = "rblganul_a10_3_avengers_kombucha_stress_50_50_dashboard.json"
A10_WITCHHUNTER = "rblganul_a10_3_avengers_kombucha_stress_witchhunter_dark_tail.json"
NAS_PATHS = (
    "/api/status",
    "/api/swarm/status",
    "/api/swarm/archivarius/report",
)
TAILS = ("z30", "z32", "z33", "z34", "z35", "z36", "z38", "z39")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def read_only_get(url: str, timeout: float) -> Dict[str, Any]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(4096)
        text = raw.decode("utf-8", errors="replace")
        parsed: Optional[Any] = None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        return {
            "url": url,
            "ok": 200 <= int(response.status) < 300,
            "status": int(response.status),
            "sample": text[:500],
            "json": parsed if isinstance(parsed, dict) else None,
        }
    except urllib.error.HTTPError as exc:
        raw = exc.read(4096)
        return {
            "url": url,
            "ok": False,
            "status": int(exc.code),
            "sample": raw.decode("utf-8", errors="replace")[:500],
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(exc),
        }


def newest_run(i0_root: Path, explicit_run_dir: Optional[Path]) -> Optional[Path]:
    if explicit_run_dir:
        return explicit_run_dir.resolve()
    runs_root = i0_root / "janus_io_o1_runs"
    if not runs_root.exists():
        return None
    dirs = [p for p in runs_root.glob(A10_RUN_GLOB) if p.is_dir()]
    if not dirs:
        return None
    return max(dirs, key=lambda p: p.stat().st_mtime)


def group_summary(acct: Dict[str, Any], name: str) -> Dict[str, Any]:
    row = nested(acct, "groups", name, default={})
    tails = row.get("accepted_tails", {}) if isinstance(row, dict) else {}
    return {
        "accepted": int(row.get("accepted", 0) or 0) if isinstance(row, dict) else 0,
        "best_z": int(row.get("best_z", 0) or 0) if isinstance(row, dict) else 0,
        "tails": {tail: int(tails.get(tail, 0) or 0) for tail in TAILS},
    }


def summarize_run(run_dir: Optional[Path]) -> Dict[str, Any]:
    if run_dir is None:
        return {"exists": False, "reason": "no A10.3 run directory found"}

    acct_path = run_dir / A10_ACCOUNTING
    dash_path = run_dir / A10_DASHBOARD
    witch_path = run_dir / A10_WITCHHUNTER
    acct = load_json(acct_path) if acct_path.exists() else {}
    dash = load_json(dash_path) if dash_path.exists() else {}
    witch = load_json(witch_path) if witch_path.exists() else {}
    proofs_dir = run_dir / "proofs"
    proof_count = 0
    if proofs_dir.exists():
        proof_count = sum(1 for p in proofs_dir.glob("accepted_20*_z*_nonce0x*.json") if p.is_file())

    return {
        "exists": True,
        "run_dir": str(run_dir),
        "written_at_utc": acct.get("written_at_utc"),
        "proof_count": proof_count,
        "health": {
            "accepted": int(nested(acct, "health", "accepted", default=0) or 0),
            "submitted": int(nested(acct, "health", "submitted", default=0) or 0),
            "rejected": int(nested(acct, "health", "rejected", default=0) or 0),
            "reject_rate": float(nested(acct, "health", "reject_rate", default=0.0) or 0.0),
        },
        "bunnyhop": {
            "phase": nested(acct, "bunnyhop", "phase", default=""),
            "reason": nested(acct, "bunnyhop", "reason", default=""),
        },
        "wire_change_required": bool(acct.get("wire_change_required", False)),
        "janus": group_summary(acct, "janus_bunnyhop_arm"),
        "mirror": group_summary(acct, "randomized_traversal_mirror"),
        "proofmind": {
            "mode": nested(dash, "proofmind", "mode", default=""),
            "hunger": float(nested(dash, "proofmind", "hunger", default=0.0) or 0.0),
            "batch_factor": float(nested(dash, "endurance", "last_batch_factor", default=0.0) or 0.0),
            "cooldown": bool(nested(dash, "endurance", "cooldown", default=False)),
        },
        "witchhunter": {
            "highest_dark_z": int(witch.get("highest_dark_z", 0) or 0),
            "janus_dark_events": int(witch.get("janus_dark_events", 0) or 0),
            "mirror_dark_events": int(witch.get("mirror_dark_events", 0) or 0),
            "scheduler_effect": witch.get("scheduler_effect", "unknown"),
        },
    }


def summarize_nas(nas_url: Optional[str], timeout: float) -> Dict[str, Any]:
    if not nas_url:
        return {"enabled": False, "ok": False, "reason": "no --nas-url supplied"}
    base = nas_url.rstrip("/")
    attempts = [read_only_get(base + path, timeout) for path in NAS_PATHS]
    api_status = next((x for x in attempts if x["url"].endswith("/api/status")), {})
    swarm_ok = any(x.get("ok") and "/api/swarm/" in str(x.get("url", "")) for x in attempts)
    return {
        "enabled": True,
        "base_url": base,
        "ok": any(x.get("ok") for x in attempts),
        "gateway_ok": bool(api_status.get("ok")),
        "swarm_api_mapped": bool(swarm_ok),
        "service": nested(api_status.get("json") or {}, "service", default=""),
        "devices": nested(api_status.get("json") or {}, "devices", default=None),
        "nodes": nested(api_status.get("json") or {}, "nodes", default=None),
        "attempts": attempts,
    }


def summarize_lastswarm(janus_root: Path) -> Dict[str, Any]:
    root = janus_root / "LastSwarm"
    files = {
        "ADV_Elite": root / "ADV_Elite.ino",
        "Core2": root / "CORE2.ino",
        "Yaks_Gate": root / "Yaks_Gate" / "Yaks_Gate.ino",
        "ChaosDirector": root / "JANUS_CHAOS_DIRECTOR_MECHANICS.md",
    }
    return {
        "root": str(root),
        "available": root.exists(),
        "nodes": {name: path.exists() for name, path in files.items()},
    }


def choose_advisory(run: Dict[str, Any], nas: Dict[str, Any]) -> Dict[str, Any]:
    if not run.get("exists"):
        action = "WAIT_FOR_A10_3_RUN"
        reason = "no local A10.3 accounting found"
    elif run.get("wire_change_required"):
        action = "STOP_AND_INSPECT"
        reason = "wire_change_required is true"
    else:
        health = run.get("health", {})
        janus = run.get("janus", {})
        mirror = run.get("mirror", {})
        reject_rate = float(health.get("reject_rate", 0.0) or 0.0)
        accepted = int(health.get("accepted", 0) or 0)
        best_gap = int(mirror.get("best_z", 0) or 0) - int(janus.get("best_z", 0) or 0)
        z32_gap = int(mirror.get("tails", {}).get("z32", 0) or 0) - int(janus.get("tails", {}).get("z32", 0) or 0)
        if reject_rate > 0.02:
            action = "JANUS_SURVIVE_OBSERVER"
            reason = "reject pressure above 2 percent"
        elif best_gap >= 2 or z32_gap > 0:
            action = "JANUS_RESCOUT_PRESSURE"
            reason = f"mirror pressure best_gap={best_gap} z32_gap={z32_gap}"
        elif accepted < 1000:
            action = "JANUS_COLLECT_SCOUT_CORPUS"
            reason = "fresh accepted-share corpus below 1000"
        else:
            action = "JANUS_KEEP_STRESS_KOMBUCHA"
            reason = "baseline healthy; keep collecting"

    endpoint_status = "nas_swarm_ready" if nas.get("swarm_api_mapped") else "nas_gateway_only"
    return {
        "action": action,
        "reason": reason,
        "target_side": "JANUS_ONLY",
        "mirror_effect": "FORBIDDEN",
        "wire_effect": "NONE",
        "submit_gate_effect": "NONE",
        "nas_endpoint_status": endpoint_status,
        "janus_priors": {
            "allowed": True,
            "requires_explicit_runner_flag": True,
            "allowed_inputs": [
                "device_health",
                "thermal_hint",
                "radio_stability",
                "corpus_tags",
                "archivarius_memory",
                "operator_directive_context",
            ],
            "forbidden_inputs": [
                "mirror_hints",
                "target_mutation",
                "submit_pressure",
                "wire_bytes",
            ],
        },
    }


def build_report(i0_root: Path, janus_root: Optional[Path], run_dir: Optional[Path], nas_url: Optional[str], timeout: float) -> Dict[str, Any]:
    i0_root = i0_root.resolve()
    janus_root = (janus_root or (i0_root.parent / "Janus")).resolve()
    run = summarize_run(newest_run(i0_root, run_dir))
    nas = summarize_nas(nas_url, timeout)
    lastswarm = summarize_lastswarm(janus_root)
    return {
        "schema": "janus-first-swarm-advisory-1",
        "generated_at_utc": utc_now(),
        "policy": {
            "name": "JANUS_FIRST_SWARM_ADVISORY",
            "swarm_priority": "JANUS_FIRST",
            "mirror_effect": "FORBIDDEN",
            "writes_to_nas": False,
            "starts_miner": False,
            "connects_to_pool": False,
            "changes_wire": False,
            "changes_submit_gate": False,
        },
        "a10_3_run": run,
        "nas": nas,
        "lastswarm": lastswarm,
        "advisory": choose_advisory(run, nas),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--i0-root", type=Path, default=Path.cwd())
    parser.add_argument("--janus-root", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--nas-url", help="optional read-only NAS Brain base URL")
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--output", type=Path, help="optional local output path")
    args = parser.parse_args()

    report = build_report(args.i0_root, args.janus_root, args.run_dir, args.nas_url, args.timeout)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
