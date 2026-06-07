#!/usr/bin/env python3
"""Emit a public-safe A9.11 summary from local accounting artifacts.

The script is read-only by default. It does not inspect raw proof payloads; it
counts accepted proof filenames after the fresh boundary and summarizes the
accounting/dashboard/WitchHunter JSON files.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


RUN_GLOB = "A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50*"
ACCT_NAME = "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_accounting.json"
DASH_NAME = "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_dashboard.json"
BOUNDARY_NAME = "a9_11_fresh_session_boundary.json"
WITCHHUNTER_NAME = "rblganul_a9_11_v32_witchhunter_dark_tail.json"


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_utc(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def newest_run(base: Path) -> Path:
    candidates = [
        path for path in base.glob(RUN_GLOB)
        if path.is_dir() and (path / ACCT_NAME).exists()
    ]
    if not candidates:
        raise SystemExit(f"No A9.11 run with {ACCT_NAME} found under {base}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def count_fresh_accepted(proofs_dir: Path, fresh_start: datetime) -> int:
    if not proofs_dir.exists():
        return 0
    count = 0
    for path in proofs_dir.glob("accepted_20*_z*_nonce0x*.json"):
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if mtime >= fresh_start:
            count += 1
    return count


def nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def group_summary(group: Dict[str, Any]) -> Dict[str, Any]:
    tails = group.get("accepted_tails") or {}
    return {
        "accepted": group.get("accepted"),
        "best_z": group.get("best_z"),
        "tails": {f"z{z}": tails.get(f"z{z}", 0) for z in range(30, 41)},
    }


def build_snapshot(run_dir: Path) -> Dict[str, Any]:
    acct = load_json(run_dir / ACCT_NAME)
    boundary = load_json(run_dir / BOUNDARY_NAME)
    dash = load_json(run_dir / DASH_NAME) if (run_dir / DASH_NAME).exists() else {}
    wh = load_json(run_dir / WITCHHUNTER_NAME) if (run_dir / WITCHHUNTER_NAME).exists() else {}

    fresh_start = parse_utc(boundary["fresh_started_at_utc"])
    fresh_count = count_fresh_accepted(run_dir / "proofs", fresh_start)

    janus = nested(acct, "groups", "janus_bunnyhop_arm", default={})
    mirror = nested(acct, "groups", "randomized_traversal_mirror", default={})

    return {
        "run": run_dir.name,
        "written_at_utc": acct.get("written_at_utc"),
        "fresh_started_at_utc": boundary.get("fresh_started_at_utc"),
        "fresh_accepted_share_corpus": fresh_count,
        "health": {
            "accepted": nested(acct, "health", "accepted"),
            "submitted": nested(acct, "health", "submitted"),
            "rejected": nested(acct, "health", "rejected"),
            "reject_rate": nested(acct, "health", "reject_rate"),
            "cooldown": nested(acct, "health", "cooldown"),
            "proofmind_mode": nested(acct, "health", "proofmind_mode"),
            "hps_ewma": dash.get("hps_ewma"),
            "proofmind_best_z_seen": nested(dash, "proofmind", "best_z_seen"),
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
        "publication_note": (
            "Public-safe summary only. Raw proof files, local paths, worker labels, "
            "and live run state are intentionally excluded."
        ),
    }


def row(label: str, data: Dict[str, Any]) -> str:
    tails = data["tails"]
    cells: Iterable[Any] = [
        label,
        data.get("accepted"),
        data.get("best_z"),
        tails["z30"],
        tails["z32"],
        tails["z33"],
        tails["z34"],
        tails["z35"],
        tails["z36"],
        tails["z37"],
        tails["z38"],
    ]
    return "| " + " | ".join(str(cell) for cell in cells) + " |"


def render_markdown(snapshot: Dict[str, Any]) -> str:
    health = snapshot["health"]
    bunnyhop = snapshot["bunnyhop"]
    wire = snapshot["wire"]
    wh = snapshot["witchhunter"]
    lines = [
        "# A9.11 Public-Safe Snapshot",
        "",
        "This summary excludes raw proof payloads, local paths, worker labels, and live dashboards.",
        "",
        "```text",
        f"run: {snapshot['run']}",
        f"written_at_utc: {snapshot['written_at_utc']}",
        f"fresh_started_at_utc: {snapshot['fresh_started_at_utc']}",
        f"fresh accepted-share corpus: {snapshot['fresh_accepted_share_corpus']}",
        f"phase: {bunnyhop['phase']}",
        f"reason: {bunnyhop['reason']}",
        f"reject_rate: {health['reject_rate']}",
        f"hps_ewma: {health['hps_ewma']}",
        f"proofmind: {health['proofmind_mode']}",
        f"proofmind_best_z_seen: {health['proofmind_best_z_seen']}",
        f"frozen wire: wire_change_required={wire['wire_change_required']}",
        "```",
        "",
        "| side | accepted | best_z | z30+ | z32+ | z33+ | z34+ | z35+ | z36+ | z37+ | z38+ |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        row("JANUS", snapshot["janus"]),
        row("randomized traversal mirror", snapshot["randomized_traversal_mirror"]),
        "",
        "WitchHunter dark-tail summary:",
        "",
        "```text",
        f"highest_dark_z: {wh['highest_dark_z']}",
        f"JANUS dark events: {wh['janus_dark_events']}",
        f"mirror dark events: {wh['mirror_dark_events']}",
        "```",
        "",
        (
            "Verdict: public-safe traversal snapshot. Use as a curated summary "
            "only; do not treat it as a SHA-256 break, nonce-prediction claim, "
            "or block-discovery claim."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("janus_io_o1_runs"))
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path, help="optional curated output path")
    args = parser.parse_args()

    run_dir = args.run_dir or newest_run(args.base)
    snapshot = build_snapshot(run_dir)
    text = (
        json.dumps(snapshot, indent=2, sort_keys=True)
        if args.format == "json"
        else render_markdown(snapshot)
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
