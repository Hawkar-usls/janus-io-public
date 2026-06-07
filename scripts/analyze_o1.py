#!/usr/bin/env python3
"""Offline analyzer for Janus Io O1 experiment artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


AGENTS = (
    "A0_RANDOM_PURE",
    "A1_LINEAR_PURE",
    "A2_ZIM_ONLY",
    "A3_JANUS_FULL",
    "A4_DUAL_LOCK_TEST",
)
THRESHOLDS = (24, 28, 30, 32)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Optional[Any]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def parse_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default


def parse_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default


def mean(values: Iterable[float]) -> float:
    clean = [float(v) for v in values if v is not None]
    return statistics.fmean(clean) if clean else 0.0


def pstdev(values: Iterable[float]) -> float:
    clean = [float(v) for v in values if v is not None]
    return statistics.pstdev(clean) if len(clean) > 1 else 0.0


def fresh_stats(agent: str) -> Dict[str, Any]:
    return {
        "agent": agent,
        "sources": [],
        "accepted_candidates": [],
        "rejected_candidates": [],
        "submitted_candidates": [],
        "best_z_candidates": [],
        "proof_z": [],
        "best_z_samples": [],
        "hps_samples": [],
        "checked_hashes": 0,
        "duration_seconds": 0.0,
    }


def add_source(stats: Dict[str, Any], source: str) -> None:
    if source not in stats["sources"]:
        stats["sources"].append(source)


def public_source(source: str) -> str:
    base, sep, fragment = source.partition("#")
    try:
        path = Path(base)
        if path.exists():
            rel = path.resolve().relative_to(repo_root())
            cleaned = rel.as_posix()
        else:
            cleaned = base
    except (OSError, ValueError):
        cleaned = base
    return cleaned + (sep + fragment if sep else "")


def ingest_report(stats_by_agent: Dict[str, Dict[str, Any]], report_path: Path) -> None:
    report = load_json(report_path)
    if not isinstance(report, dict):
        return
    agents = report.get("agents")
    if not isinstance(agents, dict):
        return
    for agent, data in agents.items():
        if agent not in stats_by_agent or not isinstance(data, dict):
            continue
        stats = stats_by_agent[agent]
        add_source(stats, str(report_path))
        stats["accepted_candidates"].append(parse_int(data.get("accepted")))
        stats["rejected_candidates"].append(parse_int(data.get("rejected")))
        stats["submitted_candidates"].append(parse_int(data.get("submitted")))
        stats["best_z_candidates"].append(parse_int(data.get("best_z")))
        last_hps = parse_float(data.get("last_hps"))
        if last_hps:
            stats["hps_samples"].append(last_hps)
        session = data.get("session_summary")
        if isinstance(session, dict):
            ingest_summary_dict(stats, session, f"{report_path}#session_summary")


def ingest_events(stats_by_agent: Dict[str, Dict[str, Any]], events_path: Path) -> None:
    try:
        lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        agent = event.get("agent")
        if agent in stats_by_agent:
            add_source(stats_by_agent[agent], str(events_path))
            stats_by_agent[agent]["duration_seconds"] += parse_float(event.get("elapsed_seconds"))


def ingest_summary_dict(stats: Dict[str, Any], data: Dict[str, Any], source: str) -> None:
    add_source(stats, source)
    stats["accepted_candidates"].append(parse_int(data.get("accepted")))
    stats["rejected_candidates"].append(parse_int(data.get("rejected")))
    stats["submitted_candidates"].append(parse_int(data.get("submitted")))
    stats["best_z_candidates"].append(parse_int(data.get("best_z")))
    stats["duration_seconds"] += parse_float(data.get("duration_seconds"))
    last_hps = parse_float(data.get("last_hps"))
    if last_hps:
        stats["hps_samples"].append(last_hps)


def ingest_summaries(stats: Dict[str, Any], agent_dir: Path) -> None:
    for path in sorted(agent_dir.glob("*_session_summary.json")):
        data = load_json(path)
        if isinstance(data, dict):
            ingest_summary_dict(stats, data, str(path))


def ingest_csv(stats: Dict[str, Any], agent_dir: Path) -> None:
    for path in sorted(agent_dir.glob("*_lab.csv")):
        try:
            with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except OSError:
            continue
        if not rows:
            continue
        add_source(stats, str(path))
        for row in rows:
            checked = parse_int(row.get("checked"))
            hps = parse_float(row.get("hps"))
            best_z = parse_int(row.get("best_z"))
            stats["checked_hashes"] += checked
            if hps:
                stats["hps_samples"].append(hps)
            if best_z:
                stats["best_z_samples"].append(best_z)
                stats["best_z_candidates"].append(best_z)
        last = rows[-1]
        stats["accepted_candidates"].append(parse_int(last.get("accepted")))
        stats["rejected_candidates"].append(parse_int(last.get("rejected")))
        stats["submitted_candidates"].append(parse_int(last.get("submitted")))


def ingest_proofs(stats: Dict[str, Any], agent_dir: Path) -> None:
    proofs_dir = agent_dir / "proofs"
    if not proofs_dir.exists():
        return
    index = proofs_dir / "accepted_index.json"
    data = load_json(index)
    accepted: List[Any] = []
    if isinstance(data, dict) and isinstance(data.get("accepted"), list):
        accepted = data["accepted"]
        add_source(stats, str(index))
    elif isinstance(data, list):
        accepted = data
        add_source(stats, str(index))
    if not accepted:
        for path in sorted(proofs_dir.glob("accepted_*.json")):
            item = load_json(path)
            if isinstance(item, dict):
                accepted.append(item)
        if accepted:
            add_source(stats, str(proofs_dir))
    if accepted:
        stats["accepted_candidates"].append(len(accepted))
    for item in accepted:
        if isinstance(item, dict):
            zbits = parse_int(item.get("zbits") or item.get("z") or item.get("best_z"))
            if zbits:
                stats["proof_z"].append(zbits)
                stats["best_z_candidates"].append(zbits)


LOG_CHECKED_RE = re.compile(r"\bchecked=([0-9][0-9,]*)")
LOG_HPS_RE = re.compile(r"(?<![A-Za-z_])hps[~=:]([0-9][0-9,]*)")
LOG_BEST_Z_RE = re.compile(r"\bbest_z=(\d+)")
LOG_ACCEPT_RE = re.compile(r"\bACCEPTED\b")
LOG_REJECT_RE = re.compile(r"\bREJECT(?:ED)?\b")


def ingest_logs(stats: Dict[str, Any], agent_dir: Path) -> None:
    log_paths = sorted(agent_dir.glob("slot_*.log"))
    if not log_paths and (agent_dir / "raw_log.txt").exists():
        log_paths = [agent_dir / "raw_log.txt"]
    accepted = 0
    rejected = 0
    for path in log_paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        add_source(stats, str(path))
        for match in LOG_CHECKED_RE.finditer(text):
            stats["checked_hashes"] += parse_int(match.group(1))
        for match in LOG_HPS_RE.finditer(text):
            hps = parse_float(match.group(1))
            if hps:
                stats["hps_samples"].append(hps)
        for match in LOG_BEST_Z_RE.finditer(text):
            best_z = parse_int(match.group(1))
            if best_z:
                stats["best_z_samples"].append(best_z)
                stats["best_z_candidates"].append(best_z)
        accepted += len(LOG_ACCEPT_RE.findall(text))
        rejected += len(LOG_REJECT_RE.findall(text))
    if accepted:
        stats["accepted_candidates"].append(accepted)
    if rejected:
        stats["rejected_candidates"].append(rejected)


def finalize(stats: Dict[str, Any]) -> Dict[str, Any]:
    accepted = max(stats["accepted_candidates"] or [0])
    rejected = max(stats["rejected_candidates"] or [0])
    submitted = max(stats["submitted_candidates"] or [accepted + rejected])
    best_z = max(stats["best_z_candidates"] or [0])
    hps_mean = mean(stats["hps_samples"])
    hps_std = pstdev(stats["hps_samples"])
    total_hashes = int(stats["checked_hashes"])
    if total_hashes <= 0 and hps_mean and stats["duration_seconds"]:
        total_hashes = int(hps_mean * stats["duration_seconds"])
    total_mh = total_hashes / 1_000_000.0 if total_hashes > 0 else 0.0
    z_samples = stats["best_z_samples"] or stats["proof_z"]
    z_counts = {f"z{threshold}": sum(1 for z in z_samples if z >= threshold) for threshold in THRESHOLDS}

    def per_mh(count: int) -> float:
        return float(count) / total_mh if total_mh else 0.0

    out = {
        "accepted": accepted,
        "rejected": rejected,
        "submitted": submitted,
        "best_z": best_z,
        "total_hashes": total_hashes,
        "total_MH": total_mh,
        "accepted_per_MH": per_mh(accepted),
        "reject_rate": float(rejected) / float(submitted) if submitted else 0.0,
        "hps_mean": hps_mean,
        "hps_std": hps_std,
        "z_threshold_counts": z_counts,
        "z24_per_MH": per_mh(z_counts["z24"]),
        "z28_per_MH": per_mh(z_counts["z28"]),
        "z30_per_MH": per_mh(z_counts["z30"]),
        "z32_per_MH": per_mh(z_counts["z32"]),
        "sources": [public_source(source) for source in stats["sources"]],
    }
    return out


def write_markdown(path: Path, summary: Dict[str, Any]) -> None:
    rows = []
    for agent in AGENTS:
        metrics = summary["agents"].get(agent, {})
        rows.append(
            "| {agent} | {accepted} | {rejected} | {best_z} | {mh:.3f} | {apmh:.6f} | "
            "{z24:.6f} | {z28:.6f} | {z30:.6f} | {z32:.6f} | {reject:.6f} | "
            "{hps_mean:.2f} | {hps_std:.2f} |".format(
                agent=agent,
                accepted=metrics.get("accepted", 0),
                rejected=metrics.get("rejected", 0),
                best_z=metrics.get("best_z", 0),
                mh=metrics.get("total_MH", 0.0),
                apmh=metrics.get("accepted_per_MH", 0.0),
                z24=metrics.get("z24_per_MH", 0.0),
                z28=metrics.get("z28_per_MH", 0.0),
                z30=metrics.get("z30_per_MH", 0.0),
                z32=metrics.get("z32_per_MH", 0.0),
                reject=metrics.get("reject_rate", 0.0),
                hps_mean=metrics.get("hps_mean", 0.0),
                hps_std=metrics.get("hps_std", 0.0),
            )
        )
    body = [
        "# O1-01 Analysis Summary",
        "",
        f"Generated: {summary['generated_at_utc']}",
        f"Input root: `{summary['input_root']}`",
        "",
        "| Agent | Accepted | Rejected | Best z | MH | accepted/MH | z24/MH | z28/MH | z30/MH | z32/MH | reject rate | hps mean | hps std |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *rows,
        "",
        "Rates are normalized by observed or estimated MH. z-threshold rates use best-z samples from lab CSV/log telemetry when available, falling back to accepted proof zbits.",
        "",
    ]
    path.write_text("\n".join(body), encoding="utf-8")


def main() -> int:
    root = repo_root()
    default_input = root / "janus_io_o1_runs"
    if not default_input.exists():
        default_input = root / "experiments" / "o1-01"
    parser = argparse.ArgumentParser(description="Analyze Janus Io O1 artifacts offline.")
    parser.add_argument("--input-root", type=Path, default=default_input)
    parser.add_argument("--output-dir", type=Path, default=root / "experiments" / "o1-01")
    args = parser.parse_args()

    input_root = args.input_root
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    stats_by_agent = {agent: fresh_stats(agent) for agent in AGENTS}
    ingest_report(stats_by_agent, input_root / "o1_report.json")
    ingest_events(stats_by_agent, input_root / "o1_events.jsonl")
    for agent in AGENTS:
        agent_dir = input_root / agent
        if not agent_dir.exists():
            continue
        stats = stats_by_agent[agent]
        ingest_summaries(stats, agent_dir)
        ingest_csv(stats, agent_dir)
        ingest_proofs(stats, agent_dir)
        ingest_logs(stats, agent_dir)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_root": str(input_root.relative_to(root) if input_root.is_relative_to(root) else input_root),
        "agents": {agent: finalize(stats_by_agent[agent]) for agent in AGENTS},
    }

    json_path = output_dir / "o1_analysis_summary.json"
    md_path = output_dir / "o1_analysis_summary.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(md_path, summary)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
