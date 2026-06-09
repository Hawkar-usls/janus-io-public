#!/usr/bin/env python3
"""Offline pool-behavior window comparison for JANUS runs.

The script classifies local telemetry into explicit windows, for example
operator/Codex interaction windows versus quiet control windows. It never
connects to a pool and never modifies proof artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TAILS = (23, 24, 25, 26, 28, 30, 32, 33, 34, 35, 36, 37, 38, 39)


def parse_iso(value: str) -> datetime:
    text = str(value or "").strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_windows(path: Path) -> List[Dict[str, Any]]:
    data = load_json(path)
    windows = data.get("windows", []) if isinstance(data, dict) else []
    out = []
    for item in windows:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "interaction"))
        try:
            start = parse_iso(str(item["start_utc"]))
            end = parse_iso(str(item["end_utc"]))
        except Exception:
            continue
        if end <= start:
            continue
        out.append({
            "label": label,
            "start": start,
            "end": end,
            "note": str(item.get("note", "")),
        })
    return sorted(out, key=lambda x: (x["start"], x["end"]))


def classify(dt: datetime, windows: List[Dict[str, Any]]) -> str:
    for w in windows:
        if w["start"] <= dt <= w["end"]:
            return str(w["label"])
    return "quiet"


def inc_tail(counter: Counter, zbits: int) -> None:
    for z in TAILS:
        if zbits >= z:
            counter[f"z{z}"] += 1


def base_bucket() -> Dict[str, Any]:
    return {
        "lab_rows": 0,
        "submitted_delta": 0,
        "accepted_delta": 0,
        "rejected_delta": 0,
        "job_changes": 0,
        "jobs": set(),
        "hps": [],
        "lab_best_z": 0,
        "accepted_proofs": 0,
        "proof_best_z": 0,
        "proof_tails": Counter(),
        "proof_groups": Counter(),
        "proof_job_age_ms": [],
        "glyph_rows": 0,
        "glyph_families": Counter(),
        "glyph_family_job_ntime": defaultdict(set),
        "glyph_keywords": Counter(),
    }


def read_lab(run_dir: Path, windows: List[Dict[str, Any]], buckets: Dict[str, Dict[str, Any]]) -> None:
    paths = sorted(run_dir.glob("*_lab.csv"))
    if not paths:
        return
    path = paths[-1]
    prev: Optional[Dict[str, int]] = None
    prev_job: Optional[str] = None
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.fromtimestamp(int(float(row.get("ts", "0"))), timezone.utc)
            except Exception:
                continue
            label = classify(dt, windows)
            b = buckets[label]
            b["lab_rows"] += 1
            job = str(row.get("job", ""))
            if job:
                b["jobs"].add(job)
                if prev_job is not None and job != prev_job:
                    b["job_changes"] += 1
                prev_job = job
            try:
                b["hps"].append(float(row.get("hps") or 0))
            except Exception:
                pass
            try:
                b["lab_best_z"] = max(int(b["lab_best_z"]), int(float(row.get("best_z") or 0)))
            except Exception:
                pass
            curr = {}
            for field in ("submitted", "accepted", "rejected"):
                try:
                    curr[field] = int(float(row.get(field) or 0))
                except Exception:
                    curr[field] = 0
            if prev is None:
                delta = curr
            elif any(curr[k] < prev.get(k, 0) for k in curr):
                delta = curr
            else:
                delta = {k: max(0, curr[k] - prev.get(k, 0)) for k in curr}
            b["submitted_delta"] += int(delta.get("submitted", 0))
            b["accepted_delta"] += int(delta.get("accepted", 0))
            b["rejected_delta"] += int(delta.get("rejected", 0))
            prev = curr


def read_proofs(run_dir: Path, windows: List[Dict[str, Any]], buckets: Dict[str, Dict[str, Any]]) -> None:
    proofs = sorted((run_dir / "proofs").glob("accepted_20*_z*_nonce0x*.json"))
    for path in proofs:
        data = load_json(path)
        try:
            dt = parse_iso(str(data.get("created_at_utc") or data.get("accepted_at_utc")))
        except Exception:
            continue
        label = classify(dt, windows)
        b = buckets[label]
        z = 0
        try:
            z = int((data.get("hash") or {}).get("zbits") or data.get("zbits") or 0)
        except Exception:
            z = 0
        b["accepted_proofs"] += 1
        b["proof_best_z"] = max(int(b["proof_best_z"]), z)
        inc_tail(b["proof_tails"], z)
        miner = data.get("miner") if isinstance(data.get("miner"), dict) else {}
        lane = str(miner.get("lane") or data.get("lane") or "")
        if lane.startswith("random_mirror:"):
            group = "randomized_traversal_mirror"
        elif lane.startswith("janus_bunnyhop_rescout:"):
            group = "janus_bunnyhop_rescout"
        elif lane.startswith("janus_bunnyhop_scout:"):
            group = "janus_bunnyhop_scout"
        elif "janus" in lane:
            group = "janus_broad_mixture"
        else:
            group = "unknown"
        b["proof_groups"][group] += 1
        try:
            job = data.get("job") if isinstance(data.get("job"), dict) else {}
            accepted_ms = int(parse_iso(str(data.get("created_at_utc"))).timestamp() * 1000)
            age = accepted_ms - int(job.get("received_ms") or accepted_ms)
            if age >= 0:
                b["proof_job_age_ms"].append(age)
        except Exception:
            pass


def read_glyphs(run_dir: Path, windows: List[Dict[str, Any]], buckets: Dict[str, Dict[str, Any]]) -> None:
    path = run_dir / "rblganul_a10_3_avengers_kombucha_stress_janus_glyph_events.jsonl"
    if not path.exists():
        matches = list(run_dir.glob("*glyph_events.jsonl"))
        path = matches[0] if matches else path
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except Exception:
                continue
            try:
                dt = parse_iso(str(row.get("observed_at_utc") or row.get("written_at_utc")))
            except Exception:
                continue
            label = classify(dt, windows)
            b = buckets[label]
            b["glyph_rows"] += 1
            families = row.get("mirror_families")
            if not isinstance(families, list):
                families = [c for c in row.get("categories", []) if str(c).endswith("_mirror_family")] if isinstance(row.get("categories"), list) else []
            job_key = "|".join(str(x or "") for x in (row.get("job_id"), row.get("ntime")))
            for family in families:
                if not family:
                    continue
                b["glyph_families"][str(family)] += 1
                if job_key.strip("|"):
                    b["glyph_family_job_ntime"][str(family)].add(job_key)
            for kw in row.get("keywords") or []:
                b["glyph_keywords"][str(kw)] += 1


def finalize_bucket(bucket: Dict[str, Any]) -> Dict[str, Any]:
    submitted = int(bucket["submitted_delta"])
    rejected = int(bucket["rejected_delta"])
    hps = [x for x in bucket["hps"] if x > 0]
    ages = bucket["proof_job_age_ms"]
    accepted_proofs = int(bucket["accepted_proofs"])
    proof_tails = dict(bucket["proof_tails"])
    tail_per_1000 = {
        k: round((int(v) / accepted_proofs * 1000.0), 4) if accepted_proofs else 0.0
        for k, v in proof_tails.items()
    }
    return {
        "lab_rows": bucket["lab_rows"],
        "submitted_delta": submitted,
        "accepted_delta": int(bucket["accepted_delta"]),
        "rejected_delta": rejected,
        "reject_pct": (rejected / submitted * 100.0) if submitted else 0.0,
        "job_changes": bucket["job_changes"],
        "unique_jobs_seen": len(bucket["jobs"]),
        "hps_avg": round(statistics.mean(hps), 2) if hps else 0,
        "lab_best_z": int(bucket["lab_best_z"]),
        "accepted_proofs": accepted_proofs,
        "proof_best_z": int(bucket["proof_best_z"]),
        "proof_tails": proof_tails,
        "proof_tail_per_1000": tail_per_1000,
        "proof_groups": dict(bucket["proof_groups"]),
        "proof_job_age_ms_avg": round(statistics.mean(ages), 2) if ages else 0,
        "proof_job_age_ms_median": round(statistics.median(ages), 2) if ages else 0,
        "glyph_rows": int(bucket["glyph_rows"]),
        "glyph_families": dict(bucket["glyph_families"]),
        "glyph_family_job_ntime": {k: len(v) for k, v in bucket["glyph_family_job_ntime"].items()},
        "glyph_keywords": dict(bucket["glyph_keywords"].most_common(16)),
    }


def write_markdown(path: Path, run_dir: Path, windows: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
    interaction = result.get("interaction", {})
    quiet = result.get("quiet", {})
    interaction_rates = interaction.get("proof_tail_per_1000", {}) if isinstance(interaction, dict) else {}
    quiet_rates = quiet.get("proof_tail_per_1000", {}) if isinstance(quiet, dict) else {}
    lines = [
        "# A10.3 Pool Behavior: Interaction vs Quiet - 2026-06-09",
        "",
        "Status: derived offline report from local JANUS telemetry.",
        "",
        "No network mining was started by this report. Raw proof artifacts were not rewritten.",
        "",
        "## Run",
        "",
        "```text",
        f"run_dir: {run_dir.name}",
        "pool: pool.nerdminers.org:3333",
        "pool_diff: 0.001",
        "frozen_wire: wire_change_required=false in dashboard/proof artifacts",
        "```",
        "",
        "## Window Model",
        "",
        "Interaction windows are explicit operator/Codex activity windows. Quiet is the complement inside the same local run.",
        "",
        "```text",
    ]
    for w in windows:
        lines.append(f"{w['label']}: {iso(w['start'])} -> {iso(w['end'])}  {w.get('note','')}")
    lines += [
        "```",
        "",
        "## Comparison",
        "",
        "| metric | interaction | quiet |",
        "| --- | ---: | ---: |",
    ]
    metrics = [
        "submitted_delta", "accepted_delta", "rejected_delta", "reject_pct",
        "job_changes", "unique_jobs_seen", "hps_avg", "lab_best_z",
        "accepted_proofs", "proof_best_z", "proof_job_age_ms_avg",
        "glyph_rows",
    ]
    for m in metrics:
        lines.append(f"| `{m}` | `{interaction.get(m, 0)}` | `{quiet.get(m, 0)}` |")
    lines += [
        "",
        "## Rare Tails",
        "",
        "```text",
        f"interaction: {interaction.get('proof_tails', {})}",
        f"quiet:       {quiet.get('proof_tails', {})}",
        "```",
        "",
        "Normalized per 1000 accepted proofs:",
        "",
        "```text",
        f"interaction: {interaction.get('proof_tail_per_1000', {})}",
        f"quiet:       {quiet.get('proof_tail_per_1000', {})}",
        "```",
        "",
        "## Groups",
        "",
        "```text",
        f"interaction: {interaction.get('proof_groups', {})}",
        f"quiet:       {quiet.get('proof_groups', {})}",
        "```",
        "",
        "## Glyph Families",
        "",
        "```text",
        f"interaction rows: {interaction.get('glyph_families', {})}",
        f"interaction job_id|ntime: {interaction.get('glyph_family_job_ntime', {})}",
        f"quiet rows: {quiet.get('glyph_families', {})}",
        f"quiet job_id|ntime: {quiet.get('glyph_family_job_ntime', {})}",
        "```",
        "",
        "## Current Signal",
        "",
        "```text",
        f"interaction z33/z34 per 1000: {interaction_rates.get('z33', 0)} / {interaction_rates.get('z34', 0)}",
        f"quiet z33/z34/z35 per 1000: {quiet_rates.get('z33', 0)} / {quiet_rates.get('z34', 0)} / {quiet_rates.get('z35', 0)}",
        f"interaction reject_pct: {interaction.get('reject_pct', 0)}",
        f"quiet reject_pct: {quiet.get('reject_pct', 0)}",
        f"interaction job_age_ms_avg: {interaction.get('proof_job_age_ms_avg', 0)}",
        f"quiet job_age_ms_avg: {quiet.get('proof_job_age_ms_avg', 0)}",
        "",
        "Current reading: interaction windows show slightly higher z33/z34 density,",
        "but quiet windows still hold the single z35 and overall best_z. Reject%",
        "is also slightly higher during interaction. Job age is essentially equal.",
        "The pLEA/AELp family appears only inside interaction windows so far,",
        "but only as one independent job_id|ntime source.",
        "```",
        "",
        "## Preliminary Reading",
        "",
        "```text",
        "This report can show correlation windows, not pool memory or intent.",
        "The current strongest falsifiable question is whether JANUS-active windows",
        "produce a repeatable shift in reject%, job-age-at-accept, z-tail density,",
        "or independent glyph-family repeats compared with quiet windows.",
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--windows", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()
    run_dir = Path(args.run_dir)
    windows = load_windows(Path(args.windows))
    buckets: Dict[str, Dict[str, Any]] = defaultdict(base_bucket)
    read_lab(run_dir, windows, buckets)
    read_proofs(run_dir, windows, buckets)
    read_glyphs(run_dir, windows, buckets)
    result = {label: finalize_bucket(bucket) for label, bucket in sorted(buckets.items())}
    result["windows"] = [
        {"label": w["label"], "start_utc": iso(w["start"]), "end_utc": iso(w["end"]), "note": w.get("note", "")}
        for w in windows
    ]
    result["run_dir"] = str(run_dir)
    Path(args.out_json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(Path(args.out_md), run_dir, windows, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
