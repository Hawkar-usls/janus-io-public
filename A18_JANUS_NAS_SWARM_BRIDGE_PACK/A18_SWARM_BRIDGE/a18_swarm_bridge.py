#!/usr/bin/env python3
"""A18 JANUS NAS swarm observer bridge.

Reads NAS Brain endpoints with GET-only requests and writes sanitized local
summaries for future HRain overlays. It is not a miner, not a Stratum proxy,
and never sends commands to Buzz, NAS Brain, or A14/A17.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


VERSION = "A18_JANUS_NAS_SWARM_BRIDGE_v0_1"
LAYER = "A18_JANUS_NAS_SWARM_BRIDGE"

SAFETY_SENTINELS: Dict[str, Any] = {
    "observer_only": True,
    "stratum_proxy": False,
    "miner_control": False,
    "submit_path_touched": False,
    "mirror_control_touched": False,
    "bias_output_only": True,
    "tranception_inference": False,
    "miner_untouched": True,
    "wire_hash_submit_frozen": True,
    "mirror_untouched": True,
}

READ_ENDPOINTS: Tuple[Tuple[str, str], ...] = (
    ("health", "/api/health"),
    ("nodes", "/api/swarm/nodes"),
    ("tranception", "/api/swarm/tranception"),
    ("status", "/api/swarm/status"),
)


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        cfg = json.load(f)
    cfg.setdefault("nas_base_url", "http://YOUR_NAS_HOST:YOUR_NAS_PORT")
    cfg.setdefault("poll_seconds", 5)
    cfg.setdefault("timeout_seconds", 2)
    cfg.setdefault("write_outputs", True)
    cfg.setdefault("read_only", True)
    return cfg


def atomic_write_json(path: Path, obj: Dict[str, Any], retries: int = 6) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = f".{os.getpid()}.{int(time.time() * 1000)}.{random.randint(1000, 9999)}.tmp"
    tmp = path.with_name(path.name + suffix)
    data = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        for attempt in range(retries):
            try:
                os.replace(str(tmp), str(path))
                return True
            except PermissionError as exc:
                delay = 0.05 * (attempt + 1)
                print(f"[A18][WARN] locked output {path.name}: {exc}; retry={attempt + 1}", file=sys.stderr)
                time.sleep(delay)
        print(f"[A18][WARN] skipped output after lock retries: {path}", file=sys.stderr)
        return False
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def is_placeholder_url(url: str) -> bool:
    return "YOUR_NAS_HOST" in url or "YOUR_NAS_PORT" in url or not url.startswith(("http://", "https://"))


def http_get_json(base_url: str, endpoint: str, timeout: float) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    url = base_url.rstrip("/") + endpoint
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2_000_000)
        return json.loads(raw.decode("utf-8", "replace")), None
    except urllib.error.HTTPError as exc:
        return None, f"http_{exc.code}"
    except urllib.error.URLError as exc:
        return None, f"url_error:{exc.reason}"
    except TimeoutError:
        return None, "timeout"
    except Exception as exc:  # Keep observer alive on malformed endpoint responses.
        return None, f"{type(exc).__name__}:{exc}"


def synthetic_payloads() -> Dict[str, Dict[str, Any]]:
    now_ms = int(time.time() * 1000)
    return {
        "health": {
            "ok": True,
            "source": "dry_run",
            "known_count": 3,
            "live_count": 2,
            "server_time_ms": now_ms,
        },
        "nodes": {
            "ok": True,
            "source": "dry_run",
            "known_count": 3,
            "live_count": 2,
            "nodes": [
                {"node_id": "Buzz", "role": "master", "health": "live", "rssi": -55, "hash_rate": 0, "best_bits": 0},
                {"node_id": "PEA4", "role": "camera_presence_observer", "health": "unknown", "rssi": None},
                {"node_id": "ExampleWorker", "role": "worker", "health": "stale", "rssi": -71, "best_bits": 21},
            ],
        },
        "tranception": {
            "ok": True,
            "model": "janus_tranception_lite",
            "placeholder_only": True,
            "inference_run": False,
            "directive": {},
        },
        "status": {"ok": True, "source": "dry_run"},
    }


def pick(raw: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in raw and raw[key] is not None:
            return raw[key]
    return default


def normalize_node(raw: Dict[str, Any]) -> Dict[str, Any]:
    node_id = str(pick(raw, "node_id", "id", "name", "node", default="unknown"))
    role = str(pick(raw, "role", "kind", "type", default="swarm_node"))
    health = str(pick(raw, "health", "state", "status", default="unknown"))
    online = health.lower() in {"live", "online", "ok", "healthy", "active"}
    return {
        "node_id": node_id,
        "role": role,
        "online": online,
        "health": health,
        "last_seen": pick(raw, "last_seen", "last_seen_ms", "last_update_ms", default=None),
        "rssi": pick(raw, "rssi", "wifi_rssi", default=None),
        "wifi_health": pick(raw, "wifi_health", "wifi_state", default=None),
        "uptime": pick(raw, "uptime", "uptime_ms", default=None),
        "free_heap": pick(raw, "free_heap", "heap", "mem_free", default=None),
        "temperature": pick(raw, "temperature", "temp", "thermal", default=None),
        "hash_rate": pick(raw, "hash_rate", "hashrate", "H", default=None),
        "best_bits": pick(raw, "best_bits", "bestBits", "best_z", default=None),
        "accepted": pick(raw, "accepted", "shares", default=None),
        "rejected": pick(raw, "rejected", "rejects", default=None),
        "audio_mode": pick(raw, "audio_mode", "audio", default=None),
        "trust": pick(raw, "trust", "swarmTrust", default=None),
        "stress": pick(raw, "stress", "localStress", default=None),
        "dopamine": pick(raw, "dopamine", default=None),
        "oxytokin": pick(raw, "oxytokin", "oxy", default=None),
        "presence": pick(raw, "presence", default=None),
        "textcast": pick(raw, "textcast", "ssid_textcast", default=None),
        "camera": pick(raw, "camera", default=None),
    }


def extract_nodes(payloads: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    nodes_payload = payloads.get("nodes") or {}
    raw_nodes = nodes_payload.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raw_nodes = []
    return [normalize_node(n) for n in raw_nodes if isinstance(n, dict)]


def build_alerts(nodes: Iterable[Dict[str, Any]], endpoint_errors: Dict[str, str]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    for name, err in endpoint_errors.items():
        alerts.append({"kind": "endpoint_warn", "endpoint": name, "message": err})
    for node in nodes:
        if not node.get("online"):
            alerts.append({"kind": "node_not_live", "node_id": node.get("node_id"), "health": node.get("health")})
        rssi = node.get("rssi")
        if isinstance(rssi, (int, float)) and rssi <= -75:
            alerts.append({"kind": "weak_wifi", "node_id": node.get("node_id"), "rssi": rssi})
    return alerts


def build_outputs(payloads: Dict[str, Dict[str, Any]], endpoint_errors: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
    written_at = utc_now()
    nodes = extract_nodes(payloads)
    alerts = build_alerts(nodes, endpoint_errors)
    live_count = sum(1 for n in nodes if n.get("online"))
    summary = {
        "nodes_known": len(nodes),
        "nodes_live": live_count,
        "endpoint_errors": endpoint_errors,
        "tranception_status": {
            "available": "tranception" in payloads and "tranception" not in endpoint_errors,
            "placeholder_only": True,
            "inference_run": False,
        },
    }
    base = {
        "schema": "JANUS/A18/swarm-bridge/v1",
        "layer": LAYER,
        "version": VERSION,
        "written_at_utc": written_at,
        **SAFETY_SENTINELS,
    }
    events = [
        {"kind": "node_state", "node_id": n.get("node_id"), "role": n.get("role"), "health": n.get("health")}
        for n in nodes
    ]
    return {
        "a18_swarm_state.json": {**base, "source": "NAS_Brain/Buzz/ESP32_M5_swarm", "summary": summary},
        "a18_swarm_nodes.json": {**base, "nodes": nodes, "summary": summary},
        "a18_swarm_sense.json": {**base, "raw_endpoint_keys": sorted(payloads.keys()), "summary": summary},
        "a18_hrain_swarm_overlay.json": {
            **base,
            "source": "NAS_Brain/Buzz/ESP32_M5_swarm",
            "nodes": nodes,
            "events": events,
            "alerts": alerts,
            "summary": summary,
        },
        "a18_status.json": {**base, "ok": True, "dry_safe": True, "summary": summary},
    }


def poll_once(cfg: Dict[str, Any], dry_run: bool) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    if not cfg.get("read_only", True):
        raise SystemExit("A18 refuses to run with read_only=false")
    base_url = str(cfg.get("nas_base_url", "")).strip().rstrip("/")
    if dry_run or is_placeholder_url(base_url):
        return synthetic_payloads(), {}
    payloads: Dict[str, Dict[str, Any]] = {}
    errors: Dict[str, str] = {}
    timeout = float(cfg.get("timeout_seconds", 2))
    for name, endpoint in READ_ENDPOINTS:
        data, err = http_get_json(base_url, endpoint, timeout)
        if data is None:
            errors[name] = err or "unknown_error"
        else:
            payloads[name] = data
    return payloads, errors


def run(args: argparse.Namespace) -> int:
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    out_dir = Path(args.output_dir).resolve() if args.output_dir else cfg_path.parent
    while True:
        payloads, errors = poll_once(cfg, dry_run=args.dry_run)
        outputs = build_outputs(payloads, errors)
        if cfg.get("write_outputs", True):
            for name, obj in outputs.items():
                atomic_write_json(out_dir / name, obj)
        print(
            f"[A18] ok nodes={outputs['a18_swarm_state.json']['summary']['nodes_known']} "
            f"live={outputs['a18_swarm_state.json']['summary']['nodes_live']} "
            f"errors={len(errors)} dry_run={int(args.dry_run)} observer_only=1"
        )
        if args.once:
            return 0
        time.sleep(max(1.0, float(cfg.get("poll_seconds", 5))))


def main() -> int:
    parser = argparse.ArgumentParser(description="A18 JANUS NAS swarm observer bridge")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
