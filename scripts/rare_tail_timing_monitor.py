#!/usr/bin/env python3
"""Build and maintain a rare-tail timing index for JANUS accepted proofs.

This is an observer-only sidecar. It reads accepted proof JSON files and writes
derived timing tables. It never starts mining, never submits shares, never
changes scheduler decisions, and never mutates proof artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover - Python has zoneinfo, keep fallback tiny.
    ZoneInfo = None  # type: ignore[assignment]


ACCEPTED_RE = re.compile(
    r"^accepted_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_z(\d+)_nonce0x([0-9a-fA-F]+)_job(.+)\.json$"
)

FIELDNAMES = [
    "kyiv_time",
    "utc_time",
    "kyiv_hour",
    "z",
    "run",
    "group",
    "lane",
    "strategy",
    "sector",
    "worker_id",
    "job_seq",
    "job_id",
    "round_id",
    "accepted_total",
    "nonce",
    "hash_prefix",
    "proof_file",
]


def utc_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def kyiv_zone() -> timezone:
    if ZoneInfo is not None:
        try:
            return ZoneInfo("Europe/Kyiv")  # type: ignore[return-value]
        except Exception:
            pass
    return timezone.utc


def parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def filename_identity(path: Path) -> Optional[tuple[str, str, int, str, str]]:
    match = ACCEPTED_RE.match(path.name)
    if not match:
        return None
    date_s, time_s, z_s, nonce_s, job_s = match.groups()
    return date_s, time_s, int(z_s), nonce_s.lower(), job_s


def is_raw_duplicate(path: Path) -> bool:
    return any(part.lower() == "raw_accepted" for part in path.parts)


def iter_candidate_files(source: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        for dirpath, _, filenames in os.walk(source):
            base = Path(dirpath)
            for name in filenames:
                if ACCEPTED_RE.match(name):
                    yield base / name
        return

    proofs = source / "proofs"
    if not proofs.exists():
        return
    yield from proofs.glob("accepted_20*_z*_nonce0x*.json")
    raw = proofs / "raw_accepted"
    if raw.exists():
        yield from raw.glob("accepted_20*_z*_nonce0x*.json")


def choose_unique_files(source: Path, min_z: int, recursive: bool) -> List[Path]:
    chosen: Dict[tuple[str, str, int, str, str], Path] = {}
    for path in iter_candidate_files(source, recursive):
        ident = filename_identity(path)
        if ident is None:
            continue
        if ident[2] < min_z:
            continue
        previous = chosen.get(ident)
        if previous is None:
            chosen[ident] = path
            continue
        if is_raw_duplicate(previous) and not is_raw_duplicate(path):
            chosen[ident] = path
    return list(chosen.values())


def run_name_for(path: Path, source: Path, recursive: bool) -> str:
    if not recursive:
        return source.name
    try:
        return path.relative_to(source).parts[0]
    except Exception:
        return ""


def extract_row(path: Path, source: Path, recursive: bool, tz: timezone) -> Optional[Dict[str, object]]:
    ident = filename_identity(path)
    if ident is None:
        return None
    date_s, time_s, z_from_name, nonce_s, job_s = ident
    ts_from_name = f"{date_s}T{time_s.replace('-', ':')}Z"

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "error": str(exc),
            "proof_file": str(path),
        }

    raw = data.get("raw_candidate") or {}
    miner = data.get("miner") or {}
    labels = data.get("observer_labels") or {}
    triad = labels.get("sovereign_triad") or {}
    proof_hash = data.get("hash") or {}
    job_obj = data.get("job") or {}

    z = int(proof_hash.get("zbits") or raw.get("zbits") or z_from_name)
    ts_utc_raw = (
        data.get("created_at_utc")
        or raw.get("accepted_at_utc")
        or raw.get("submitted_at_utc")
        or data.get("submitted_at_utc")
        or ts_from_name
    )
    try:
        dt_utc = parse_utc(str(ts_utc_raw))
    except Exception:
        dt_utc = parse_utc(ts_from_name)
    dt_local = dt_utc.astimezone(tz)

    group = triad.get("group") or raw.get("group") or data.get("group") or ""
    lane = miner.get("lane") or raw.get("lane") or data.get("lane") or ""
    strategy = miner.get("strategy") or raw.get("strategy") or data.get("strategy") or ""
    sector = miner.get("sector") if miner.get("sector") is not None else raw.get("sector", data.get("sector", ""))
    worker_id = miner.get("worker_id") if miner.get("worker_id") is not None else raw.get("worker_id", "")
    round_id = miner.get("round_id") if miner.get("round_id") is not None else raw.get("round_id", "")
    job_seq = job_obj.get("seq") if job_obj.get("seq") is not None else raw.get("job_seq", "")
    display_hash = proof_hash.get("double_sha256_display_hex") or raw.get("display_hash", "")

    return {
        "kyiv_time": dt_local.strftime("%Y-%m-%d %H:%M:%S"),
        "utc_time": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kyiv_hour": dt_local.strftime("%H:00"),
        "z": z,
        "run": run_name_for(path, source, recursive),
        "group": group,
        "lane": lane,
        "strategy": strategy,
        "sector": sector,
        "worker_id": worker_id,
        "job_seq": job_seq,
        "job_id": job_obj.get("job_id") or raw.get("job_id") or job_s,
        "round_id": round_id,
        "accepted_total": raw.get("accepted_total", ""),
        "nonce": "0x" + nonce_s,
        "hash_prefix": str(display_hash)[:24],
        "proof_file": str(path),
    }


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def build_summary(rows: List[Dict[str, object]], source: Path, min_z: int, recursive: bool) -> Dict[str, object]:
    by_hour: Dict[str, List[int]] = defaultdict(list)
    by_run: Dict[str, int] = defaultdict(int)
    by_group: Dict[str, int] = defaultdict(int)
    for row in rows:
        z = int(row["z"])
        by_hour[str(row["kyiv_hour"])].append(z)
        by_run[str(row["run"])] += 1
        by_group[str(row["group"] or "unlabeled")] += 1

    hour_summary = {}
    for hour, zs in sorted(by_hour.items()):
        hour_summary[hour] = {
            "z32_plus": sum(1 for z in zs if z >= 32),
            "z33_plus": sum(1 for z in zs if z >= 33),
            "z34_plus": sum(1 for z in zs if z >= 34),
            "z35_plus": sum(1 for z in zs if z >= 35),
            "z36_plus": sum(1 for z in zs if z >= 36),
            "z38_plus": sum(1 for z in zs if z >= 38),
            "best_z": max(zs),
        }

    return {
        "schema": "janus-rare-tail-timing-monitor-1",
        "written_at_utc": utc_stamp(),
        "source": str(source),
        "source_mode": "scan_root" if recursive else "run_dir",
        "min_z": min_z,
        "rows": len(rows),
        "best_z": max((int(row["z"]) for row in rows), default=0),
        "first_utc": rows[0]["utc_time"] if rows else None,
        "last_utc": rows[-1]["utc_time"] if rows else None,
        "kyiv_hour_summary": hour_summary,
        "run_counts": dict(sorted(by_run.items())),
        "group_counts": dict(sorted(by_group.items())),
        "scheduler_effect": "observe_only",
        "wire_change_required": False,
        "note": "Timing metric only; counts are not MH-normalized exposure rates.",
    }


def write_outputs(source: Path, output_dir: Path, min_z: int, recursive: bool) -> Dict[str, object]:
    tz = kyiv_zone()
    rows: List[Dict[str, object]] = []
    errors: List[Dict[str, object]] = []
    for path in choose_unique_files(source, min_z=min_z, recursive=recursive):
        row = extract_row(path, source=source, recursive=recursive, tz=tz)
        if row is None:
            continue
        if "error" in row:
            errors.append(row)
            continue
        rows.append(row)

    rows.sort(key=lambda row: (str(row["utc_time"]), int(row["z"]), str(row["run"])))
    output_dir.mkdir(parents=True, exist_ok=True)
    base = f"rare_tail_timing_z{min_z}_plus"

    jsonl = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if jsonl:
        jsonl += "\n"
    atomic_write_text(output_dir / f"{base}.jsonl", jsonl)
    write_csv(output_dir / f"{base}.csv", rows)

    summary = build_summary(rows, source=source, min_z=min_z, recursive=recursive)
    summary["errors"] = errors[:25]
    summary["error_count"] = len(errors)
    atomic_write_text(
        output_dir / f"{base}_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run-dir", help="single JANUS run directory to monitor")
    group.add_argument("--scan-root", help="scan all run directories under a root")
    parser.add_argument("--output-dir", required=True, help="directory for JSONL/CSV/summary outputs")
    parser.add_argument("--min-z", type=int, default=32, help="minimum accepted tail zbits to index")
    parser.add_argument("--interval", type=float, default=15.0, help="seconds between monitor passes")
    parser.add_argument("--once", action="store_true", help="write one snapshot and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.run_dir or args.scan_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    recursive = bool(args.scan_root)

    previous_rows = -1
    while True:
        try:
            summary = write_outputs(source, output_dir=output_dir, min_z=args.min_z, recursive=recursive)
            rows = int(summary.get("rows", 0))
            new_rows = rows - previous_rows if previous_rows >= 0 else rows
            previous_rows = rows
            print(
                f"[RARETAIL/TIME] ok rows={rows} new={max(new_rows, 0)} "
                f"best_z={summary.get('best_z', 0)} out={output_dir}",
                flush=True,
            )
        except Exception as exc:
            print(f"[RARETAIL/TIME] warn monitor_error={exc}", file=sys.stderr, flush=True)

        if args.once:
            return 0
        time.sleep(max(5.0, float(args.interval or 15.0)))


if __name__ == "__main__":
    raise SystemExit(main())
