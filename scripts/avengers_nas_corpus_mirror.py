#!/usr/bin/env python3
"""Mirror an Avengers run corpus to a NAS Janus folder.

This is a sidecar archiver, not a miner controller. It never starts or stops
the runner, never changes Stratum wire policy, and never deletes destination
files. If the NAS is unavailable, the sidecar reports the error and the miner
can continue independently.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List


RUN_LEVEL_PATTERNS = (
    "*.json",
    "*.jsonl",
    "*.csv",
)

PROOF_PATTERNS = (
    "accepted_20*_z*_nonce0x*.json",
    "accepted_index.json",
)


def utc_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def iter_files(source: Path) -> Iterable[Path]:
    for pattern in RUN_LEVEL_PATTERNS:
        yield from source.glob(pattern)
    proofs = source / "proofs"
    if proofs.exists():
        for pattern in PROOF_PATTERNS:
            yield from proofs.glob(pattern)
        registry = proofs / "registry"
        if registry.exists():
            yield from registry.rglob("*")


def should_copy(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    if not dst.exists():
        return True
    try:
        s_stat = src.stat()
        d_stat = dst.stat()
        return s_stat.st_mtime > d_stat.st_mtime + 0.001 or s_stat.st_size != d_stat.st_size
    except OSError:
        return True


def copy_atomic(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def mirror_once(source: Path, dest: Path) -> Dict[str, object]:
    if not source.exists():
        return {
            "ok": False,
            "reason": "source_missing",
            "source": str(source),
            "dest": str(dest),
            "written_at_utc": utc_stamp(),
        }

    copied: List[str] = []
    scanned = 0
    errors: List[str] = []
    for src in iter_files(source):
        scanned += 1
        try:
            rel = src.relative_to(source)
            dst = dest / rel
            if should_copy(src, dst):
                copy_atomic(src, dst)
                copied.append(str(rel).replace("\\", "/"))
        except Exception as exc:  # keep sidecar non-fatal
            errors.append(f"{src}: {exc}")

    manifest = {
        "schema": "a10-3-avengers-nas-corpus-mirror-1",
        "written_at_utc": utc_stamp(),
        "source_run_dir": str(source),
        "destination_run_dir": str(dest),
        "scanned_files": scanned,
        "copied_files": len(copied),
        "copied_sample": copied[:25],
        "errors": errors[:25],
        "ok": not errors,
        "delete_policy": "never_delete_destination_files",
        "wire_change_required": False,
        "scheduler_effect": "none",
    }
    dest.mkdir(parents=True, exist_ok=True)
    with open(dest / "avengers_corpus_mirror_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-dir", required=True, help="local run directory to mirror")
    parser.add_argument("--nas-janus-root", required=True, help="NAS folder named Janus, or the desired Janus corpus root")
    parser.add_argument("--run-name", default="", help="destination run folder name; defaults to source folder name")
    parser.add_argument("--interval", type=float, default=60.0, help="seconds between mirror passes")
    parser.add_argument("--once", action="store_true", help="copy once and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source_run_dir).expanduser().resolve()
    nas_root = Path(args.nas_janus_root).expanduser()
    run_name = args.run_name or source.name
    dest = nas_root / "avengers_corpus" / run_name

    while True:
        try:
            result = mirror_once(source, dest)
            status = "ok" if result.get("ok") else "warn"
            print(
                f"[NAS/CORPUS] {status} copied={result.get('copied_files', 0)} "
                f"scanned={result.get('scanned_files', 0)} dest={dest}",
                flush=True,
            )
        except Exception as exc:
            print(f"[NAS/CORPUS] warn sidecar_error={exc}", file=sys.stderr, flush=True)

        if args.once:
            return 0
        time.sleep(max(5.0, float(args.interval or 60.0)))


if __name__ == "__main__":
    raise SystemExit(main())
