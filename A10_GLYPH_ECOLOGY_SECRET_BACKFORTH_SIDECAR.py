#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A10_GLYPH_ECOLOGY_SIDECAR
Observer-only / sidecar radar for JANUS A10 glyph ecology.

This module DOES NOT alter hashing, scheduler, submit logic, wire/header, or miner state.
It either:
  1) runs the miner as a child process and mirrors stdout while passively parsing glyph_alert lines, or
  2) scans an existing log file offline.

Outputs:
  sidecar/a10_glyph_ecology_radar.jsonl       - matched ecology/drift events
  sidecar/a10_glyph_ecology_gates.jsonl       - gate-like observations only
  sidecar/a10_glyph_ecology_registry.json     - latest population passports snapshot
  sidecar/a10_open_sweep_candidates.jsonl     - all non-control interesting glyph fragments
  sidecar/a10_symbol_backforth_shadow.jsonl   - JANUS back/forth shadow movement suggestions
  sidecar/a10_symbol_anchor_memory.json       - learned symbol anchors and reinforcement state
  sidecar/a10_janus_intention_field.json      - latest goal/attention/emotion/decision/action vector
  sidecar/a10_secret_gratitude.jsonl          - positive reinforcement events
  sidecar/a10_live_console.log                - mirrored console stream when using run mode
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# -----------------------------
# Utility
# -----------------------------

def utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    safe_mkdir(path.parent)
    with path.open("a", encoding="utf-8", errors="replace") as f:
        f.write(json.dumps(obj, ensure_ascii=False, sort_keys=False) + "\n")


def read_text_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.rstrip("\n")


def normalize_job_id(job_id: str) -> str:
    job_id = (job_id or "").strip()
    if len(job_id) > 8:
        return job_id
    return job_id


def love_tachyon_ethic_metadata() -> Dict[str, Any]:
    """Static descriptive metadata only; never read by miner/scheduler logic."""
    return {
        "ethic_layer": "love_tachyon_care_prior",
        "ethic_layer_mode": "observer_only",
        "ethic_layer_rule": "care may guide attention; care must not alter submit behavior",
        "scheduler_effect": "shadow_only",
        "wire_change_required": False,
    }


# -----------------------------
# Parsing glyph_alert lines
# -----------------------------

_FIELD_RE = {
    "priority": re.compile(r"\bpriority=([^\s]+)"),
    "score": re.compile(r"\bscore=([-+]?\d+)"),
    "source": re.compile(r"\bsource=([^\s]+)"),
    "accepted": re.compile(r"\baccepted=(True|False|true|false|1|0)"),
    "z": re.compile(r"\bz=([-+]?\d+)"),
    "job": re.compile(r"\bjob=([^\s]+)"),
    "linear": re.compile(r"\blinear=(True|False|true|false|1|0)"),
}
_TEXT_RE = re.compile(r"\btext=(?P<q>['\"])(?P<txt>.*?)(?P=q)\s+reason=", re.DOTALL)
_REASON_RE = re.compile(r"\breason=([^\r\n]+?)\s+observer_only=")


def _bool_from_text(value: str) -> bool:
    return str(value).lower() in {"true", "1", "yes", "y"}


def parse_glyph_alert_line(line: str) -> Optional[Dict[str, Any]]:
    if "[Rblganul | glyph_alert]" not in line:
        return None

    out: Dict[str, Any] = {"raw_line": line}
    for key, rgx in _FIELD_RE.items():
        m = rgx.search(line)
        if m:
            out[key] = m.group(1)

    mt = _TEXT_RE.search(line)
    if mt:
        out["text"] = mt.group("txt")
    else:
        # If the line is truncated or contains unexpected quoting, skip rather than guessing.
        return None

    mr = _REASON_RE.search(line)
    if mr:
        out["reason"] = mr.group(1)
    else:
        out["reason"] = ""

    try:
        out["score"] = int(out.get("score", 0))
    except Exception:
        out["score"] = 0
    try:
        out["z"] = int(out.get("z", 0))
    except Exception:
        out["z"] = 0
    out["accepted"] = _bool_from_text(out.get("accepted", "False"))
    out["linear"] = _bool_from_text(out.get("linear", "False"))
    out["job"] = normalize_job_id(out.get("job", ""))

    source = out.get("source", "") or ""
    if "/" in source:
        out["transform_view"] = source.split("/", 1)[1]
        out["source_base"] = source.split("/", 1)[0]
    else:
        out["transform_view"] = "unknown"
        out["source_base"] = source
    return out


# -----------------------------
# Population passports
# -----------------------------

CONTROL_FORMS = {
    "ckpool",
    "loopkc",
    "/mined by nerdminer/",
    "/renimdren yb denim/",
    "ldeni yb drenenim",
    "oopkm/",
    "loonim/b deen yimdr/ren",
    "mined",
    "deen",
    "yimdr",
    "ren",
}


# -----------------------------
# Open sweep + JANUS "The Secret" Back/Forth Shadow
# -----------------------------

STRONG_REASON_TOKENS = {
    "encoding_strong_candidate",
    "baseline_anomaly_low_entropy",
    "encoding_mirror_glyph",
    "encoding_regex_like_glyph",
}
SOFT_REASON_TOKENS = {
    "encoding_encoded_fragment",
    "symbol_glyph_candidate",
    "weird_glyph_candidate",
    "linear_context",
}
COINBASE_SOURCES = {"coinb2", "coinbase_full"}


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def is_control_glyph(glyph: str) -> bool:
    low = (glyph or "").strip().lower()
    if not low:
        return True
    if low in CONTROL_FORMS:
        return True
    return any(token in low for token in ("nerdminer", "renimdren", "loopkc", "ckpool", "denim", "yimdr/ren", "loonim/b"))


def glyph_skeleton(glyph: str) -> str:
    """Shape-level fingerprint: keeps punctuation, compresses letters/digits."""
    out: List[str] = []
    for ch in glyph:
        if ch.isdigit():
            out.append("9")
        elif "A" <= ch <= "Z":
            out.append("A")
        elif "a" <= ch <= "z":
            out.append("a")
        elif ch.isspace():
            out.append("_")
        else:
            out.append(ch)
    return "".join(out)


def reverse_text(glyph: str) -> str:
    return (glyph or "")[::-1]


def anchor_key_for(parsed: Dict[str, Any]) -> str:
    glyph = str(parsed.get("text", ""))
    # Exact glyph is kept, but source_base is included so merkle/ntime/coinbase ecology do not collapse.
    raw = "|".join([
        str(parsed.get("source_base", "")),
        glyph_skeleton(glyph),
        glyph,
    ])
    return hashlib.sha1(raw.encode("utf-8", "replace")).hexdigest()[:16]


def reason_tokens(reason: str) -> Set[str]:
    return {x.strip() for x in str(reason or "").split(",") if x.strip()}


def open_sweep_score(parsed: Dict[str, Any]) -> int:
    glyph = str(parsed.get("text", ""))
    z = int(parsed.get("z", 0) or 0)
    score = int(parsed.get("score", 0) or 0)
    accepted = bool(parsed.get("accepted", False))
    src_base = str(parsed.get("source_base", ""))
    view = str(parsed.get("transform_view", ""))
    tokens = reason_tokens(str(parsed.get("reason", "")))

    out = score
    out += min(60, max(0, z) * 2)
    if accepted:
        out += 25
    if z >= 28:
        out += 35
    elif z >= 25:
        out += 12
    if tokens & STRONG_REASON_TOKENS:
        out += 25
    if "encoding_encoded_fragment" in tokens:
        out += 8
    if "linear_context" in tokens:
        out += 5
    if view in {"reversed", "word_reversed"}:
        out += 5
    if src_base in COINBASE_SOURCES:
        out -= 15
    if is_control_glyph(glyph):
        out -= 200
    if len(glyph.strip()) < 3:
        out -= 20
    return int(out)


def is_open_sweep_candidate(parsed: Dict[str, Any]) -> bool:
    glyph = str(parsed.get("text", ""))
    if is_control_glyph(glyph):
        return False
    z = int(parsed.get("z", 0) or 0)
    accepted = bool(parsed.get("accepted", False))
    tokens = reason_tokens(str(parsed.get("reason", "")))
    score = open_sweep_score(parsed)
    # Broad archaeology sweep: do not pre-name families, but avoid dumping pure boilerplate.
    return bool(
        score >= 58
        or (accepted and score >= 48)
        or z >= 28
        or bool(tokens & STRONG_REASON_TOKENS and score >= 45)
    )


@dataclass
class SecretAnchorState:
    anchor_id: str
    glyph: str
    skeleton: str
    source_base: str
    first_seen_utc: str = ""
    last_seen_utc: str = ""
    events_total: int = 0
    accepted_events: int = 0
    rare_tail_events_z28_plus: int = 0
    max_z: int = 0
    unique_jobs: Set[str] = field(default_factory=set)
    views: Dict[str, int] = field(default_factory=dict)
    reasons: Dict[str, int] = field(default_factory=dict)
    forward_reward: float = 0.0
    backward_reward: float = 0.0
    mirror_reward: float = 0.0
    last_motion: str = "HOLD_OBSERVE"
    belief: float = 0.0
    resistance: float = 1.0
    gratitude: float = 0.0

    def observe(self, parsed: Dict[str, Any], sweep_score: int) -> Dict[str, Any]:
        now = utc_now_iso()
        if not self.first_seen_utc:
            self.first_seen_utc = now
        self.last_seen_utc = now
        self.events_total += 1
        glyph = str(parsed.get("text", ""))
        if glyph and glyph != self.glyph and len(glyph) > len(self.glyph):
            self.glyph = glyph
        z = int(parsed.get("z", 0) or 0)
        accepted = bool(parsed.get("accepted", False))
        if accepted:
            self.accepted_events += 1
        if accepted and z >= 28:
            self.rare_tail_events_z28_plus += 1
        self.max_z = max(self.max_z, z)
        job = str(parsed.get("job", ""))
        if job:
            self.unique_jobs.add(job)
        view = str(parsed.get("transform_view", "unknown"))
        self.views[view] = self.views.get(view, 0) + 1
        for token in reason_tokens(str(parsed.get("reason", ""))):
            self.reasons[token] = self.reasons.get(token, 0) + 1

        reward = max(0.0, sweep_score / 100.0)
        if accepted:
            reward += 0.35
        if z >= 28:
            reward += 0.70
        elif z >= 25:
            reward += 0.20
        tokens = reason_tokens(str(parsed.get("reason", "")))
        if tokens & STRONG_REASON_TOKENS:
            reward += 0.30

        # Machine translation of "The Secret": repeated focus reinforces the path that keeps producing useful feedback.
        if view == "raw":
            self.forward_reward += reward
        elif view in {"reversed", "word_reversed"}:
            self.backward_reward += reward
        else:
            self.forward_reward += reward * 0.5
            self.backward_reward += reward * 0.5
        if "encoding_mirror_glyph" in tokens or reverse_text(glyph) != glyph:
            self.mirror_reward += reward * 0.55
        if accepted or z >= 28:
            self.gratitude += reward

        total_reward = self.forward_reward + self.backward_reward + self.mirror_reward
        repeat_bonus = min(0.25, max(0, len(self.unique_jobs) - 1) * 0.05)
        self.belief = clamp01(0.08 + total_reward / 8.0 + repeat_bonus)
        self.resistance = clamp01(1.0 - self.belief)
        return self.motion_vector(parsed, sweep_score)

    def motion_vector(self, parsed: Dict[str, Any], sweep_score: int) -> Dict[str, Any]:
        view = str(parsed.get("transform_view", "unknown"))
        src_base = str(parsed.get("source_base", ""))
        tokens = reason_tokens(str(parsed.get("reason", "")))
        z = int(parsed.get("z", 0) or 0)
        accepted = bool(parsed.get("accepted", False))

        f = 0.34 + self.forward_reward
        b = 0.34 + self.backward_reward
        m = 0.32 + self.mirror_reward
        if view == "raw":
            f += 0.25
        if view == "reversed":
            b += 0.25
        if view == "word_reversed":
            b += 0.16
            m += 0.16
        if "encoding_mirror_glyph" in tokens:
            m += 0.45
        if "baseline_anomaly_low_entropy" in tokens:
            m += 0.12
            b += 0.08
        if src_base.startswith("merkle_branch"):
            f += 0.10
            b += 0.10
        if src_base == "ntime":
            m += 0.25
        if accepted:
            # Receiving feedback: do not jump wildly; walk around the accepted surface.
            f += 0.15
            b += 0.15
        if z >= 28:
            f += 0.25
            b += 0.25
            m += 0.25

        total = max(0.0001, f + b + m)
        fw, bw, mw = f / total, b / total, m / total
        if mw >= fw and mw >= bw:
            motion = "MIRROR_BACKFORTH"
        elif fw >= bw:
            motion = "FORWARD_PROBE"
        else:
            motion = "BACKWARD_PROBE"
        if self.belief < 0.22 and not accepted and z < 28:
            motion = "HOLD_OBSERVE"
        self.last_motion = motion
        step_hint = "small"
        if accepted and z >= 28:
            step_hint = "rare_tail_anchor_radius"
        elif accepted:
            step_hint = "accepted_surface_radius"
        elif z >= 28:
            step_hint = "rare_tail_shadow_radius"
        return {
            "motion": motion,
            "forward_score": round(fw, 4),
            "backward_score": round(bw, 4),
            "mirror_score": round(mw, 4),
            "step_hint": step_hint,
            "janus_half_only": True,
            "mirror_control_effect": "none",
            "wire_change_required": False,
            "scheduler_effect": "shadow_only",
            "why": {
                "ask": "seek non-control glyph surfaces that repeat near accepted/rare-tail contexts",
                "believe": round(self.belief, 4),
                "resistance": round(self.resistance, 4),
                "receive_ready": bool(accepted or z >= 28),
                "attention_score": int(sweep_score),
            },
        }

    def to_state(self) -> Dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "glyph": self.glyph,
            "skeleton": self.skeleton,
            "source_base": self.source_base,
            "first_seen_utc": self.first_seen_utc,
            "last_seen_utc": self.last_seen_utc,
            "events_total": self.events_total,
            "accepted_events": self.accepted_events,
            "rare_tail_events_z28_plus": self.rare_tail_events_z28_plus,
            "max_z": self.max_z,
            "unique_job_count": len(self.unique_jobs),
            "unique_job_ids_tail": sorted(self.unique_jobs)[-20:],
            "views": dict(sorted(self.views.items())),
            "top_reasons": dict(sorted(self.reasons.items(), key=lambda kv: kv[1], reverse=True)[:12]),
            "rewards": {
                "forward": round(self.forward_reward, 4),
                "backward": round(self.backward_reward, 4),
                "mirror": round(self.mirror_reward, 4),
            },
            "last_motion": self.last_motion,
            "belief": round(self.belief, 4),
            "resistance": round(self.resistance, 4),
            "gratitude": round(self.gratitude, 4),
        }


class JanusSecretBackForthEngine:
    """Observer-only learner inspired by the user's machine translation of The Secret.

    It does not move the miner yet. It creates an intention field: what JANUS would
    focus on and whether it would probe forward/backward/mirror around a symbol anchor.
    This keeps the randomized mirror and wire clean.
    """

    def __init__(self) -> None:
        self.anchors: Dict[str, SecretAnchorState] = {}
        self.events_total = 0
        self.shadow_events = 0
        self.gratitude_events = 0
        self.last_intention: Dict[str, Any] = {}

    def process(self, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not is_open_sweep_candidate(parsed):
            return None
        self.events_total += 1
        glyph = str(parsed.get("text", ""))
        key = anchor_key_for(parsed)
        if key not in self.anchors:
            self.anchors[key] = SecretAnchorState(
                anchor_id=key,
                glyph=glyph,
                skeleton=glyph_skeleton(glyph),
                source_base=str(parsed.get("source_base", "")),
            )
        sweep_score = open_sweep_score(parsed)
        anchor = self.anchors[key]
        motion = anchor.observe(parsed, sweep_score)
        accepted = bool(parsed.get("accepted", False))
        z = int(parsed.get("z", 0) or 0)
        is_positive = bool(accepted or z >= 28 or (reason_tokens(str(parsed.get("reason", ""))) & STRONG_REASON_TOKENS))
        if is_positive:
            self.gratitude_events += 1
        event = {
            "ts_utc": utc_now_iso(),
            "family_layer": "A10_SECRET_BACKFORTH_SHADOW",
            "observer_only": True,
            "sidecar_only": True,
            "wire_change_required": False,
            "scheduler_effect": "shadow_only",
            "ethic_layer": love_tachyon_ethic_metadata(),
            "secret_model": {
                "core_principle": "repeated focus shapes attention filter, decision bias and action selection",
                "ask": "define desired glyph surface: non-control, repeatable, accepted/rare-tail linked",
                "believe": "keep searching path unless feedback proves it is noise",
                "receive": "when opportunity/accepted-tail appears, mark anchor and suggest local back/forth probe",
                "gratitude": "positive reinforcement for useful anchors, not mystical proof",
            },
            "detected_glyph": glyph,
            "anchor_id": key,
            "skeleton": glyph_skeleton(glyph),
            "open_sweep_score": sweep_score,
            "context": {
                "job_id": parsed.get("job", ""),
                "zbits": z,
                "accepted": accepted,
                "source": parsed.get("source", ""),
                "source_base": parsed.get("source_base", ""),
                "transform_view": parsed.get("transform_view", ""),
                "priority": parsed.get("priority", ""),
                "score": parsed.get("score", 0),
                "linear": parsed.get("linear", False),
                "reason": parsed.get("reason", ""),
            },
            "motion_vector": motion,
            "anchor_state": anchor.to_state(),
            "control_rejected": False,
        }
        if motion.get("motion") != "HOLD_OBSERVE":
            self.shadow_events += 1
        self.last_intention = self._build_intention_field(event)
        return event

    def _build_intention_field(self, last_event: Dict[str, Any]) -> Dict[str, Any]:
        top = self.top_anchors(8)
        return {
            "ts_utc": utc_now_iso(),
            "family_layer": "A10_JANUS_INTENTION_FIELD",
            "observer_only": True,
            "sidecar_only": True,
            "wire_change_required": False,
            "scheduler_effect": "shadow_only",
            "ethic_layer": love_tachyon_ethic_metadata(),
            "goal": "increase detection of useful non-control glyph surfaces without touching wire/hash/submit",
            "pipeline": [
                "THOUGHT/GOAL -> target non-control accepted/rare-tail glyph surfaces",
                "ATTENTION_FILTER -> open_sweep_score",
                "EMOTION_STATE -> belief/resistance/gratitude weights",
                "DECISION_BIAS -> forward/backward/mirror shadow motion",
                "ACTION -> write intention only; JANUS scheduler not modified yet",
                "FEEDBACK -> accepted/z/repeat/job diversity reinforces anchor",
            ],
            "last_anchor": {
                "anchor_id": last_event.get("anchor_id"),
                "glyph": last_event.get("detected_glyph"),
                "motion_vector": last_event.get("motion_vector"),
            },
            "stats": {
                "open_sweep_events": self.events_total,
                "shadow_motion_events": self.shadow_events,
                "gratitude_events": self.gratitude_events,
                "anchor_count": len(self.anchors),
            },
            "top_anchors": top,
        }

    def top_anchors(self, limit: int = 12) -> List[Dict[str, Any]]:
        rows = [a.to_state() for a in self.anchors.values()]
        rows.sort(key=lambda r: (
            int(r.get("rare_tail_events_z28_plus", 0)),
            int(r.get("accepted_events", 0)),
            int(r.get("unique_job_count", 0)),
            int(r.get("max_z", 0)),
            float(r.get("belief", 0.0)),
            int(r.get("events_total", 0)),
        ), reverse=True)
        return rows[:max(1, int(limit))]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "ts_utc": utc_now_iso(),
            "family_layer": "A10_SECRET_BACKFORTH_SHADOW",
            "observer_only": True,
            "sidecar_only": True,
            "wire_change_required": False,
            "scheduler_effect": "shadow_only",
            "ethic_layer": love_tachyon_ethic_metadata(),
            "stats": {
                "open_sweep_events": self.events_total,
                "shadow_motion_events": self.shadow_events,
                "gratitude_events": self.gratitude_events,
                "anchor_count": len(self.anchors),
            },
            "top_anchors": self.top_anchors(50),
        }


@dataclass
class FamilyPassport:
    family_id: str
    canonical: str
    mirror: str = ""
    family_type: str = "repeated glyph family"
    status: str = "semantic unconfirmed"
    forms: Set[str] = field(default_factory=set)
    events_by_form: Dict[str, int] = field(default_factory=dict)
    unique_jobs: Set[str] = field(default_factory=set)
    accepted_link_events: int = 0
    rare_tail_links: int = 0
    max_z: int = 0
    source_distribution: Dict[str, int] = field(default_factory=dict)
    transform_views: Dict[str, int] = field(default_factory=dict)
    z_histogram: Dict[str, int] = field(default_factory=dict)
    last_seen_utc: str = ""
    last_job_id: str = ""

    def __post_init__(self) -> None:
        if not self.forms:
            self.forms = {self.canonical}
            if self.mirror:
                self.forms.add(self.mirror)
        for form in list(self.forms):
            self.events_by_form.setdefault(form, 0)

    def observe(self, glyph: str, job_id: str, zbits: int, accepted: bool, source: str, view: str) -> Dict[str, Any]:
        self.forms.add(glyph)
        self.events_by_form[glyph] = self.events_by_form.get(glyph, 0) + 1
        if job_id:
            self.unique_jobs.add(job_id)
        if accepted:
            self.accepted_link_events += 1
        if accepted and zbits >= 28:
            self.rare_tail_links += 1
        if zbits > self.max_z:
            self.max_z = zbits
        self.source_distribution[source] = self.source_distribution.get(source, 0) + 1
        self.transform_views[view] = self.transform_views.get(view, 0) + 1
        self.z_histogram[str(zbits)] = self.z_histogram.get(str(zbits), 0) + 1
        self.last_seen_utc = utc_now_iso()
        self.last_job_id = job_id
        return self.to_state()

    def to_state(self) -> Dict[str, Any]:
        return {
            "family_id": self.family_id,
            "canonical": self.canonical,
            "mirror": self.mirror,
            "type": self.family_type,
            "status": self.status,
            "forms": sorted(self.forms),
            "events_total": sum(self.events_by_form.values()),
            "events_by_form": dict(sorted(self.events_by_form.items())),
            "unique_job_count": len(self.unique_jobs),
            "unique_job_ids_tail": sorted(self.unique_jobs)[-20:],
            "accepted_link_events": self.accepted_link_events,
            "rare_tail_links_z28_plus": self.rare_tail_links,
            "max_z_historic": self.max_z,
            "source_distribution": dict(sorted(self.source_distribution.items())),
            "transform_views": dict(sorted(self.transform_views.items())),
            "z_histogram": dict(sorted(self.z_histogram.items(), key=lambda kv: int(kv[0]) if str(kv[0]).lstrip('-').isdigit() else 0)),
            "last_seen_utc": self.last_seen_utc,
            "last_job_id": self.last_job_id,
        }


class JanusGlyphEcologyRadar:
    def __init__(self) -> None:
        self.registry: Dict[str, FamilyPassport] = {}
        self._seed_registry()
        self.mutation_history: List[Dict[str, Any]] = []
        self.seen_lines = 0
        self.matched_events = 0
        self.gate_events = 0

    def _seed_registry(self) -> None:
        def add(p: FamilyPassport) -> None:
            self.registry[p.family_id] = p

        add(FamilyPassport(
            family_id="VECTOR_POINTER_VV",
            canonical="VV<~",
            mirror="~<VV",
            family_type="repeated glyph candidate",
            status="rare-tail linked, semantic unconfirmed",
            max_z=28,
        ))
        add(FamilyPassport(
            family_id="EXTREME_COMPRESSED_VA",
            canonical="va^&",
            mirror="k#@\"",
            family_type="encoded-fragment ecology",
            status="mirror z35-context candidate, semantic unconfirmed",
            max_z=35,
        ))
        add(FamilyPassport(
            family_id="MIRROR_GEOMETRY_8CCG",
            canonical="8CCG",
            mirror="GCC8",
            family_type="stable mirror form",
            status="strong mirror form, no rare-tail gate yet",
            max_z=26,
        ))
        add(FamilyPassport(
            family_id="SECONDARY_KRRO",
            canonical="KRRO",
            family_type="secondary strong candidate",
            status="max z30, needs repeat on new job_id",
            max_z=30,
        ))
        add(FamilyPassport(
            family_id="SECONDARY_AMP_FU",
            canonical="&&fU",
            family_type="secondary encoded-fragment candidate",
            status="max z32, old one-job context, needs repeat outside old job",
            max_z=32,
        ))
        add(FamilyPassport(
            family_id="HOLD_PLEA_AELP_KEY",
            canonical="pLEA",
            mirror="AELp",
            family_type="hold candidate",
            status="hold; target scan did not repeat",
            forms={"pLEA", "AELp", "key"},
        ))
        # Known local/mutation structures. These are watch-only, not gates by themselves.
        add(FamilyPassport(
            family_id="MUTATION_BRACKET_B_L",
            canonical="?b?L",
            mirror="L?b?",
            family_type="mutation/drift family",
            status="tracking structural drift; semantic unconfirmed",
        ))
        add(FamilyPassport(
            family_id="MUTATION_CORE_22",
            canonical=">22+",
            mirror="1>22+",
            family_type="mutation/drift family",
            status="tracking numeric-core drift; semantic unconfirmed",
            forms={">22+", "1>22+", "+22>1", "1>22+"},
        ))

    def _control_match(self, glyph: str) -> Optional[Dict[str, Any]]:
        low = glyph.strip().lower()
        if low in CONTROL_FORMS:
            return {
                "family_id": "POOL_BOILERPLATE_CONTROL",
                "canonical": glyph,
                "mirror": "",
                "type": "coinbase boilerplate/control",
                "status": "control/background; not an easter egg",
                "events_total": None,
                "unique_job_count": None,
                "max_z_historic": None,
            }
        # Coinb2/coinbase reversed fragments can be partial but recognizable.
        if any(token in low for token in ("nerdminer", "renimdren", "loopkc", "ckpool")):
            return {
                "family_id": "POOL_BOILERPLATE_CONTROL",
                "canonical": glyph,
                "mirror": "",
                "type": "coinbase boilerplate/control",
                "status": "control/background; not an easter egg",
                "events_total": None,
                "unique_job_count": None,
                "max_z_historic": None,
            }
        return None

    def _match_family(self, glyph: str) -> Optional[FamilyPassport]:
        for passport in self.registry.values():
            if glyph in passport.forms:
                return passport
        return None

    def _mutation_notes(self, glyph: str) -> List[str]:
        notes: List[str] = []
        # Numeric core drift is intentionally narrow:
        # track forms like >22+, 1>23+, +22>1, not every random digit+letter fragment.
        flow_like = bool(
            re.search(r"^\d*>\d{2,}\+$", glyph)
            or re.search(r"^\+\d{2,}>\d+$", glyph)
            or ("22" in glyph and (">" in glyph or "+" in glyph))
        )
        if flow_like:
            digits = re.findall(r"\d+", glyph)
            if digits:
                notes.append("numeric_core=" + ",".join(digits[:3]))
            notes.append("flow_operator_pattern")
        if "?" in glyph and "L" in glyph and len(glyph) <= 8:
            notes.append("bracket_frame_candidate")
        if glyph in {"d)A)", ")A)d", ")<)c", "c)<)", "mD'&'", "'&'Dm"}:
            notes.append("local_low_entropy_mirror_like_form")
        return notes

    def process_glyph_alert(self, parsed: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.seen_lines += 1
        glyph = str(parsed.get("text", ""))
        job_id = str(parsed.get("job", ""))
        zbits = int(parsed.get("z", 0) or 0)
        accepted = bool(parsed.get("accepted", False))
        source = str(parsed.get("source", ""))
        view = str(parsed.get("transform_view", "unknown"))

        control_state = self._control_match(glyph)
        passport = self._match_family(glyph)
        mutation_notes = self._mutation_notes(glyph)

        # Emit only when a known family/drift is involved, or when a control appears in an accepted/rare context.
        if not passport and not mutation_notes and not (control_state and (accepted or zbits >= 28)):
            return None

        if passport:
            population_state = passport.observe(glyph, job_id, zbits, accepted, source, view)
            family_id = passport.family_id
            classification = passport.family_type
            status = passport.status
        elif control_state:
            population_state = control_state
            family_id = control_state["family_id"]
            classification = control_state["type"]
            status = control_state["status"]
        else:
            population_state = {
                "family_id": "MUTATION_DRIFT_CANDIDATE",
                "canonical": "unknown",
                "mirror": "unknown",
                "type": "mutation/drift candidate",
                "status": "tracking drift; semantic unconfirmed",
                "max_z_historic": zbits,
            }
            family_id = "MUTATION_DRIFT_CANDIDATE"
            classification = "mutation/drift candidate"
            status = "tracking drift; semantic unconfirmed"

        gate_candidate = bool(
            accepted
            and (
                zbits >= 28
                and family_id not in {"POOL_BOILERPLATE_CONTROL"}
            )
        )
        high_interest = bool(gate_candidate or zbits >= 32 or family_id in {"VECTOR_POINTER_VV", "EXTREME_COMPRESSED_VA"})

        event = {
            "ts_utc": utc_now_iso(),
            "family_layer": "A10_GLYPH_ECOLOGY_RADAR",
            "observer_only": True,
            "sidecar_only": True,
            "wire_change_required": False,
            "detected_glyph": glyph,
            "classification": classification,
            "status": status,
            "context": {
                "job_id": job_id,
                "zbits": zbits,
                "accepted": accepted,
                "source": source,
                "source_base": parsed.get("source_base", ""),
                "transform_view": view,
                "priority": parsed.get("priority", ""),
                "score": parsed.get("score", 0),
                "linear": parsed.get("linear", False),
                "reason": parsed.get("reason", ""),
            },
            "population_state": population_state,
            "mutation_tracker_notes": mutation_notes if mutation_notes else ["stable_form_no_drift"],
            "gate_candidate": gate_candidate,
            "high_interest": high_interest,
        }
        self.matched_events += 1
        if gate_candidate:
            self.gate_events += 1
        return event

    def snapshot(self) -> Dict[str, Any]:
        return {
            "ts_utc": utc_now_iso(),
            "family_layer": "A10_GLYPH_ECOLOGY_RADAR",
            "observer_only": True,
            "sidecar_only": True,
            "wire_change_required": False,
            "stats": {
                "seen_glyph_alert_lines": self.seen_lines,
                "matched_radar_events": self.matched_events,
                "gate_events": self.gate_events,
            },
            "families": {fid: passport.to_state() for fid, passport in sorted(self.registry.items())},
        }


# -----------------------------
# Sidecar sink
# -----------------------------

class SidecarSink:
    def __init__(self, out_dir: Path, echo_radar: bool = True) -> None:
        self.out_dir = out_dir
        safe_mkdir(out_dir)
        self.radar_jsonl = out_dir / "a10_glyph_ecology_radar.jsonl"
        self.gates_jsonl = out_dir / "a10_glyph_ecology_gates.jsonl"
        self.registry_json = out_dir / "a10_glyph_ecology_registry.json"
        self.console_log = out_dir / "a10_live_console.log"
        self.open_sweep_jsonl = out_dir / "a10_open_sweep_candidates.jsonl"
        self.backforth_jsonl = out_dir / "a10_symbol_backforth_shadow.jsonl"
        self.anchor_memory_json = out_dir / "a10_symbol_anchor_memory.json"
        self.intention_field_json = out_dir / "a10_janus_intention_field.json"
        self.gratitude_jsonl = out_dir / "a10_secret_gratitude.jsonl"
        self.echo_radar = echo_radar
        self._last_snapshot = 0.0
        # Touch output files so tooling can always find them, even before first gate.
        for fp in (self.radar_jsonl, self.gates_jsonl, self.console_log, self.open_sweep_jsonl, self.backforth_jsonl, self.gratitude_jsonl):
            try:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.touch(exist_ok=True)
            except Exception:
                pass

    def write_console_line(self, line: str) -> None:
        with self.console_log.open("a", encoding="utf-8", errors="replace") as f:
            f.write(line + "\n")

    def write_event(self, event: Dict[str, Any]) -> None:
        append_jsonl(self.radar_jsonl, event)
        if event.get("gate_candidate") or event.get("high_interest"):
            append_jsonl(self.gates_jsonl, event)
        if self.echo_radar:
            fam = event.get("population_state", {}).get("family_id", "?")
            glyph = event.get("detected_glyph", "")
            ctx = event.get("context", {})
            tag = "GATE" if event.get("gate_candidate") else "RADAR"
            print(f"[A10_ECOLOGY | {tag}] family={fam} glyph={glyph!r} z={ctx.get('zbits')} accepted={ctx.get('accepted')} job={ctx.get('job_id')} view={ctx.get('transform_view')}", flush=True)

    def write_secret_event(self, event: Dict[str, Any]) -> None:
        append_jsonl(self.open_sweep_jsonl, event)
        if event.get("motion_vector", {}).get("motion") != "HOLD_OBSERVE":
            append_jsonl(self.backforth_jsonl, event)
        ctx = event.get("context", {})
        if ctx.get("accepted") or int(ctx.get("zbits", 0) or 0) >= 28:
            append_jsonl(self.gratitude_jsonl, event)
        if self.echo_radar:
            mv = event.get("motion_vector", {})
            glyph = event.get("detected_glyph", "")
            print(f"[A10_SECRET | SHADOW] glyph={glyph!r} motion={mv.get('motion')} f={mv.get('forward_score')} b={mv.get('backward_score')} m={mv.get('mirror_score')} score={event.get('open_sweep_score')} z={ctx.get('zbits')} accepted={ctx.get('accepted')} job={ctx.get('job_id')}", flush=True)

    def maybe_snapshot(self, radar: JanusGlyphEcologyRadar, backforth: Optional[JanusSecretBackForthEngine] = None, force: bool = False) -> None:
        now = time.time()
        if force or (now - self._last_snapshot) >= 15:
            with self.registry_json.open("w", encoding="utf-8", errors="replace") as f:
                json.dump(radar.snapshot(), f, ensure_ascii=False, indent=2)
            if backforth is not None:
                with self.anchor_memory_json.open("w", encoding="utf-8", errors="replace") as f:
                    json.dump(backforth.snapshot(), f, ensure_ascii=False, indent=2)
                with self.intention_field_json.open("w", encoding="utf-8", errors="replace") as f:
                    json.dump(backforth.last_intention or backforth.snapshot(), f, ensure_ascii=False, indent=2)
            self._last_snapshot = now


def output_dir_from_args(output_root: Optional[str], run_name: str, explicit_dir: Optional[str]) -> Path:
    if explicit_dir:
        return Path(explicit_dir).expanduser().resolve()
    root = Path(output_root or os.environ.get("AVENGERS_RADAR_ROOT") or os.getcwd()).expanduser()
    return (root / run_name / "sidecar").resolve()


def extract_run_name(pass_through_args: List[str], default: str) -> str:
    for i, arg in enumerate(pass_through_args):
        if arg == "--io-run-name" and i + 1 < len(pass_through_args):
            return pass_through_args[i + 1]
        if arg.startswith("--io-run-name="):
            return arg.split("=", 1)[1]
    return default


def process_line(line: str, radar: JanusGlyphEcologyRadar, sink: SidecarSink, backforth: Optional[JanusSecretBackForthEngine] = None) -> None:
    parsed = parse_glyph_alert_line(line)
    if not parsed:
        return
    try:
        if backforth is not None:
            backforth_event = backforth.process(parsed)
            if backforth_event:
                sink.write_secret_event(backforth_event)
        event = radar.process_glyph_alert(parsed)
        if event:
            sink.write_event(event)
    except Exception as exc:
        # Never allow sidecar failures to affect miner/scan.
        err = {
            "ts_utc": utc_now_iso(),
            "family_layer": "A10_GLYPH_ECOLOGY_RADAR",
            "observer_only": True,
            "sidecar_only": True,
            "wire_change_required": False,
            "error": "sidecar_parse_exception",
            "exception": repr(exc),
        }
        append_jsonl(sink.out_dir / "a10_glyph_ecology_errors.jsonl", err)


# -----------------------------
# CLI modes
# -----------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    run_name = args.run_name
    out_dir = output_dir_from_args(args.output_root, run_name, args.output_dir)
    radar = JanusGlyphEcologyRadar()
    backforth = JanusSecretBackForthEngine()
    sink = SidecarSink(out_dir, echo_radar=not args.quiet)
    input_path = Path(args.input).expanduser().resolve()

    if not input_path.exists():
        print(f"ERROR: input log not found: {input_path}", file=sys.stderr)
        return 2

    for line in read_text_lines(input_path):
        process_line(line, radar, sink, backforth)
        sink.maybe_snapshot(radar, backforth)
    sink.maybe_snapshot(radar, backforth, force=True)
    print(f"[A10_ECOLOGY] scan complete: {input_path}")
    print(f"[A10_ECOLOGY] output: {out_dir}")
    print(f"[A10_ECOLOGY] matched_events={radar.matched_events} gate_events={radar.gate_events}")
    print(f"[A10_SECRET] open_sweep_events={backforth.events_total} shadow_motion_events={backforth.shadow_events}")
    return 0


def cmd_run(args: argparse.Namespace, pass_through_args: List[str]) -> int:
    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print(f"ERROR: target miner not found: {target}", file=sys.stderr)
        return 2

    run_name = args.run_name or extract_run_name(pass_through_args, "A10_ENCODING_ARCHAEOLOGY_THE_AVENGERS")
    out_dir = output_dir_from_args(args.output_root, run_name, args.output_dir)
    radar = JanusGlyphEcologyRadar()
    backforth = JanusSecretBackForthEngine()
    sink = SidecarSink(out_dir, echo_radar=not args.quiet)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8:replace")

    cmd = [sys.executable, "-u", str(target)] + pass_through_args
    print("[A10_ECOLOGY] SIDEcar mode: observer-only, wire frozen, miner file unmodified", flush=True)
    print("[A10_SECRET] Back/Forth Shadow enabled: ask/believe/receive attention loop, shadow-only", flush=True)
    print("[A10_ETHIC] Love Tachyon care-prior: observer-only; WIRE/HASH/SUBMIT frozen", flush=True)
    print(f"[A10_ECOLOGY] target: {target}", flush=True)
    print(f"[A10_ECOLOGY] output: {out_dir}", flush=True)
    print(f"[A10_ECOLOGY] command: {' '.join(cmd)}", flush=True)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=None,
            cwd=str(target.parent),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as exc:
        print(f"ERROR: failed to launch target miner: {exc!r}", file=sys.stderr)
        return 3

    assert proc.stdout is not None
    try:
        for raw_line in proc.stdout:
            line = raw_line.rstrip("\r\n")
            # Mirror original miner output first.
            print(line, flush=True)
            try:
                sink.write_console_line(line)
            except Exception:
                pass
            process_line(line, radar, sink, backforth)
            sink.maybe_snapshot(radar, backforth)
    except KeyboardInterrupt:
        print("[A10_ECOLOGY] KeyboardInterrupt: terminating child miner...", flush=True)
        try:
            proc.terminate()
        except Exception:
            pass
    finally:
        try:
            rc = proc.wait(timeout=10)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            rc = 1
        sink.maybe_snapshot(radar, backforth, force=True)
        print(f"[A10_ECOLOGY] child exit code: {rc}", flush=True)
        print(f"[A10_ECOLOGY] matched_events={radar.matched_events} gate_events={radar.gate_events}", flush=True)
        print(f"[A10_SECRET] open_sweep_events={backforth.events_total} shadow_motion_events={backforth.shadow_events}", flush=True)
        print(f"[A10_ECOLOGY] registry: {sink.registry_json}", flush=True)
        print(f"[A10_SECRET] anchor_memory: {sink.anchor_memory_json}", flush=True)
        print(f"[A10_SECRET] intention_field: {sink.intention_field_json}", flush=True)
    return int(rc or 0)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="A10 glyph ecology sidecar radar")
    sub = p.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("scan", help="scan an existing log file offline")
    s.add_argument("--input", required=True, help="path to log file")
    s.add_argument("--run-name", default="A10_ENCODING_ARCHAEOLOGY_THE_AVENGERS")
    s.add_argument("--output-root", default=None)
    s.add_argument("--output-dir", default=None)
    s.add_argument("--quiet", action="store_true")

    r = sub.add_parser("run", help="run miner as child process and parse stdout sidecar-only")
    r.add_argument("--target", required=True, help="path to miner .py file")
    r.add_argument("--run-name", default=None)
    r.add_argument("--output-root", default=None)
    r.add_argument("--output-dir", default=None)
    r.add_argument("--quiet", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" in argv:
        idx = argv.index("--")
        own_args = argv[:idx]
        pass_through = argv[idx + 1:]
    else:
        own_args = argv
        pass_through = []
    parser = build_parser()
    args = parser.parse_args(own_args)
    if args.mode == "scan":
        return cmd_scan(args)
    if args.mode == "run":
        return cmd_run(args, pass_through)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
