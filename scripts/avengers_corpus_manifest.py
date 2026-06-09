#!/usr/bin/env python3
"""Build a private, read-only Avengers corpus manifest.

This is an offline repository tool. It does not start mining, connect to a
pool, or inspect raw proof payloads. Proof files are counted by filename and
mtime only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


RUN_GLOB = "A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50*"
ACCT_NAME = "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_accounting.json"
DASH_NAME = "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_dashboard.json"
BOUNDARY_NAME = "a9_11_fresh_session_boundary.json"
WITCHHUNTER_NAME = "rblganul_a9_11_v32_witchhunter_dark_tail.json"
ACCEPTED_GLOB = "accepted_20*_z*_nonce0x*.json"
TAILS = (30, 32, 33, 34, 35, 36, 37, 38, 39)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_mtime(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def file_entry(path: Path, label: Optional[str] = None) -> Dict[str, Any]:
    exists = path.exists()
    entry: Dict[str, Any] = {
        "label": label or path.name,
        "path": str(path),
        "exists": exists,
    }
    if exists:
        stat = path.stat()
        entry.update({
            "bytes": stat.st_size,
            "modified_at_utc": iso_mtime(path),
        })
    return entry


def count_files(paths: Iterable[Path]) -> Dict[str, Any]:
    count = 0
    total_bytes = 0
    newest: Optional[Path] = None
    for path in paths:
        if not path.is_file():
            continue
        count += 1
        stat = path.stat()
        total_bytes += stat.st_size
        if newest is None or stat.st_mtime > newest.stat().st_mtime:
            newest = path
    return {
        "count": count,
        "bytes": total_bytes,
        "newest_path": str(newest) if newest else None,
        "newest_modified_at_utc": iso_mtime(newest) if newest else None,
    }


def text_marker_counts(path: Path, markers: Iterable[str], max_bytes: int = 2_000_000) -> Dict[str, Any]:
    result: Dict[str, Any] = {marker: 0 for marker in markers}
    if not path.exists() or path.stat().st_size > max_bytes:
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in markers:
        result[marker] = text.count(marker)
    return result


def newest_a911_run(runs_root: Path) -> Optional[Path]:
    candidates = [
        path for path in runs_root.glob(RUN_GLOB)
        if path.is_dir() and (path / ACCT_NAME).exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def count_fresh_accepted(proofs_dir: Path, fresh_start: datetime) -> int:
    if not proofs_dir.exists():
        return 0
    count = 0
    for path in proofs_dir.glob(ACCEPTED_GLOB):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if mtime >= fresh_start:
            count += 1
    return count


def group_summary(group: Dict[str, Any]) -> Dict[str, Any]:
    tails = group.get("accepted_tails") or {}
    return {
        "accepted": group.get("accepted"),
        "best_z": group.get("best_z"),
        "tails": {f"z{z}": tails.get(f"z{z}", 0) for z in TAILS},
    }


def summarize_a911(runs_root: Path) -> Dict[str, Any]:
    run_dir = newest_a911_run(runs_root)
    if run_dir is None:
        return {"present": False, "reason": f"no {RUN_GLOB} run with accounting found"}

    acct = load_json(run_dir / ACCT_NAME)
    boundary = load_json(run_dir / BOUNDARY_NAME) if (run_dir / BOUNDARY_NAME).exists() else {}
    dash = load_json(run_dir / DASH_NAME) if (run_dir / DASH_NAME).exists() else {}
    wh = load_json(run_dir / WITCHHUNTER_NAME) if (run_dir / WITCHHUNTER_NAME).exists() else {}
    fresh_start_value = boundary.get("fresh_started_at_utc")
    fresh_count = None
    if fresh_start_value:
        fresh_count = count_fresh_accepted(run_dir / "proofs", parse_utc(fresh_start_value))
    boundary_snapshots = summarize_boundaries(run_dir)

    janus = nested(acct, "groups", "janus_bunnyhop_arm", default={})
    mirror = nested(acct, "groups", "randomized_traversal_mirror", default={})
    return {
        "present": True,
        "run_name": run_dir.name,
        "run_path": str(run_dir),
        "written_at_utc": acct.get("written_at_utc"),
        "fresh_started_at_utc": fresh_start_value,
        "fresh_accepted_share_corpus": fresh_count,
        "archived_fresh_boundaries": boundary_snapshots,
        "health": {
            "reject_rate": nested(acct, "health", "reject_rate"),
            "cooldown": nested(acct, "health", "cooldown"),
            "hps_ewma": dash.get("hps_ewma"),
        },
        "bunnyhop": {
            "phase": nested(acct, "bunnyhop", "phase"),
            "reason": nested(acct, "bunnyhop", "reason"),
        },
        "wire": {
            "wire_change_required": acct.get("wire_change_required"),
            "status": "frozen" if acct.get("wire_change_required") is False else "review_required",
        },
        "janus": group_summary(janus),
        "randomized_traversal_mirror": group_summary(mirror),
        "witchhunter": {
            "highest_dark_z": wh.get("highest_dark_z"),
            "janus_dark_events": wh.get("janus_dark_events"),
            "mirror_dark_events": wh.get("mirror_dark_events"),
        },
        "proof_file_count_by_filename_only": count_files((run_dir / "proofs").glob(ACCEPTED_GLOB)),
    }


def summarize_boundaries(run_dir: Path, limit: int = 12) -> Dict[str, Any]:
    proofs_dir = run_dir / "proofs"
    rows: List[Dict[str, Any]] = []
    for path in sorted(run_dir.glob("a9_11_fresh_session_boundary*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            obj = load_json(path)
            fresh_start = obj.get("fresh_started_at_utc")
            fresh_count = count_fresh_accepted(proofs_dir, parse_utc(fresh_start)) if fresh_start else None
            rows.append({
                "name": path.name,
                "modified_at_utc": iso_mtime(path),
                "fresh_started_at_utc": fresh_start,
                "fresh_accepted_share_corpus": fresh_count,
                "previous_accepted_proof_files": obj.get("previous_accepted_proof_files"),
                "wire_change_required": obj.get("wire_change_required"),
            })
        except Exception as exc:
            rows.append({
                "name": path.name,
                "modified_at_utc": iso_mtime(path),
                "error": str(exc),
            })
    valid = [row for row in rows if isinstance(row.get("fresh_accepted_share_corpus"), int)]
    max_row = max(valid, key=lambda row: int(row.get("fresh_accepted_share_corpus") or 0)) if valid else None
    gate_7000_rows = [row for row in valid if int(row.get("fresh_accepted_share_corpus") or 0) >= 7000]
    nearest_7000 = (
        min(gate_7000_rows, key=lambda row: abs(int(row.get("fresh_accepted_share_corpus") or 0) - 7000))
        if gate_7000_rows else None
    )
    return {
        "latest": rows[0] if rows else None,
        "max_fresh_corpus_boundary": max_row,
        "nearest_7000_gate_boundary": nearest_7000,
        "recent": rows[:limit],
    }


def summarize_runs(runs_root: Path) -> Dict[str, Any]:
    if not runs_root.exists():
        return {"present": False, "path": str(runs_root)}
    run_dirs = [path for path in runs_root.iterdir() if path.is_dir()]
    return {
        "present": True,
        "path": str(runs_root),
        "run_dir_count": len(run_dirs),
        "newest_run_dir": str(max(run_dirs, key=lambda path: path.stat().st_mtime)) if run_dirs else None,
        "a9_11_latest": summarize_a911(runs_root),
    }


def summarize_nas_brain(janus_root: Path) -> Dict[str, Any]:
    root = janus_root / "janus_nas_brain"
    files = [
        root / "janus_nas_brain.py",
        root / "README.md",
        root / "docker-compose.yml",
        root / "NAS_BRAIN_FACE_MOLD.md",
    ]
    markers = {
        "janus_nas_brain.py": [
            "DEFAULT_PORT",
            "/api/swarm/sense",
            "/api/swarm/telemetry",
            "/api/swarm/corpus",
            "/api/swarm/voice",
            "/api/device/command",
        ],
        "README.md": [
            "5000",
            "/api/swarm/sense",
            "never fake shares",
            "never change pool target",
            "never increase submit pressure",
        ],
    }
    return {
        "present": root.exists(),
        "path": str(root),
        "files": [file_entry(path) for path in files],
        "markers": {
            name: text_marker_counts(root / name, values)
            for name, values in markers.items()
        },
    }


def summarize_lastswarm(janus_root: Path) -> Dict[str, Any]:
    root = janus_root / "LastSwarm"
    sketches = [
        ("ADV_Elite", root / "ADV_Elite.ino"),
        ("Core2", root / "CORE2.ino"),
        ("Yaks_Gate", root / "Yaks_Gate" / "Yaks_Gate.ino"),
    ]
    markers = [
        "esp_now",
        "HTTPClient",
        "SwarmSensePacket",
        "A9FieldSense",
        "/api/swarm/sense",
        "/api/swarm/telemetry",
        "/api/swarm/voice",
        ":5000",
        ":8008",
    ]
    return {
        "present": root.exists(),
        "path": str(root),
        "sketches": [
            {
                **file_entry(path, label=name),
                "markers": text_marker_counts(path, markers),
            }
            for name, path in sketches
        ],
        "review_findings": [
            "Review local ESP32/NAS endpoint ports before enabling live swarm advisory output."
        ],
    }


def summarize_exports(janus_root: Path) -> Dict[str, Any]:
    exports_root = janus_root / "J" / "jgpt_pc_bridge_v12_swarm_demiurge" / "exports"
    if not exports_root.exists():
        return {"present": False, "path": str(exports_root)}
    files = sorted(exports_root.glob("nas_quant_cycle_*_int8.json"))
    return {
        "present": True,
        "path": str(exports_root),
        "nas_quant_cycle_int8": count_files(files),
    }


def build_manifest(i0_root: Path, janus_root: Optional[Path]) -> Dict[str, Any]:
    i0_root = i0_root.resolve()
    janus_root = (janus_root or (i0_root.parent / "Janus")).resolve()
    return {
        "codename": "Avengers",
        "generated_at_utc": utc_now(),
        "doctrine": {
            "stance": "deadpool_clause",
            "summary": (
                "Keep prior PoW work visible, use it as the allied baseline, "
                "and add JANUS scheduler/corpus/swarm telemetry without "
                "claiming to replace the underlying proof primitives."
            ),
            "deadpool_multiverse": (
                "JANUS is plural: runner generations, NAS Brain, ESP32 Swarm, "
                "WitchHunter, ProofMind, and the randomized mirror preserve "
                "artifacts so the experiment can regenerate across versions."
            ),
            "source_anchors": [
                "https://bitcoin.org/bitcoin.pdf",
                "https://primecoin.io/primecoin-paper.pdf",
                "https://cryptopapers.info/assets/pdf/cuckoo.pdf",
                "https://ledger.pitt.edu/ojs/ledger/article/view/48",
            ],
        },
        "safety": {
            "read_only_manifest": True,
            "starts_miner": False,
            "connects_to_pool": False,
            "changes_wire": False,
            "inspects_raw_proof_payloads": False,
            "proofs_counted_by_filename_only": True,
        },
        "roots": {
            "i0": str(i0_root),
            "janus": str(janus_root),
        },
        "i0": {
            "runs": summarize_runs(i0_root / "janus_io_o1_runs"),
            "runner": file_entry(i0_root / "RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py"),
            "docs": count_files((i0_root / "docs").glob("*.md")) if (i0_root / "docs").exists() else {"count": 0},
        },
        "nas_brain": summarize_nas_brain(janus_root),
        "lastswarm": summarize_lastswarm(janus_root),
        "exports": summarize_exports(janus_root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--i0-root", type=Path, default=Path.cwd())
    parser.add_argument("--janus-root", type=Path)
    parser.add_argument("--output", type=Path, help="optional private output path")
    args = parser.parse_args()

    manifest = build_manifest(args.i0_root, args.janus_root)
    text = json.dumps(manifest, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
