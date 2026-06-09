#!/usr/bin/env python3
"""Offline Butterfly Ledger / Director Mode analyzer.

This script does not start mining and does not affect a live scheduler.
It reads JSON/JSONL event streams, groups small perturbations into scenes,
and emits counterfactual probe suggestions with conservative verdicts.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


VERDICTS = (
    "LUCK_ONLY",
    "REPLAY_NEARBY",
    "RESCOUT_NOW",
    "PROMOTE_TO_CORPUS",
    "AVENGERS_STONE_CANDIDATE",
)


def utc_stamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def pick(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return default


def flatten_event(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Merge common nested payload shapes without destroying top-level fields."""
    out = dict(obj)
    for key in ("payload", "event", "data", "empirical_layer"):
        child = obj.get(key)
        if isinstance(child, dict):
            for child_key, child_value in child.items():
                out.setdefault(child_key, child_value)
    return out


def load_events(paths: Iterable[Path]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*.jsonl")):
                events.extend(load_events([child]))
            for child in sorted(path.rglob("*.json")):
                events.extend(load_events([child]))
            continue
        try:
            if path.suffix.lower() == ".jsonl":
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(obj, dict):
                            events.append(flatten_event(obj))
            elif path.suffix.lower() == ".json":
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    obj = json.load(handle)
                if isinstance(obj, list):
                    events.extend(flatten_event(x) for x in obj if isinstance(x, dict))
                elif isinstance(obj, dict):
                    for key in ("events", "recent_dark_events", "accepted_candidates", "rejected_candidates", "top_groups"):
                        rows = obj.get(key)
                        if isinstance(rows, list):
                            events.extend(flatten_event(x) for x in rows if isinstance(x, dict))
                    events.append(flatten_event(obj))
        except OSError:
            continue
    return events


@dataclass
class Scene:
    key: str
    side: str
    lane: str
    sector: int
    strategy: str
    cfg_name: str
    events: int = 0
    checked: int = 0
    accepted: int = 0
    rejected: int = 0
    stale: int = 0
    best_z: int = 0
    hps_sum: float = 0.0
    load_sum: float = 0.0
    mirror_gap_sum: float = 0.0
    job_ids: List[str] = field(default_factory=list)
    phases: Dict[str, int] = field(default_factory=dict)
    sources: Dict[str, int] = field(default_factory=dict)

    def observe(self, event: Dict[str, Any]) -> None:
        self.events += 1
        self.checked += parse_int(pick(event, "checked", "checked_hashes", "range_size"), 0)
        self.accepted += parse_int(pick(event, "accepted", "accepts", "acc"), 0)
        self.rejected += parse_int(pick(event, "rejected", "rejects", "rej"), 0)
        self.stale += parse_int(pick(event, "stale", "stales", "stale_drops"), 0)
        self.best_z = max(self.best_z, parse_int(pick(event, "best_z", "zbits", "best_bits", "best"), 0))
        self.hps_sum += parse_float(pick(event, "hps", "hash_rate", "hashrate", "H"), 0.0)
        self.load_sum += parse_float(pick(event, "load", "thermal_load", "cpu_load"), 0.0)
        janus_best = parse_int(pick(event, "janus_best_z", "janus_best"), 0)
        mirror_best = parse_int(pick(event, "mirror_best_z", "mirror_best"), 0)
        if janus_best or mirror_best:
            self.mirror_gap_sum += float(mirror_best - janus_best)
        job_id = str(pick(event, "job_id", "job", "job_seq", default=""))
        if job_id and job_id not in self.job_ids and len(self.job_ids) < 8:
            self.job_ids.append(job_id)
        phase = str(pick(event, "phase", "mode", default="unknown"))
        self.phases[phase] = self.phases.get(phase, 0) + 1
        source = str(pick(event, "source", "node_id", "node", default="unknown"))
        self.sources[source] = self.sources.get(source, 0) + 1

    @property
    def reject_rate(self) -> float:
        submitted = self.accepted + self.rejected
        return float(self.rejected) / float(submitted) if submitted else 0.0

    @property
    def stale_rate(self) -> float:
        total = self.events + self.stale
        return float(self.stale) / float(total) if total else 0.0

    @property
    def hps_avg(self) -> float:
        return self.hps_sum / self.events if self.events else 0.0

    @property
    def load_avg(self) -> float:
        return self.load_sum / self.events if self.events else 0.0

    @property
    def mirror_gap_avg(self) -> float:
        return self.mirror_gap_sum / self.events if self.events else 0.0


def event_side(event: Dict[str, Any]) -> str:
    side = str(pick(event, "source_side", "side", "group", "lane", default="unknown")).lower()
    if "mirror" in side or "random" in side or "control" in side:
        return "control"
    if "bh" in side or "blackstar" in side or "gargantua" in side:
        return "bh"
    if "yaks" in side or "gate" in side:
        return "yaks"
    if "janus" in side or "zim" in side or "bunnyhop" in side or "dual" in side:
        return "janus"
    return side or "unknown"


def event_key(event: Dict[str, Any]) -> Tuple[str, str, int, str, str, str]:
    side = event_side(event)
    lane = str(pick(event, "lane", "method", "group", default="unknown"))
    strategy = str(pick(event, "strategy", "method", default="unknown"))
    cfg_name = str(pick(event, "cfg_name", "cfg", "wire", default="canonical"))
    sector = parse_int(pick(event, "sector", "sec", default=0), 0) % 64
    key = f"{side}|{lane}|s{sector}|{strategy}|{cfg_name}"
    return key, side, sector, lane, strategy, cfg_name


def build_scenes(events: Iterable[Dict[str, Any]]) -> List[Scene]:
    scenes: Dict[str, Scene] = {}
    for event in events:
        key, side, sector, lane, strategy, cfg_name = event_key(event)
        scene = scenes.get(key)
        if scene is None:
            scene = Scene(key=key, side=side, lane=lane, sector=sector, strategy=strategy, cfg_name=cfg_name)
            scenes[key] = scene
        scene.observe(event)
    out = list(scenes.values())
    out.sort(key=lambda s: (director_score(s), s.best_z, s.accepted, s.events), reverse=True)
    return out


def director_score(scene: Scene) -> float:
    score = scene.best_z * 12.0
    score += min(scene.accepted, 20) * 18.0
    score += min(scene.events, 12) * 4.0
    score += max(0.0, -scene.mirror_gap_avg) * 10.0
    score -= scene.reject_rate * 180.0
    score -= scene.stale_rate * 120.0
    if scene.side == "control":
        score -= 12.0
    return round(score, 3)


def verdict(scene: Scene) -> str:
    score = director_score(scene)
    if scene.best_z >= 36 and scene.accepted > 0 and scene.events >= 2 and scene.reject_rate <= 0.02:
        return "AVENGERS_STONE_CANDIDATE"
    if scene.accepted > 0 and scene.best_z >= 32 and scene.reject_rate <= 0.03:
        return "PROMOTE_TO_CORPUS"
    if scene.side == "control" and (scene.best_z >= 32 or scene.mirror_gap_avg >= 2.0):
        return "RESCOUT_NOW"
    if scene.best_z >= 30 or score >= 360.0 or scene.events >= 4:
        return "REPLAY_NEARBY"
    return "LUCK_ONLY"


def probe_plan(scene: Scene) -> List[Dict[str, Any]]:
    base = {
        "side": "janus" if scene.side == "control" else scene.side,
        "lane": scene.lane,
        "strategy": scene.strategy,
        "cfg_name": scene.cfg_name,
        "wire_change_required": False,
        "submit_pressure_changed": False,
    }
    plans: List[Dict[str, Any]] = []
    if verdict(scene) == "LUCK_ONLY":
        plans.append({**base, "action": "archive_only", "reason": "single weak trace"})
        return plans
    for delta in (-1, 1):
        plans.append({
            **base,
            "action": "counterfactual_probe",
            "sector": (scene.sector + delta) % 64,
            "batch_scale": 0.90 if delta < 0 else 1.10,
            "stride_hint": "nearby_stride_jitter",
            "reason": "replay nearby sector without changing wire",
        })
    if scene.side == "control":
        plans.append({
            **base,
            "action": "janus_rescout",
            "sector": scene.sector,
            "batch_scale": 1.0,
            "stride_hint": "mirror_gap_response",
            "reason": "control/mirror pressure should be answered by JANUS rescout",
        })
    return plans


def summarize(events: List[Dict[str, Any]], limit: int) -> Dict[str, Any]:
    scenes = build_scenes(events)
    top = []
    verdict_counts = {name: 0 for name in VERDICTS}
    for scene in scenes[:limit]:
        v = verdict(scene)
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
        top.append({
            **asdict(scene),
            "reject_rate": round(scene.reject_rate, 6),
            "stale_rate": round(scene.stale_rate, 6),
            "hps_avg": round(scene.hps_avg, 3),
            "load_avg": round(scene.load_avg, 3),
            "mirror_gap_avg": round(scene.mirror_gap_avg, 3),
            "director_score": director_score(scene),
            "director_verdict": v,
            "probe_plan": probe_plan(scene),
        })
    return {
        "schema": "janus-butterfly-director-1",
        "written_at_utc": utc_stamp(),
        "objective": "event -> context snapshot -> counterfactual probe plan -> repeatability score -> director verdict",
        "wire_change_required": False,
        "scheduler_effect": "observe_only",
        "events_seen": len(events),
        "scenes_seen": len(scenes),
        "verdict_counts": verdict_counts,
        "top_scenes": top,
        "rule": "do not confuse luck with law; no frozen-wire mutation",
    }


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(path)


def self_test() -> int:
    rows = [
        {"source_side": "janus", "lane": "janus_bunnyhop_scout", "strategy": "zim_reverse", "sector": 6, "accepted": 1, "best_z": 37, "hps": 2400000, "job_id": "jobA"},
        {"source_side": "janus", "lane": "janus_bunnyhop_scout", "strategy": "zim_reverse", "sector": 6, "accepted": 1, "best_z": 34, "hps": 2400000, "job_id": "jobB"},
        {"source_side": "control", "lane": "randomized_traversal_mirror", "strategy": "random", "sector": 11, "accepted": 1, "best_z": 33, "mirror_best_z": 33, "janus_best_z": 30},
        {"source_side": "bh", "lane": "HORIZON", "strategy": "lens", "sector": 13, "stale": 1, "best_z": 29},
    ]
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        path = Path(tmp) / "events.jsonl"
        out = Path(tmp) / "butterfly.json"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        summary = summarize(load_events([path]), limit=8)
        write_json(out, summary)
        assert summary["events_seen"] == 4
        assert any(s["director_verdict"] == "AVENGERS_STONE_CANDIDATE" for s in summary["top_scenes"])
        assert out.exists()
    print("butterfly self-test ok")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", "-i", action="append", type=Path, default=[], help="JSON/JSONL file or directory to scan. Can be repeated.")
    parser.add_argument("--output", "-o", type=Path, default=Path("butterfly_director_report.json"), help="Output JSON report path.")
    parser.add_argument("--limit", type=int, default=24, help="Top scene count.")
    parser.add_argument("--self-test", action="store_true", help="Run offline self-test and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()
    if not args.input:
        raise SystemExit("provide --input path or use --self-test")
    events = load_events(args.input)
    summary = summarize(events, limit=max(1, int(args.limit)))
    write_json(args.output, summary)
    print(f"butterfly report: {args.output}")
    print(f"events={summary['events_seen']} scenes={summary['scenes_seen']} verdicts={summary['verdict_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
