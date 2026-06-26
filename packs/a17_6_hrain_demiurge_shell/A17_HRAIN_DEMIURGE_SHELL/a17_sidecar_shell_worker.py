#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os, re, time, hashlib, sys, random
from pathlib import Path
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, List, Optional

VERSION = "A17_6_HRAIN_DEMIURGE_REPO_READY_VIDEO_SAFE_20260626"
SENTINEL = "A17_6_REPO_READY_OBSERVER_ONLY_WIRE_HASH_SUBMIT_FROZEN_MIRROR_UNTOUCHED"
EXTS = {".log", ".txt", ".jsonl", ".json", ".csv"}

CONCEPTS = {
    "ORDER": ["janus","accepted","proof","truth","canonical","lock","commit","route","temple","order","поряд"],
    "ENTROPY": ["random","mirror","rollback","reject","stale","chaos","entropy","хаос","энтроп"],
    "BRIDGE": ["pool","stratum","job","bridge","link","map","a14_nav","hrain","sidecar","shell"],
    "PROOF": ["accepted","submit","pool_pass","nonce","hash","z=","best_z","share","proof"],
    "GLYPH": ["glyph","symbol","coinbase","merkle","weird","linear_message","open_vocabulary"],
    "MIND": ["hrain","inaihr","demiurge","concept","meaning","kernel","canvas","mind","смысл"],
    "TAIL": ["z28","z29","z30","z31","z32","z33","rare_tail","best_z=30","best_z=31","best_z=32"],
    "CAT": ["catgpt","cat","кот","behavior","movement","state","tail_angle","ear_left","slime_trace"],
}

ROUTE_PATTERNS = [
    "a14_navigator:zim_reverse_s6",
    "a14_navigator:linear_proof",
    "a14_navigator:janus_dispatcher",
    "a14_navigator:dual_lock",
    "janus_dispatcher",
    "linear_proof",
    "dual_lock",
    "zim_reverse_s6",
    "zim_reverse",
    "knight/s11",
    "bitrev",
    "randomized_traversal_mirror",
    "random_mirror",
    "random/s6",
    "random",
    "linear",
]

def sha8(x: Any) -> str:
    return hashlib.sha256(str(x).encode("utf-8","ignore")).hexdigest()[:8]

def safe_id(prefix: str, raw: Any, limit: int=96) -> str:
    r = str(raw if raw is not None else "none")
    x = re.sub(r"[^A-Za-z0-9_.:/@+-]+", "_", r.strip())[:limit].strip("_") or "node"
    return f"{prefix}:{x}:{sha8(r)}"

def write_atomic(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, indent=2)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.{random.randrange(1_000_000):06d}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        last_err = None
        for attempt in range(6):
            try:
                tmp.replace(path)
                return
            except OSError as exc:
                last_err = exc
                time.sleep(0.05 * (attempt + 1))
        print(f"[A17 WARN] atomic replace failed for {path.name}: {last_err}", flush=True)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass

def read_json(path: Path, default: Any):
    try:
        return json.loads(path.read_text("utf-8", errors="replace"))
    except Exception:
        return default

def z_from_text(t: str) -> int:
    vals = []
    for pat in [r"\bbest_z[=:](\d+)", r"\bz[=:](\d+)", r"_z(\d+)_", r" z=(\d+)"]:
        vals += [int(x) for x in re.findall(pat, t)]
    return max(vals) if vals else 0

def route_from_text(t: str) -> str:
    low = t.lower()
    m = re.search(r"choice=([A-Za-z0-9_:/@.+-]+)", low)
    if m and m.group(1) not in ("none","null"):
        return "a14_navigator:" + m.group(1)
    m = re.search(r"\blane=([A-Za-z0-9_:/@.+-]+)", low)
    if m and m.group(1) not in ("none","null"):
        return m.group(1)
    m = re.search(r"\bgroup=([A-Za-z0-9_:/@.+-]+)", low)
    if m:
        return m.group(1)
    for r in ROUTE_PATTERNS:
        if r.lower() in low:
            return r
    if "pool" in low or "stratum" in low or "job=" in low:
        return "pool_job"
    if "accepted" in low or "proof" in low:
        return "proof_event"
    return "event"

def classify(line: str, route: str) -> str:
    low = (line + " " + route).lower()
    # explicit mirror wins
    if any(x in low for x in ["randomized_traversal_mirror", "random_mirror", "mirror", "random/s6", "random"]):
        return "mirror"
    if any(x in low for x in ["a14_navigator", "janus_dispatcher", "dual_lock", "zim_reverse", "linear_proof", "janus_broad_mixture"]):
        return "janus"
    if any(x in low for x in ["pool", "stratum", "job="]):
        return "pool"
    return "event"

def concepts_for(line: str) -> List[str]:
    low = line.lower()
    got = []
    for k, words in CONCEPTS.items():
        if any(w.lower() in low for w in words):
            got.append(k)
    return got or ["ORDER"]

@dataclass
class Graph:
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    links: Dict[Tuple[str,str,str], Dict[str, Any]] = field(default_factory=dict)
    counters: Counter = field(default_factory=Counter)
    route_stats: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    transitions: Dict[Tuple[str,str], Counter] = field(default_factory=lambda: defaultdict(Counter))
    seen_event: set = field(default_factory=set)
    last_route_by_file: Dict[str, str] = field(default_factory=dict)

    def node(self, id: str, label: str, kind: str, group: str, score: float=1.0, **data):
        n = self.nodes.get(id)
        if n is None:
            n = {"id": id, "label": label, "kind": kind, "group": group, "score": 0.0, "data": {}}
            self.nodes[id] = n
        n["label"] = label or n.get("label", id)
        n["kind"] = kind or n.get("kind", "node")
        n["group"] = group or n.get("group", "default")
        n["score"] = float(n.get("score", 0)) + float(score or 0)
        for k,v in data.items():
            if v is None: continue
            if k in ("z","priority","purity","confidence"): n[k] = v
            else: n.setdefault("data", {})[k] = v
        return id

    def link(self, a: str, b: str, kind: str, weight: float=1.0, **data):
        if not a or not b or a == b: return
        key = (a,b,kind)
        l = self.links.get(key)
        if l is None:
            l = {"source": a, "target": b, "kind": kind, "weight": 0.0, "data": {}}
            self.links[key] = l
        l["weight"] = float(l.get("weight", 0)) + float(weight or 0)
        for k,v in data.items():
            if v is not None:
                l.setdefault("data", {})[k] = v

def init_graph(g: Graph):
    g.node("HRAIN_CORE", "HRAIN CORE", "core", "core", 80, style="living broth/caviar nucleus")
    g.node("DEMIURGE_GOVERNOR", "JANUS DEMIURGE GOVERNOR", "governor", "janus", 55, mode="hypothesis architect; output-only")
    g.node("SIDECAR_SHELL", "SIDECAR SHELL", "sidecar", "mind", 50, mode="tail-only observer")
    g.node("A14_MINER", "A14.2 PURE ROUTE MINER", "miner", "proof", 40)
    g.node("A15_HRAIN_LOD", "HRAIN LOD CANVAS", "ui", "mind", 35)
    g.node("WIRE_HASH_SUBMIT_FROZEN", "WIRE/HASH/SUBMIT FROZEN", "safety", "safety", 60)
    g.node("MIRROR_UNTOUCHED", "MIRROR UNTOUCHED", "safety", "mirror", 60)
    g.link("A14_MINER", "SIDECAR_SHELL", "live_tail", 6)
    g.link("SIDECAR_SHELL", "HRAIN_CORE", "feeds", 7)
    g.link("DEMIURGE_GOVERNOR", "HRAIN_CORE", "interprets", 5)
    g.link("WIRE_HASH_SUBMIT_FROZEN", "A14_MINER", "boundary", 8)
    g.link("MIRROR_UNTOUCHED", "A14_MINER", "boundary", 8)
    for c in CONCEPTS:
        cid = f"CONCEPT_{c}"
        group = "concept_order" if c in ("ORDER","PROOF","BRIDGE") else ("concept_chaos" if c=="ENTROPY" else ("tail" if c=="TAIL" else "concept"))
        g.node(cid, c, "concept", group, 22)
        g.link("HRAIN_CORE", cid, "concept", 2)

def discover(root: Path, max_files: int) -> List[Path]:
    bases = [
        root/"A14_2_PURE_ROUTE_LOCK_PACK"/"janus_io_o1_runs"/"A14_2_PURE_ROUTE_LOCK_V1",
        root/"A14_2_PURE_ROUTE_LOCK_PACK"/"janus_io_o1_runs",
        root/"A14_2_PURE_ROUTE_LOCK_PACK",
        root/"A17_HRAIN_DEMIURGE_SHELL",
        root,
    ]
    files = []
    seen = set()
    for base in bases:
        if not base.exists(): continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in EXTS: continue
            low = p.name.lower()
            if "__pycache__" in str(p) or low.endswith(".tmp"): continue
            if any(k in low for k in ["dashboard","summary","events","glyph","witchhunter","proof","accepted","live_console","open_sweep","backforth","gratitude","route","bias","state","catgpt"]):
                if p not in seen:
                    files.append(p); seen.add(p)
            if len(files) >= max_files: break
        if len(files) >= max_files: break
    # prefer fresh/small-ish files first by mtime
    files.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return files[:max_files]

def line_events_from_json(obj: Any, path: Path) -> List[str]:
    lines = []
    def walk(x, depth=0):
        if depth > 5: return
        if isinstance(x, dict):
            if any(k in x for k in ("route","group","accepted","z","best_z","nonce","hash","job_id","job")):
                lines.append(json.dumps(x, ensure_ascii=False))
            for v in x.values(): walk(v, depth+1)
        elif isinstance(x, list):
            for v in x[:400]: walk(v, depth+1)
    walk(obj)
    return lines[:900]

def read_new_lines(path: Path, offsets: Dict[str, int], initial_tail: int, max_read: int, max_lines: int) -> List[str]:
    key = str(path)
    try:
        size = path.stat().st_size
    except OSError:
        return []
    off = int(offsets.get(key, 0))
    if off <= 0:
        off = max(0, size - initial_tail)
    if off > size:
        off = 0
    n = min(max_read, max(0, size - off))
    if n <= 0:
        offsets[key] = size
        return []
    with path.open("rb") as f:
        f.seek(off)
        data = f.read(n)
    offsets[key] = off + len(data)
    text = data.decode("utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            return line_events_from_json(json.loads(text), path)
        except Exception:
            pass
    if path.suffix.lower() == ".jsonl":
        lines = text.splitlines()
        return lines[-max_lines:]
    return [l for l in text.splitlines() if l.strip()][-max_lines:]

def process_line(g: Graph, line: str, path: Path, file_key: str):
    if not line or len(line) < 4: return
    eid = sha8(str(path) + "|" + line)
    if eid in g.seen_event: return
    g.seen_event.add(eid)
    route = route_from_text(line)
    group = classify(line, route)
    z = z_from_text(line)
    accepted = bool(re.search(r"\bACCEPTED\b|accepted[\"'=:\s]+true|accepted proof saved|pool_pass=True", line, re.I))
    rollback = "rollback" in line.lower()
    rejected = bool(re.search(r"\bREJECT|rejected|stale", line, re.I))
    glyph = "glyph" in line.lower() or "symbol" in line.lower()
    tail = z >= 28 or "rare_tail" in line.lower()
    kind = "accepted" if accepted else ("tail" if tail else ("glyph" if glyph else ("route_event" if route!="event" else "event")))
    score = 1 + (10 if accepted else 0) + max(0, z-22)*2 + (4 if glyph else 0) + (8 if tail else 0)

    g.counters["events_seen"] += 1
    if accepted: g.counters["accepted_seen"] += 1
    if group == "janus": g.counters["accepted_janus" if accepted else "janus_events"] += 1
    elif group == "mirror": g.counters["accepted_mirror" if accepted else "mirror_events"] += 1
    elif group == "pool": g.counters["pool_events"] += 1

    rs = g.route_stats[route]
    rs["seen"] += 1
    rs[group] += 1
    if accepted: rs["accepted"] += 1
    if rollback: rs["rollback"] += 1
    if rejected: rs["rejected"] += 1
    if glyph: rs["glyph"] += 1
    rs["best_z"] = max(int(rs.get("best_z",0)), z)

    rid = safe_id("route", route)
    r_group = group if group in ("janus","mirror","pool") else "route"
    purity = 0.0
    total = max(1, rs["janus"] + rs["mirror"])
    if rs["janus"] > 0 or rs["mirror"] > 0:
        purity = (rs["janus"] - rs["mirror"]) / total
    g.node(rid, route, "route", r_group, score/2, z=z or None, purity=round(purity,3), stats=dict(rs))
    g.link("HRAIN_CORE", rid, "route", 1 + score/10)
    g.link("SIDECAR_SHELL", rid, "observes", 0.8)

    ev_id = safe_id("event", eid)
    label = ("ACCEPTED " if accepted else "") + (route[:28])
    g.node(ev_id, label, kind, group, score, z=z or None, path=str(path.name), line=line[:240])
    g.link(rid, ev_id, "emits", 1 + score/15)
    if accepted:
        g.link("A14_MINER", ev_id, "accepted", 3)
    if tail:
        g.link("CONCEPT_TAIL", ev_id, "rare_tail", 3)
    if glyph:
        g.link("CONCEPT_GLYPH", ev_id, "glyph", 2)

    for c in concepts_for(line):
        cid = f"CONCEPT_{c}"
        g.counters[f"concept_{c}"] += 1
        g.link(cid, rid, "concept_route", 1)
        g.link(cid, ev_id, "concept_event", 0.7)

    prev = g.last_route_by_file.get(file_key)
    if prev and prev != route:
        g.transitions[(prev, route)]["count"] += 1
        g.transitions[(prev, route)]["accepted"] += 1 if accepted else 0
        g.transitions[(prev, route)]["best_z"] = max(int(g.transitions[(prev, route)].get("best_z",0)), z)
        prev_id = safe_id("route", prev)
        g.link(prev_id, rid, "markov_transition", 1 + (2 if accepted else 0), best_z=z or None)
    if route != "event":
        g.last_route_by_file[file_key] = route

def compact(g: Graph, max_nodes: int, max_links: int):
    # Preserve core/concepts/routes/bias/tails/accepted high-z first.
    nodes = list(g.nodes.values())
    def key(n):
        keep = 0
        if n.get("kind") in ("core","concept","safety","governor","sidecar","miner","ui","route","bias","hypothesis"): keep += 100000
        if n.get("kind") in ("accepted","tail"): keep += 50000
        return keep + float(n.get("score",0)) + 10*float(n.get("z",0) or 0)
    nodes.sort(key=key, reverse=True)
    keep = {n["id"] for n in nodes[:max_nodes]}
    links = [l for l in g.links.values() if l["source"] in keep and l["target"] in keep]
    links.sort(key=lambda l: float(l.get("weight",0)), reverse=True)
    links = links[:max_links]
    keep2 = set()
    for l in links:
        keep2.add(l["source"]); keep2.add(l["target"])
    keep |= keep2
    return [g.nodes[i] for i in keep if i in g.nodes], links

def build_bias(g: Graph):
    safe_bias = {}
    rejected = {}
    details = {}
    for route, c in g.route_stats.items():
        janus = int(c.get("janus",0)); mirror = int(c.get("mirror",0)); seen=int(c.get("seen",0))
        accepted=int(c.get("accepted",0)); best_z=int(c.get("best_z",0))
        rejected_count=int(c.get("rejected",0)); rollback=int(c.get("rollback",0)); glyph=int(c.get("glyph",0))
        details[route] = dict(c)

        is_pure_route = any(k in route.lower() for k in ["a14_navigator","janus_dispatcher","dual_lock","zim_reverse","linear_proof"])
        if not is_pure_route:
            rejected[route] = {"reason":"not a pure/Janus route", **dict(c)}
            continue

        total_jm = max(1, janus + mirror)
        purity = (janus - mirror) / total_jm
        mirror_ratio = mirror / total_jm
        accepted_rate = accepted / max(1, seen)
        rollback_rate = rollback / max(1, seen)
        rejected_rate = rejected_count / max(1, seen)
        tail_score = max(0.0, min(1.0, (best_z - 23) / 8.0))
        glyph_score = min(1.0, glyph / max(1, seen))

        if mirror >= janus or purity < 0.08:
            rejected[route] = {"reason":"mirror-polluted evidence; not safe for Janus bias", **dict(c), "purity": round(purity, 4), "mirror_ratio": round(mirror_ratio, 4)}
            continue

        # A17.5: non-saturating confidence so bias is not flattened to 0.2/0.2/0.2.
        confidence = (
            max(0.0, purity) * 0.42 +
            accepted_rate * 0.22 +
            tail_score * 0.18 +
            glyph_score * 0.08 +
            min(1.0, seen / 1200.0) * 0.10
        )
        penalty = min(0.55, rollback_rate * 0.35 + rejected_rate * 0.35 + mirror_ratio * 0.20)
        confidence = max(0.0001, confidence * (1.0 - penalty))
        safe_bias[route] = confidence

    s = sum(safe_bias.values()) or 1.0
    safe_bias = {k: round(v/s, 6) for k,v in sorted(safe_bias.items(), key=lambda kv: kv[1], reverse=True)}
    return safe_bias, rejected, details


def build_transition_matrix(g: Graph, limit: int):
    rows = []
    outsum = Counter()
    for (a,b), c in g.transitions.items():
        outsum[a] += int(c["count"])
    for (a,b), c in g.transitions.items():
        count = int(c["count"])
        rows.append({
            "from": a, "to": b, "count": count,
            "probability": round(count / max(1,outsum[a]), 6),
            "accepted": int(c.get("accepted",0)),
            "best_z": int(c.get("best_z",0))
        })
    rows.sort(key=lambda x: (x["count"], x["accepted"], x["best_z"]), reverse=True)
    return rows[:limit]

def build_hypotheses(g: Graph, bias: Dict[str,float], rejected: Dict[str,Any], transitions: List[Dict[str,Any]], top: int):
    hyp = []
    for route, w in list(bias.items())[:top]:
        st = g.route_stats.get(route, Counter())
        hyp.append({
            "type": "route_bias_candidate",
            "route": route,
            "weight": w,
            "why": "Janus-classified route with mirror pollution filter passed",
            "seen": int(st.get("seen",0)),
            "accepted": int(st.get("accepted",0)),
            "best_z": int(st.get("best_z",0)),
            "safety": "output-only; do not touch mirror or submit"
        })
    for tr in transitions[:min(6, top)]:
        if tr["probability"] >= 0.2 or tr["accepted"] > 0 or tr["best_z"] >= 28:
            hyp.append({
                "type": "markov_transition_hint",
                "transition": f'{tr["from"]} -> {tr["to"]}',
                "probability": tr["probability"],
                "accepted": tr["accepted"],
                "best_z": tr["best_z"],
                "why": "route transition repeatedly appears in live stream",
                "safety": "hypothesis only"
            })
    for route, item in list(rejected.items())[:min(5, top)]:
        if item.get("reason","").startswith("mirror-polluted"):
            hyp.append({
                "type": "reject_polluted_route",
                "route": route,
                "why": item.get("reason"),
                "janus": item.get("janus",0),
                "mirror": item.get("mirror",0),
                "safety": "must not enter Janus bias"
            })
    if not hyp:
        hyp.append({"type":"warmup","why":"not enough live evidence yet","safety":"observer-only"})
    return hyp[:top]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--graph", required=True)
    ap.add_argument("--bias", required=True)
    ap.add_argument("--status", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--bus", required=True)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--hypotheses", required=True)
    ap.add_argument("--poll", type=float, default=4)
    ap.add_argument("--max-files", type=int, default=160)
    ap.add_argument("--initial-tail-bytes", type=int, default=800000)
    ap.add_argument("--max-read-bytes", type=int, default=420000)
    ap.add_argument("--max-lines-per-file", type=int, default=3200)
    ap.add_argument("--max-nodes", type=int, default=2200)
    ap.add_argument("--max-links", type=int, default=4200)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    graph_path = Path(args.graph)
    bias_path = Path(args.bias)
    status_path = Path(args.status)
    state_path = Path(args.state)
    bus_path = Path(args.bus)
    matrix_path = Path(args.matrix)
    hyp_path = Path(args.hypotheses)

    offsets = read_json(state_path, {})
    if not isinstance(offsets, dict): offsets = {}
    files = []
    last_discover = 0
    cycle = 0
    g = Graph()
    init_graph(g)
    print(f"[A17] root={root}", flush=True)
    print("[A17] Demiurge Sidecar Shell active; observer-only; NOT stratum proxy; submit path untouched", flush=True)

    while True:
        cycle += 1
        if not files or time.time() - last_discover > 60:
            files = discover(root, args.max_files)
            last_discover = time.time()
            print(f"[A17 discover] watching files={len(files)}", flush=True)

        added = 0
        for p in files:
            lines = read_new_lines(p, offsets, args.initial_tail_bytes, args.max_read_bytes, args.max_lines_per_file)
            if not lines: continue
            file_key = str(p)
            for line in lines:
                process_line(g, line, p, file_key)
                added += 1

        bias, rejected, details = build_bias(g)
        transitions = build_transition_matrix(g, 256)
        hypotheses = build_hypotheses(g, bias, rejected, transitions, 16)

        for route, w in bias.items():
            bid = safe_id("bias", route)
            rid = safe_id("route", route)
            g.node(bid, f"BIAS {route}", "bias", "bias", 25*w+5, confidence=round(w,4), route=route)
            g.link("DEMIURGE_GOVERNOR", bid, "exports_bias", 2+w*10)
            g.link(bid, rid, "bias_for", 2+w*10)
        for h in hypotheses[:8]:
            hid = safe_id("hyp", h.get("type","hyp") + "|" + h.get("route", h.get("transition","")))
            g.node(hid, h.get("type","hypothesis"), "hypothesis", "mind", 8, **h)
            g.link("DEMIURGE_GOVERNOR", hid, "hypothesis", 2)

        nodes, links = compact(g, args.max_nodes, args.max_links)
        top_bias = list(bias.items())[:12]
        graph_obj = {
            "version": VERSION,
            "sentinel": SENTINEL,
            "observer_only": True,
            "wire_hash_submit_frozen": True,
            "mirror_untouched": True,
            "miner_not_modified": True,
            "stratum_proxy": False,
            "style": "bubble_caviar_spore_broth_canvas_lod",
            "mtime": time.time(),
            "meta": {
                "counters": dict(g.counters),
                "top_bias_routes": top_bias,
                "nodes_total_before_lod": len(g.nodes),
                "links_total_before_lod": len(g.links),
                "render_nodes": len(nodes),
                "render_links": len(links),
                "live_files": len(files),
                "cycle": cycle,
                "added_last_cycle": added
            },
            "nodes": nodes,
            "links": links
        }
        write_atomic(graph_path, graph_obj)
        write_atomic(bias_path, {
            "version": VERSION,
            "sentinel": SENTINEL,
            "observer_only": True,
            "bias_file_output_only": True,
            "miner_not_modified": True,
            "wire_hash_submit_frozen": True,
            "mirror_untouched": True,
            "janus_route_bias": bias,
            "rejected_routes_due_to_mirror_pollution": rejected,
            "route_details": details,
            "mirror_control": {"random":"untouched","randomized_traversal_mirror":"untouched"},
            "note": "A17 exports only safe Janus-classified routes. A14.2 does not read this file."
        })
        write_atomic(matrix_path, {
            "version": VERSION,
            "observer_only": True,
            "kind": "markov_like_route_transition_memory",
            "transitions": transitions
        })
        write_atomic(hyp_path, {
            "version": VERSION,
            "observer_only": True,
            "demiurge_role": "explain and propose; never submit",
            "hypotheses": hypotheses
        })
        write_atomic(bus_path, {
            "version": VERSION,
            "observer_only": True,
            "sidecar_bus": {
                "events_seen": int(g.counters.get("events_seen",0)),
                "accepted_janus": int(g.counters.get("accepted_janus",0)),
                "accepted_mirror": int(g.counters.get("accepted_mirror",0)),
                "safe_bias_routes": len(bias),
                "rejected_routes": len(rejected),
                "transition_edges": len(transitions),
                "hypotheses": len(hypotheses)
            },
            "files": [str(p) for p in files[:40]]
        })
        write_atomic(status_path, {
            "version": VERSION,
            "sentinel": SENTINEL,
            "stage": "live",
            "message": "A17 HRain Demiurge Sidecar Shell running",
            "mtime": time.time(),
            "cycle": cycle,
            "added_last_cycle": added,
            "events_seen": int(g.counters.get("events_seen",0)),
            "accepted_janus": int(g.counters.get("accepted_janus",0)),
            "accepted_mirror": int(g.counters.get("accepted_mirror",0)),
            "nodes": len(nodes),
            "links": len(links),
            "files": len(files),
            "policy": {
                "observer_only": True,
                "stratum_proxy": False,
                "wire_hash_submit_frozen": True,
                "mirror_untouched": True,
                "client_lod": True,
                "bubble_spore_style": True
            }
        })
        write_atomic(state_path, offsets)

        if added or cycle % 5 == 0:
            print(f"[A17 live] cycle={cycle} added={added} events={g.counters.get('events_seen',0)} janus={g.counters.get('accepted_janus',0)} mirror={g.counters.get('accepted_mirror',0)} nodes={len(nodes)} routes={len(g.route_stats)} bias={len(bias)} transitions={len(transitions)}", flush=True)
        time.sleep(args.poll)

if __name__ == "__main__":
    raise SystemExit(main())
