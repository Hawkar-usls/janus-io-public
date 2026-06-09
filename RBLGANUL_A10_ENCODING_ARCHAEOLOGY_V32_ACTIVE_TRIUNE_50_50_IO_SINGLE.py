#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBLGANUL A9.11 / V32 TRIUNE ATOMIC CLOCK KOMBUCHA FINAL STRICT 50_50 SINGLE
2026-06-05

Goal:
  1) Use all CPU cores by default.
  2) Mine Stratum V1 work from a lottery-style NerdMiner solo pool by default.
  3) Treat zbits as rarity logs, not as SHA direction signals.
  4) Fix/diagnose the core problem seen in V19/V20/V22 logs:
       local "pool_pass=True" but pool rejects with "Difficulty too low".
  5) V24 NonceWire: canonical header still uses LE nonce bytes, but Stratum submit
     sends nonce as big-endian integer hex so the pool reconstructs the same header.
  6) V24 TruthGate: submit only pool-reconstructable canonical headers by default.
  7) AutoStart profile: pool.nerdminers.org:3333, public placeholder worker,
     no forced pool-diff suggestion, local_submit_z=0, with auto-escalation disabled.
  8) ZimCore imports the useful mechanics from Zim.ino: NerdMiner subscribe tag,
     LE extranonce2 sequence, reverse odd-stride nonce walk, online stride bandit,
     notify-cadence pause, canonical NonceWire TruthGate, and persistent stride memory.

Run on PC:
  python RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py

A9.11 experiment:
  Strict 50/50 comparison of a BunnyHop JANUS arm against a randomized
  traversal mirror. The JANUS arm starts in BunnyHop Scout: random nonce
  traversal inside JANUS-shaped lane/sector scaffolds. It wakes into the
  original V32 broad JANUS mixture only after a fresh accepted-share corpus gate
  or a rare-tail anchor. If broad JANUS later stalls before the next target
  tail, BunnyHop Memory ReJump briefly re-enters a JANUS-shaped re-scout phase
  instead of falling back to the mirror. No wire, header, submit, prevhash,
  extranonce, or allocator path is changed.

V31 modes:
  --mode proof    fixed local gate, no auto-relax after accepted; default
  --mode lab      effective gate follows pool_z for maximum proof frequency
  --mode lottery  fixed local gate, reserved for future high-z policy


V31 DualLock Oracle additions, imported from your GitHub architecture:
  - JanusModeController: EXPLORE / EXPLOIT / SURVIVE / CHAOS / HUNT task allocation.
  - ProofMind memory: elite combos, bad/reject memory, best_brain persistence.
  - Registry split: raw_accepted / registry / inferred / meta_rules.
  - Tachyon-lite action scoring and PSO-lite batch pressure, controlling scheduler only.
  - StaleGuard before submit: drops candidates if a clean newer job arrived.
  - EnduranceOracle: dynamic batch governor, strategy pruning, sector lock,
    accepted-per-MH metrics, cooldown/SURVIVE guard, proof_dashboard.json.

Hard lock:
  Wire bytes are frozen from accepted V26/V27/V28. V31 changes scheduler/endurance/proof/lane weights only.

Embedded defaults:
  --host pool.nerdminers.org --port 3333 --user CHANGE_ME.JanusA10Public --password x
  --suggest-diff 1.0 --local-submit-z 0 --no-auto-escalate-local-z --no-lowdiff-jump-to-floor --matrix canonical

Optional:
  python RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py --workers 16 --batch 100000

Important:
  This is an experimental harness. It does not break SHA-256.
  It measures and submits shares according to Stratum job data.

A9.11 note:
  V32 scheduler/wire behavior is preserved. A9.11 keeps the BunnyHop Memory ReJump
  50/50 survival test and adds WitchHunter: an observer-only dark-tail corpus
  for pool rejects, StaleGuard drops, and reconnect old-round drops. WitchHunter
  intentionally ignores accepted shares, never creates extra submits, and never
  changes scheduler/wire behavior. It asks whether rare-tail telemetry also
  appears in the trash boundary ordinary miners ignore.

  A9.11 adds Active SovereignGate on top of Sovereign Triad + Kombucha Cell
  Microkernel + Triune Atomic Clock:
    - Red / Trickster: exploration pressure and rare-tail hunger.
    - Blue / Shadow: recovery pressure, stalls, cooldown, re-scout need.
    - Gold / Sovereign: frozen wire guard, stability, hold on weak margins.
    - Kombucha cells: 12 tiny nuclei with acid/yeast/bacteria/charge/paradox,
      surface spread, and microkernel_pressure for correlation only.
    - Triune Atomic Clock: timing jitter, phase bucket, battery charge, and
      Janus-particle boundary orientation. It treats the wire as fixed
      chemistry and observes how traversal surfaces contact the pool boundary.
  A9.11 is the first build where the triad is allowed to act, but only inside
  the JANUS half of the strict 50/50 experiment. The randomized traversal mirror
  remains untouched. Wire/header/nonce/submit/extranonce remain frozen.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures as cf
import csv
import dataclasses
import decimal
import hashlib
import json
import math
import os
import random
import re
import select
import socket
import ssl
import struct
import sys
import time
import traceback
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None  # type: ignore[assignment]


VERSION = "Rblganul A9.11 V32 Active Triune Sovereign Gate Strict 50_50 IO SINGLE 20260605"
SENTINEL = "RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE_20260605"

DEFAULT_HOST = "pool.nerdminers.org"
DEFAULT_PORT = 3333
DEFAULT_TLS = False

# Public repository placeholder. Set RBLGANUL_USER for any live run.
DEFAULT_USER = "CHANGE_ME.JanusA10Public"
DEFAULT_PASSWORD = "x"
DIAGNOSTIC_LABEL = "zimcore"

U256_MAX = (1 << 256) - 1

# Bitcoin difficulty-1 target.
DIFF1_TARGET = int(
    "00000000ffff0000000000000000000000000000000000000000000000000000", 16
)

STRATEGIES = ("zim_reverse", "zim_bandit", "linear", "random", "janus", "knight", "bitrev")
SECTORS = 12

DEFAULT_SUBSCRIBE_TAG = "NerdMinerV2/JanusA10EncodingArchaeology-Public"
ZIM_STRIDE_ARMS = (1, 3, 5, 7, 11, 17, 29, 31, 53, 97, 257, 521, 4099, 65537, 0x9E3779B9, 0xC4111903, 0x4F1BBCDD)
ZIM_STRIDE_MIN_BITS = 16

# V31 ProofMind session state. This is intentionally outside the wire path.
SESSION_STATE: Dict[str, Any] = {
    "active": False,
    "summary_path": "session_summary.json",
    "started_wall": 0.0,
    "started_at_utc": "",
    "round": 0,
    "best_z": 0,
    "submitted": 0,
    "accepted": 0,
    "rejected": 0,
}
STRATEGY_SCOREBOARD: Dict[str, Dict[str, Any]] = {}
SESSION_ATEXIT_INSTALLED = False

# V31 DualLock Oracle runtime objects. They are intentionally outside the hot
# worker loop and outside wire construction. They only track scheduler lanes,
# accepted/MH, and high-z tail events.
V31_RATEBOOK = None
V31_TAIL_TRACKER = None
V31_DUALLOCK_MEMORY = None
A9_ACCOUNTING = None
WITCH_HUNTER = None
V32_NETWORK_RECOVERY = None
RARE_TAIL_TIMING_MONITOR = None
JANUS_GLYPH_OBSERVER = None

JANUS_MODES = ("EXPLORE", "EXPLOIT", "SURVIVE", "CHAOS", "HUNT")
PROOFMIND_SCHEMA_VERSION = "v31-duallock-oracle-registry-1"


def scoreboard_key(strategy: Any, sector: Any, cfg_name: Any) -> str:
    return f"{strategy}/s{sector}/{cfg_name}"


def _score_entry(strategy: Any, sector: Any, cfg_name: Any) -> Dict[str, Any]:
    key = scoreboard_key(strategy, sector, cfg_name)
    if key not in STRATEGY_SCOREBOARD:
        STRATEGY_SCOREBOARD[key] = {
            "key": key,
            "strategy": strategy,
            "sector": sector,
            "cfg_name": cfg_name,
            "accepted": 0,
            "observations": 0,
            "best_z": 0,
            "last_hps": 0,
        }
    return STRATEGY_SCOREBOARD[key]


def score_observe_result(r: Any) -> None:
    try:
        e = _score_entry(r.strategy, r.sector, r.cfg_name)
        e["observations"] = int(e.get("observations", 0)) + 1
        e["best_z"] = max(int(e.get("best_z", 0)), int(getattr(r, "best_z", 0)))
        e["last_hps"] = int(getattr(r, "hps", 0) or 0)
    except Exception:
        pass


def score_observe_accepted(cand: Dict[str, Any]) -> None:
    try:
        e = _score_entry(cand.get("strategy"), cand.get("sector"), cand.get("cfg_name"))
        e["accepted"] = int(e.get("accepted", 0)) + 1
        e["best_z"] = max(int(e.get("best_z", 0)), int(cand.get("zbits", 0) or 0))
    except Exception:
        pass


def top_strategy_scoreboard(limit: int = 3) -> List[Dict[str, Any]]:
    rows = list(STRATEGY_SCOREBOARD.values())
    rows.sort(key=lambda x: (int(x.get("accepted", 0)), int(x.get("best_z", 0)), int(x.get("observations", 0))), reverse=True)
    return rows[: max(1, int(limit))]


def compute_effective_submit_z(mode: str, local_submit_z: int, learned_floor_z: int, pool_z: float) -> int:
    """V31 gate policy; does not alter any header/submit bytes."""
    pool_gate = int(math.ceil(pool_z))
    if mode == "lab":
        return max(pool_gate, 0)
    # proof and lottery keep the requested local gate fixed; learned_floor_z only moves if
    # the user explicitly enabled reject-driven escalation.
    return max(int(local_submit_z), int(learned_floor_z), pool_gate)


def update_session_state(**kw: Any) -> None:
    SESSION_STATE.update(kw)


def write_session_summary(path: Optional[str] = None) -> None:
    try:
        if not SESSION_STATE.get("active"):
            return
        out = dict(SESSION_STATE)
        out["written_at_utc"] = utc_stamp_iso()
        started_wall = float(out.get("started_wall") or 0.0)
        out["duration_seconds"] = max(0.0, time.time() - started_wall) if started_wall else 0.0
        out["top_strategy_scoreboard"] = top_strategy_scoreboard(10)
        atomic_json(path or str(out.get("summary_path") or "session_summary.json"), out)
    except Exception as e:
        try:
            log("summary", f"session_summary write failed: {e}")
        except Exception:
            pass


def install_session_atexit() -> None:
    global SESSION_ATEXIT_INSTALLED
    if not SESSION_ATEXIT_INSTALLED:
        import atexit
        atexit.register(write_session_summary)
        SESSION_ATEXIT_INSTALLED = True


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def log(tag: str, msg: str) -> None:
    print(f"[Rblganul | {tag}] {msg}", flush=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def dsha(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def revhex(h: str) -> str:
    return bytes.fromhex(h)[::-1].hex()


def reverse_word_bytes_py(data: bytes) -> bytes:
    """Reverse byte order inside each 32-bit word, exactly like Zim.ino reverse_word_bytes()."""
    if len(data) % 4 != 0:
        raise ValueError("reverse_word_bytes_py requires length multiple of 4")
    return b"".join(data[i:i+4][::-1] for i in range(0, len(data), 4))


def safe_hex_to_bytes(h: str, field: str = "hex") -> bytes:
    h = h.strip()
    if len(h) % 2:
        raise ValueError(f"{field}: odd hex length")
    try:
        return bytes.fromhex(h)
    except ValueError as e:
        raise ValueError(f"{field}: invalid hex: {h[:64]}...") from e


def int_u32_le_hex(x: int) -> str:
    return (x & 0xFFFFFFFF).to_bytes(4, "little").hex()


def int_u32_be_hex(x: int) -> str:
    return (x & 0xFFFFFFFF).to_bytes(4, "big").hex()


def hex_u32_to_le_bytes(h: str) -> bytes:
    return int(h, 16).to_bytes(4, "little")


def hex_u32_to_be_bytes(h: str) -> bytes:
    return int(h, 16).to_bytes(4, "big")


def bit_reverse32(x: int) -> int:
    x &= 0xFFFFFFFF
    x = ((x & 0x55555555) << 1) | ((x >> 1) & 0x55555555)
    x = ((x & 0x33333333) << 2) | ((x >> 2) & 0x33333333)
    x = ((x & 0x0F0F0F0F) << 4) | ((x >> 4) & 0x0F0F0F0F)
    x = ((x & 0x00FF00FF) << 8) | ((x >> 8) & 0x00FF00FF)
    x = ((x & 0x0000FFFF) << 16) | ((x >> 16) & 0x0000FFFF)
    return x & 0xFFFFFFFF


def leading_zero_bits_display(display_hash_hex: str) -> int:
    # display_hash_hex is big-endian human hash, normally raw_digest[::-1].hex().
    n = 0
    for ch in display_hash_hex:
        v = int(ch, 16)
        if v == 0:
            n += 4
            continue
        # count leading zeros in nibble
        if v < 2:
            n += 3
        elif v < 4:
            n += 2
        elif v < 8:
            n += 1
        break
    return n


def difficulty_to_target(diff: float) -> int:
    if diff <= 0:
        diff = 1.0
    decimal.getcontext().prec = 80
    d = decimal.Decimal(str(diff))
    t = decimal.Decimal(DIFF1_TARGET) / d
    if t < 0:
        return 0
    if t > U256_MAX:
        return U256_MAX
    return int(t)


def target_to_z_approx(target: int) -> float:
    if target <= 0:
        return 256.0
    return max(0.0, 256.0 - math.log2(target + 1))


def z_to_target(zbits: int) -> int:
    """A strict leading-zero-bit target used as an internal submit gate."""
    z = max(0, min(256, int(zbits)))
    if z >= 256:
        return 0
    return (1 << (256 - z)) - 1


def z_to_difficulty(zbits: int) -> float:
    """Approximate Stratum difficulty represented by an internal zbits floor."""
    t = z_to_target(zbits)
    if t <= 0:
        return float("inf")
    return max(0.0, float(decimal.Decimal(DIFF1_TARGET) / decimal.Decimal(t)))


def difficulty_to_z_ceiling(diff: float) -> int:
    """Small helper for the PoolFloor jump: difficulty -> strict zbits gate."""
    return int(math.ceil(target_to_z_approx(difficulty_to_target(float(diff)))))

def expected_share_seconds(diff: float, hps: float) -> float:
    """Expected seconds per accepted share at Stratum difficulty diff."""
    if hps <= 0:
        return float("inf")
    return float(diff) * 4294967296.0 / float(hps)

def fmt_duration(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        return "inf"
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = seconds / 60.0
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60.0
    if hours < 24:
        return f"{hours:.1f}h"
    days = hours / 24.0
    if days < 365:
        return f"{days:.1f}d"
    return f"{days/365.0:.2f}y"


def compact_bits_to_target(nbits_hex: str) -> int:
    """
    Bitcoin compact nBits target.
    nbits is sent as hex like '1d00ffff'. It is a compact big-endian number.
    """
    nbits_hex = nbits_hex.strip()
    if len(nbits_hex) != 8:
        return 0
    nbits = int(nbits_hex, 16)
    exp = nbits >> 24
    mant = nbits & 0x007fffff
    if exp <= 3:
        return mant >> (8 * (3 - exp))
    return mant << (8 * (exp - 3))


def mask_hex(h: str, n: int = 32) -> str:
    if len(h) <= n:
        return h
    return h[:n] + "..."


def make_extranonce2(counter: int, size: int, endian: str = "big") -> str:
    # Critical fix vs previous crash: Python requires "big" / "little", not "be" / "le".
    endian = {"be": "big", "le": "little"}.get(endian, endian)
    if endian not in ("big", "little"):
        endian = "big"
    if size <= 0:
        return ""
    return (counter & ((1 << (size * 8)) - 1)).to_bytes(size, endian).hex()


def stable_seed(*parts: Any) -> int:
    h = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return int.from_bytes(h[:8], "little")


# ---------------------------------------------------------------------------
# Stratum
# ---------------------------------------------------------------------------

class JsonLineSocket:
    def __init__(self, host: str, port: int, use_tls: bool, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.buf = b""

    def connect(self) -> None:
        raw = socket.create_connection((self.host, self.port), timeout=self.timeout)
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if self.use_tls:
            ctx = ssl.create_default_context()
            self.sock = ctx.wrap_socket(raw, server_hostname=self.host)
        else:
            self.sock = raw
        self.sock.setblocking(False)

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None

    def send_json(self, obj: Dict[str, Any]) -> None:
        if not self.sock:
            raise RuntimeError("socket not connected")
        data = (json.dumps(obj, separators=(",", ":")) + "\n").encode("utf-8")
        total = 0
        while total < len(data):
            try:
                sent = self.sock.send(data[total:])
                if sent <= 0:
                    raise ConnectionError("socket closed on send")
                total += sent
            except (BlockingIOError, InterruptedError):
                select.select([], [self.sock], [], 0.2)

    def recv_one(self, timeout: float = 0.0) -> Optional[Dict[str, Any]]:
        if not self.sock:
            return None

        end = time.time() + max(0.0, timeout)
        while True:
            nl = self.buf.find(b"\n")
            if nl >= 0:
                line = self.buf[:nl]
                self.buf = self.buf[nl + 1:]
                if not line.strip():
                    continue
                try:
                    return json.loads(line.decode("utf-8", "replace"))
                except json.JSONDecodeError:
                    log("wire", f"bad json line={line[:160]!r}")
                    continue

            remain = max(0.0, end - time.time()) if timeout > 0 else 0.0
            r, _, _ = select.select([self.sock], [], [], remain)
            if not r:
                return None

            try:
                chunk = self.sock.recv(65536)
            except (BlockingIOError, InterruptedError):
                if timeout <= 0:
                    return None
                continue
            if not chunk:
                raise ConnectionError("socket closed by peer")
            self.buf += chunk


@dataclass
class Job:
    job_id: str
    prevhash: str
    coinb1: str
    coinb2: str
    merkle_branch: List[str]
    version: str
    nbits: str
    ntime: str
    clean: bool
    seq: int = 0
    received_ms: int = 0

    @classmethod
    def from_notify(cls, params: List[Any], seq: int) -> "Job":
        # Stratum V1 mining.notify:
        # [job_id, prevhash, coinb1, coinb2, merkle_branch, version, nbits, ntime, clean_jobs]
        if len(params) < 9:
            raise ValueError(f"mining.notify has {len(params)} params, expected >=9")
        return cls(
            job_id=str(params[0]),
            prevhash=str(params[1]),
            coinb1=str(params[2]),
            coinb2=str(params[3]),
            merkle_branch=[str(x) for x in params[4]],
            version=str(params[5]),
            nbits=str(params[6]),
            ntime=str(params[7]),
            clean=bool(params[8]),
            seq=seq,
            received_ms=now_ms(),
        )


class StratumClient:
    def __init__(self, host: str, port: int, use_tls: bool, user: str, password: str, subscribe_tag: str = DEFAULT_SUBSCRIBE_TAG, proof_dir: str = "proofs"):
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.user = user
        self.password = password
        self.subscribe_tag = subscribe_tag
        self.proof_dir = proof_dir
        self.sock = JsonLineSocket(host, port, use_tls)

        self.next_id = 1
        self.extranonce1 = ""
        self.extranonce2_size = 0
        self.authorized = False
        self.pool_diff = 1.0
        self.job: Optional[Job] = None
        self.job_seq = 0

        self.pending_submits: Dict[int, Dict[str, Any]] = {}
        self.accepted = 0
        self.rejected = 0
        self.submitted = 0

    def connect(self) -> None:
        log("stratum", f"connecting {self.host}:{self.port} tls={self.use_tls}")
        self.sock.connect()

    def send(self, method: str, params: List[Any]) -> int:
        msg_id = self.next_id
        self.next_id += 1
        self.sock.send_json({"id": msg_id, "method": method, "params": params})
        return msg_id

    def subscribe(self) -> int:
        return self.send("mining.subscribe", [self.subscribe_tag])

    def authorize(self) -> int:
        return self.send("mining.authorize", [self.user, self.password])

    def suggest_difficulty(self, diff: float) -> int:
        return self.send("mining.suggest_difficulty", [diff])

    def submit(self, cand: Dict[str, Any]) -> int:
        """
        Stratum submit params:
          worker_name, job_id, extranonce2, ntime, nonce
        nonce is sent as exact header nonce bytes hex by default.
        """
        nonce_submit_hex = cand["nonce_submit_hex"]
        params = [
            self.user,
            cand["job_id"],
            cand["extranonce2"],
            cand["ntime"],
            nonce_submit_hex,
        ]
        cand["submit_params"] = list(params)
        cand["submitted_at_utc"] = utc_stamp_iso()
        msg_id = self.send("mining.submit", params)
        self.pending_submits[msg_id] = cand
        self.submitted += 1
        log(
            "submit",
            "candidate id={} cfg={} z={} nonce_submit={} nonce_int={:08x} en2={} hash={}".format(
                msg_id,
                cand.get("cfg_name"),
                cand.get("zbits"),
                nonce_submit_hex,
                int(cand.get("nonce_int", 0)),
                cand.get("extranonce2"),
                mask_hex(cand.get("display_hash", ""), 48),
            ),
        )
        return msg_id

    def handle_message(self, msg: Dict[str, Any]) -> None:
        method = msg.get("method")
        if method == "mining.set_difficulty":
            params = msg.get("params") or []
            if params:
                try:
                    self.pool_diff = float(params[0])
                    log("stratum", f"difficulty={self.pool_diff:g}")
                except Exception:
                    log("stratum", f"bad difficulty params={params}")
            return

        if method == "mining.notify":
            params = msg.get("params") or []
            self.job_seq += 1
            try:
                self.job = Job.from_notify(params, self.job_seq)
                log("stratum", f"new job={self.job.job_id} clean={self.job.clean} seq={self.job.seq}")
            except Exception as e:
                log("stratum", f"bad notify: {e}")
            return

        # Response
        if "id" in msg:
            mid = msg.get("id")
            if mid in self.pending_submits:
                cand = self.pending_submits.pop(mid)
                if msg.get("result") is True:
                    self.accepted += 1
                    log(
                        "submit",
                        "ACCEPTED total={} cfg={} z={} nonce={} hash={}".format(
                            self.accepted,
                            cand.get("cfg_name"),
                            cand.get("zbits"),
                            cand.get("nonce_submit_hex"),
                            mask_hex(cand.get("display_hash", ""), 64),
                        ),
                    )
                    cand2 = dict(cand)
                    cand2["pool_response"] = msg
                    cand2["accepted_at_utc"] = utc_stamp_iso()
                    cand2["accepted_total"] = self.accepted
                    dump_json("rblganul_v31_endurance_last_accepted.json", cand2)
                    dump_accepted_proof(self.proof_dir, cand2)
                else:
                    self.rejected += 1
                    log(
                        "submit",
                        "REJECT total={} cfg={} z={} result={} error={} nonce={} hash={}".format(
                            self.rejected,
                            cand.get("cfg_name"),
                            cand.get("zbits"),
                            msg.get("result"),
                            msg.get("error"),
                            cand.get("nonce_submit_hex"),
                            mask_hex(cand.get("display_hash", ""), 64),
                        ),
                    )
                    cand2 = dict(cand)
                    cand2["pool_response"] = msg
                    dump_json("rblganul_v31_endurance_last_reject.json", cand2)
                    dump_reject_registry_artifact(self.proof_dir, cand2)
                    try:
                        if V31_RATEBOOK is not None:
                            V31_RATEBOOK.observe_rejected(cand2)
                            V31_RATEBOOK.save()
                        if A9_ACCOUNTING is not None:
                            A9_ACCOUNTING.observe_rejected(cand2)
                        if WITCH_HUNTER is not None:
                            WITCH_HUNTER.observe_rejected(cand2)
                    except Exception as e:
                        log("v31", f"reject observer failed: {e}")
                return

            # Subscribe result.
            result = msg.get("result")
            if isinstance(result, list) and len(result) >= 3 and isinstance(result[1], str):
                self.extranonce1 = result[1]
                self.extranonce2_size = int(result[2])
                log(
                    "stratum",
                    f"subscribed extranonce1={self.extranonce1} extranonce2_size={self.extranonce2_size}",
                )
                return

            # Authorize result.
            if isinstance(result, bool):
                self.authorized = result
                log("stratum", f"authorized={result} error={msg.get('error')}")
                return

    def read_available(self, max_messages: int = 100, timeout: float = 0.0) -> int:
        n = 0
        for i in range(max_messages):
            msg = self.sock.recv_one(timeout=timeout if i == 0 else 0.0)
            if msg is None:
                break
            n += 1
            self.handle_message(msg)
        return n


class V32NetworkRecovery:
    """V32 socket lifecycle guard.

    This module is intentionally outside the mining/wire path. It only reconnects
    Stratum transport and resets stale active jobs after disconnects. It does not
    change header assembly, nonce endian, extranonce2, prevhash mirror, TruthGate,
    submit gate, proof format, or scheduler weights.
    """

    def __init__(self, initial_backoff: float = 1.0, max_backoff: float = 30.0) -> None:
        self.enabled = True
        self.initial_backoff = max(0.1, float(initial_backoff or 1.0))
        self.max_backoff = max(self.initial_backoff, float(max_backoff or 30.0))
        self.current_backoff = self.initial_backoff
        self.reconnect_count = 0
        self.failed_connect_count = 0
        self.last_disconnect_reason: Optional[str] = None
        self.last_disconnect_utc: Optional[str] = None
        self.last_reconnect_utc: Optional[str] = None
        self.last_connect_error: Optional[str] = None
        self.session_generation = 0
        self.stale_round_drops = 0

    def reset_client_transport(self, client: StratumClient, reason: str) -> None:
        self.last_disconnect_reason = str(reason)
        self.last_disconnect_utc = utc_stamp_iso()
        try:
            client.sock.close()
        except Exception:
            pass
        # Discard unread bytes and all submit responses tied to the dead socket.
        client.sock = JsonLineSocket(client.host, client.port, client.use_tls)
        client.extranonce1 = ""
        client.extranonce2_size = 0
        client.authorized = False
        client.job = None
        client.pending_submits.clear()
        self.session_generation += 1

    def connect_sequence(self, client: StratumClient, args: argparse.Namespace, reason: str = "startup") -> None:
        backoff = self.initial_backoff
        first = True
        while True:
            try:
                if not first or reason != "startup":
                    log("v32_net", f"connecting after {reason}; generation={self.session_generation}")
                client.connect()
                client.subscribe()
                if not args.no_suggest_diff:
                    client.suggest_difficulty(args.suggest_diff)
                client.authorize()
                wait_initial_job(client)
                self.reconnect_count += 0 if reason == "startup" else 1
                self.last_reconnect_utc = utc_stamp_iso()
                self.current_backoff = self.initial_backoff
                log("v32_net", f"connected generation={self.session_generation} reconnect_count={self.reconnect_count} job={client.job.job_id if client.job else None}")
                return
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.failed_connect_count += 1
                self.last_connect_error = str(e)
                log("v32_net", f"connect/init failed: {e}; retrying in {backoff:.1f}s")
                try:
                    client.sock.close()
                except Exception:
                    pass
                time.sleep(backoff)
                backoff = min(self.max_backoff, max(self.initial_backoff, backoff * 2.0))
                self.current_backoff = backoff
                # Fresh socket after each failed attempt.
                client.sock = JsonLineSocket(client.host, client.port, client.use_tls)
                first = False

    def recover(self, client: StratumClient, args: argparse.Namespace, reason: str) -> None:
        self.reset_client_transport(client, reason)
        self.connect_sequence(client, args, reason=reason)

    def snapshot(self, client: Optional[StratumClient] = None) -> Dict[str, Any]:
        job_id = None
        job_seq = None
        socket_alive = False
        if client is not None:
            try:
                job_id = client.job.job_id if client.job else None
                job_seq = client.job.seq if client.job else None
                socket_alive = bool(client.sock and client.sock.sock)
            except Exception:
                pass
        return {
            "schema": "v32-network-recovery-1",
            "enabled": self.enabled,
            "reconnect_count": self.reconnect_count,
            "failed_connect_count": self.failed_connect_count,
            "last_disconnect_reason": self.last_disconnect_reason,
            "last_disconnect_utc": self.last_disconnect_utc,
            "last_reconnect_utc": self.last_reconnect_utc,
            "last_connect_error": self.last_connect_error,
            "current_backoff_seconds": self.current_backoff,
            "session_generation": self.session_generation,
            "stale_round_drops": self.stale_round_drops,
            "socket_alive": socket_alive,
            "active_job_id": job_id,
            "active_job_seq": job_seq,
            "wire_change_required": False,
        }


# ---------------------------------------------------------------------------
# Build configs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BuildConfig:
    name: str

    # Job byte handling.
    # NerdMiner/Zim pool quirk: prevhash bytes are swapped per 32-bit word, not full 32-byte reversed.
    prevhash_reverse: bool = True
    prevhash_word_reverse: bool = False
    merkle_branch_reverse: bool = False
    merkle_header_reverse: bool = False

    version_little: bool = True
    ntime_little: bool = True
    nbits_little: bool = True
    nonce_little_in_header: bool = True

    # Submit handling.
    submit_nonce_from_header_bytes: bool = True
    submit_nonce_big_int: bool = False

    # Extranonce2.
    extranonce2_endian: str = "big"

    # True only for headers the pool can reconstruct from mining.submit fields.
    # Non-canonical byte experiments are useful for lab telemetry, but submitting
    # them is guaranteed to be rejected because Stratum submit cannot tell the
    # pool "I reversed prevhash/nbits/ntime/merkle".
    submit_compatible: bool = True


def build_configs(matrix: str) -> List[BuildConfig]:
    # Canonical Bitcoin header uses little-endian nonce bytes inside the 80-byte header,
    # but Stratum mining.submit expects the nonce field as an 8-hex-character
    # big-endian integer string. Example: nonce_int=0x01020304 is hashed in
    # the header as bytes 04 03 02 01, but submitted as "01020304".
    canonical = BuildConfig(
        "canonical",
        # V26/Zim correction: Zim.ino does reverse_word_bytes(prevhash),
        # not full reverse(prevhash). This is the missing NerdMiner pool mirror.
        prevhash_reverse=False,
        prevhash_word_reverse=True,
        submit_nonce_from_header_bytes=False,
        submit_nonce_big_int=True,
        extranonce2_endian="little",
    )
    if matrix == "canonical":
        return [canonical]

    # The extended matrix is deliberately small enough to keep hashrate usable.
    # Each mode is a plausible place where local hash != pool hash can arise.
    return [
        canonical,

        # If full 32-byte reverse was needed instead of Zim word-swap.
        BuildConfig("prev_full_reverse", prevhash_reverse=True, prevhash_word_reverse=False, submit_compatible=False),

        # If merkle branches were accidentally endian-flipped.
        BuildConfig("branch_rev", merkle_branch_reverse=True, submit_compatible=False),

        # If prevhash was not reversed.
        BuildConfig("prev_raw", prevhash_reverse=False, prevhash_word_reverse=False, submit_compatible=False),

        # If merkle root is inserted reversed into header.
        BuildConfig("merkle_header_rev", merkle_header_reverse=True, submit_compatible=False),

        # Submit nonce as integer hex, but header still canonical LE.
        BuildConfig("submit_be_nonce", submit_nonce_from_header_bytes=False, submit_nonce_big_int=True),

        # If nonce in header was accidentally big-endian.
        BuildConfig("nonce_be_header_submit_be", nonce_little_in_header=False,
                    submit_nonce_from_header_bytes=False, submit_nonce_big_int=True, submit_compatible=False),

        # Some broken/miner variants use raw time/bits bytes.
        BuildConfig("ntime_raw", ntime_little=False, submit_compatible=False),
        BuildConfig("nbits_raw", nbits_little=False, submit_compatible=False),
    ]


def field4_bytes(hex8: str, little: bool) -> bytes:
    if len(hex8) != 8:
        raise ValueError(f"expected 4-byte hex, got {hex8!r}")
    return int(hex8, 16).to_bytes(4, "little" if little else "big")


@dataclass
class HeaderBuild:
    header_prefix: bytes
    coinbase_hash_raw: bytes
    merkle_root_raw: bytes
    merkle_root_header: bytes


def prepare_header_prefix(job: Job, extranonce1: str, extranonce2: str, cfg: BuildConfig) -> HeaderBuild:
    coinbase_hex = job.coinb1 + extranonce1 + extranonce2 + job.coinb2
    coinbase = safe_hex_to_bytes(coinbase_hex, "coinbase")
    coinbase_hash = dsha(coinbase)

    merkle = coinbase_hash
    for branch_hex in job.merkle_branch:
        branch = safe_hex_to_bytes(branch_hex, "merkle_branch")
        if cfg.merkle_branch_reverse:
            branch = branch[::-1]
        merkle = dsha(merkle + branch)

    merkle_header = merkle[::-1] if cfg.merkle_header_reverse else merkle

    version_b = field4_bytes(job.version, cfg.version_little)
    prev_b0 = safe_hex_to_bytes(job.prevhash, "prevhash")
    if cfg.prevhash_word_reverse:
        prev_b = reverse_word_bytes_py(prev_b0)
    elif cfg.prevhash_reverse:
        prev_b = prev_b0[::-1]
    else:
        prev_b = prev_b0
    ntime_b = field4_bytes(job.ntime, cfg.ntime_little)
    nbits_b = field4_bytes(job.nbits, cfg.nbits_little)

    prefix = version_b + prev_b + merkle_header + ntime_b + nbits_b
    if len(prefix) != 76:
        raise ValueError(f"bad header prefix length={len(prefix)} cfg={cfg.name}")

    return HeaderBuild(
        header_prefix=prefix,
        coinbase_hash_raw=coinbase_hash,
        merkle_root_raw=merkle,
        merkle_root_header=merkle_header,
    )


def build_nonce_bytes(nonce_int: int, cfg: BuildConfig) -> bytes:
    return (nonce_int & 0xFFFFFFFF).to_bytes(
        4, "little" if cfg.nonce_little_in_header else "big"
    )


def submit_nonce_hex(nonce_int: int, nonce_header_bytes: bytes, cfg: BuildConfig) -> str:
    if cfg.submit_nonce_from_header_bytes:
        return nonce_header_bytes.hex()
    if cfg.submit_nonce_big_int:
        return int_u32_be_hex(nonce_int)
    return int_u32_le_hex(nonce_int)


def pool_nonce_bytes_from_submit(nonce_submit_hex_value: str, cfg: BuildConfig) -> bytes:
    """
    Model how a Stratum pool reconstructs the nonce bytes for the block header.

    Wire rule used by public-pool-style Stratum:
      mining.submit nonce field is an 8-hex-character big-endian integer string.
      The pool parses that integer, then serializes it into the Bitcoin header
      as little-endian uint32 bytes.

    This function intentionally mirrors the pool side, not the local miner side.
    It is the guard that prevents the old V23 bug:
      local header bytes 04 03 02 01 were submitted as "04030201",
      pool parsed that as 0x04030201 and rebuilt header bytes 01 02 03 04.
    """
    ns = str(nonce_submit_hex_value).strip().lower()
    if len(ns) != 8:
        raise ValueError(f"bad submit nonce length: {ns!r}")
    n = int(ns, 16) & 0xFFFFFFFF
    return n.to_bytes(4, "little" if cfg.nonce_little_in_header else "big")


def verify_submit_mirror(job: Job, extranonce1: str, cand: Dict[str, Any], cfg: BuildConfig) -> Tuple[bool, str]:
    """
    Rebuild the exact header from submit-visible fields exactly as the pool will.
    If this fails, never submit.

    V24 fix: do NOT trust cand["nonce_header_hex"] here. That is the local
    header nonce. The pool never receives it. The pool receives nonce_submit_hex,
    parses it as a big-endian integer string, and then writes uint32 LE bytes into
    the block header. This mirror checks that pool reconstruction equals the
    local header that produced the candidate hash.
    """
    try:
        hb = prepare_header_prefix(job, extranonce1, cand["extranonce2"], cfg)
        pool_nonce_bytes = pool_nonce_bytes_from_submit(cand["nonce_submit_hex"], cfg)
        local_nonce_bytes = bytes.fromhex(cand["nonce_header_hex"])
        if pool_nonce_bytes != local_nonce_bytes:
            return (
                False,
                "pool_nonce_wire_mismatch:"
                f"local={local_nonce_bytes.hex()} "
                f"submit={cand['nonce_submit_hex']} "
                f"pool={pool_nonce_bytes.hex()}",
            )
        header = hb.header_prefix + pool_nonce_bytes
        if header.hex() != cand["header_hex"]:
            return False, "header_hex_mismatch_after_pool_rebuild"
        raw = dsha(header)
        display = raw[::-1].hex()
        if display != cand["display_hash"]:
            return False, "hash_mismatch_after_pool_rebuild"
        return True, "ok"
    except Exception as e:
        return False, f"exception:{e}"


# ---------------------------------------------------------------------------
# Nonce generation / strategies
# ---------------------------------------------------------------------------

def sector_base_range(sector: int) -> Tuple[int, int]:
    width = (1 << 32) // SECTORS
    s = max(0, min(SECTORS - 1, int(sector)))
    start = s * width
    # Let the last sector absorb the remainder.
    end = (1 << 32) if s == SECTORS - 1 else (s + 1) * width
    return start, end - start


def nonce_for(strategy: str, sector: int, i: int, seed: int, batch: int, stride: int = 0) -> int:
    start, width = sector_base_range(sector)
    i &= 0xFFFFFFFF
    stride = int(stride or 0) | 1

    if strategy == "zim_reverse":
        # Direct pull from Zim.ino: start near a seeded cursor and walk backwards by an odd stride.
        return (start + ((seed - i * stride) % width)) & 0xFFFFFFFF

    if strategy == "zim_bandit":
        # Same reverse walk, but stride is chosen by ZimStrideBandit in the controller.
        wobble = bit_reverse32((seed ^ (i * 0xA5A5A5A5)) & 0xFFFFFFFF) & 0xFFFF
        return (start + ((seed + wobble - i * stride) % width)) & 0xFFFFFFFF

    if strategy == "linear":
        # Sequential within sector, shifted by seed to avoid repeated starts.
        return (start + ((seed + i) % width)) & 0xFFFFFFFF

    if strategy == "random":
        # Deterministic xorshift64* stream, cheap and reproducible.
        x = (seed + 0x9E3779B97F4A7C15 * (i + 1)) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 12) & 0xFFFFFFFFFFFFFFFF
        x ^= (x << 25) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27) & 0xFFFFFFFFFFFFFFFF
        x = (x * 0x2545F4914F6CDD1D) & 0xFFFFFFFFFFFFFFFF
        return (start + (x % width)) & 0xFFFFFFFF

    if strategy == "janus":
        # Balanced around sector center: center, -1, +1, -2, +2...
        center = width // 2
        step = (i + 1) // 2
        off = center + (step if (i & 1) else -step)
        return (start + (off % width)) & 0xFFFFFFFF

    if strategy == "knight":
        # Full-cycle-ish additive walk with odd stride.
        stride2 = int(width * 0.6180339887498949) | 1
        return (start + ((seed + i * stride2) % width)) & 0xFFFFFFFF

    if strategy == "bitrev":
        # Bit reversal, then map into sector. Good at jumping scales.
        return (start + (bit_reverse32((seed + i) & 0xFFFFFFFF) % width)) & 0xFFFFFFFF

    return (start + ((seed + i) % width)) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Worker mining task
# ---------------------------------------------------------------------------

@dataclass
class MineTask:
    round_id: int
    worker_id: int
    job: Job
    extranonce1: str
    extranonce2_size: int
    pool_diff: float
    batch: int
    strategy: str
    sector: int
    cfg: BuildConfig
    seed: int
    submit_limit: int
    signal_z: int
    local_submit_z: int
    lane: str = "janus_dispatcher"
    stride: int = 0
    stride_arm: int = -1


@dataclass
class MineResult:
    round_id: int
    worker_id: int
    strategy: str
    sector: int
    cfg_name: str
    lane: str
    checked: int
    best_z: int
    best_hash: str
    best_nonce: int
    hps: float
    candidates: List[Dict[str, Any]]
    stride: int = 0
    stride_arm: int = -1
    error: Optional[str] = None


def mine_task(task: MineTask) -> MineResult:
    t0 = time.perf_counter()
    checked = 0
    best_z = -1
    best_hash = ""
    best_nonce = 0
    candidates: List[Dict[str, Any]] = []

    try:
        pool_target = difficulty_to_target(task.pool_diff)
        net_target = compact_bits_to_target(task.job.nbits)
        pool_z = target_to_z_approx(pool_target)
        net_z = target_to_z_approx(net_target) if net_target else 0.0

        # V22 core fix: do NOT submit merely at the pool's very low advertised
        # floor.  After repeated "Difficulty too low" replies, the controller
        # raises task.local_submit_z.  This is an internal difficulty escalator:
        # only hashes below BOTH the pool target and our stricter z target are sent.
        effective_local_z = max(int(math.ceil(pool_z)), int(task.local_submit_z))
        local_submit_target = min(pool_target, z_to_target(effective_local_z))

        # Unique extranonce2 per task. In mining, extranonce2 is part of coinbase.
        # It must be exactly the same bytes in local header and submit.
        en2_counter = (
            task.round_id * 1_000_003
            + task.worker_id * 97
            + task.sector * 13
            + (task.seed & 0xFFFF)
        )
        extranonce2 = make_extranonce2(en2_counter, task.extranonce2_size, task.cfg.extranonce2_endian)

        hb = prepare_header_prefix(task.job, task.extranonce1, extranonce2, task.cfg)

        # For mirror diagnostics.
        merkle_raw_hex = hb.merkle_root_raw.hex()
        merkle_header_hex = hb.merkle_root_header.hex()
        coinbase_hash_hex = hb.coinbase_hash_raw.hex()

        local_submit_count = 0
        seed32 = task.seed & 0xFFFFFFFF

        for i in range(task.batch):
            nonce_int = nonce_for(task.strategy, task.sector, i, seed32, task.batch, task.stride)
            nonce_b = build_nonce_bytes(nonce_int, task.cfg)
            header = hb.header_prefix + nonce_b

            raw = dsha(header)
            # Correct Bitcoin display/hash integer:
            # raw digest interpreted little-endian == reversed digest big-endian.
            hash_int = int.from_bytes(raw, "little")
            display_hash = raw[::-1].hex()
            z = leading_zero_bits_display(display_hash)

            checked += 1
            if z > best_z:
                best_z = z
                best_hash = display_hash
                best_nonce = nonce_int

            # Log deeper local signals but do not confuse them with proof of direction.
            target_pass = hash_int <= local_submit_target
            if target_pass or z >= task.signal_z:
                if target_pass and local_submit_count < task.submit_limit:
                    nonce_submit = submit_nonce_hex(nonce_int, nonce_b, task.cfg)
                    cand = {
                        "version": VERSION,
                        "sentinel": SENTINEL,
                        "round_id": task.round_id,
                        "worker_id": task.worker_id,
                        "job_id": task.job.job_id,
                        "job_seq": task.job.seq,
                        "cfg_name": task.cfg.name,
                        "cfg": asdict(task.cfg),
                        "lane": task.lane,
                        "strategy": task.strategy,
                        "sector": task.sector,
                        "stride": task.stride,
                        "stride_arm": task.stride_arm,
                        "pool_diff": task.pool_diff,
                        "pool_target_hex": f"{pool_target:064x}",
                        "pool_z_approx": pool_z,
                        "local_submit_z": effective_local_z,
                        "local_submit_diff_approx": z_to_difficulty(effective_local_z),
                        "local_submit_target_hex": f"{local_submit_target:064x}",
                        "net_target_hex": f"{net_target:064x}" if net_target else "",
                        "net_z_approx": net_z,
                        "zbits": z,
                        "target_pass": True,
                        "hash_int_le_hex": f"{hash_int:064x}",
                        "display_hash": display_hash,
                        "raw_hash_hex": raw.hex(),
                        "nonce_int": nonce_int,
                        "nonce_header_hex": nonce_b.hex(),
                        "nonce_submit_hex": nonce_submit,
                        "nonce_wire_rule": "submit is big-endian uint32 hex; pool rebuilds header uint32 little-endian",
                        "extranonce1": task.extranonce1,
                        "extranonce2": extranonce2,
                        "ntime": task.job.ntime,
                        "nbits": task.job.nbits,
                        "prevhash": task.job.prevhash,
                        "coinb1": task.job.coinb1,
                        "coinb2": task.job.coinb2,
                        "merkle_branch": list(task.job.merkle_branch),
                        "clean": task.job.clean,
                        "version_hex": task.job.version,
                        "job": {
                            "job_id": task.job.job_id,
                            "prevhash": task.job.prevhash,
                            "coinb1": task.job.coinb1,
                            "coinb2": task.job.coinb2,
                            "merkle_branch": list(task.job.merkle_branch),
                            "version": task.job.version,
                            "nbits": task.job.nbits,
                            "ntime": task.job.ntime,
                            "clean": task.job.clean,
                            "seq": task.job.seq,
                            "received_ms": task.job.received_ms,
                        },
                        "coinbase_hash_raw": coinbase_hash_hex,
                        "merkle_root_raw": merkle_raw_hex,
                        "merkle_root_header": merkle_header_hex,
                        "header_hex": header.hex(),
                        "header_len": len(header),
                        "submit_params": [
                            "<user>",
                            task.job.job_id,
                            extranonce2,
                            task.job.ntime,
                            nonce_submit,
                        ],
                    }
                    candidates.append(cand)
                    local_submit_count += 1

        dt = max(1e-9, time.perf_counter() - t0)
        return MineResult(
            round_id=task.round_id,
            worker_id=task.worker_id,
            strategy=task.strategy,
            sector=task.sector,
            cfg_name=task.cfg.name,
            lane=task.lane,
            checked=checked,
            best_z=max(0, best_z),
            best_hash=best_hash,
            best_nonce=best_nonce,
            hps=checked / dt,
            candidates=candidates,
            stride=task.stride,
            stride_arm=task.stride_arm,
        )

    except BaseException:
        dt = max(1e-9, time.perf_counter() - t0)
        return MineResult(
            round_id=task.round_id,
            worker_id=task.worker_id,
            strategy=task.strategy,
            sector=task.sector,
            cfg_name=task.cfg.name,
            lane=task.lane,
            checked=checked,
            best_z=max(0, best_z),
            best_hash=best_hash,
            best_nonce=best_nonce,
            hps=checked / dt,
            candidates=candidates,
            stride=task.stride,
            stride_arm=task.stride_arm,
            error=traceback.format_exc(),
        )


# ---------------------------------------------------------------------------
# Adaptive scheduler / Zim stride memory / Kombucha memory
# ---------------------------------------------------------------------------


class ZimStrideBandit:
    """Tiny Zim-style no-regret selector for odd reverse strides.

    This does not predict SHA-256. It only allocates more scan time to stride arms
    that recently produced rare zbits in this specific run, while keeping exploration.
    """
    def __init__(self, arms: Tuple[int, ...] = ZIM_STRIDE_ARMS, path: str = "rblganul_v31_zim_stride_memory.json"):
        self.arms = tuple(int(a) | 1 for a in arms)
        self.weights = [256.0 for _ in self.arms]
        self.hits = 0
        self.last_arm = 14 if len(self.arms) > 14 else 0
        self.reward_ema = 0.0
        self.path = path
        self.dirty = False
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            ws = obj.get("weights") or []
            if len(ws) == len(self.weights):
                self.weights = [float(max(16.0, min(8192.0, x))) for x in ws]
                self.last_arm = int(obj.get("last_arm", self.last_arm)) % len(self.arms)
                self.hits = int(obj.get("hits", 0))
                self.reward_ema = float(obj.get("reward_ema", 0.0))
                log("zimcore", f"loaded stride memory arms={len(self.arms)} hits={self.hits} last_arm={self.last_arm}")
        except FileNotFoundError:
            pass
        except Exception as e:
            log("zimcore", f"stride memory load skipped: {e}")

    def save(self, force: bool = False) -> None:
        if (not self.dirty) and (not force):
            return
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"weights": self.weights, "hits": self.hits, "last_arm": self.last_arm, "reward_ema": self.reward_ema}, f, indent=2)
            self.dirty = False
        except Exception as e:
            log("zimcore", f"stride memory save failed: {e}")

    def choose(self, rng: random.Random, seed: int) -> Tuple[int, int]:
        # ~10% exploration, like Zim's EXPLORE_Q8=26.
        if rng.randrange(256) < 26:
            idx = rng.randrange(len(self.arms))
        else:
            total = sum(self.weights)
            pick = (rng.random() * total) if total > 0 else 0.0
            acc = 0.0
            idx = len(self.arms) - 1
            for i, w in enumerate(self.weights):
                acc += w
                if pick <= acc:
                    idx = i
                    break
        # rotate with seed so equal arms do not collide between workers.
        idx = (idx + (seed & 3)) % len(self.arms)
        self.last_arm = idx
        return idx, self.arms[idx]

    def observe(self, arm_idx: int, best_z: int, candidate_count: int, accepted_delta: int, rejected_delta: int) -> None:
        if arm_idx < 0 or arm_idx >= len(self.weights):
            return
        reward = 0.0
        if best_z >= ZIM_STRIDE_MIN_BITS:
            reward += min(64.0, float((best_z - ZIM_STRIDE_MIN_BITS + 1) ** 2))
        if candidate_count > 0:
            reward += 64.0 * candidate_count
        if accepted_delta > 0:
            reward += 512.0 * accepted_delta
        if rejected_delta > 0:
            reward -= 32.0 * rejected_delta
        self.reward_ema = self.reward_ema * 0.93 + reward * 0.07
        # Multiplicative-ish bounded update.
        if reward >= 0:
            self.weights[arm_idx] = min(8192.0, self.weights[arm_idx] * (1.0 + reward / 4096.0) + 1.0)
        else:
            self.weights[arm_idx] = max(16.0, self.weights[arm_idx] * 0.94)
        self.hits += 1 if reward > 0 else 0
        self.dirty = True

    def line(self) -> str:
        return f"stride_arm={self.last_arm}/{len(self.arms)-1} stride={self.arms[self.last_arm]} reward_ema={self.reward_ema:.2f} hits={self.hits} dirty={int(self.dirty)}"


class NotifyOracle:
    """Zim-like notify cadence observer. Avoids launching long chunks right before expected clean job."""
    def __init__(self) -> None:
        self.last_seq = 0
        self.last_ms = 0
        self.intervals = deque(maxlen=24)
        self.pauses = 0

    def update(self, job: Job) -> None:
        if job.seq == self.last_seq:
            return
        now = now_ms()
        if self.last_ms:
            dt = max(1, now - self.last_ms)
            if 500 <= dt <= 900000:
                self.intervals.append(dt)
        self.last_ms = now
        self.last_seq = job.seq

    def median_ms(self) -> int:
        if not self.intervals:
            return 0
        xs = sorted(self.intervals)
        return int(xs[len(xs)//2])

    def should_pause(self, window_ms: int = 450) -> bool:
        med = self.median_ms()
        if not med or not self.last_ms:
            return False
        elapsed = now_ms() - self.last_ms
        rem = med - (elapsed % med)
        if 0 < rem <= window_ms:
            self.pauses += 1
            return True
        return False

    def line(self) -> str:
        return f"notify_median_ms={self.median_ms()} pauses={self.pauses}"

class KombuchaMemory:
    """
    Lightweight adaptive scheduler.

    The name is a project metaphor:
      brew        = exploration pressure
      acidity     = penalty from rejects / low quality
      carbonation = batch expansion confidence

    It never claims SHA direction. It only allocates compute budget across
    strategies/sectors/configs that recently produced rarer candidates or
    better throughput.
    """

    def __init__(self, strategies: Iterable[str], sectors: int, cfg_names: Iterable[str]):
        self.stats: Dict[Tuple[str, int, str], Dict[str, float]] = defaultdict(
            lambda: {"checked": 0.0, "best_z": 0.0, "hps": 0.0, "hits": 0.0, "score": 1.0}
        )
        self.strategies = list(strategies)
        self.sectors = sectors
        self.cfg_names = list(cfg_names)
        self.brew = 0.10
        self.acidity = 0.20
        self.carbonation = 0.80

    def update_result(self, r: MineResult) -> None:
        k = (r.strategy, r.sector, r.cfg_name)
        s = self.stats[k]
        s["checked"] += r.checked
        s["best_z"] = max(s["best_z"], r.best_z)
        s["hps"] = 0.85 * s["hps"] + 0.15 * r.hps if s["hps"] else r.hps
        if r.best_z >= 22:
            s["hits"] += 1.0
        # Rarity reward is logarithmic-ish; speed matters but cannot dominate.
        rarity = max(0.0, (r.best_z - 18) / 8.0)
        speed = min(2.0, r.hps / 200_000.0)
        s["score"] = max(0.05, 0.75 * s["score"] + 0.25 * (1.0 + rarity + 0.15 * speed))

    def on_submit_result(self, accepted: bool) -> None:
        if accepted:
            self.brew = max(0.03, self.brew * 0.85)
            self.acidity = max(0.05, self.acidity * 0.70)
            self.carbonation = min(1.0, self.carbonation + 0.05)
        else:
            self.acidity = min(1.0, self.acidity + 0.03)
            self.brew = min(0.35, self.brew + 0.01)

    def choose(self, rng: random.Random, cfgs: List[BuildConfig], round_id: int, worker_id: int) -> Tuple[str, int, BuildConfig]:
        # Warm start: cover the matrix deterministically.
        if round_id < 4:
            st = self.strategies[(worker_id + round_id) % len(self.strategies)]
            sec = (worker_id * 5 + round_id * 3) % self.sectors
            cfg = cfgs[(worker_id + round_id) % len(cfgs)]
            return st, sec, cfg

        # Explore sometimes.
        if rng.random() < self.brew:
            return (
                rng.choice(self.strategies),
                rng.randrange(self.sectors),
                rng.choice(cfgs),
            )

        # Exploit weighted score.
        choices: List[Tuple[float, str, int, BuildConfig]] = []
        for st in self.strategies:
            for sec in range(self.sectors):
                for cfg in cfgs:
                    s = self.stats[(st, sec, cfg.name)]
                    score = s["score"]
                    # Keep canonical slightly preferred unless another mode proves itself.
                    if cfg.name == "canonical":
                        score *= 1.10
                    choices.append((score, st, sec, cfg))
        total = sum(max(0.01, x[0]) for x in choices)
        pick = rng.random() * total
        acc = 0.0
        for score, st, sec, cfg in choices:
            acc += max(0.01, score)
            if acc >= pick:
                return st, sec, cfg
        _, st, sec, cfg = choices[-1]
        return st, sec, cfg

    def next_batch(self, base_batch: int, accepted: int, rejected: int) -> int:
        # If rejects dominate, shrink to faster diagnostic cycles.
        if rejected > 0 and accepted == 0:
            factor = max(0.35, 1.0 - min(0.65, rejected * 0.002))
        else:
            factor = 1.0 + 0.25 * self.carbonation
        factor *= 1.0 + min(0.5, self.brew)
        return max(10_000, min(2_000_000, int(base_batch * factor)))

    def line(self, next_batch: int) -> str:
        return (
            f"brew={self.brew:.2f} acidity={self.acidity:.2f} "
            f"carbonation={self.carbonation:.2f} next_batch={next_batch:,}"
        )


class JanusProofMind:
    """V31 scheduler brain.

    This is the safe part of Janus-Demiurge ported into Rblganul:
    it changes only task allocation, memory, proof registry, and logging.
    It never changes header bytes, nonce wire format, merkle, prevhash, ntime, or nbits.
    """

    def __init__(self, path: str, registry_dir: str, run_mode: str = "proof") -> None:
        self.path = path
        self.registry_dir = registry_dir
        self.run_mode = run_mode
        self.mode = "EXPLORE"
        self.mode_strength = 0.15
        self.hunger = 0.0
        self.rounds_since_accept = 0
        self.best_z_seen = 0
        self.best_combo: Optional[str] = None
        self.accepted_total_seen = 0
        self.rejected_total_seen = 0
        self.elite: Dict[str, Dict[str, Any]] = {}
        self.bad: Dict[str, Dict[str, Any]] = {}
        self.recent_rewards: Deque[float] = deque(maxlen=64)
        self.pso = {
            "batch_pressure": 1.0,
            "explore_bias": 0.10,
            "chaos_bias": 0.02,
            "survive_bias": 0.0,
        }
        self.load()

    @staticmethod
    def combo_key(strategy: Any, sector: Any, cfg_name: Any, stride_arm: Any = -1) -> str:
        return f"{strategy}/s{sector}/{cfg_name}/a{stride_arm}"

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                self.mode = str(obj.get("mode", self.mode)) if obj.get("mode") in JANUS_MODES else self.mode
                self.mode_strength = float(obj.get("mode_strength", self.mode_strength))
                self.hunger = float(obj.get("hunger", self.hunger))
                self.best_z_seen = int(obj.get("best_z_seen", self.best_z_seen))
                self.best_combo = obj.get("best_combo") or self.best_combo
                self.elite = obj.get("elite", {}) if isinstance(obj.get("elite", {}), dict) else {}
                self.bad = obj.get("bad", {}) if isinstance(obj.get("bad", {}), dict) else {}
                pso = obj.get("pso")
                if isinstance(pso, dict):
                    self.pso.update({k: float(v) for k, v in pso.items() if k in self.pso})
                log("proofmind", f"loaded brain path={self.path} mode={self.mode} elite={len(self.elite)} bad={len(self.bad)} best_z={self.best_z_seen}")
        except FileNotFoundError:
            pass
        except Exception as e:
            log("proofmind", f"brain load skipped: {e}")

    def save(self, force: bool = False) -> None:
        try:
            obj = {
                "version": VERSION,
                "sentinel": SENTINEL,
                "schema": PROOFMIND_SCHEMA_VERSION,
                "updated_at_utc": utc_stamp_iso(),
                "mode": self.mode,
                "mode_strength": self.mode_strength,
                "hunger": self.hunger,
                "best_z_seen": self.best_z_seen,
                "best_combo": self.best_combo,
                "elite": self.elite,
                "bad": self.bad,
                "pso": self.pso,
                "wire_lock": {
                    "nonce_submit_big_endian_uint32_hex": True,
                    "nonce_header_little_endian_bytes": True,
                    "prevhash_word_reverse": True,
                    "extranonce2_little_endian": True,
                },
            }
            atomic_json(self.path, obj)
        except Exception as e:
            log("proofmind", f"brain save failed: {e}")

    def update_mode(self, accepted: int, rejected: int, round_id: int, pool_diff: float) -> None:
        # Janus-Demiurge-inspired instincts, grounded in miner telemetry.
        if accepted > self.accepted_total_seen:
            self.rounds_since_accept = 0
            self.hunger = max(0.0, self.hunger * 0.35)
            self.mode = "EXPLOIT"
            self.mode_strength = min(1.0, self.mode_strength + 0.20)
        else:
            self.rounds_since_accept += 1
            self.hunger = min(1.0, self.hunger + 0.006)

        if rejected > self.rejected_total_seen and rejected > accepted * 0.05 + 3:
            self.mode = "SURVIVE"
            self.mode_strength = min(1.0, self.mode_strength + 0.18)
        elif self.hunger > 0.75:
            self.mode = "CHAOS"
            self.mode_strength = min(1.0, self.mode_strength + 0.10)
        elif self.best_z_seen >= 30 and self.rounds_since_accept < 8:
            self.mode = "HUNT"
            self.mode_strength = min(1.0, self.mode_strength + 0.08)
        elif round_id < 5:
            self.mode = "EXPLORE"
        elif self.mode_strength < 0.25:
            self.mode = "EXPLORE"

        # Slow decay prevents mode lock-in.
        self.mode_strength = max(0.05, self.mode_strength * 0.985)
        self.accepted_total_seen = accepted
        self.rejected_total_seen = rejected

    def reward_for_result(self, r: MineResult) -> float:
        reward = 0.0
        if r.best_z >= 22:
            reward += (r.best_z - 21) ** 2
        reward += min(5.0, (r.hps or 0.0) / 500_000.0)
        reward += 4.0 * len(r.candidates)
        return float(reward)

    def observe_result(self, r: MineResult) -> None:
        key = self.combo_key(r.strategy, r.sector, r.cfg_name, r.stride_arm)
        reward = self.reward_for_result(r)
        self.recent_rewards.append(reward)
        if r.best_z > self.best_z_seen:
            self.best_z_seen = int(r.best_z)
            self.best_combo = key
        e = self.elite.setdefault(key, {
            "key": key, "strategy": r.strategy, "sector": r.sector, "cfg_name": r.cfg_name,
            "stride_arm": r.stride_arm, "observations": 0, "accepted": 0, "rejected": 0,
            "best_z": 0, "reward_ema": 0.0, "last_hps": 0,
        })
        e["observations"] = int(e.get("observations", 0)) + 1
        e["best_z"] = max(int(e.get("best_z", 0)), int(r.best_z))
        e["last_hps"] = int(r.hps or 0)
        e["reward_ema"] = float(e.get("reward_ema", 0.0)) * 0.90 + reward * 0.10
        # Keep memory bounded and useful.
        if len(self.elite) > 512:
            rows = sorted(self.elite.values(), key=lambda x: (int(x.get("accepted", 0)), int(x.get("best_z", 0)), float(x.get("reward_ema", 0.0))), reverse=True)[:256]
            self.elite = {x["key"]: x for x in rows}

    def observe_submit_delta(self, acc_delta: int, rej_delta: int, best: MineResult) -> None:
        if best:
            key = self.combo_key(best.strategy, best.sector, best.cfg_name, best.stride_arm)
            e = self.elite.setdefault(key, {"key": key, "strategy": best.strategy, "sector": best.sector, "cfg_name": best.cfg_name, "stride_arm": best.stride_arm, "observations": 0, "accepted": 0, "rejected": 0, "best_z": 0, "reward_ema": 0.0})
            e["accepted"] = int(e.get("accepted", 0)) + int(acc_delta)
            e["rejected"] = int(e.get("rejected", 0)) + int(rej_delta)
            e["best_z"] = max(int(e.get("best_z", 0)), int(best.best_z or 0))
            if rej_delta > 0 and acc_delta == 0:
                b = self.bad.setdefault(key, {"key": key, "rejected": 0, "last_seen_utc": ""})
                b["rejected"] = int(b.get("rejected", 0)) + int(rej_delta)
                b["last_seen_utc"] = utc_stamp_iso()
            if acc_delta > 0:
                self.pso["explore_bias"] = max(0.03, self.pso["explore_bias"] * 0.92)
                self.pso["batch_pressure"] = min(1.35, self.pso["batch_pressure"] * 1.02)
            if rej_delta > 0:
                self.pso["survive_bias"] = min(0.50, self.pso["survive_bias"] + 0.02 * rej_delta)
                self.pso["batch_pressure"] = max(0.55, self.pso["batch_pressure"] * 0.96)

    def _pick_elite(self, rng: random.Random, cfgs: List[BuildConfig]) -> Optional[Tuple[str, int, BuildConfig]]:
        if not self.elite:
            return None
        rows = list(self.elite.values())
        rows.sort(key=lambda x: (int(x.get("accepted", 0)), int(x.get("best_z", 0)), float(x.get("reward_ema", 0.0))), reverse=True)
        pool = rows[: min(16, len(rows))]
        if not pool:
            return None
        row = rng.choice(pool[: max(1, min(4, len(pool)))]) if self.mode == "HUNT" else rng.choice(pool)
        cfg_name = row.get("cfg_name", "canonical")
        cfg = next((c for c in cfgs if c.name == cfg_name), cfgs[0])
        return str(row.get("strategy", "zim_reverse")), int(row.get("sector", 0)) % SECTORS, cfg

    def choose(self, memory: KombuchaMemory, rng: random.Random, cfgs: List[BuildConfig], round_id: int, worker_id: int) -> Tuple[str, int, BuildConfig]:
        # SURVIVE: avoid known bad combos and prefer the proven canonical Zim path.
        if self.mode == "SURVIVE" and rng.random() < 0.65:
            cfg = next((c for c in cfgs if c.name == "canonical"), cfgs[0])
            return rng.choice(("zim_reverse", "zim_bandit", "linear")), rng.randrange(SECTORS), cfg
        # CHAOS: deliberate exploration, but still canonical by default.
        if self.mode == "CHAOS" and rng.random() < 0.70:
            cfg = next((c for c in cfgs if c.name == "canonical"), rng.choice(cfgs))
            return rng.choice(STRATEGIES), rng.randrange(SECTORS), cfg
        # EXPLOIT/HUNT: bias toward best observed combos.
        if self.mode in ("EXPLOIT", "HUNT") and rng.random() < (0.55 + 0.25 * self.mode_strength):
            picked = self._pick_elite(rng, cfgs)
            if picked:
                return picked
        # EXPLORE or fallback: existing kombucha scheduler.
        return memory.choose(rng, cfgs, round_id, worker_id)

    def batch_factor(self) -> float:
        if self.mode == "SURVIVE":
            return max(0.55, self.pso.get("batch_pressure", 1.0) * 0.80)
        if self.mode == "CHAOS":
            return min(1.15, self.pso.get("batch_pressure", 1.0) * 0.95)
        if self.mode == "HUNT":
            return min(1.35, self.pso.get("batch_pressure", 1.0) * 1.08)
        return float(self.pso.get("batch_pressure", 1.0))

    def line(self) -> str:
        return f"mode={self.mode} strength={self.mode_strength:.2f} hunger={self.hunger:.2f} elite={len(self.elite)} bad={len(self.bad)} best_z={self.best_z_seen} batch_factor={self.batch_factor():.2f}"

    def write_meta_rules(self, args: argparse.Namespace, cfgs: List[BuildConfig]) -> None:
        try:
            root = self.registry_dir
            os.makedirs(os.path.join(root, "meta_rules"), exist_ok=True)
            payload = {
                "schema": PROOFMIND_SCHEMA_VERSION,
                "created_at_utc": utc_stamp_iso(),
                "version": VERSION,
                "sentinel": SENTINEL,
                "rules": {
                    "raw_vs_inferred": "raw proofs and interpreted scores must stay separated",
                    "wire_bytes_frozen": True,
                    "nonce_submit": "big-endian uint32 hex",
                    "nonce_header": "little-endian uint32 bytes",
                    "prevhash": "reverse bytes inside each 32-bit word only",
                    "extranonce2": "little-endian",
                    "noncanonical_submit": bool(args.allow_noncanonical_submit),
                },
                "cfgs": [asdict(c) for c in cfgs],
            }
            atomic_json(os.path.join(root, "meta_rules", "wire_invariants_v30.json"), payload)
        except Exception as e:
            log("proofmind", f"meta_rules write failed: {e}")

    def write_registry_event(self, kind: str, payload: Dict[str, Any]) -> None:
        try:
            safe_kind = ''.join(ch if ch.isalnum() or ch in ('_', '-') else '_' for ch in kind)
            path = os.path.join(self.registry_dir, "registry", f"{safe_kind}_{utc_stamp_file()}_{now_ms()}.json")
            event = {
                "schema": PROOFMIND_SCHEMA_VERSION,
                "kind": kind,
                "created_at_utc": utc_stamp_iso(),
                "version": VERSION,
                "sentinel": SENTINEL,
                "empirical_layer": payload,
                "hypothesis_layer": {},
                "correlation_analysis": {},
                "meta_rules_ref": "meta_rules/wire_invariants_v30.json",
            }
            atomic_json(path, event)
        except Exception as e:
            log("proofmind", f"registry event write failed: {e}")


# ---------------------------------------------------------------------------
# CSV / dumps / ProofPack
# ---------------------------------------------------------------------------

def utc_stamp_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def utc_stamp_file() -> str:
    return time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime())


def atomic_json(path: str, obj: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, path)


def accepted_proof_files_count(proofs_dir: Path) -> int:
    try:
        return sum(1 for p in proofs_dir.glob("accepted_20*_z*_nonce0x*.json") if p.is_file())
    except Exception:
        return 0


def latest_accepted_proof_mtime_utc(proofs_dir: Path) -> str:
    try:
        latest = max(
            (p.stat().st_mtime for p in proofs_dir.glob("accepted_20*_z*_nonce0x*.json") if p.is_file()),
            default=0.0,
        )
        if latest <= 0:
            return ""
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(latest))
    except Exception:
        return ""


def a9_11_fresh_session_boundary(run_dir: Path, proofs_dir: Path) -> Dict[str, Any]:
    """Fresh corpus marker for repeated same-run-dir launches; reporting only."""
    session_id = utc_stamp_file()
    previous_count = accepted_proof_files_count(proofs_dir)
    latest_mtime = latest_accepted_proof_mtime_utc(proofs_dir)
    return {
        "schema": "a9-11-fresh-session-boundary-1",
        "version": VERSION,
        "sentinel": SENTINEL,
        "session_id": session_id,
        "fresh_started_at_utc": utc_stamp_iso(),
        "io_run_dir": str(run_dir),
        "proofs_dir": str(proofs_dir),
        "previous_accepted_proof_files": previous_count,
        "previous_latest_accepted_proof_mtime_utc": latest_mtime,
        "fresh_filter_rule": "For repeated launches in the same run_dir, treat only proof files with mtime/filename timestamp >= fresh_started_at_utc as the fresh accepted-share corpus; total proof files may include older corpus.",
        "dashboard_rule": "Dashboard/accounting counters are process-fresh; proof directory totals are archive totals unless filtered by this boundary.",
        "wire_change_required": False,
        "scheduler_effect": "none",
    }


def a9_11_load_fresh_session_boundary(path: Path, run_dir: Path, proofs_dir: Path) -> Optional[Dict[str, Any]]:
    """Load an existing fresh corpus marker for explicit resume runs.

    Resume mode is reporting-only: it keeps the accepted-share corpus cutoff
    stable across process restarts. It does not change scheduler or wire logic.
    """
    try:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, dict):
            return None
        if obj.get("schema") != "a9-11-fresh-session-boundary-1":
            return None
        obj = dict(obj)
        obj["resume_reused_at_utc"] = utc_stamp_iso()
        obj["resume_mode"] = True
        obj["io_run_dir"] = str(run_dir)
        obj["proofs_dir"] = str(proofs_dir)
        obj["resume_rule"] = "Existing fresh_started_at_utc was reused for an explicit corpus resume; no new cutoff was created."
        obj["wire_change_required"] = False
        obj["scheduler_effect"] = "none"
        return obj
    except Exception:
        return None



class StrategyRateBook:
    """V31 per-lane/per-strategy proof-rate tracker.

    It imports whatever V30 already wrote (dashboard/session/proof index), then
    continues counting in V31-specific JSON files. It never touches Stratum wire,
    header construction, submit order, or TruthGate.
    """

    def __init__(self, path: str, window: int = 256) -> None:
        self.path = path
        self.window = max(16, int(window or 256))
        self.started_at_utc = utc_stamp_iso()
        self.imported = {"accepted": 0, "rejected": 0, "submitted": 0, "best_z": 0, "checked": 0}
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.recent: Deque[Dict[str, Any]] = deque(maxlen=self.window)
        self.load()

    @staticmethod
    def key(lane: Any, strategy: Any, sector: Any, cfg_name: Any) -> str:
        return f"{lane or 'unknown'}::{strategy}/s{sector}/{cfg_name}"

    def _row(self, lane: Any, strategy: Any, sector: Any, cfg_name: Any) -> Dict[str, Any]:
        k = self.key(lane, strategy, sector, cfg_name)
        if k not in self.rows:
            self.rows[k] = {
                "key": k,
                "lane": str(lane or "unknown"),
                "strategy": str(strategy or "unknown"),
                "sector": int(sector or 0) % SECTORS,
                "cfg_name": str(cfg_name or "canonical"),
                "checked": 0,
                "accepted": 0,
                "rejected": 0,
                "submitted": 0,
                "best_z": 0,
                "hps_ewma": 0.0,
                "z24": 0,
                "z28": 0,
                "z30": 0,
                "z32": 0,
                "z33": 0,
                "last_seen_utc": "",
            }
        return self.rows[k]

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                rows = obj.get("rows")
                if isinstance(rows, dict):
                    self.rows = rows
                imp = obj.get("imported")
                if isinstance(imp, dict):
                    self.imported.update({k: imp.get(k, self.imported.get(k, 0)) for k in self.imported})
        except FileNotFoundError:
            pass
        except Exception as e:
            log("v31", f"strategy ratebook load skipped: {e}")

    def import_dashboard(self, path: str) -> Dict[str, Any]:
        out = {"path": path, "loaded": False}
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if not isinstance(obj, dict):
                return out
            out["loaded"] = True
            self.imported["accepted"] = max(int(self.imported.get("accepted", 0)), int(obj.get("accepted", 0) or 0))
            self.imported["rejected"] = max(int(self.imported.get("rejected", 0)), int(obj.get("rejected", 0) or 0))
            self.imported["submitted"] = max(int(self.imported.get("submitted", 0)), int(obj.get("submitted", 0) or 0))
            self.imported["best_z"] = max(int(self.imported.get("best_z", 0)), int(obj.get("best_z", 0) or 0))
            top = obj.get("top_strategy_scoreboard") or []
            if isinstance(top, list):
                for item in top:
                    if not isinstance(item, dict):
                        continue
                    lane = item.get("lane") or "v30_import"
                    row = self._row(lane, item.get("strategy"), item.get("sector", 0), item.get("cfg_name", "canonical"))
                    row["accepted"] = max(int(row.get("accepted", 0)), int(item.get("accepted", 0) or 0))
                    row["best_z"] = max(int(row.get("best_z", 0)), int(item.get("best_z", 0) or 0))
                    row["last_seen_utc"] = utc_stamp_iso()
        except FileNotFoundError:
            pass
        except Exception as e:
            out["error"] = str(e)
            log("v31", f"dashboard import skipped: {e}")
        return out

    def import_accepted_index(self, proof_dir: str) -> Dict[str, Any]:
        path = os.path.join(proof_dir, "accepted_index.json")
        out = {"path": path, "loaded": False, "count": 0}
        try:
            with open(path, "r", encoding="utf-8") as f:
                idx = json.load(f)
            if not isinstance(idx, dict):
                return out
            accepted = idx.get("accepted") or []
            if not isinstance(accepted, list):
                return out
            out["loaded"] = True
            out["count"] = len(accepted)
            self.imported["accepted"] = max(int(self.imported.get("accepted", 0)), len(accepted))
            for ent in accepted[-min(len(accepted), 10000):]:
                if not isinstance(ent, dict):
                    continue
                lane = ent.get("lane") or "v30_import"
                row = self._row(lane, ent.get("strategy"), ent.get("sector", 0), ent.get("cfg_name", "canonical"))
                row["accepted"] = int(row.get("accepted", 0)) + 1
                z = int(ent.get("zbits", ent.get("z", 0)) or 0)
                row["best_z"] = max(int(row.get("best_z", 0)), z)
                for th in (24, 28, 30, 32, 33):
                    if z >= th:
                        row[f"z{th}"] = int(row.get(f"z{th}", 0)) + 1
                row["last_seen_utc"] = utc_stamp_iso()
        except FileNotFoundError:
            pass
        except Exception as e:
            out["error"] = str(e)
            log("v31", f"accepted_index import skipped: {e}")
        return out

    def observe_result(self, r: Any) -> None:
        row = self._row(getattr(r, "lane", "unknown"), getattr(r, "strategy", "unknown"), getattr(r, "sector", 0), getattr(r, "cfg_name", "canonical"))
        checked = max(0, int(getattr(r, "checked", 0) or 0))
        row["checked"] = int(row.get("checked", 0)) + checked
        row["best_z"] = max(int(row.get("best_z", 0)), int(getattr(r, "best_z", 0) or 0))
        hps = float(getattr(r, "hps", 0.0) or 0.0)
        row["hps_ewma"] = hps if float(row.get("hps_ewma", 0.0)) <= 0 else float(row.get("hps_ewma", 0.0)) * 0.85 + hps * 0.15
        row["last_seen_utc"] = utc_stamp_iso()
        self.recent.append({"kind": "result", "key": row["key"], "checked": checked, "best_z": int(getattr(r, "best_z", 0) or 0)})

    def observe_accepted(self, cand: Dict[str, Any]) -> None:
        row = self._row(cand.get("lane", "unknown"), cand.get("strategy"), cand.get("sector", 0), cand.get("cfg_name", "canonical"))
        row["accepted"] = int(row.get("accepted", 0)) + 1
        row["submitted"] = int(row.get("submitted", 0)) + 1
        z = int(cand.get("zbits", 0) or 0)
        row["best_z"] = max(int(row.get("best_z", 0)), z)
        for th in (24, 28, 30, 32, 33):
            if z >= th:
                row[f"z{th}"] = int(row.get(f"z{th}", 0)) + 1
        row["last_seen_utc"] = utc_stamp_iso()
        self.recent.append({"kind": "accepted", "key": row["key"], "z": z})

    def observe_rejected(self, cand: Dict[str, Any]) -> None:
        row = self._row(cand.get("lane", "unknown"), cand.get("strategy"), cand.get("sector", 0), cand.get("cfg_name", "canonical"))
        row["rejected"] = int(row.get("rejected", 0)) + 1
        row["submitted"] = int(row.get("submitted", 0)) + 1
        row["last_seen_utc"] = utc_stamp_iso()

    def rows_list(self) -> List[Dict[str, Any]]:
        rows = []
        for row in self.rows.values():
            x = dict(row)
            mh = max(0.0, float(x.get("checked", 0) or 0) / 1_000_000.0)
            x["mh"] = mh
            x["accepted_per_mh"] = float(x.get("accepted", 0) or 0) / mh if mh > 0 else 0.0
            x["z24_per_mh"] = float(x.get("z24", 0) or 0) / mh if mh > 0 else 0.0
            x["z28_per_mh"] = float(x.get("z28", 0) or 0) / mh if mh > 0 else 0.0
            x["z30_per_mh"] = float(x.get("z30", 0) or 0) / mh if mh > 0 else 0.0
            x["z32_per_mh"] = float(x.get("z32", 0) or 0) / mh if mh > 0 else 0.0
            rows.append(x)
        rows.sort(key=lambda r: (float(r.get("accepted_per_mh", 0.0)), int(r.get("accepted", 0)), int(r.get("best_z", 0))), reverse=True)
        return rows

    def summary(self, limit: int = 10) -> Dict[str, Any]:
        rows = self.rows_list()
        return {
            "version": VERSION,
            "sentinel": SENTINEL,
            "schema": "v31-strategy-rates-1",
            "written_at_utc": utc_stamp_iso(),
            "started_at_utc": self.started_at_utc,
            "imported": dict(self.imported),
            "rows": {r["key"]: r for r in rows},
            "top": rows[:max(1, int(limit))],
        }

    def save(self, force: bool = False) -> None:
        try:
            atomic_json(self.path, self.summary(32))
        except Exception as e:
            log("v31", f"strategy ratebook save failed: {e}")

    def line(self) -> str:
        top = self.rows_list()[:3]
        if not top:
            return "rates=empty"
        return "; ".join(f"{r['key']} acc/MH={r['accepted_per_mh']:.4f} acc={r.get('accepted',0)} best_z={r.get('best_z',0)}" for r in top)


class TailTracker:
    """V31 high-z tail event writer for z30/z32/z33 analysis."""

    def __init__(self, path: str, tail_z: int = 30, tail_z33: int = 33) -> None:
        self.path = path
        self.tail_z = max(1, int(tail_z or 30))
        self.tail_z33 = max(self.tail_z, int(tail_z33 or 33))
        self.counts: Dict[str, int] = {"z30": 0, "z32": 0, "z33": 0, "events": 0}
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        except Exception:
            pass

    def observe_candidate(self, cand: Dict[str, Any], accepted: Optional[bool] = None) -> None:
        z = int(cand.get("zbits", 0) or 0)
        if z < self.tail_z:
            return
        ev = {
            "ts_utc": utc_stamp_iso(),
            "version": VERSION,
            "sentinel": SENTINEL,
            "accepted": accepted,
            "lane": cand.get("lane", "unknown"),
            "strategy": cand.get("strategy"),
            "sector": cand.get("sector"),
            "cfg_name": cand.get("cfg_name"),
            "zbits": z,
            "nonce_submit_hex": cand.get("nonce_submit_hex"),
            "job_id": cand.get("job_id"),
            "job_seq": cand.get("job_seq"),
            "hash": cand.get("display_hash"),
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
            self.counts["events"] = self.counts.get("events", 0) + 1
            if z >= 30:
                self.counts["z30"] = self.counts.get("z30", 0) + 1
            if z >= 32:
                self.counts["z32"] = self.counts.get("z32", 0) + 1
            if z >= self.tail_z33:
                self.counts["z33"] = self.counts.get("z33", 0) + 1
        except Exception as e:
            log("v31", f"tail event write failed: {e}")

    def summary(self) -> Dict[str, Any]:
        return {"path": self.path, "tail_z": self.tail_z, "tail_z33": self.tail_z33, "counts": dict(self.counts)}


class RareTailTimingMonitor:
    """Observer-only accepted-share timing index for pool rare-tail analysis.

    The monitor records when z32+ accepted shares arrive, which arm produced
    them, and the active Stratum job timing context. It writes derived telemetry
    only; proof artifacts, scheduler policy, and frozen wire behavior are not
    changed.
    """

    FIELDNAMES = [
        "schema",
        "written_at_utc",
        "accepted_at_utc",
        "accepted_at_kyiv",
        "kyiv_date",
        "kyiv_hour",
        "utc_hour",
        "zbits",
        "run_name",
        "group",
        "lane",
        "strategy",
        "sector",
        "cfg_name",
        "round_id",
        "worker_id",
        "job_id",
        "job_seq",
        "job_clean",
        "job_received_ms",
        "job_age_ms_at_accept",
        "accepted_total",
        "nonce_submit_hex",
        "hash_prefix",
        "pool_diff",
        "pool_z_approx",
        "pool_response_result",
        "pool_response_error",
        "proof_name",
        "proof_path",
        "scheduler_effect",
        "wire_change_required",
    ]

    TAILS = (32, 33, 34, 35, 36, 37, 38, 39)
    ACCEPTED_RE = re.compile(r"^accepted_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_z(\d+)_nonce0x[0-9a-fA-F]+_job.+\.json$")

    def __init__(self, events_path: str, csv_path: str, dashboard_path: str, min_z: int = 32, proofs_dir: Optional[str] = None) -> None:
        self.events_path = str(events_path)
        self.csv_path = str(csv_path)
        self.dashboard_path = str(dashboard_path)
        self.proofs_dir = str(proofs_dir or "")
        self.min_z = max(1, int(min_z or 32))
        self.started_at_utc = utc_stamp_iso()
        self.rows: List[Dict[str, Any]] = []
        self.seen: set[str] = set()
        self.zone = self._kyiv_zone()
        try:
            os.makedirs(os.path.dirname(self.events_path) or ".", exist_ok=True)
            os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
            os.makedirs(os.path.dirname(self.dashboard_path) or ".", exist_ok=True)
        except Exception:
            pass
        self._load_existing()
        if self.proofs_dir:
            self.backfill_existing_proofs(self.proofs_dir)

    @staticmethod
    def _kyiv_zone() -> timezone:
        if ZoneInfo is not None:
            try:
                return ZoneInfo("Europe/Kyiv")  # type: ignore[return-value]
            except Exception:
                pass
        return timezone.utc

    @staticmethod
    def _parse_utc(ts: Any) -> datetime:
        value = str(ts or "").strip()
        try:
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    @staticmethod
    def _job_received_ms(cand: Dict[str, Any]) -> Optional[int]:
        job = cand.get("job") if isinstance(cand.get("job"), dict) else {}
        for value in (job.get("received_ms"), cand.get("received_ms")):
            try:
                if value is not None:
                    return int(value)
            except Exception:
                pass
        return None

    @staticmethod
    def _group(cand: Dict[str, Any]) -> str:
        try:
            return A99SovereignTriadAccounting.group_name(cand.get("lane"), cand.get("strategy"))
        except Exception:
            lane = str(cand.get("lane", "") or "")
            if lane.startswith("random_mirror:") or lane in ("random_baseline", "randomized_traversal_mirror"):
                return "randomized_traversal_mirror"
            if lane.startswith("janus_bunnyhop_scout:"):
                return "janus_bunnyhop_scout"
            if lane.startswith("janus_bunnyhop_rescout:"):
                return "janus_bunnyhop_rescout"
            return "janus_broad_mixture"

    @staticmethod
    def _row_key(row: Dict[str, Any]) -> str:
        return "|".join(
            str(row.get(k, ""))
            for k in ("accepted_at_utc", "job_id", "job_seq", "nonce_submit_hex", "zbits", "proof_name")
        )

    def _load_existing(self) -> None:
        try:
            if not os.path.exists(self.events_path):
                return
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(row, dict):
                        continue
                    key = self._row_key(row)
                    if key in self.seen:
                        continue
                    self.seen.add(key)
                    self.rows.append(row)
            self.rows.sort(key=lambda r: str(r.get("accepted_at_utc", "")))
        except Exception as e:
            log("rare_tail_time", f"existing event load failed: {e}")

    def _build_row(self, cand: Dict[str, Any], proof_path: Optional[str]) -> Dict[str, Any]:
        accepted_dt = self._parse_utc(cand.get("accepted_at_utc") or utc_stamp_iso())
        local_dt = accepted_dt.astimezone(self.zone)
        job_received_ms = self._job_received_ms(cand)
        job_age_ms = None
        if job_received_ms is not None:
            try:
                job_age_ms = int(accepted_dt.timestamp() * 1000) - int(job_received_ms)
            except Exception:
                job_age_ms = None
        job = cand.get("job") if isinstance(cand.get("job"), dict) else {}
        pool_response = cand.get("pool_response") if isinstance(cand.get("pool_response"), dict) else {}
        proof_path_s = str(proof_path or "")
        return {
            "schema": "a9-rare-tail-timing-1",
            "written_at_utc": utc_stamp_iso(),
            "accepted_at_utc": accepted_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "accepted_at_kyiv": local_dt.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "kyiv_date": local_dt.strftime("%Y-%m-%d"),
            "kyiv_hour": int(local_dt.hour),
            "utc_hour": int(accepted_dt.hour),
            "zbits": int(cand.get("zbits", 0) or 0),
            "run_name": Path(os.getcwd()).name,
            "group": self._group(cand),
            "lane": cand.get("lane", "unknown"),
            "strategy": cand.get("strategy"),
            "sector": cand.get("sector"),
            "cfg_name": cand.get("cfg_name"),
            "round_id": cand.get("round_id"),
            "worker_id": cand.get("worker_id"),
            "job_id": cand.get("job_id"),
            "job_seq": cand.get("job_seq"),
            "job_clean": job.get("clean", cand.get("clean")),
            "job_received_ms": job_received_ms,
            "job_age_ms_at_accept": job_age_ms,
            "accepted_total": cand.get("accepted_total"),
            "nonce_submit_hex": cand.get("nonce_submit_hex"),
            "hash_prefix": mask_hex(cand.get("display_hash", ""), 32),
            "pool_diff": cand.get("pool_diff"),
            "pool_z_approx": cand.get("pool_z_approx"),
            "pool_response_result": pool_response.get("result"),
            "pool_response_error": pool_response.get("error"),
            "proof_name": os.path.basename(proof_path_s),
            "proof_path": proof_path_s,
            "scheduler_effect": "observe_only",
            "wire_change_required": False,
        }

    def observe_accepted(self, cand: Dict[str, Any], proof_path: Optional[str] = None) -> None:
        try:
            z = int(cand.get("zbits", 0) or 0)
            if z < self.min_z:
                return
            row = self._build_row(cand, proof_path)
            key = self._row_key(row)
            if key in self.seen:
                return
            self.seen.add(key)
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            self.rows.append(row)
            self.rows.sort(key=lambda r: str(r.get("accepted_at_utc", "")))
            self.write_csv()
            self.write_summary()
            log("rare_tail_time", f"z{z} {row.get('group')} kyiv={row.get('accepted_at_kyiv')} job={row.get('job_id')} age_ms={row.get('job_age_ms_at_accept')}")
        except Exception as e:
            log("rare_tail_time", f"observe accepted failed: {e}")

    def _proof_candidate(self, proof_path: Path) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(proof_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            cand = data.get("raw_candidate") if isinstance(data.get("raw_candidate"), dict) else {}
            if not cand:
                cand = {
                    "zbits": data.get("hash", {}).get("zbits"),
                    "pool_diff": data.get("pool", {}).get("pool_diff"),
                    "pool_z_approx": data.get("pool", {}).get("pool_z_approx"),
                    "pool_response": data.get("pool", {}).get("pool_response"),
                }
                miner = data.get("miner") if isinstance(data.get("miner"), dict) else {}
                job = data.get("job") if isinstance(data.get("job"), dict) else {}
                nonce = data.get("nonce") if isinstance(data.get("nonce"), dict) else {}
                cand.update({
                    "lane": miner.get("lane"),
                    "strategy": miner.get("strategy"),
                    "sector": miner.get("sector"),
                    "worker_id": miner.get("worker_id"),
                    "round_id": miner.get("round_id"),
                    "cfg_name": miner.get("cfg_name"),
                    "job": job,
                    "job_id": job.get("job_id"),
                    "job_seq": job.get("seq"),
                    "nonce_submit_hex": nonce.get("submit_be_hex"),
                    "display_hash": data.get("hash", {}).get("double_sha256_display_hex"),
                })
            if not cand.get("accepted_at_utc"):
                cand["accepted_at_utc"] = data.get("created_at_utc") or utc_stamp_iso()
            if not cand.get("zbits"):
                match = self.ACCEPTED_RE.match(proof_path.name)
                if match:
                    cand["zbits"] = int(match.group(1))
            return cand
        except Exception as e:
            log("rare_tail_time", f"proof backfill read failed {proof_path.name}: {e}")
            return None

    def backfill_existing_proofs(self, proofs_dir: str) -> None:
        added = 0
        try:
            root = Path(proofs_dir)
            if not root.exists():
                return
            candidates: List[Path] = []
            for path in root.rglob("accepted_20*_z*_nonce0x*.json"):
                if any(part.lower() == "raw_accepted" for part in path.parts):
                    continue
                match = self.ACCEPTED_RE.match(path.name)
                if match and int(match.group(1)) >= self.min_z:
                    candidates.append(path)
            for path in sorted(candidates, key=lambda p: p.name):
                cand = self._proof_candidate(path)
                if not cand:
                    continue
                before = len(self.rows)
                self.observe_accepted(cand, proof_path=str(path))
                if len(self.rows) > before:
                    added += 1
            if added:
                log("rare_tail_time", f"backfilled {added} existing z{self.min_z}+ accepted proofs from {proofs_dir}")
        except Exception as e:
            log("rare_tail_time", f"proof backfill failed: {e}")

    def _hour_summary(self) -> Dict[str, Dict[str, Any]]:
        hours: Dict[str, Dict[str, Any]] = {}
        for row in self.rows:
            hour = f"{int(row.get('kyiv_hour', 0) or 0):02d}"
            z = int(row.get("zbits", 0) or 0)
            item = hours.setdefault(hour, {"count": 0, "best_z": 0, "by_group": {}})
            item["count"] = int(item.get("count", 0)) + 1
            item["best_z"] = max(int(item.get("best_z", 0) or 0), z)
            for tail in self.TAILS:
                key = f"z{tail}_plus"
                item[key] = int(item.get(key, 0)) + (1 if z >= tail else 0)
            group = str(row.get("group", "unknown"))
            by_group = item.setdefault("by_group", {})
            by_group[group] = int(by_group.get(group, 0)) + 1
        return dict(sorted(hours.items()))

    def _group_summary(self) -> Dict[str, Dict[str, Any]]:
        groups: Dict[str, Dict[str, Any]] = {}
        for row in self.rows:
            group = str(row.get("group", "unknown"))
            z = int(row.get("zbits", 0) or 0)
            item = groups.setdefault(group, {"count": 0, "best_z": 0})
            item["count"] = int(item.get("count", 0)) + 1
            item["best_z"] = max(int(item.get("best_z", 0) or 0), z)
            for tail in self.TAILS:
                key = f"z{tail}_plus"
                item[key] = int(item.get(key, 0)) + (1 if z >= tail else 0)
        return dict(sorted(groups.items()))

    def write_csv(self) -> None:
        try:
            tmp = self.csv_path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES, extrasaction="ignore")
                writer.writeheader()
                for row in self.rows:
                    writer.writerow(row)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            os.replace(tmp, self.csv_path)
        except Exception as e:
            log("rare_tail_time", f"csv write failed: {e}")

    def summary(self) -> Dict[str, Any]:
        best_z = max((int(r.get("zbits", 0) or 0) for r in self.rows), default=0)
        return {
            "schema": "a9-rare-tail-timing-summary-1",
            "version": VERSION,
            "sentinel": SENTINEL,
            "written_at_utc": utc_stamp_iso(),
            "started_at_utc": self.started_at_utc,
            "observer_only": True,
            "scheduler_effect": "none",
            "wire_change_required": False,
            "objective": "Accepted rare-tail timing corpus for pool hour/window analysis; future scheduler material only after enough evidence.",
            "min_z": self.min_z,
            "events_path": self.events_path,
            "csv_path": self.csv_path,
            "dashboard_path": self.dashboard_path,
            "total_events": len(self.rows),
            "best_z": best_z,
            "first_accepted_at_utc": self.rows[0].get("accepted_at_utc") if self.rows else "",
            "last_accepted_at_utc": self.rows[-1].get("accepted_at_utc") if self.rows else "",
            "by_kyiv_hour": self._hour_summary(),
            "by_group": self._group_summary(),
            "recent": self.rows[-16:],
            "pool_timing_note": "job_age_ms_at_accept is derived from Stratum notify received_ms and accepted_at_utc; use as correlation evidence, not submit policy.",
        }

    def write_summary(self) -> None:
        try:
            atomic_json(self.dashboard_path, self.summary())
        except Exception as e:
            log("rare_tail_time", f"summary write failed: {e}")


class JanusGlyphObserver:
    """Observer-only scanner for readable strings in pre-hash Stratum inputs.

    This is a data archaeology layer. It inspects coinbase/job bytes before the
    80-byte header is hashed, links matches to accepted rare-tail telemetry, and
    never changes header construction, submit policy, extranonce, target, or
    scheduler decisions.
    """

    DEFAULT_KEYWORDS = (
        "satoshi",
        "nakamoto",
        "bitcoin",
        "btc",
        "janus",
        "jan",
        "january",
        "tobi",
        "sperman",
        "rose",
        "wine",
        "hawkar",
        "genesis",
        "times",
        "chancellor",
        "bank",
        "banks",
        "bailout",
        "second bailout",
        "federal",
        "reserve",
        "fed",
        "debt",
        "money",
        "crisis",
        "liberty",
        "freedom",
        "anon",
        "anonymous",
        "god",
        "block",
        "chain",
        "hash",
        "nonce",
        "zero",
        "one",
        "door",
        "gate",
        "key",
        "ready",
        "player",
        "tesseract",
        "plea",
        "aelp",
        "leap",
        "peal",
        "pale",
        "pela",
    )
    GENESIS_HEADLINE = "the times 03/jan/2009 chancellor on brink of second bailout for banks"
    GENESIS_WORDS = ("the times", "03/jan/2009", "chancellor", "second bailout", "banks")
    OPERATOR_SIGNAL_WORDS = ("janus", "jan", "tobi", "sperman", "rose", "wine", "hawkar")
    PLEA_MIRROR_WORDS = ("plea", "aelp", "leap", "peal", "pale", "pela")
    GP_D_MIRROR_TOKENS = ("*gp:d", "d:pg*")
    OPEN_WORD_SOURCE_NAMES = ("coinb1", "coinb2", "coinbase_full")
    WORD_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9_/-]{2,47}(?![A-Za-z0-9])")
    SYMBOL_RE = re.compile(r"[!-\/:-@\[-`{-~]{2,}")
    BASE64_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{8,}={0,2}(?![A-Za-z0-9+/])")
    DATE_RE = re.compile(
        r"\b(?:\d{1,2}[/.-](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2})[/.-]\d{2,4}|(?:19|20)\d{2})\b",
        re.IGNORECASE,
    )
    ENCODING_REGEX_CHARS_RE = re.compile(r"[\?\(\)\[\]\^\-\$\>\<\\\/\|]")
    ASCII85_PAD_CHAR = "u"
    BASELINE_WINDOW_LIMIT = 200
    BASELINE_MIN_WINDOWS = 8
    BASELINE_WINDOW_SIZES = (4, 5, 7, 8, 11, 16)
    CSV_FIELDS = [
        "schema",
        "event_type",
        "written_at_utc",
        "observed_at_utc",
        "source_context",
        "source_name",
        "variant",
        "offset",
        "text",
        "normalized_glyph_text",
        "independent_glyph_key",
        "open_words",
        "unknown_words",
        "symbol_glyphs",
        "weird_glyphs",
        "keywords",
        "dates",
        "categories",
        "mirror_families",
        "confidence",
        "encoding_probe",
        "glyph_type",
        "encoding_confidence",
        "looks_like",
        "decode_status",
        "decode_codec",
        "decode_padded",
        "decoded_hex_preview",
        "regex_shape_score",
        "mirror_shape_score",
        "raw_entropy",
        "raw_entropy_norm",
        "decoded_entropy",
        "decoded_entropy_norm",
        "decoded_len",
        "short_sample_warning",
        "baseline_entropy_mean",
        "baseline_entropy_std",
        "baseline_entropy_z_score",
        "baseline_status",
        "match_priority",
        "score",
        "match_reasons",
        "meaning",
        "exact_genesis_headline",
        "run_name",
        "job_id",
        "job_seq",
        "ntime",
        "nbits",
        "clean",
        "accepted",
        "zbits",
        "group",
        "lane",
        "strategy",
        "linear_context",
        "sector",
        "round_id",
        "worker_id",
        "proof_name",
        "proof_path",
        "registry_path",
        "source_sha256_16",
        "coinbase_dsha",
        "raw_layer",
        "inferred_layer",
        "myth_layer",
        "scheduler_effect",
        "wire_change_required",
    ]
    ACCEPTED_RE = re.compile(r"^accepted_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_z(\d+)_nonce0x[0-9a-fA-F]+_job.+\.json$")

    def __init__(
        self,
        events_path: str,
        csv_path: str,
        summary_path: str,
        min_len: int = 4,
        accepted_link_min_z: int = 32,
        keywords: Optional[Iterable[str]] = None,
        proofs_dir: Optional[str] = None,
    ) -> None:
        self.events_path = str(events_path)
        self.csv_path = str(csv_path)
        self.summary_path = str(summary_path)
        self.min_len = max(3, int(min_len or 4))
        self.accepted_link_min_z = max(1, int(accepted_link_min_z or 32))
        self.keywords = tuple(
            sorted({str(k).strip().lower() for k in (keywords or self.DEFAULT_KEYWORDS) if str(k).strip()})
        )
        self.proofs_dir = str(proofs_dir or "")
        self.registry_dir = str(Path(self.proofs_dir) / "registry" / "glyph") if self.proofs_dir else ""
        self.started_at_utc = utc_stamp_iso()
        self.rows: List[Dict[str, Any]] = []
        self.seen: set[str] = set()
        self.seen_jobs: set[str] = set()
        try:
            os.makedirs(os.path.dirname(self.events_path) or ".", exist_ok=True)
            os.makedirs(os.path.dirname(self.csv_path) or ".", exist_ok=True)
            os.makedirs(os.path.dirname(self.summary_path) or ".", exist_ok=True)
        except Exception:
            pass
        self._load_existing()
        if self.proofs_dir:
            self.backfill_existing_proofs(self.proofs_dir)

    @staticmethod
    def _bytes_from_hex(value: Any) -> bytes:
        text = str(value or "").strip()
        if not text:
            return b""
        try:
            return bytes.fromhex(text)
        except Exception:
            return b""

    @staticmethod
    def _word_reverse(data: bytes) -> bytes:
        out = bytearray()
        for i in range(0, len(data), 4):
            chunk = data[i : i + 4]
            out.extend(chunk[::-1] if len(chunk) == 4 else chunk)
        return bytes(out)

    @staticmethod
    def _ascii_spans(data: bytes, min_len: int) -> List[Dict[str, Any]]:
        spans: List[Dict[str, Any]] = []
        cur = bytearray()
        start = 0
        for idx, b in enumerate(data):
            if 32 <= int(b) <= 126:
                if not cur:
                    start = idx
                cur.append(b)
            else:
                if len(cur) >= min_len:
                    spans.append({"offset": start, "text": cur.decode("ascii", "ignore")})
                cur.clear()
        if len(cur) >= min_len:
            spans.append({"offset": start, "text": cur.decode("ascii", "ignore")})
        return spans

    def _hex_ascii_spans(self, text: str, base_offset: int) -> List[Dict[str, Any]]:
        cleaned = re.sub(r"[^0-9a-fA-F]", "", str(text or ""))
        if len(cleaned) < self.min_len * 2 or (len(cleaned) % 2):
            return []
        try:
            decoded = bytes.fromhex(cleaned)
        except Exception:
            return []
        out = []
        for span in self._ascii_spans(decoded, self.min_len):
            out.append({"offset": base_offset, "text": span.get("text", ""), "variant": "hex_ascii"})
        return out

    def _base64_ascii_spans(self, text: str, base_offset: int) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for match in self.BASE64_TOKEN_RE.finditer(str(text or "")):
            base64_candidate = match.group(0)
            if len(base64_candidate) % 4:
                continue
            try:
                decoded = base64.b64decode(base64_candidate.encode("ascii"), validate=True)
            except Exception:
                continue
            if not decoded:
                continue
            printable = sum(1 for b in decoded if 32 <= int(b) <= 126 or int(b) in (9, 10, 13))
            if printable / max(1, len(decoded)) < 0.75:
                continue
            for span in self._ascii_spans(decoded, self.min_len):
                out.append({
                    "offset": base_offset + int(match.start()),
                    "text": span.get("text", ""),
                    "variant": "base64_ascii",
                })
        return out

    def _extract_strings(self, data: bytes) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        variants = [
            ("raw", data),
            ("reversed", data[::-1]),
            ("word_reversed", self._word_reverse(data)),
        ]
        for variant, payload in variants:
            for span in self._ascii_spans(payload, self.min_len):
                text = str(span.get("text", ""))
                items.append({"variant": variant, "offset": span.get("offset", 0), "text": text})
                for decoded in self._hex_ascii_spans(text, int(span.get("offset", 0) or 0)):
                    items.append(decoded)
                for decoded in self._base64_ascii_spans(text, int(span.get("offset", 0) or 0)):
                    items.append(decoded)
        return items

    @staticmethod
    def _normalized_text(text: str) -> str:
        low = str(text or "").lower()
        low = re.sub(r"\s+", " ", low)
        return low.strip()

    @staticmethod
    def _normalized_glyph_key_text(text: str) -> str:
        clean = re.sub(r"\s+", " ", str(text or "")).strip().lower()
        return clean[:128]

    @staticmethod
    def _has_keyword(low: str, keyword: str) -> bool:
        key = str(keyword or "").lower().strip()
        if not key:
            return False
        if len(key) <= 3:
            return bool(re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", low))
        return key in low

    @staticmethod
    def _repeat_tags(text: str) -> List[str]:
        compact = re.sub(r"\s+", "", str(text or ""))
        tags: List[str] = []
        if len(compact) < 8:
            return tags
        for size in range(2, 9):
            for idx in range(0, max(0, len(compact) - size * 3 + 1)):
                chunk = compact[idx : idx + size]
                if len(set(chunk)) <= 1:
                    continue
                repeats = 1
                pos = idx + size
                while compact[pos : pos + size] == chunk:
                    repeats += 1
                    pos += size
                if repeats >= 3:
                    tags.append(f"repeat_{size}x{repeats}:{chunk[:12]}")
                    return tags
        return tags

    def _open_words(self, text: str) -> List[str]:
        words: List[str] = []
        seen: set[str] = set()
        for match in self.WORD_RE.finditer(str(text or "")):
            raw = match.group(0).strip("/_-").lower()
            if len(raw) < self.min_len:
                continue
            alpha = sum(1 for ch in raw if "a" <= ch <= "z")
            if alpha < max(3, int(len(raw) * 0.55)):
                continue
            if raw not in seen:
                seen.add(raw)
                words.append(raw)
        return words

    def _symbol_glyphs(self, text: str) -> List[str]:
        glyphs: List[str] = []
        seen: set[str] = set()
        for match in self.SYMBOL_RE.finditer(str(text or "")):
            raw = match.group(0)
            if len(raw) < 2:
                continue
            if raw not in seen:
                seen.add(raw)
                glyphs.append(raw[:64])
        return glyphs

    def _weird_glyphs(self, text: str) -> List[str]:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(clean) < self.min_len:
            return []
        total = max(1, len(clean))
        alpha = sum(1 for ch in clean if ch.isalpha())
        digit = sum(1 for ch in clean if ch.isdigit())
        symbol = sum(1 for ch in clean if (not ch.isalnum()) and (not ch.isspace()))
        if symbol == 0 and digit == 0:
            return []
        alpha_ratio = alpha / total
        looks_weird = symbol >= 2 or (digit >= 1 and alpha >= 2) or (0 < alpha_ratio < 0.55 and (symbol + digit) >= 1)
        return [clean[:96]] if looks_weird else []

    @staticmethod
    def _shannon_entropy_bytes(data: bytes) -> float:
        """Shannon entropy in bits for short byte strings; observer-only metric."""
        if not data:
            return 0.0
        counts = Counter(data)
        n = float(len(data))
        entropy = 0.0
        for count in counts.values():
            p = float(count) / n
            if p > 0:
                entropy -= p * math.log2(p)
        return round(entropy, 4)

    @classmethod
    def _normalized_entropy_bytes(cls, data: bytes) -> float:
        if not data:
            return 0.0
        max_entropy = math.log2(min(256, len(data)))
        if max_entropy <= 0:
            return 0.0
        return round(cls._shannon_entropy_bytes(data) / max_entropy, 4)

    @staticmethod
    def _char_class_signature(text: str) -> Dict[str, Any]:
        classes = {"lower": 0, "upper": 0, "digit": 0, "symbol": 0, "space": 0, "other": 0}
        for ch in str(text or ""):
            if ch.islower():
                classes["lower"] += 1
            elif ch.isupper():
                classes["upper"] += 1
            elif ch.isdigit():
                classes["digit"] += 1
            elif ch.isspace():
                classes["space"] += 1
            elif 33 <= ord(ch) <= 126:
                classes["symbol"] += 1
            else:
                classes["other"] += 1
        total = max(1, len(str(text or "")))
        return {
            "counts": classes,
            "ratios": {k: round(v / total, 3) for k, v in classes.items()},
        }

    @staticmethod
    def _calculate_mirror_score(text: str) -> float:
        """Visual mirror score with common paired ASCII glyphs."""
        s = str(text or "")
        if not s:
            return 0.0
        mirror_map = {
            "/": "\\", "\\": "/",
            "[": "]", "]": "[",
            "(": ")", ")": "(",
            "<": ">", ">": "<",
            "{": "}", "}": "{",
        }
        transformed = "".join(mirror_map.get(ch, ch) for ch in s[::-1])
        matches = sum(1 for a, b in zip(s, transformed) if a == b)
        return round(matches / max(1, len(s)), 4)

    @classmethod
    def _calculate_regex_score(cls, text: str) -> float:
        s = str(text or "")
        if not s:
            return 0.0
        return round(len(cls.ENCODING_REGEX_CHARS_RE.findall(s)) / max(1, len(s)), 4)

    @classmethod
    def _try_ascii85(cls, text: str) -> Dict[str, Any]:
        """Try RFC1924 Base85 then Adobe Ascii85. Short fragments are padded with 'u'."""
        clean = str(text or "").replace(" ", "")
        if not clean:
            return {"status": "failed", "codec": "", "hex": None, "padded": False, "decoded_len": 0}
        try:
            clean.encode("ascii")
        except Exception:
            return {"status": "failed", "codec": "", "hex": None, "padded": False, "decoded_len": 0}
        orig_len = len(clean)
        padded_clean = clean
        if orig_len % 5 != 0:
            padded_clean += cls.ASCII85_PAD_CHAR * (5 - (orig_len % 5))
        for codec, decoder in (("base85", base64.b85decode), ("ascii85", base64.a85decode)):
            try:
                decoded = decoder(padded_clean.encode("ascii"))
                return {
                    "status": "success",
                    "codec": codec,
                    "hex": decoded.hex(),
                    "padded": len(padded_clean) > orig_len,
                    "decoded_len": len(decoded),
                }
            except Exception:
                continue
        return {"status": "failed", "codec": "", "hex": None, "padded": False, "decoded_len": 0}

    @classmethod
    def _entropy_profile(cls, text: str, decoded_hex: Optional[str] = None) -> Dict[str, Any]:
        raw = str(text or "").encode("utf-8", "ignore")
        profile: Dict[str, Any] = {
            "raw_entropy": cls._shannon_entropy_bytes(raw),
            "raw_entropy_norm": cls._normalized_entropy_bytes(raw),
            "char_classes": cls._char_class_signature(str(text or "")),
            "length": len(str(text or "")),
            "short_sample_warning": len(str(text or "")) < 8,
            "decoded_entropy": None,
            "decoded_entropy_norm": None,
            "decoded_len": 0,
        }
        if decoded_hex:
            try:
                decoded = bytes.fromhex(str(decoded_hex))
                profile["decoded_entropy"] = cls._shannon_entropy_bytes(decoded)
                profile["decoded_entropy_norm"] = cls._normalized_entropy_bytes(decoded)
                profile["decoded_len"] = len(decoded)
            except Exception:
                pass
        return profile

    @classmethod
    def _variant_payload(cls, payload: bytes, variant: str) -> bytes:
        if variant == "reversed":
            return payload[::-1]
        if variant == "word_reversed":
            return cls._word_reverse(payload)
        return payload

    @classmethod
    def _baseline_entropy_comparison(
        cls,
        payload: bytes,
        variant: str,
        text: str,
    ) -> Dict[str, Any]:
        """Compare glyph entropy against same-source sliding-window entropy."""
        glyph_len = len(str(text or "").encode("utf-8", "ignore"))
        if glyph_len <= 0:
            return {"mean": None, "std": None, "z_score": None, "window_count": 0, "status": "insufficient_sample"}
        source = cls._variant_payload(payload or b"", variant)
        if len(source) < glyph_len or glyph_len < 2:
            return {"mean": None, "std": None, "z_score": None, "window_count": 0, "status": "insufficient_sample"}
        max_start = len(source) - glyph_len
        total_windows = max_start + 1
        if total_windows <= 0:
            return {"mean": None, "std": None, "z_score": None, "window_count": 0, "status": "insufficient_sample"}
        step = max(1, total_windows // cls.BASELINE_WINDOW_LIMIT)
        values: List[float] = []
        for pos in range(0, total_windows, step):
            values.append(cls._shannon_entropy_bytes(source[pos : pos + glyph_len]))
            if len(values) >= cls.BASELINE_WINDOW_LIMIT:
                break
        if len(values) < cls.BASELINE_MIN_WINDOWS:
            return {
                "mean": round(sum(values) / max(1, len(values)), 4) if values else None,
                "std": None,
                "z_score": None,
                "window_count": len(values),
                "status": "insufficient_sample",
            }
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / max(1, len(values))
        std = math.sqrt(variance)
        glyph_entropy = cls._shannon_entropy_bytes(str(text or "").encode("utf-8", "ignore"))
        if std <= 1e-9:
            z_score = 0.0
        else:
            z_score = (glyph_entropy - mean) / std
        if z_score <= -2.5:
            status = "anomaly_low_entropy"
        elif z_score >= 2.5:
            status = "anomaly_high_entropy"
        else:
            status = "baseline_normal"
        return {
            "mean": round(mean, 4),
            "std": round(std, 4),
            "z_score": round(z_score, 4),
            "window_count": len(values),
            "status": status,
        }

    @staticmethod
    def _classify_encoding_confidence(
        a85_res: Dict[str, Any],
        entropy: Dict[str, Any],
        regex_score: float,
        mirror_score: float,
        baseline: Dict[str, Any],
    ) -> str:
        score = 0
        if a85_res.get("status") == "success":
            score += 2
        if mirror_score >= 0.75:
            score += 2
        elif mirror_score >= 0.40:
            score += 1
        if regex_score >= 0.50:
            score += 1
        if float(entropy.get("raw_entropy_norm") or 0.0) >= 0.75:
            score += 1
        if baseline.get("status") in ("anomaly_low_entropy", "anomaly_high_entropy"):
            score += 1
        if entropy.get("short_sample_warning"):
            score -= 1
        if score >= 4:
            return "strong_candidate"
        if score >= 2:
            return "candidate"
        return "noise"

    @staticmethod
    def _classify_glyph_type(
        text: str,
        a85_res: Dict[str, Any],
        entropy: Dict[str, Any],
        regex_score: float,
        mirror_score: float,
        baseline: Dict[str, Any],
    ) -> str:
        low = str(text or "").lower()
        if "/mined by nerdminer/" in low or "ckpool" in low:
            return "POOL_BOILERPLATE"
        if mirror_score >= 0.75 or baseline.get("status") == "anomaly_low_entropy" and mirror_score >= 0.40:
            return "MIRROR_GLYPH"
        if regex_score >= 0.50:
            return "REGEX_LIKE_GLYPH"
        if a85_res.get("status") == "success" and float(entropy.get("decoded_entropy_norm") or 0.0) >= 0.60:
            return "ENCODED_FRAGMENT"
        if float(entropy.get("raw_entropy_norm") or 0.0) < 0.45:
            return "ASCII_MARKER"
        return "NOISE"

    def _encoding_probe(self, text: str, source_name: str, variant: str, payload: bytes) -> Dict[str, Any]:
        a85_res = self._try_ascii85(text)
        regex_score = self._calculate_regex_score(text)
        mirror_score = self._calculate_mirror_score(text)
        entropy = self._entropy_profile(text, a85_res.get("hex"))
        baseline = self._baseline_entropy_comparison(payload, variant, text)
        looks_like: List[str] = []
        if a85_res.get("status") == "success":
            looks_like.append("ascii85")
        if regex_score > 0.40:
            looks_like.append("regex_shape")
        if mirror_score > 0.40:
            looks_like.append("mirror_shape")
        if "reversed" in str(variant):
            looks_like.append("word_reversed" if variant == "word_reversed" else "reversed")
        if baseline.get("status") in ("anomaly_low_entropy", "anomaly_high_entropy"):
            looks_like.append(str(baseline.get("status")))
        confidence = self._classify_encoding_confidence(a85_res, entropy, regex_score, mirror_score, baseline)
        glyph_type = self._classify_glyph_type(text, a85_res, entropy, regex_score, mirror_score, baseline)
        return {
            "encoding_probe": True,
            "glyph_type": glyph_type,
            "encoding_confidence": confidence,
            "looks_like": sorted(set(looks_like)),
            "decode_status": a85_res.get("status", "failed"),
            "decode_codec": a85_res.get("codec", ""),
            "decode_padded": bool(a85_res.get("padded")),
            "decoded_hex_preview": str(a85_res.get("hex") or "")[:96],
            "regex_shape_score": regex_score,
            "mirror_shape_score": mirror_score,
            "raw_entropy": entropy.get("raw_entropy"),
            "raw_entropy_norm": entropy.get("raw_entropy_norm"),
            "decoded_entropy": entropy.get("decoded_entropy"),
            "decoded_entropy_norm": entropy.get("decoded_entropy_norm"),
            "decoded_len": entropy.get("decoded_len"),
            "short_sample_warning": bool(entropy.get("short_sample_warning")),
            "char_classes": entropy.get("char_classes"),
            "baseline_entropy_mean": baseline.get("mean"),
            "baseline_entropy_std": baseline.get("std"),
            "baseline_entropy_z_score": baseline.get("z_score"),
            "baseline_window_count": baseline.get("window_count"),
            "baseline_status": baseline.get("status"),
        }

    def _classify(self, text: str) -> Tuple[List[str], List[str], List[str], List[str], List[str], List[str], List[str], str]:
        low = str(text or "").lower()
        normalized = self._normalized_text(text)
        open_words = self._open_words(text)
        symbol_glyphs = self._symbol_glyphs(text)
        weird_glyphs = self._weird_glyphs(text)
        keywords = [k for k in self.keywords if self._has_keyword(low, k)]
        keyword_set = set(keywords)
        unknown_words = [w for w in open_words if w not in keyword_set]
        dates = [m.group(0) for m in self.DATE_RE.finditer(str(text or ""))]
        categories: List[str] = []
        if open_words:
            categories.append("open_vocabulary_words")
        if unknown_words:
            categories.append("unknown_word_candidate")
        if len(open_words) >= 2:
            categories.append("open_vocabulary_phrase")
        if symbol_glyphs:
            categories.append("symbol_glyph_candidate")
        if weird_glyphs:
            categories.append("weird_glyph_candidate")
        exact_genesis = self.GENESIS_HEADLINE in normalized
        genesis_word_hits = [w for w in self.GENESIS_WORDS if w in normalized]
        if exact_genesis:
            categories.append("genesis_headline_exact")
        elif len(genesis_word_hits) >= 3:
            categories.append("genesis_headline_partial")
        if any(k in keywords for k in ("satoshi", "nakamoto", "genesis", "times", "chancellor", "bailout", "bank", "banks")):
            categories.append("genesis_or_satoshi_echo")
        if any(k in keywords for k in ("janus", "jan", "january", "door", "gate", "key")):
            categories.append("janus_gate_language")
        if any(k in keywords for k in self.OPERATOR_SIGNAL_WORDS):
            categories.append("janus_operator_signal")
        if any(k in keywords for k in self.PLEA_MIRROR_WORDS):
            categories.append("plea_mirror_family")
        compact = re.sub(r"\s+", "", str(text or "").lower())
        if compact in self.GP_D_MIRROR_TOKENS:
            categories.append("gp_d_mirror_family")
        if any(k in keywords for k in ("block", "chain", "hash", "nonce", "zero", "one")):
            categories.append("pow_language")
        if any(k in keywords for k in ("ready", "player", "tesseract")):
            categories.append("quest_language")
        if any(k in keywords for k in ("federal", "reserve", "fed", "debt", "money", "crisis", "liberty", "freedom")):
            categories.append("monetary_or_crisis_language")
        if any(k in keywords for k in ("anon", "anonymous", "god")):
            categories.append("identity_or_myth_language")
        if dates:
            categories.append("date_or_timestamp")
        categories.extend(self._repeat_tags(text))
        if keywords or dates:
            confidence = "raw_observed"
        elif open_words:
            confidence = "open_vocabulary"
        elif symbol_glyphs or weird_glyphs:
            confidence = "glyph_shape"
        else:
            confidence = "rare_tail_context"
        return keywords, open_words, unknown_words, symbol_glyphs, weird_glyphs, dates, sorted(set(categories)), confidence

    def _score_hit(
        self,
        text: str,
        keywords: List[str],
        open_words: List[str],
        unknown_words: List[str],
        symbol_glyphs: List[str],
        weird_glyphs: List[str],
        dates: List[str],
        categories: List[str],
        accepted: bool,
        zbits: int,
        source_name: str,
        variant: str,
        linear_context: bool = False,
    ) -> Dict[str, Any]:
        score = 0
        reasons: List[str] = []
        cats = set(categories)
        exact = "genesis_headline_exact" in cats
        partial = "genesis_headline_partial" in cats

        if exact:
            score += 140
            reasons.append("exact_genesis_headline")
        elif partial:
            score += 95
            reasons.append("partial_genesis_headline")
        if "genesis_or_satoshi_echo" in cats:
            score += 42
            reasons.append("genesis_or_satoshi_keyword")
        if "janus_gate_language" in cats:
            score += 28
            reasons.append("janus_gate_keyword")
        if "janus_operator_signal" in cats:
            score += 34
            reasons.append("janus_operator_signal")
        if "plea_mirror_family" in cats:
            score += 26
            reasons.append("plea_mirror_family")
        if "gp_d_mirror_family" in cats:
            score += 18
            reasons.append("gp_d_mirror_family")
        if "date_or_timestamp" in cats:
            score += 22
            reasons.append("date_or_timestamp")
        if "monetary_or_crisis_language" in cats:
            score += 18
            reasons.append("monetary_or_crisis_language")
        if "pow_language" in cats:
            score += 12
            reasons.append("pow_language")
        if "quest_language" in cats:
            score += 12
            reasons.append("quest_language")
        if any(str(c).startswith("repeat_") for c in cats):
            score += 8
            reasons.append("repeat_pattern")
        if "encoding_strong_candidate" in cats:
            score += 22
            reasons.append("encoding_strong_candidate")
        elif "encoding_candidate" in cats:
            score += 10
            reasons.append("encoding_candidate")
        if "encoding_encoded_fragment" in cats:
            score += 14
            reasons.append("encoding_encoded_fragment")
        if "encoding_mirror_glyph" in cats:
            score += 18
            reasons.append("encoding_mirror_glyph")
        if "encoding_regex_like_glyph" in cats:
            score += 10
            reasons.append("encoding_regex_like_glyph")
        if "baseline_anomaly_low_entropy" in cats:
            score += 14
            reasons.append("baseline_anomaly_low_entropy")
        if "baseline_anomaly_high_entropy" in cats:
            score += 10
            reasons.append("baseline_anomaly_high_entropy")
        if open_words:
            score += min(18, len(open_words) * 3)
            reasons.append("open_vocabulary_words")
        if unknown_words:
            score += min(12, len(unknown_words) * 3)
            reasons.append("unknown_word_candidate")
        if symbol_glyphs:
            score += min(10, len(symbol_glyphs) * 3)
            reasons.append("symbol_glyph_candidate")
        if weird_glyphs:
            score += min(14, len(weird_glyphs) * 6)
            reasons.append("weird_glyph_candidate")
        if linear_context:
            score += 10
            reasons.append("linear_context")
        if keywords:
            score += min(20, len(keywords) * 4)
            reasons.append("keyword_count")
        if accepted:
            score += 8
            reasons.append("accepted_share_context")
            if zbits >= self.accepted_link_min_z:
                score += 22 + max(0, zbits - self.accepted_link_min_z) * 4
                reasons.append(f"rare_tail_z{zbits}")
            if zbits >= 35:
                score += 20
                reasons.append("z35_plus_context")
            if zbits >= 36:
                score += 35
                reasons.append("z36_plus_context")
        if source_name in ("coinb1", "coinb2", "coinbase_full"):
            score += 10
            reasons.append("coinbase_source")
        if variant != "raw":
            score += 6
            reasons.append(f"{variant}_view")

        if exact:
            priority = "GENESIS_ECHO"
            meaning = "exact Genesis headline present in pre-hash input"
            myth = "Janus gate / Bitcoin genesis threshold"
        elif partial:
            priority = "GENESIS_ECHO"
            meaning = "partial Genesis headline vocabulary present in pre-hash input"
            myth = "possible Genesis echo, not proof of intent"
        elif score >= 80:
            priority = "HIGH_GLYPH"
            meaning = "strong readable pre-hash glyph with multiple matching signals"
            myth = "Avengers clue candidate"
        elif "encoding_strong_candidate" in cats:
            priority = "ENCODING_PROBE"
            meaning = "strong structured encoding/glyph candidate measured by entropy, mirror, regex, or decoder probes"
            myth = "tunnel inscription candidate, still observer-only"
        elif accepted and zbits >= self.accepted_link_min_z:
            priority = "RARE_TAIL_LINK"
            meaning = "readable pre-hash string linked to accepted rare-tail telemetry"
            myth = "tunnel writing near rare-tail boundary"
        elif (keywords or dates) and score >= 35:
            priority = "GLYPH"
            meaning = "readable pre-hash keyword/date glyph"
            myth = "catalog hint only"
        elif linear_context and (open_words or symbol_glyphs or weird_glyphs):
            priority = "LINEAR_MESSAGE"
            meaning = "readable or symbolic pre-hash fragment observed in a linear lane/context"
            myth = "linear inscription candidate for SAT3 review"
        elif "encoding_candidate" in cats or "encoding_encoded_fragment" in cats:
            priority = "ENCODING_PROBE"
            meaning = "structured encoding/glyph candidate measured by observer-only probes"
            myth = "measured glyph shape, not semantic proof"
        elif symbol_glyphs or weird_glyphs:
            priority = "SYMBOL_GLYPH"
            meaning = "symbolic or weird printable glyph in pre-hash input"
            myth = "strange inscription candidate until repeated or decoded"
        elif open_words:
            priority = "OPEN_WORD"
            meaning = "open-vocabulary readable word in pre-hash input"
            myth = "unknown inscription candidate until repeated or linked to rare tails"
        else:
            priority = "LOW_CONTEXT"
            meaning = "low-confidence readable context"
            myth = "noise until repeated"
        return {
            "score": int(score),
            "match_priority": priority,
            "match_reasons": sorted(set(reasons)),
            "meaning": meaning,
            "myth_layer": myth,
            "exact_genesis_headline": bool(exact),
        }

    @staticmethod
    def _group(cand: Dict[str, Any]) -> str:
        try:
            return A99SovereignTriadAccounting.group_name(cand.get("lane"), cand.get("strategy"))
        except Exception:
            lane = str(cand.get("lane", "") or "")
            if lane.startswith("random_mirror:") or lane in ("random_baseline", "randomized_traversal_mirror"):
                return "randomized_traversal_mirror"
            if lane.startswith("janus_bunnyhop_scout:"):
                return "janus_bunnyhop_scout"
            if lane.startswith("janus_bunnyhop_rescout:"):
                return "janus_bunnyhop_rescout"
            return "janus_broad_mixture"

    @staticmethod
    def _job_from_candidate(cand: Dict[str, Any]) -> Dict[str, Any]:
        job = cand.get("job") if isinstance(cand.get("job"), dict) else {}
        return {
            "job_id": cand.get("job_id") or job.get("job_id"),
            "job_seq": cand.get("job_seq") or job.get("seq"),
            "coinb1": cand.get("coinb1") or job.get("coinb1"),
            "coinb2": cand.get("coinb2") or job.get("coinb2"),
            "merkle_branch": cand.get("merkle_branch") or job.get("merkle_branch") or [],
            "version": cand.get("version_hex") or job.get("version"),
            "nbits": cand.get("nbits") or job.get("nbits"),
            "ntime": cand.get("ntime") or job.get("ntime"),
            "clean": cand.get("clean") if cand.get("clean") is not None else job.get("clean"),
        }

    def _source_blobs(self, cand: Dict[str, Any], include_full_coinbase: bool = True) -> Tuple[List[Tuple[str, bytes]], str]:
        job = self._job_from_candidate(cand)
        blobs: List[Tuple[str, bytes]] = []
        coinb1 = self._bytes_from_hex(job.get("coinb1"))
        coinb2 = self._bytes_from_hex(job.get("coinb2"))
        extranonce1 = self._bytes_from_hex(cand.get("extranonce1"))
        extranonce2 = self._bytes_from_hex(cand.get("extranonce2"))
        coinbase_dsha = ""
        if coinb1:
            blobs.append(("coinb1", coinb1))
        if coinb2:
            blobs.append(("coinb2", coinb2))
        if include_full_coinbase and coinb1 and coinb2 and (extranonce1 or cand.get("extranonce1") == "") and extranonce2:
            coinbase = coinb1 + extranonce1 + extranonce2 + coinb2
            blobs.append(("coinbase_full", coinbase))
            try:
                coinbase_dsha = dsha(coinbase).hex()
            except Exception:
                coinbase_dsha = ""
        branches = job.get("merkle_branch") if isinstance(job.get("merkle_branch"), list) else []
        for idx, branch_hex in enumerate(branches[:16]):
            branch = self._bytes_from_hex(branch_hex)
            if branch:
                blobs.append((f"merkle_branch_{idx}", branch))
        version_raw = self._bytes_from_hex(job.get("version") or job.get("version_hex"))
        if version_raw:
            blobs.append(("version", version_raw))
        for field in ("ntime", "nbits"):
            raw = self._bytes_from_hex(job.get(field))
            if raw:
                blobs.append((field, raw))
        return blobs, coinbase_dsha

    def _row_key(self, row: Dict[str, Any]) -> str:
        return "|".join(
            str(row.get(k, ""))
            for k in (
                "source_context",
                "job_id",
                "job_seq",
                "source_name",
                "variant",
                "offset",
                "text",
                "zbits",
                "proof_name",
            )
        )

    def _independent_glyph_key(
        self,
        job: Dict[str, Any],
        source_name: str,
        text: str,
        variant: str,
    ) -> str:
        return "|".join(
            str(part or "")
            for part in (
                job.get("job_id"),
                job.get("ntime"),
                source_name,
                self._normalized_glyph_key_text(text),
                variant,
            )
        )

    def _load_existing(self) -> None:
        try:
            if not os.path.exists(self.events_path):
                return
            with open(self.events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(row, dict):
                        continue
                    key = self._row_key(row)
                    if key in self.seen:
                        continue
                    self.seen.add(key)
                    self.rows.append(row)
            self.rows.sort(key=lambda r: str(r.get("observed_at_utc", "")))
        except Exception as e:
            log("glyph", f"existing event load failed: {e}")

    def _registry_path_for(self, row: Dict[str, Any]) -> str:
        if not self.registry_dir:
            return ""
        try:
            stamp = re.sub(r"[^0-9A-Za-z]+", "-", str(row.get("observed_at_utc") or utc_stamp_iso())).strip("-")
            job_id = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(row.get("job_id") or "job"))[:24]
            source = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(row.get("source_name") or "source"))[:24]
            digest = hashlib.sha256(self._row_key(row).encode("utf-8", "ignore")).hexdigest()[:12]
            score = int(row.get("score", 0) or 0)
            priority = re.sub(r"[^0-9A-Za-z_.-]+", "_", str(row.get("match_priority") or "glyph"))[:24]
            return str(Path(self.registry_dir) / f"glyph_{stamp}_score{score}_{priority}_{job_id}_{source}_{digest}.json")
        except Exception:
            return ""

    def _write_registry_event(self, row: Dict[str, Any]) -> str:
        path = self._registry_path_for(row)
        if not path:
            return ""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            atomic_json(path, {
                "schema": "a10-janus-glyph-registry-event-1",
                "created_at_utc": utc_stamp_iso(),
                "event": row,
                "claim_boundary": {
                    "sha256_reverse_claim": False,
                    "pre_hash_input_scan": True,
                    "scheduler_effect": "none",
                    "wire_change_required": False,
                },
            })
            return path
        except Exception as e:
            log("glyph", f"registry write failed: {e}")
            return ""

    def _write_row(self, row: Dict[str, Any]) -> bool:
        key = self._row_key(row)
        if key in self.seen:
            return False
        self.seen.add(key)
        try:
            if int(row.get("score", 0) or 0) >= 20:
                registry_path = self._write_registry_event(row)
                if registry_path:
                    row["registry_path"] = registry_path
            with open(self.events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            self.rows.append(row)
            self.rows.sort(key=lambda r: str(r.get("observed_at_utc", "")))
            self.write_csv()
            self.write_summary()
            return True
        except Exception as e:
            log("glyph", f"event write failed: {e}")
            return False

    @staticmethod
    def _loggable_text(text: str, limit: int = 96) -> str:
        clean = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(clean) <= limit:
            return clean
        return clean[: max(0, limit - 3)] + "..."

    def _log_match(self, row: Dict[str, Any]) -> None:
        try:
            priority = str(row.get("match_priority", ""))
            score = int(row.get("score", 0) or 0)
            if priority not in ("GENESIS_ECHO", "HIGH_GLYPH", "RARE_TAIL_LINK") and score < 35:
                return
            if priority == "OPEN_WORD" and int(row.get("zbits", 0) or 0) < self.accepted_link_min_z:
                return
            if (
                priority == "RARE_TAIL_LINK"
                and not row.get("keywords")
                and not row.get("dates")
                and str(row.get("variant", "")) != "raw"
            ):
                return
            log(
                "glyph_alert",
                "priority={} score={} source={}/{} accepted={} z={} job={} family={} keywords={} words={} symbols={} weird={} linear={} dates={} text={!r} reason={} observer_only=True".format(
                    priority,
                    score,
                    row.get("source_name"),
                    row.get("variant"),
                    row.get("accepted"),
                    row.get("zbits"),
                    row.get("job_id"),
                    ",".join(str(x) for x in row.get("mirror_families", [])[:4]) if isinstance(row.get("mirror_families"), list) else row.get("mirror_families"),
                    ",".join(str(x) for x in row.get("keywords", [])[:6]) if isinstance(row.get("keywords"), list) else row.get("keywords"),
                    ",".join(str(x) for x in row.get("open_words", [])[:6]) if isinstance(row.get("open_words"), list) else row.get("open_words"),
                    ",".join(str(x) for x in row.get("symbol_glyphs", [])[:6]) if isinstance(row.get("symbol_glyphs"), list) else row.get("symbol_glyphs"),
                    ",".join(str(x) for x in row.get("weird_glyphs", [])[:3]) if isinstance(row.get("weird_glyphs"), list) else row.get("weird_glyphs"),
                    row.get("linear_context"),
                    ",".join(str(x) for x in row.get("dates", [])[:4]) if isinstance(row.get("dates"), list) else row.get("dates"),
                    self._loggable_text(str(row.get("text", ""))),
                    ",".join(str(x) for x in row.get("match_reasons", [])[:8]) if isinstance(row.get("match_reasons"), list) else row.get("match_reasons"),
                ),
            )
        except Exception:
            pass

    def _emit_matches(
        self,
        cand: Dict[str, Any],
        source_context: str,
        accepted: bool = False,
        proof_path: Optional[str] = None,
        include_full_coinbase: bool = True,
    ) -> int:
        added = 0
        z = int(cand.get("zbits", 0) or 0)
        job = self._job_from_candidate(cand)
        blobs, coinbase_dsha = self._source_blobs(cand, include_full_coinbase=include_full_coinbase)
        observed_at = str(cand.get("accepted_at_utc") or cand.get("observed_at_utc") or utc_stamp_iso())
        proof_path_s = str(proof_path or "")
        for source_name, payload in blobs:
            source_hash = hashlib.sha256(payload).hexdigest()[:16]
            for item in self._extract_strings(payload):
                text = str(item.get("text", "")).strip()
                if not text:
                    continue
                variant = str(item.get("variant", "raw"))
                keywords, open_words, unknown_words, symbol_glyphs, weird_glyphs, dates, categories, confidence = self._classify(text)
                encoding_probe = self._encoding_probe(text, source_name, variant, payload)
                if encoding_probe.get("encoding_confidence") == "strong_candidate":
                    categories = sorted(set(list(categories) + ["encoding_strong_candidate"]))
                elif encoding_probe.get("encoding_confidence") == "candidate":
                    categories = sorted(set(list(categories) + ["encoding_candidate"]))
                glyph_type_tag = str(encoding_probe.get("glyph_type", "")).lower()
                if glyph_type_tag and glyph_type_tag != "noise":
                    categories = sorted(set(list(categories) + [f"encoding_{glyph_type_tag}"]))
                baseline_status_tag = str(encoding_probe.get("baseline_status", ""))
                if baseline_status_tag in ("anomaly_low_entropy", "anomaly_high_entropy"):
                    categories = sorted(set(list(categories) + [f"baseline_{baseline_status_tag}"]))
                source_is_coinbase = source_name in self.OPEN_WORD_SOURCE_NAMES
                live_open_context = source_context in ("stratum_job", "accepted_share")
                lane_s = str(cand.get("lane", "") or "")
                strategy_s = str(cand.get("strategy", "") or "")
                linear_context = "linear" in lane_s.lower() or strategy_s.lower() == "linear"
                if linear_context:
                    categories = sorted(set(list(categories) + ["linear_context"]))
                mirror_families = sorted(str(c) for c in categories if str(c).endswith("_mirror_family"))
                normalized_glyph_text = self._normalized_glyph_key_text(text)
                independent_glyph_key = self._independent_glyph_key(job, source_name, text, variant)
                should_record = bool(keywords or dates)
                if (open_words or symbol_glyphs or weird_glyphs) and source_is_coinbase and live_open_context:
                    should_record = True
                if linear_context and (open_words or symbol_glyphs or weird_glyphs) and live_open_context:
                    should_record = True
                if encoding_probe.get("encoding_confidence") in ("candidate", "strong_candidate") and (accepted or live_open_context):
                    should_record = True
                if accepted and z >= self.accepted_link_min_z:
                    should_record = True
                if not should_record:
                    continue
                score = self._score_hit(
                    text=text,
                    keywords=keywords,
                    open_words=open_words,
                    unknown_words=unknown_words,
                    symbol_glyphs=symbol_glyphs,
                    weird_glyphs=weird_glyphs,
                    dates=dates,
                    categories=categories,
                    accepted=accepted,
                    zbits=z,
                    source_name=source_name,
                    variant=variant,
                    linear_context=linear_context,
                )
                row = {
                    "schema": "a10-janus-glyph-event-1",
                    "event_type": "janus_glyph_event",
                    "written_at_utc": utc_stamp_iso(),
                    "observed_at_utc": observed_at,
                    "source_context": source_context,
                    "source_name": source_name,
                    "variant": variant,
                    "offset": item.get("offset", 0),
                    "text": text[:512],
                    "normalized_glyph_text": normalized_glyph_text,
                    "independent_glyph_key": independent_glyph_key,
                    "open_words": open_words,
                    "unknown_words": unknown_words,
                    "symbol_glyphs": symbol_glyphs,
                    "weird_glyphs": weird_glyphs,
                    "keywords": keywords,
                    "dates": dates,
                    "categories": categories,
                    "mirror_families": mirror_families,
                    "confidence": confidence,
                    "encoding_probe": bool(encoding_probe.get("encoding_probe")),
                    "glyph_type": encoding_probe.get("glyph_type"),
                    "encoding_confidence": encoding_probe.get("encoding_confidence"),
                    "looks_like": encoding_probe.get("looks_like", []),
                    "decode_status": encoding_probe.get("decode_status"),
                    "decode_codec": encoding_probe.get("decode_codec"),
                    "decode_padded": encoding_probe.get("decode_padded"),
                    "decoded_hex_preview": encoding_probe.get("decoded_hex_preview"),
                    "regex_shape_score": encoding_probe.get("regex_shape_score"),
                    "mirror_shape_score": encoding_probe.get("mirror_shape_score"),
                    "raw_entropy": encoding_probe.get("raw_entropy"),
                    "raw_entropy_norm": encoding_probe.get("raw_entropy_norm"),
                    "decoded_entropy": encoding_probe.get("decoded_entropy"),
                    "decoded_entropy_norm": encoding_probe.get("decoded_entropy_norm"),
                    "decoded_len": encoding_probe.get("decoded_len"),
                    "short_sample_warning": encoding_probe.get("short_sample_warning"),
                    "char_classes": encoding_probe.get("char_classes"),
                    "baseline_entropy_mean": encoding_probe.get("baseline_entropy_mean"),
                    "baseline_entropy_std": encoding_probe.get("baseline_entropy_std"),
                    "baseline_entropy_z_score": encoding_probe.get("baseline_entropy_z_score"),
                    "baseline_window_count": encoding_probe.get("baseline_window_count"),
                    "baseline_status": encoding_probe.get("baseline_status"),
                    "confidence": confidence,
                    "match_priority": score["match_priority"],
                    "score": score["score"],
                    "match_reasons": score["match_reasons"],
                    "meaning": score["meaning"],
                    "exact_genesis_headline": score["exact_genesis_headline"],
                    "run_name": Path(os.getcwd()).name,
                    "job_id": job.get("job_id"),
                    "job_seq": job.get("job_seq"),
                    "ntime": job.get("ntime"),
                    "nbits": job.get("nbits"),
                    "clean": job.get("clean"),
                    "accepted": bool(accepted),
                    "zbits": z,
                    "group": self._group(cand) if accepted else "",
                    "lane": cand.get("lane", ""),
                    "strategy": cand.get("strategy", ""),
                    "linear_context": bool(linear_context),
                    "sector": cand.get("sector", ""),
                    "round_id": cand.get("round_id", ""),
                    "worker_id": cand.get("worker_id", ""),
                    "proof_name": os.path.basename(proof_path_s),
                    "proof_path": proof_path_s,
                    "source_sha256_16": source_hash,
                    "coinbase_dsha": coinbase_dsha or cand.get("coinbase_hash_raw", ""),
                    "raw_layer": "pre_hash_input_bytes",
                    "inferred_layer": categories,
                    "myth_layer": score["myth_layer"],
                    "scheduler_effect": "observe_only",
                    "wire_change_required": False,
                }
                if self._write_row(row):
                    added += 1
                    self._log_match(row)
        return added

    def observe_job(self, job: Job, extranonce1: str = "") -> None:
        try:
            key = f"{job.job_id}|{job.seq}"
            if key in self.seen_jobs:
                return
            self.seen_jobs.add(key)
            cand = {
                "job_id": job.job_id,
                "job_seq": job.seq,
                "coinb1": job.coinb1,
                "coinb2": job.coinb2,
                "merkle_branch": list(job.merkle_branch),
                "version": job.version,
                "version_hex": job.version,
                "nbits": job.nbits,
                "ntime": job.ntime,
                "clean": job.clean,
                "extranonce1": extranonce1,
                "observed_at_utc": utc_stamp_iso(),
            }
            added = self._emit_matches(cand, "stratum_job", accepted=False, include_full_coinbase=False)
            if added:
                log("glyph", f"job={job.job_id} seq={job.seq} matches={added} observer_only=True")
        except Exception as e:
            log("glyph", f"job observe failed: {e}")

    def observe_accepted(self, cand: Dict[str, Any], proof_path: Optional[str] = None) -> None:
        try:
            added = self._emit_matches(cand, "accepted_share", accepted=True, proof_path=proof_path, include_full_coinbase=True)
            if added:
                log("glyph", f"accepted z={cand.get('zbits')} group={self._group(cand)} matches={added} observer_only=True")
        except Exception as e:
            log("glyph", f"accepted observe failed: {e}")

    def _proof_candidate(self, proof_path: Path) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(proof_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            cand = data.get("raw_candidate") if isinstance(data.get("raw_candidate"), dict) else {}
            if not cand:
                return None
            if not cand.get("accepted_at_utc"):
                cand["accepted_at_utc"] = data.get("created_at_utc") or utc_stamp_iso()
            if not cand.get("zbits"):
                match = self.ACCEPTED_RE.match(proof_path.name)
                if match:
                    cand["zbits"] = int(match.group(1))
            return cand
        except Exception as e:
            log("glyph", f"proof backfill read failed {proof_path.name}: {e}")
            return None

    def backfill_existing_proofs(self, proofs_dir: str) -> None:
        added = 0
        try:
            root = Path(proofs_dir)
            if not root.exists():
                return
            for path in sorted(root.rglob("accepted_20*_z*_nonce0x*.json"), key=lambda p: p.name):
                if any(part.lower() == "raw_accepted" for part in path.parts):
                    continue
                cand = self._proof_candidate(path)
                if not cand:
                    continue
                z = int(cand.get("zbits", 0) or 0)
                if z < self.accepted_link_min_z:
                    # Still scan lower-z proofs if they contain explicit glyph keywords.
                    before = len(self.rows)
                    self._emit_matches(cand, "accepted_share_backfill", accepted=False, proof_path=str(path), include_full_coinbase=True)
                    added += max(0, len(self.rows) - before)
                    continue
                before = len(self.rows)
                self.observe_accepted(cand, proof_path=str(path))
                added += max(0, len(self.rows) - before)
            if added:
                log("glyph", f"backfilled {added} glyph events from accepted proofs in {proofs_dir}")
        except Exception as e:
            log("glyph", f"proof backfill failed: {e}")

    def _count_map(self, field: str) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for row in self.rows:
            value = row.get(field)
            values = value if isinstance(value, list) else [value]
            for item in values:
                if item is None or item == "":
                    continue
                key = str(item)
                out[key] = int(out.get(key, 0)) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def _count_map_filtered(self, field: str, variants: Iterable[str]) -> Dict[str, int]:
        allowed = {str(v) for v in variants}
        out: Dict[str, int] = {}
        for row in self.rows:
            if str(row.get("variant", "")) not in allowed:
                continue
            value = row.get(field)
            values = value if isinstance(value, list) else [value]
            for item in values:
                if item is None or item == "":
                    continue
                key = str(item)
                out[key] = int(out.get(key, 0)) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def _row_independent_glyph_key(self, row: Dict[str, Any]) -> str:
        existing = str(row.get("independent_glyph_key", "") or "")
        if existing:
            return existing
        return "|".join(
            str(part or "")
            for part in (
                row.get("job_id"),
                row.get("ntime"),
                row.get("source_name"),
                row.get("normalized_glyph_text") or self._normalized_glyph_key_text(str(row.get("text", ""))),
                row.get("variant"),
            )
        )

    def _independent_count(self) -> int:
        return len({self._row_independent_glyph_key(row) for row in self.rows if self._row_independent_glyph_key(row)})

    def _independent_by_mirror_family(self) -> Dict[str, int]:
        buckets: Dict[str, set[str]] = {}
        for row in self.rows:
            families = self._row_mirror_families(row)
            key = self._row_independent_glyph_key(row)
            if not key:
                continue
            for family in families:
                if not family:
                    continue
                buckets.setdefault(str(family), set()).add(key)
        return dict(sorted(((k, len(v)) for k, v in buckets.items()), key=lambda kv: (-kv[1], kv[0])))

    @staticmethod
    def _row_job_ntime_key(row: Dict[str, Any]) -> str:
        return "|".join(str(part or "") for part in (row.get("job_id"), row.get("ntime")))

    def _job_ntime_by_mirror_family(self) -> Dict[str, int]:
        buckets: Dict[str, set[str]] = {}
        for row in self.rows:
            key = self._row_job_ntime_key(row)
            if not key.strip("|"):
                continue
            for family in self._row_mirror_families(row):
                if not family:
                    continue
                buckets.setdefault(str(family), set()).add(key)
        return dict(sorted(((k, len(v)) for k, v in buckets.items()), key=lambda kv: (-kv[1], kv[0])))

    def _row_mirror_families(self, row: Dict[str, Any]) -> List[str]:
        families = set()
        existing = row.get("mirror_families")
        if isinstance(existing, list):
            families.update(str(x) for x in existing if x)
        categories = row.get("categories")
        if isinstance(categories, list):
            families.update(str(c) for c in categories if str(c).endswith("_mirror_family"))
        words: List[str] = []
        for field in ("open_words", "unknown_words", "keywords"):
            value = row.get(field)
            if isinstance(value, list):
                words.extend(str(x).lower() for x in value)
        text_key = self._normalized_glyph_key_text(str(row.get("text", "")))
        if any(w in self.PLEA_MIRROR_WORDS for w in words) or text_key in self.PLEA_MIRROR_WORDS:
            families.add("plea_mirror_family")
        compact = re.sub(r"\s+", "", str(row.get("text", "")).lower())
        if compact in self.GP_D_MIRROR_TOKENS:
            families.add("gp_d_mirror_family")
        return sorted(families)

    def _mirror_family_count_map(self, variants: Optional[Iterable[str]] = None) -> Dict[str, int]:
        allowed = {str(v) for v in variants} if variants is not None else None
        out: Dict[str, int] = {}
        for row in self.rows:
            if allowed is not None and str(row.get("variant", "")) not in allowed:
                continue
            for family in self._row_mirror_families(row):
                if not family:
                    continue
                out[str(family)] = int(out.get(str(family), 0)) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    def _top_events(self, limit: int = 16) -> List[Dict[str, Any]]:
        rows = sorted(
            self.rows,
            key=lambda r: (int(r.get("score", 0) or 0), int(r.get("zbits", 0) or 0), str(r.get("observed_at_utc", ""))),
            reverse=True,
        )
        return rows[:limit]

    def write_csv(self) -> None:
        try:
            tmp = self.csv_path + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS, extrasaction="ignore")
                writer.writeheader()
                for row in self.rows:
                    flat = dict(row)
                    for field in (
                        "open_words",
                        "unknown_words",
                        "symbol_glyphs",
                        "weird_glyphs",
                        "keywords",
                        "dates",
                        "categories",
                        "mirror_families",
                        "looks_like",
                        "match_reasons",
                        "inferred_layer",
                    ):
                        value = flat.get(field)
                        if isinstance(value, list):
                            flat[field] = ";".join(str(x) for x in value)
                    if isinstance(flat.get("char_classes"), dict):
                        flat["char_classes"] = json.dumps(flat.get("char_classes"), ensure_ascii=False, sort_keys=True)
                    writer.writerow(flat)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            os.replace(tmp, self.csv_path)
        except Exception as e:
            log("glyph", f"csv write failed: {e}")

    def summary(self) -> Dict[str, Any]:
        best_z = max((int(r.get("zbits", 0) or 0) for r in self.rows), default=0)
        accepted_rows = [r for r in self.rows if r.get("accepted")]
        return {
            "schema": "a10-janus-glyph-summary-1",
            "version": VERSION,
            "sentinel": SENTINEL,
            "written_at_utc": utc_stamp_iso(),
            "started_at_utc": self.started_at_utc,
            "observer_only": True,
            "scheduler_effect": "none",
            "wire_change_required": False,
            "objective": "Scan pre-hash Stratum job/coinbase bytes for readable glyphs, then link them to accepted-share rare-tail telemetry without changing mining behavior.",
            "min_len": self.min_len,
            "accepted_link_min_z": self.accepted_link_min_z,
            "events_path": self.events_path,
            "csv_path": self.csv_path,
            "summary_path": self.summary_path,
            "registry_dir": self.registry_dir,
            "total_events": len(self.rows),
            "accepted_link_events": len(accepted_rows),
            "best_z": best_z,
            "keywords": list(self.keywords),
            "by_priority": self._count_map("match_priority"),
            "by_source_context": self._count_map("source_context"),
            "by_source_name": self._count_map("source_name"),
            "by_open_word": self._count_map("open_words"),
            "by_unknown_word": self._count_map("unknown_words"),
            "by_symbol_glyph": self._count_map("symbol_glyphs"),
            "by_weird_glyph": self._count_map("weird_glyphs"),
            "by_mirror_family": self._mirror_family_count_map(),
            "by_glyph_type": self._count_map("glyph_type"),
            "by_encoding_confidence": self._count_map("encoding_confidence"),
            "by_decode_status": self._count_map("decode_status"),
            "by_baseline_status": self._count_map("baseline_status"),
            "encoding_probe": {
                "enabled": True,
                "decoder_order": ["base85", "ascii85"],
                "short_sample_warning_len_lt": 8,
                "baseline_window_limit": self.BASELINE_WINDOW_LIMIT,
                "baseline_min_windows": self.BASELINE_MIN_WINDOWS,
                "claim_boundary": "measures glyph shape/entropy only; never semantic proof and never scheduler policy",
            },
            "by_direct_open_word": self._count_map_filtered("open_words", ("raw", "hex_ascii", "base64_ascii")),
            "by_direct_unknown_word": self._count_map_filtered("unknown_words", ("raw", "hex_ascii", "base64_ascii")),
            "by_direct_symbol_glyph": self._count_map_filtered("symbol_glyphs", ("raw", "hex_ascii", "base64_ascii")),
            "by_direct_weird_glyph": self._count_map_filtered("weird_glyphs", ("raw", "hex_ascii", "base64_ascii")),
            "by_direct_mirror_family": self._mirror_family_count_map(("raw", "hex_ascii", "base64_ascii")),
            "unique_independent_glyph_keys": self._independent_count(),
            "independent_glyph_key_formula": "job_id|ntime|source_name|normalized_glyph_text|variant",
            "independent_by_mirror_family": self._independent_by_mirror_family(),
            "job_ntime_key_formula": "job_id|ntime",
            "job_ntime_by_mirror_family": self._job_ntime_by_mirror_family(),
            "linear_context_events": sum(1 for r in self.rows if r.get("linear_context")),
            "by_keyword": self._count_map("keywords"),
            "by_category": self._count_map("categories"),
            "by_group": self._count_map("group"),
            "top_events": self._top_events(16),
            "top_encoding_events": [
                r for r in self._top_events(64)
                if str(r.get("match_priority", "")) == "ENCODING_PROBE"
                or str(r.get("encoding_confidence", "")) in ("candidate", "strong_candidate")
            ][:16],
            "recent": self.rows[-24:],
            "boundary": {
                "raw": "literal strings found in pre-hash input bytes",
                "inferred": "classification tags only",
                "myth": "separate interpretation, never proof and never scheduler policy",
            },
        }

    def write_summary(self) -> None:
        try:
            atomic_json(self.summary_path, self.summary())
        except Exception as e:
            log("glyph", f"summary write failed: {e}")


class KombuchaCellMicrokernel:
    """Observer-only SCOBY-style cell map for structured JANUS randomness.

    Each nucleus has tiny local state. The aggregate pressure is recorded for
    later correlation with rare-tail telemetry, but it never feeds task choice,
    submit thresholds, nonce encoding, or Stratum wire behavior in A9.11.
    """

    SURFACES = ("cpu_lanes", "l3_cache", "ram_digest", "network_wait", "storage_manifest", "nonce_cell")
    ROLES = ("VOID", "SEEK", "FLOW", "BITE", "FERMENT", "PARADOX")
    TAILS = (28, 30, 32, 33, 34, 35, 36, 38, 39)

    def __init__(self, nuclei: int = 12, enabled: bool = True) -> None:
        self.enabled = bool(enabled)
        self.nuclei = max(3, int(nuclei or 12))
        self.cells: List[Dict[str, Any]] = [self._base_cell(i) for i in range(self.nuclei)]
        self.last: Dict[str, Any] = {
            "enabled": self.enabled,
            "observer_only": True,
            "scheduler_effect": "none",
            "wire_change_required": False,
            "nuclei": self.nuclei,
            "mode": "BOOT",
        }

    def _base_cell(self, i: int) -> Dict[str, Any]:
        return {
            "cell_id": i,
            "role": self.ROLES[i % len(self.ROLES)],
            "surface": self.SURFACES[i % len(self.SURFACES)],
            "checked": 0,
            "accepted": 0,
            "rejected": 0,
            "submitted": 0,
            "result_count": 0,
            "best_z": 0,
            "tail_hits": {f"z{z}": 0 for z in self.TAILS},
            "acid": 0.12 + (i % 5) * 0.031,
            "yeast": 0.22 + (i % 7) * 0.027,
            "bacteria": 0.31 + (i % 3) * 0.041,
            "charge": 0.0,
            "paradox": 0.0,
            "mode": "FERMENT",
            "last_seen_utc": "",
        }

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value or 0.0)))

    @classmethod
    def label_for_parts(
        cls,
        lane: Any,
        strategy: Any,
        sector: Any,
        cfg_name: Any,
        worker_id: Any,
        round_id: Any,
        job_id: Any,
        nuclei: int = 12,
    ) -> Dict[str, Any]:
        n = max(3, int(nuclei or 12))
        try:
            sec = int(sector or 0) % SECTORS
        except Exception:
            sec = 0
        try:
            wid = int(worker_id or 0)
        except Exception:
            wid = 0
        try:
            rid = int(round_id or 0)
        except Exception:
            rid = 0
        seed = stable_seed("kombucha_cell", lane, strategy, sec, cfg_name, wid, rid, job_id)
        cell_id = int(seed % n)
        phase = (((cell_id + 1) * 0.137) + (sec * 0.071) + ((wid % 32) * 0.013) + ((rid % 997) * 0.0007)) % 1.0
        surface = cls.SURFACES[(cell_id + sec) % len(cls.SURFACES)]
        role = cls.ROLES[cell_id % len(cls.ROLES)]
        return {
            "schema": "a9-11-kombucha-cell-label-1",
            "observer_only": True,
            "scheduler_effect": "none",
            "wire_change_required": False,
            "cell_id": cell_id,
            "nuclei": n,
            "role": role,
            "surface": surface,
            "phase": round(float(phase), 8),
            "lane": str(lane or ""),
            "strategy": str(strategy or ""),
            "sector": sec,
            "cfg_name": str(cfg_name or "canonical"),
        }

    @classmethod
    def label_for_candidate(cls, cand: Dict[str, Any], nuclei: int = 12) -> Dict[str, Any]:
        return cls.label_for_parts(
            cand.get("lane", ""),
            cand.get("strategy", ""),
            cand.get("sector", 0),
            cand.get("cfg_name", "canonical"),
            cand.get("worker_id", 0),
            cand.get("round_id", 0),
            cand.get("job_id", ""),
            nuclei,
        )

    def _update_cell_metabolism(self, cell: Dict[str, Any], group: str, best_z: int, load_state: str, accepted: Optional[bool] = None) -> None:
        tail_pressure = self._clamp01((float(best_z or 0) - 28.0) / 8.0)
        load_noise = 0.18 if str(load_state or "CLEAN") != "CLEAN" else 0.0
        janus_feed = 1.0 if str(group).startswith("janus_") else 0.35
        scout_feed = 0.55 if group == "janus_bunnyhop_scout" else 0.0
        rescout_feed = 0.70 if group == "janus_bunnyhop_rescout" else 0.0
        accept_feed = 0.12 if accepted is True else 0.0
        reject_noise = 0.10 if accepted is False else 0.0
        cell["acid"] = self._clamp01(float(cell.get("acid", 0.0)) * 0.93 + 0.035 + load_noise + reject_noise)
        cell["yeast"] = self._clamp01(float(cell.get("yeast", 0.0)) * 0.91 + tail_pressure * 0.10 + accept_feed + scout_feed * 0.03)
        cell["bacteria"] = self._clamp01(float(cell.get("bacteria", 0.0)) * 0.92 + janus_feed * 0.035 + rescout_feed * 0.05 + tail_pressure * 0.04)
        paradox = abs(float(cell["yeast"]) - float(cell["bacteria"])) + load_noise * 0.35 + reject_noise
        cell["paradox"] = self._clamp01(paradox)
        cell["charge"] = self._clamp01((float(cell["acid"]) + float(cell["yeast"]) + float(cell["bacteria"])) / 3.0 - float(cell["paradox"]) * 0.20)
        mode = "FERMENT"
        if float(cell["paradox"]) > 0.58:
            mode = "PARADOX_DIGEST"
        elif float(cell["charge"]) > 0.52 and str(load_state or "CLEAN") == "CLEAN":
            mode = "COLD_METABOLISM"
        elif accepted is False:
            mode = "ACIDIC_SLEEP"
        cell["mode"] = mode
        cell["last_seen_utc"] = utc_stamp_iso()

    def observe_result(self, r: Any, group: str, load_state: str) -> None:
        if not self.enabled:
            return
        label = self.label_for_parts(
            getattr(r, "lane", ""),
            getattr(r, "strategy", ""),
            getattr(r, "sector", 0),
            getattr(r, "cfg_name", "canonical"),
            getattr(r, "worker_id", 0),
            getattr(r, "round_id", 0),
            "",
            self.nuclei,
        )
        cell = self.cells[int(label["cell_id"])]
        checked = max(0, int(getattr(r, "checked", 0) or 0))
        best_z = max(0, int(getattr(r, "best_z", 0) or 0))
        cell["surface"] = label["surface"]
        cell["checked"] = int(cell.get("checked", 0)) + checked
        cell["result_count"] = int(cell.get("result_count", 0)) + 1
        cell["best_z"] = max(int(cell.get("best_z", 0) or 0), best_z)
        for z in self.TAILS:
            if best_z >= z:
                tails = cell.setdefault("tail_hits", {f"z{zz}": 0 for zz in self.TAILS})
                tails[f"z{z}"] = int(tails.get(f"z{z}", 0)) + 1
        self._update_cell_metabolism(cell, group, best_z, load_state, accepted=None)

    def observe_submit(self, cand: Dict[str, Any], group: str, accepted: bool, load_state: str) -> None:
        if not self.enabled:
            return
        label = self.label_for_candidate(cand, self.nuclei)
        cell = self.cells[int(label["cell_id"])]
        zbits = max(0, int(cand.get("zbits", 0) or 0))
        cell["surface"] = label["surface"]
        cell["submitted"] = int(cell.get("submitted", 0)) + 1
        if accepted:
            cell["accepted"] = int(cell.get("accepted", 0)) + 1
        else:
            cell["rejected"] = int(cell.get("rejected", 0)) + 1
        cell["best_z"] = max(int(cell.get("best_z", 0) or 0), zbits)
        for z in self.TAILS:
            if accepted and zbits >= z:
                tails = cell.setdefault("tail_hits", {f"z{zz}": 0 for zz in self.TAILS})
                tails[f"z{z}"] = int(tails.get(f"z{z}", 0)) + 1
        self._update_cell_metabolism(cell, group, zbits, load_state, accepted=accepted)

    def summary(self, load_state: str = "CLEAN") -> Dict[str, Any]:
        if not self.enabled:
            self.last = {
                "enabled": False,
                "observer_only": True,
                "scheduler_effect": "none",
                "wire_change_required": False,
                "nuclei": self.nuclei,
                "mode": "OFF",
            }
            return self.last
        active = [c for c in self.cells if int(c.get("result_count", 0)) or int(c.get("submitted", 0))]
        rows = active if active else self.cells
        count = max(1, len(rows))
        acid = sum(float(c.get("acid", 0.0) or 0.0) for c in rows) / count
        paradox = sum(float(c.get("paradox", 0.0) or 0.0) for c in rows) / count
        charge = sum(float(c.get("charge", 0.0) or 0.0) for c in rows) / count
        cold = 0.72 if str(load_state or "CLEAN") == "CLEAN" else 0.38
        micro_pressure = self._clamp01(charge * 0.45 + acid * 0.25 + cold * 0.25 - paradox * 0.30)
        mode = "FERMENT"
        if paradox > 0.58:
            mode = "PARADOX_DIGEST"
        elif micro_pressure > 0.48 and cold > 0.60:
            mode = "COLD_METABOLISM"
        elif cold < 0.45:
            mode = "ACIDIC_SLEEP"
        surface_counts: Dict[str, int] = defaultdict(int)
        for c in self.cells:
            surface_counts[str(c.get("surface", "unknown"))] += int(c.get("result_count", 0) or 0) + int(c.get("submitted", 0) or 0)
        top_cells = sorted(
            (dict(c) for c in self.cells),
            key=lambda c: (int(c.get("best_z", 0) or 0), int(c.get("accepted", 0) or 0), float(c.get("charge", 0.0) or 0.0)),
            reverse=True,
        )[:12]
        self.last = {
            "schema": "a9-11-kombucha-cell-microkernel-observer-1",
            "enabled": True,
            "observer_only": True,
            "scheduler_effect": "none",
            "wire_change_required": False,
            "nuclei": self.nuclei,
            "mode": mode,
            "microkernel_pressure": round(float(micro_pressure), 8),
            "acid": round(float(acid), 8),
            "paradox": round(float(paradox), 8),
            "charge": round(float(charge), 8),
            "cold_fermentation": round(float(cold), 8),
            "blocks_aggression": bool(mode in {"ACIDIC_SLEEP", "PARADOX_DIGEST"}),
            "surface_counts": dict(surface_counts),
            "top_cells": top_cells,
            "rules": [
                "cells observe JANUS-shaped randomness only",
                "microkernel pressure is telemetry, not a scheduler input in A9.11",
                "paradox digest means hold pressure, not change wire",
            ],
        }
        return self.last


class TriuneAtomicClockObserver:
    """Observer-only third-face clock for JANUS boundary orientation.

    Bitcoin work remains double SHA-256. The "third face" is the measurement
    axis: hash result, traversal path, and time/entropy phase at the pool
    boundary. This class never feeds task choice, batch pressure, submit gates,
    nonce encoding, or Stratum wire behavior.
    """

    TAILS = (28, 30, 32, 33, 34, 35, 36, 38, 39)

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = bool(enabled)
        self.started_at_utc = utc_stamp_iso()
        self.started_perf_ns = time.perf_counter_ns()
        self.last_perf_ns = 0
        self.tick = 0
        self.samples = 0
        self.delta_ema_ms = 0.0
        self.jitter_ema_ms = 0.0
        self.jitter_peak_ms = 0.0
        self.clock_phase = 0.0
        self.battery_charge = 0.50
        self.purity_score = 1.0
        self.hardware_entropy = 0.0
        self.best_z = 0
        self.last_round = 0
        self.last_group = ""
        self.last_load_state = "CLEAN"
        self.tail_hits = {f"z{z}": 0 for z in self.TAILS}
        self.last = self.snapshot()

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value or 0.0)))

    @staticmethod
    def _state_name(battery: float, jitter_ms: float, load_state: str) -> str:
        if str(load_state or "") in {"COOLDOWN", "SURVIVE"}:
            return "BLUE_RECOVERY_CLOCK"
        if battery < 0.32:
            return "LOW_BATTERY_HOLD"
        if jitter_ms > 220.0:
            return "JITTER_BOUNDARY_WATCH"
        if battery > 0.62 and jitter_ms < 80.0:
            return "STABLE_ATOMIC_CLOCK"
        return "FERMENTING_CLOCK"

    def observe_runtime(self, round_id: int, total_hps: float, load_state: str) -> None:
        if not self.enabled:
            return
        now_ns = time.perf_counter_ns()
        if self.last_perf_ns <= 0:
            self.last_perf_ns = now_ns
            self.last_round = int(round_id or 0)
            self.last_load_state = str(load_state or "CLEAN")
            self.last = self.snapshot()
            return

        delta_ms = max(0.0, (now_ns - self.last_perf_ns) / 1_000_000.0)
        self.last_perf_ns = now_ns
        self.tick += 1
        self.samples += 1
        if self.delta_ema_ms <= 0.0:
            self.delta_ema_ms = delta_ms
        jitter_ms = abs(delta_ms - self.delta_ema_ms)
        self.delta_ema_ms = self.delta_ema_ms * 0.94 + delta_ms * 0.06
        self.jitter_ema_ms = self.jitter_ema_ms * 0.92 + jitter_ms * 0.08
        self.jitter_peak_ms = max(self.jitter_peak_ms * 0.995, jitter_ms)

        hps_norm = self._clamp01(float(total_hps or 0.0) / 3_000_000.0)
        clean = str(load_state or "CLEAN") == "CLEAN"
        clean_term = 0.030 if clean else -0.035
        jitter_penalty = self._clamp01(self.jitter_ema_ms / 300.0) * 0.070
        self.battery_charge = self._clamp01(self.battery_charge * 0.985 + hps_norm * 0.022 + clean_term - jitter_penalty)
        self.purity_score = self._clamp01(1.0 - self.jitter_ema_ms / 360.0 - (0.16 if not clean else 0.0))
        phase_step = (delta_ms / 1000.0) * (0.13 + hps_norm * 0.07) + (self.jitter_ema_ms % 31.0) / 3100.0
        self.clock_phase = (self.clock_phase + phase_step) % 1.0
        entropy_word = (now_ns ^ (int(round_id or 0) << 11) ^ (os.getpid() << 5) ^ int(delta_ms * 1000.0)) & 0xFFFFFFFF
        self.hardware_entropy = float(entropy_word) / float(0xFFFFFFFF)
        self.last_round = int(round_id or 0)
        self.last_load_state = str(load_state or "CLEAN")
        self.last = self.snapshot()

    def observe_result(self, r: Any, group: str, load_state: str) -> None:
        if not self.enabled:
            return
        self.last_group = str(group or "")
        self.last_load_state = str(load_state or "CLEAN")
        best_z = max(0, int(getattr(r, "best_z", 0) or 0))
        self.best_z = max(self.best_z, best_z)
        self.last = self.snapshot()

    def observe_submit(self, cand: Dict[str, Any], group: str, accepted: bool, load_state: str) -> None:
        if not self.enabled:
            return
        self.last_group = str(group or "")
        self.last_load_state = str(load_state or "CLEAN")
        zbits = max(0, int(cand.get("zbits", 0) or 0))
        self.best_z = max(self.best_z, zbits)
        if accepted:
            for z in self.TAILS:
                if zbits >= z:
                    key = f"z{z}"
                    self.tail_hits[key] = int(self.tail_hits.get(key, 0) or 0) + 1
        self.last = self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        if not self.enabled:
            return {
                "schema": "a9-11-triune-atomic-clock-observer-1",
                "enabled": False,
                "observer_only": True,
                "scheduler_effect": "none",
                "wire_change_required": False,
                "wire_hash_function": "double_sha256",
                "state": "OFF",
            }
        phase_bucket = int(self.clock_phase * 12.0) % 12
        state = self._state_name(self.battery_charge, self.jitter_ema_ms, self.last_load_state)
        return {
            "schema": "a9-11-triune-atomic-clock-observer-1",
            "enabled": True,
            "observer_only": True,
            "scheduler_effect": "none",
            "wire_change_required": False,
            "wire_hash_function": "double_sha256",
            "third_face_policy": "measurement_axis_only",
            "started_at_utc": self.started_at_utc,
            "tick": int(self.tick),
            "samples": int(self.samples),
            "round": int(self.last_round),
            "state": state,
            "clock_phase": round(float(self.clock_phase), 8),
            "phase_bucket": phase_bucket,
            "battery_charge": round(float(self.battery_charge), 8),
            "purity_score": round(float(self.purity_score), 8),
            "timing_delta_ema_ms": round(float(self.delta_ema_ms), 6),
            "timing_jitter_ema_ms": round(float(self.jitter_ema_ms), 6),
            "timing_jitter_peak_ms": round(float(self.jitter_peak_ms), 6),
            "hardware_entropy_sample": round(float(self.hardware_entropy), 8),
            "best_z": int(self.best_z),
            "tail_hits": dict(self.tail_hits),
            "last_group": self.last_group,
            "last_load_state": self.last_load_state,
            "triune_view": {
                "faces": ["red_trickster", "blue_shadow", "gold_sovereign"],
                "axes": ["hash_result", "traversal_path", "time_entropy_phase"],
                "nexus": "interface_orientation_observer",
            },
            "janus_particle_boundary_model": {
                "fixed_chemistry": "frozen wire, double SHA-256, canonical submit",
                "surfaces": ["janus_traversal_arm", "randomized_traversal_mirror", "dark_tail_boundary"],
                "external_medium": "pool_job_time_boundary",
                "orientation_effect": "recorded as telemetry only; no scheduler feedback in A9.11",
            },
        }


class A99SovereignTriadAccounting:
    """Fresh-only A9.11 BunnyHop accounting layer plus Sovereign Triad + Kombucha Cell Microkernel labels.

    This class does not choose tasks and does not touch header/nonce/submit wire.
    It only groups the V32 lane mix into:
      - janus_bunnyhop_scout: random nonce traversal inside JANUS-shaped cells
      - janus_bunnyhop_rescout: JANUS-shaped re-jump when wake stalls
      - janus_broad_mixture: original adaptive JANUS lanes after wake
      - randomized_traversal_mirror: always-random shaped control arm
    """

    TAILS = (23, 24, 25, 26, 28, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40)

    def __init__(self, path: str, kombucha_nuclei: int = 12, kombucha_enabled: bool = True, atomic_clock_enabled: bool = True) -> None:
        self.path = path
        self.started_at_utc = utc_stamp_iso()
        self.started_wall = time.time()
        self.current_round = 0
        self.current_load_state = "CLEAN"
        self.last_runtime: Dict[str, Any] = {}
        self.groups: Dict[str, Dict[str, Any]] = {}
        self.lanes: Dict[str, Dict[str, Any]] = {}
        self.load_states: Dict[str, Dict[str, Any]] = {}
        self.events: Deque[Dict[str, Any]] = deque(maxlen=256)
        self.last_triad: Dict[str, Any] = {}
        self.kombucha_cells = KombuchaCellMicrokernel(kombucha_nuclei, kombucha_enabled)
        self.atomic_clock = TriuneAtomicClockObserver(atomic_clock_enabled)

    @staticmethod
    def group_name(lane: Any, strategy: Any = None) -> str:
        lane_s = str(lane or "unknown")
        if lane_s.startswith("janus_bunnyhop_scout:"):
            return "janus_bunnyhop_scout"
        if lane_s.startswith("janus_bunnyhop_rescout:"):
            return "janus_bunnyhop_rescout"
        if lane_s.startswith("random_mirror:"):
            return "randomized_traversal_mirror"
        if lane_s == "random_baseline":
            return "randomized_traversal_mirror"
        return "janus_broad_mixture"

    @staticmethod
    def lane_key(lane: Any, strategy: Any, sector: Any, cfg_name: Any) -> str:
        try:
            sec = int(sector or 0) % SECTORS
        except Exception:
            sec = 0
        return f"{lane or 'unknown'}::{strategy or 'unknown'}/s{sec}/{cfg_name or 'canonical'}"

    def _base_row(self, name: str, kind: str = "group") -> Dict[str, Any]:
        return {
            "name": name,
            "kind": kind,
            "checked": 0,
            "accepted": 0,
            "rejected": 0,
            "submitted": 0,
            "result_count": 0,
            "best_z": 0,
            "hps_ewma": 0.0,
            "accepted_tails": {f"z{z}": 0 for z in self.TAILS},
            "result_best_tails": {f"z{z}": 0 for z in self.TAILS},
            "last_seen_utc": "",
        }

    def _group_row(self, group: str) -> Dict[str, Any]:
        if group not in self.groups:
            self.groups[group] = self._base_row(group, "group")
        return self.groups[group]

    def _lane_row(self, key: str) -> Dict[str, Any]:
        if key not in self.lanes:
            self.lanes[key] = self._base_row(key, "lane")
        return self.lanes[key]

    def _load_row(self, state: str) -> Dict[str, Any]:
        if state not in self.load_states:
            self.load_states[state] = self._base_row(state, "load_state")
        return self.load_states[state]

    def _combine_rows(self, name: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        out = self._base_row(name, "group")
        last_seen = ""
        for row in rows:
            if not isinstance(row, dict):
                continue
            for key in ("checked", "accepted", "rejected", "submitted", "result_count"):
                out[key] = int(out.get(key, 0)) + int(row.get(key, 0) or 0)
            out["best_z"] = max(int(out.get("best_z", 0)), int(row.get("best_z", 0) or 0))
            out["hps_ewma"] = float(out.get("hps_ewma", 0.0) or 0.0) + float(row.get("hps_ewma", 0.0) or 0.0)
            for tail_key in ("accepted_tails", "result_best_tails"):
                dst = out.setdefault(tail_key, {f"z{z}": 0 for z in self.TAILS})
                src = row.get(tail_key, {}) or {}
                for z in self.TAILS:
                    k = f"z{z}"
                    dst[k] = int(dst.get(k, 0)) + int(src.get(k, 0) or 0)
            last_seen = max(last_seen, str(row.get("last_seen_utc", "") or ""))
        out["last_seen_utc"] = last_seen
        return out

    def bunnyhop_status(self, args: argparse.Namespace) -> Dict[str, Any]:
        scout_raw = self.groups.get("janus_bunnyhop_scout", self._base_row("janus_bunnyhop_scout", "group"))
        rescout_raw = self.groups.get("janus_bunnyhop_rescout", self._base_row("janus_bunnyhop_rescout", "group"))
        broad_raw = self.groups.get("janus_broad_mixture", self._base_row("janus_broad_mixture", "group"))
        mirror_raw = self.groups.get("randomized_traversal_mirror", self._base_row("randomized_traversal_mirror", "group"))
        scout = self._decorated_row(scout_raw)
        rescout = self._decorated_row(rescout_raw)
        broad = self._decorated_row(broad_raw)
        janus = self._decorated_row(self._combine_rows("janus_bunnyhop_arm", [scout_raw, rescout_raw, broad_raw]))
        mirror = self._decorated_row(mirror_raw)
        min_acc = max(0, int(getattr(args, "bunnyhop_scout_min_accepted", 500) or 500))
        wake_z = max(1, int(getattr(args, "bunnyhop_wake_z", 32) or 32))
        rescout_enabled = bool(getattr(args, "bunnyhop_rescout_enable", True))
        rescout_after = max(0, int(getattr(args, "bunnyhop_rescout_after_accepted", 250) or 250))
        rescout_burst = max(1, int(getattr(args, "bunnyhop_rescout_burst_accepted", 160) or 160))
        rescout_cycle = max(rescout_burst + 1, int(getattr(args, "bunnyhop_rescout_cycle_accepted", 420) or 420))
        rescout_target_z = max(wake_z + 1, int(getattr(args, "bunnyhop_rescout_target_z", wake_z + 2) or (wake_z + 2)))
        active_gate = bool(getattr(args, "active_sovereign_gate", True))
        active_after = max(0, int(getattr(args, "sovereign_active_after_accepted", 250) or 250))
        wake_best_gap = max(0, int(getattr(args, "sovereign_wake_best_gap", 2) or 2))
        tail_gap_z = max(23, int(getattr(args, "sovereign_tail_gap_z", 32) or 32))
        rescout_tail_gap = max(0, int(getattr(args, "sovereign_rescout_tail_gap", 1) or 1))
        scout_tails = scout.get("accepted_tails", {}) or {}
        rescout_tails = rescout.get("accepted_tails", {}) or {}
        anchor_hits = int(scout_tails.get(f"z{wake_z}", 0) or 0) + int(rescout_tails.get(f"z{wake_z}", 0) or 0)
        force_scout = bool(getattr(args, "bunnyhop_force_scout", False))
        force_wake = bool(getattr(args, "bunnyhop_force_wake", False))
        phase = "BUNNYHOP_SCOUT"
        reason = "collecting_fresh_scout_corpus"
        if force_scout:
            phase = "BUNNYHOP_SCOUT"
            reason = "forced_scout"
        elif force_wake:
            phase = "JANUS_WAKE"
            reason = "forced_wake"
        elif anchor_hits > 0:
            phase = "JANUS_WAKE"
            reason = f"accepted_z{wake_z}_anchor"
        elif int(scout.get("accepted", 0) or 0) >= min_acc:
            phase = "JANUS_WAKE"
            reason = "scout_corpus_gate"
        if active_gate and not force_scout and not force_wake and phase == "BUNNYHOP_SCOUT":
            j_acc = int(janus.get("accepted", 0) or 0)
            j_best = int(janus.get("best_z", 0) or 0)
            m_best = int(mirror.get("best_z", 0) or 0)
            j_tail = int((janus.get("accepted_tails", {}) or {}).get(f"z{tail_gap_z}", 0) or 0)
            m_tail = int((mirror.get("accepted_tails", {}) or {}).get(f"z{tail_gap_z}", 0) or 0)
            mirror_tail_pressure = m_tail > j_tail and (m_tail - j_tail) >= max(1, rescout_tail_gap)
            mirror_best_pressure = wake_best_gap > 0 and m_best >= j_best + wake_best_gap
            if j_acc >= active_after and (mirror_tail_pressure or mirror_best_pressure):
                phase = "JANUS_WAKE"
                reason = (
                    f"active_red_wake_mirror_z{tail_gap_z}_pressure"
                    if mirror_tail_pressure
                    else f"active_red_wake_best_gap_{m_best}-{j_best}"
                )
        if phase == "JANUS_WAKE" and rescout_enabled and not force_wake:
            janus_accepted = int(janus.get("accepted", 0) or 0)
            janus_best_z = int(janus.get("best_z", 0) or 0)
            broad_accepted = int(broad.get("accepted", 0) or 0)
            rescout_accepted = int(rescout.get("accepted", 0) or 0)
            progress_after_wake = max(0, broad_accepted + rescout_accepted)
            cycle_pos = (progress_after_wake - rescout_after) % rescout_cycle
            in_rescout_burst = progress_after_wake >= rescout_after and cycle_pos < rescout_burst
            needs_next_anchor = janus_best_z < rescout_target_z
            if broad_accepted > 0 and needs_next_anchor and in_rescout_burst:
                phase = "JANUS_RESCOUT"
                reason = f"stall_rejump_target_z{rescout_target_z}"
            if active_gate and broad_accepted > 0:
                j_tail = int((janus.get("accepted_tails", {}) or {}).get(f"z{tail_gap_z}", 0) or 0)
                m_tail = int((mirror.get("accepted_tails", {}) or {}).get(f"z{tail_gap_z}", 0) or 0)
                active_tail_gap = (m_tail - j_tail) >= max(1, rescout_tail_gap)
                active_best_gap = wake_best_gap > 0 and int(mirror.get("best_z", 0) or 0) >= int(janus.get("best_z", 0) or 0) + wake_best_gap
                if active_tail_gap or active_best_gap:
                    phase = "JANUS_RESCOUT"
                    reason = (
                        f"active_blue_rescout_mirror_z{tail_gap_z}_gap"
                        if active_tail_gap
                        else "active_blue_rescout_best_gap"
                    )
        return {
            "phase": phase,
            "reason": reason,
            "wake_z": wake_z,
            "rescout_enabled": rescout_enabled,
            "active_sovereign_gate": active_gate,
            "active_after_accepted": active_after,
            "active_tail_gap_z": tail_gap_z,
            "active_wake_best_gap": wake_best_gap,
            "active_rescout_tail_gap": rescout_tail_gap,
            "rescout_after_accepted": rescout_after,
            "rescout_burst_accepted": rescout_burst,
            "rescout_cycle_accepted": rescout_cycle,
            "rescout_target_z": rescout_target_z,
            "scout_min_accepted": min_acc,
            "scout_accepted": int(scout.get("accepted", 0) or 0),
            "scout_checked_mh": float(scout.get("mh", 0.0) or 0.0),
            "scout_best_z": int(scout.get("best_z", 0) or 0),
            "scout_anchor_hits": anchor_hits,
            "rescout_accepted": int(rescout.get("accepted", 0) or 0),
            "rescout_checked_mh": float(rescout.get("mh", 0.0) or 0.0),
            "rescout_best_z": int(rescout.get("best_z", 0) or 0),
            "broad_accepted": int(broad.get("accepted", 0) or 0),
            "broad_best_z": int(broad.get("best_z", 0) or 0),
            "janus_accepted": int(janus.get("accepted", 0) or 0),
            "janus_best_z": int(janus.get("best_z", 0) or 0),
        }

    def _touch_result_row(self, row: Dict[str, Any], checked: int, best_z: int, hps: float) -> None:
        row["checked"] = int(row.get("checked", 0)) + max(0, int(checked or 0))
        row["result_count"] = int(row.get("result_count", 0)) + 1
        row["best_z"] = max(int(row.get("best_z", 0)), int(best_z or 0))
        old_hps = float(row.get("hps_ewma", 0.0) or 0.0)
        row["hps_ewma"] = float(hps or 0.0) if old_hps <= 0 else old_hps * 0.90 + float(hps or 0.0) * 0.10
        tails = row.setdefault("result_best_tails", {f"z{z}": 0 for z in self.TAILS})
        for z in self.TAILS:
            if int(best_z or 0) >= z:
                tails[f"z{z}"] = int(tails.get(f"z{z}", 0)) + 1
        row["last_seen_utc"] = utc_stamp_iso()

    def _touch_submit_row(self, row: Dict[str, Any], zbits: int, accepted: Optional[bool]) -> None:
        if accepted is True:
            row["accepted"] = int(row.get("accepted", 0)) + 1
            row["submitted"] = int(row.get("submitted", 0)) + 1
            row["best_z"] = max(int(row.get("best_z", 0)), int(zbits or 0))
            tails = row.setdefault("accepted_tails", {f"z{z}": 0 for z in self.TAILS})
            for z in self.TAILS:
                if int(zbits or 0) >= z:
                    tails[f"z{z}"] = int(tails.get(f"z{z}", 0)) + 1
        elif accepted is False:
            row["rejected"] = int(row.get("rejected", 0)) + 1
            row["submitted"] = int(row.get("submitted", 0)) + 1
        row["last_seen_utc"] = utc_stamp_iso()

    def set_runtime_state(self, round_id: int, total_hps: float, endurance: Any, proofmind: Any) -> None:
        mode = str(getattr(proofmind, "mode", "") or "")
        cooldown = bool(getattr(endurance, "cooldown", False))
        hps_ewma = float(getattr(endurance, "hps_ewma", 0.0) or 0.0)
        best_hps = float(getattr(endurance, "best_hps_ewma", 0.0) or 0.0)
        load_state = "CLEAN"
        if cooldown:
            load_state = "COOLDOWN"
        elif mode == "SURVIVE":
            load_state = "SURVIVE"
        elif best_hps > 0 and hps_ewma > 0 and hps_ewma < best_hps * 0.92:
            load_state = "DESKTOP_LOAD"
        self.current_round = int(round_id)
        self.current_load_state = load_state
        self.last_runtime = {
            "round": int(round_id),
            "load_state": load_state,
            "total_hps": int(total_hps or 0),
            "hps_ewma": int(hps_ewma or 0),
            "best_hps_ewma": int(best_hps or 0),
            "cooldown": cooldown,
            "proofmind_mode": mode,
        }
        self.atomic_clock.observe_runtime(round_id, total_hps, load_state)

    def observe_result(self, r: Any) -> None:
        group = self.group_name(getattr(r, "lane", "unknown"), getattr(r, "strategy", "unknown"))
        key = self.lane_key(getattr(r, "lane", "unknown"), getattr(r, "strategy", "unknown"), getattr(r, "sector", 0), getattr(r, "cfg_name", "canonical"))
        checked = int(getattr(r, "checked", 0) or 0)
        best_z = int(getattr(r, "best_z", 0) or 0)
        hps = float(getattr(r, "hps", 0.0) or 0.0)
        for row in (self._group_row(group), self._lane_row(key), self._load_row(self.current_load_state)):
            self._touch_result_row(row, checked, best_z, hps)
        self.kombucha_cells.observe_result(r, group, self.current_load_state)
        self.atomic_clock.observe_result(r, group, self.current_load_state)

    def observe_accepted(self, cand: Dict[str, Any]) -> None:
        self._observe_submit(cand, True)

    def observe_rejected(self, cand: Dict[str, Any]) -> None:
        self._observe_submit(cand, False)

    def _observe_submit(self, cand: Dict[str, Any], accepted: bool) -> None:
        group = self.group_name(cand.get("lane", "unknown"), cand.get("strategy"))
        key = self.lane_key(cand.get("lane", "unknown"), cand.get("strategy"), cand.get("sector", 0), cand.get("cfg_name", "canonical"))
        zbits = int(cand.get("zbits", 0) or 0)
        for row in (self._group_row(group), self._lane_row(key), self._load_row(self.current_load_state)):
            self._touch_submit_row(row, zbits, accepted)
        self.kombucha_cells.observe_submit(cand, group, accepted, self.current_load_state)
        self.atomic_clock.observe_submit(cand, group, accepted, self.current_load_state)
        if accepted and zbits >= 30:
            self.events.append({
                "ts_utc": utc_stamp_iso(),
                "group": group,
                "lane_key": key,
                "load_state": self.current_load_state,
                "zbits": zbits,
                "job_id": cand.get("job_id"),
                "nonce_submit_hex": cand.get("nonce_submit_hex"),
            })

    def _decorated_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(row)
        mh = max(0.0, float(out.get("checked", 0) or 0) / 1_000_000.0)
        out["mh"] = mh
        out["accepted_per_mh"] = float(out.get("accepted", 0) or 0) / mh if mh > 0 else 0.0
        accepted_tails = dict(out.get("accepted_tails", {}) or {})
        result_tails = dict(out.get("result_best_tails", {}) or {})
        out["accepted_tails"] = accepted_tails
        out["result_best_tails"] = result_tails
        out["accepted_tail_per_mh"] = {
            k: (float(v or 0) / mh if mh > 0 else 0.0)
            for k, v in accepted_tails.items()
        }
        out["result_best_tail_per_mh"] = {
            k: (float(v or 0) / mh if mh > 0 else 0.0)
            for k, v in result_tails.items()
        }
        return out

    @staticmethod
    def _tail(row: Dict[str, Any], z: int) -> int:
        return int((row.get("accepted_tails", {}) or {}).get(f"z{z}", 0) or 0)

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value or 0.0)))

    def sovereign_triad(self, args: argparse.Namespace, client: Any, endurance: Any, proofmind: Any, janus: Dict[str, Any], mirror: Dict[str, Any]) -> Dict[str, Any]:
        """Active Red/Blue/Gold arbitration for the JANUS half only.

        A9.11 feeds this pressure into the BunnyHop phase gate, never into
        Stratum wire, mirror traversal, submit thresholds, or nonce encoding.
        """
        st = self.bunnyhop_status(args)
        min_acc = max(1, int(getattr(args, "bunnyhop_scout_min_accepted", 500) or 500))
        rescout_target = max(1, int(getattr(args, "bunnyhop_rescout_target_z", 34) or 34))
        submitted = max(1, int(getattr(client, "submitted", 0) or 0))
        rejected = int(getattr(client, "rejected", 0) or 0)
        reject_rate = float(rejected) / float(submitted)
        cooldown = bool(getattr(endurance, "cooldown", False))
        mode = str(getattr(proofmind, "mode", "") or "")
        phase = str(st.get("phase") or "UNKNOWN")
        j_acc = int(janus.get("accepted", 0) or 0)
        m_acc = int(mirror.get("accepted", 0) or 0)
        j_best = int(janus.get("best_z", 0) or 0)
        m_best = int(mirror.get("best_z", 0) or 0)
        j32 = self._tail(janus, 32)
        m32 = self._tail(mirror, 32)
        j33 = self._tail(janus, 33)
        m33 = self._tail(mirror, 33)
        j34 = self._tail(janus, 34)
        m34 = self._tail(mirror, 34)
        small_corpus = j_acc < min_acc or (j_acc + m_acc) < (min_acc * 2)
        stall = phase == "JANUS_RESCOUT" or (j_acc >= min_acc and j_best < rescout_target and j32 <= m32)
        tail_anchor = max(j32 * 0.35 + j33 * 0.55 + j34 * 0.80 + max(0, j_best - 30) * 0.10, 0.0)
        mirror_pressure = 1.0 if (m_best > j_best or m32 > j32 or m33 > j33) else 0.0
        red_score = self._clamp01(
            0.20
            + (0.18 if mode in ("EXPLORE", "CHAOS", "HUNT") else 0.0)
            + min(0.30, tail_anchor)
            + (0.14 if phase in ("BUNNYHOP_SCOUT", "JANUS_WAKE") else 0.0)
            + (0.18 if j32 > m32 or j_best > m_best else 0.0)
            + (0.10 if stall else 0.0)
        )
        blue_score = self._clamp01(
            0.15
            + (0.30 if phase == "JANUS_RESCOUT" else 0.0)
            + (0.22 if cooldown else 0.0)
            + (0.18 if reject_rate > 0.01 else 0.0)
            + (0.16 if stall else 0.0)
            + (0.14 * mirror_pressure)
            + (0.08 if self.current_load_state != "CLEAN" else 0.0)
        )
        gold_score = self._clamp01(
            0.28
            + (0.24 if reject_rate <= 0.01 else 0.0)
            + (0.18 if not cooldown else 0.0)
            + (0.18 if small_corpus else 0.0)
            + (0.10 if abs(red_score - blue_score) < 0.10 else 0.0)
            + (0.08 if j_best == m_best and j32 == m32 else 0.0)
        )
        ranked = sorted(
            (("red_trickster", red_score), ("blue_shadow", blue_score), ("gold_sovereign", gold_score)),
            key=lambda kv: kv[1],
            reverse=True,
        )
        winner, top = ranked[0]
        margin = top - ranked[1][1]
        action = {
            "red_trickster": "RED_PRESSURE_OBSERVE",
            "blue_shadow": "BLUE_RECOVERY_OBSERVE",
            "gold_sovereign": "GOLD_HOLD_OBSERVE",
        }.get(winner, "GOLD_HOLD_OBSERVE")
        if margin < 0.05:
            action = "NEXUS_HOLD_WEAK_MARGIN"
        if reject_rate > 0.03 or cooldown:
            action = "BLUE_RECOVERY_OBSERVE"
            winner = "blue_shadow"
        return {
            "schema": "a9-11-active-sovereign-triad-gate-1",
            "observer_only": False,
            "active_gate": bool(getattr(args, "active_sovereign_gate", True)),
            "scheduler_effect": "janus_half_phase_only",
            "mirror_effect": "none",
            "wire_change_required": False,
            "inputs": {
                "phase": phase,
                "phase_reason": st.get("reason"),
                "janus_accepted": j_acc,
                "mirror_accepted": m_acc,
                "janus_best_z": j_best,
                "mirror_best_z": m_best,
                "janus_z32": j32,
                "mirror_z32": m32,
                "janus_z33": j33,
                "mirror_z33": m33,
                "janus_z34": j34,
                "mirror_z34": m34,
                "reject_rate": reject_rate,
                "cooldown": cooldown,
                "proofmind_mode": mode,
                "load_state": self.current_load_state,
                "small_corpus": small_corpus,
                "stall": stall,
            },
            "scores": {
                "red_trickster": red_score,
                "blue_shadow": blue_score,
                "gold_sovereign": gold_score,
                "margin": margin,
            },
            "decision": {
                "winner": winner,
                "nexus_action": action,
                "meaning": "active phase gate for JANUS half only; mirror and frozen wire remain unchanged",
            },
            "rules": [
                "gold holds on small corpus, weak margin, clean frozen wire, and low reject pressure",
                "blue marks recovery pressure on cooldown, stale/reject pressure, mirror lead, or rescout windows",
                "red marks exploration pressure when JANUS rare-tail telemetry anchors or overtakes mirror",
            ],
        }

    def summary(self, args: argparse.Namespace, client: Any, endurance: Any, proofmind: Any) -> Dict[str, Any]:
        groups = {k: self._decorated_row(v) for k, v in self.groups.items()}
        lanes = [self._decorated_row(v) for v in self.lanes.values()]
        loads = {k: self._decorated_row(v) for k, v in self.load_states.items()}
        lanes.sort(key=lambda r: (int(r.get("best_z", 0)), float(r.get("accepted_per_mh", 0.0)), int(r.get("accepted", 0))), reverse=True)
        scout_raw = self.groups.get("janus_bunnyhop_scout", self._base_row("janus_bunnyhop_scout", "group"))
        rescout_raw = self.groups.get("janus_bunnyhop_rescout", self._base_row("janus_bunnyhop_rescout", "group"))
        broad_raw = self.groups.get("janus_broad_mixture", self._base_row("janus_broad_mixture", "group"))
        janus = self._decorated_row(self._combine_rows("janus_bunnyhop_arm", [scout_raw, rescout_raw, broad_raw]))
        groups["janus_bunnyhop_arm"] = janus
        mirror = groups.get("randomized_traversal_mirror", self._decorated_row(self._base_row("randomized_traversal_mirror")))
        advantage: Dict[str, Any] = {}
        for z in (28, 30, 32, 33, 34, 36, 38):
            key = f"z{z}"
            j = float((janus.get("accepted_tail_per_mh") or {}).get(key, 0.0) or 0.0)
            r = float((mirror.get("accepted_tail_per_mh") or {}).get(key, 0.0) or 0.0)
            advantage[key] = {
                "janus_accepted_per_mh": j,
                "randomized_traversal_mirror_accepted_per_mh": r,
                "ratio": (j / r if r > 0 else None),
            }
        mirror_mh = float(mirror.get("mh", 0.0) or 0.0)
        verdict = "NEED_MORE_MIRROR_CONTROL"
        if mirror_mh >= float(getattr(args, "a9_min_random_control_mh", 250.0) or 250.0):
            verdict = "READY_FOR_COMPARISON"
        triad = self.sovereign_triad(args, client, endurance, proofmind, janus, mirror)
        self.last_triad = triad
        kombucha_cells = self.kombucha_cells.summary(self.current_load_state)
        atomic_clock = self.atomic_clock.snapshot()
        return {
            "version": VERSION,
            "sentinel": SENTINEL,
            "schema": "a9-11-v32-active-triune-sovereign-gate-strict-50-50-accounting-1",
            "written_at_utc": utc_stamp_iso(),
            "fresh_started_at_utc": self.started_at_utc,
            "fresh_session_boundary": {
                "session_id": getattr(args, "fresh_session_id", ""),
                "fresh_started_at_utc": getattr(args, "fresh_started_at_utc", ""),
                "previous_accepted_proof_files": int(getattr(args, "previous_accepted_proof_files", 0) or 0),
                "previous_latest_accepted_proof_mtime_utc": getattr(args, "previous_latest_accepted_proof_mtime_utc", ""),
                "marker": getattr(args, "fresh_session_boundary", ""),
                "archive_marker": getattr(args, "fresh_session_boundary_archive", ""),
                "fresh_filter_rule": "When a run_dir is reused, count fresh accepted-share corpus from marker cutoff, not total proof files.",
            },
            "fresh_uptime_seconds": max(0.0, time.time() - self.started_wall),
            "objective": "Strict 50/50 comparison with Active SovereignGate controlling only the JANUS-half phase; Kombucha Cell Microkernel and Triune Atomic Clock remain telemetry; mirror and frozen wire are unchanged.",
            "wire_change_required": False,
            "engine_behavior_changed": False,
            "scheduler_control_changed": True,
            "scheduler_experiment": {
                "strict_50_50_randomized_traversal_mirror": bool(getattr(args, "strict_50_50_random_control", True)),
                "strict_50_50_random_control": bool(getattr(args, "strict_50_50_random_control", True)),
                "janus_half": "BunnyHop Scout/Wake/ReScout with Active SovereignGate phase control inside JANUS-half only",
                "mirror_half": "random nonce traversal inside JANUS-shaped lane/sector cells",
                "sovereign_triad": "active JANUS-half phase gate; no mirror feedback; no wire feedback",
                "kombucha_cell_microkernel": "observer_only cell pressure; no scheduler feedback",
                "triune_atomic_clock": "observer_only timing/boundary orientation; no scheduler feedback",
                "wire_touched": False,
            },
            "bunnyhop": self.bunnyhop_status(args),
            "sovereign_triad": triad,
            "kombucha_cell_microkernel": kombucha_cells,
            "triune_atomic_clock": atomic_clock,
            "current_runtime": dict(self.last_runtime),
            "health": {
                "submitted": int(getattr(client, "submitted", 0)),
                "accepted": int(getattr(client, "accepted", 0)),
                "rejected": int(getattr(client, "rejected", 0)),
                "reject_rate": float(getattr(client, "rejected", 0)) / max(1.0, float(getattr(client, "submitted", 0))),
                "cooldown": bool(getattr(endurance, "cooldown", False)),
                "proofmind_mode": getattr(proofmind, "mode", ""),
            },
            "strategy_mix": dict(normalized_lane_weights(args)) if "normalized_lane_weights" in globals() else {},
            "groups": groups,
            "advantage_vs_randomized_traversal_mirror": advantage,
            "advantage_vs_random_control": advantage,
            "load_states": loads,
            "top_lanes": lanes[:20],
            "recent_tail_events": list(self.events),
            "comparison_gate": {
                "verdict": verdict,
                "randomized_traversal_mirror_mh": mirror_mh,
                "random_control_mh": mirror_mh,
                "min_randomized_traversal_mirror_mh": float(getattr(args, "a9_min_random_control_mh", 250.0) or 250.0),
                "min_random_control_mh": float(getattr(args, "a9_min_random_control_mh", 250.0) or 250.0),
                "recommended_min_fresh_proofs": int(getattr(args, "a9_min_fresh_proofs", 5000) or 5000),
            },
        }

    def write_dashboard(self, args: argparse.Namespace, client: Any, endurance: Any, proofmind: Any) -> None:
        try:
            atomic_json(self.path, self.summary(args, client, endurance, proofmind))
        except Exception as e:
            log("a9", f"accounting dashboard write failed: {e}")

    def line(self) -> str:
        scout = self._decorated_row(self.groups.get("janus_bunnyhop_scout", self._base_row("janus_bunnyhop_scout")))
        rescout = self._decorated_row(self.groups.get("janus_bunnyhop_rescout", self._base_row("janus_bunnyhop_rescout")))
        janus = self._decorated_row(self._combine_rows("janus_bunnyhop_arm", [
            self.groups.get("janus_bunnyhop_scout", self._base_row("janus_bunnyhop_scout", "group")),
            self.groups.get("janus_bunnyhop_rescout", self._base_row("janus_bunnyhop_rescout", "group")),
            self.groups.get("janus_broad_mixture", self._base_row("janus_broad_mixture", "group")),
        ]))
        mirror = self._decorated_row(self.groups.get("randomized_traversal_mirror", self._base_row("randomized_traversal_mirror")))
        j32 = (janus.get("accepted_tail_per_mh") or {}).get("z32", 0.0)
        r32 = (mirror.get("accepted_tail_per_mh") or {}).get("z32", 0.0)
        st = self.bunnyhop_status(argparse.Namespace())
        triad = self.last_triad.get("decision", {}) if isinstance(self.last_triad, dict) else {}
        komb = self.kombucha_cells.last if isinstance(getattr(self, "kombucha_cells", None), KombuchaCellMicrokernel) else {}
        clock = self.atomic_clock.last if isinstance(getattr(self, "atomic_clock", None), TriuneAtomicClockObserver) else {}
        return (
            f"state={self.current_load_state} "
            f"bunnyhop={st.get('phase')}:{st.get('reason')} scout_acc={scout.get('accepted', 0)} "
            f"rescout_acc={rescout.get('accepted', 0)} "
            f"triad={triad.get('winner', 'n/a')}:{triad.get('nexus_action', 'n/a')} "
            f"komb={komb.get('mode', 'n/a')}:mu={float(komb.get('microkernel_pressure', 0.0) or 0.0):.3f} "
            f"clock={clock.get('state', 'n/a')}:p{clock.get('phase_bucket', 'n/a')}:b={float(clock.get('battery_charge', 0.0) or 0.0):.3f} "
            f"janus_mh={janus.get('mh', 0.0):.1f} mirror_mh={mirror.get('mh', 0.0):.1f} "
            f"janus_z32/MH={j32:.4f} mirror_z32/MH={r32:.4f}"
        )


class WitchHunter:
    """Observer-only dark-tail corpus for rejects and stale/drop boundaries.

    WitchHunter is intentionally not interested in accepted shares. It does not
    choose tasks, raise submit pressure, change gates, or touch wire bytes. It
    records rejected/stale/drop candidates so we can test whether rare tails
    cluster at job-boundary trash that ordinary miners ignore.
    """

    TAILS = (23, 24, 25, 26, 28, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40)

    def __init__(self, dashboard_path: str, events_path: str, min_event_z: int = 23) -> None:
        self.dashboard_path = dashboard_path
        self.events_path = events_path
        self.min_event_z = max(0, int(min_event_z or 23))
        self.started_at_utc = utc_stamp_iso()
        self.started_wall = time.time()
        self.events: Deque[Dict[str, Any]] = deque(maxlen=512)
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.errors: Dict[str, Dict[str, Any]] = {}
        self.highest_z = 0

    @staticmethod
    def group_name(lane: Any, strategy: Any = None) -> str:
        return A99SovereignTriadAccounting.group_name(lane, strategy)

    @staticmethod
    def lane_key(lane: Any, strategy: Any, sector: Any, cfg_name: Any) -> str:
        return A99SovereignTriadAccounting.lane_key(lane, strategy, sector, cfg_name)

    def _base_row(self, name: str, kind: str) -> Dict[str, Any]:
        return {
            "name": name,
            "kind": kind,
            "events": 0,
            "best_z": 0,
            "tails": {f"z{z}": 0 for z in self.TAILS},
            "pool_errors": {},
            "last_seen_utc": "",
        }

    def _row(self, table: Dict[str, Dict[str, Any]], name: str, kind: str) -> Dict[str, Any]:
        if name not in table:
            table[name] = self._base_row(name, kind)
        return table[name]

    def _touch(self, row: Dict[str, Any], zbits: int, pool_error: str) -> None:
        row["events"] = int(row.get("events", 0)) + 1
        row["best_z"] = max(int(row.get("best_z", 0)), int(zbits or 0))
        tails = row.setdefault("tails", {f"z{z}": 0 for z in self.TAILS})
        for z in self.TAILS:
            if int(zbits or 0) >= z:
                tails[f"z{z}"] = int(tails.get(f"z{z}", 0)) + 1
        errs = row.setdefault("pool_errors", {})
        err = str(pool_error or "unknown")
        errs[err] = int(errs.get(err, 0)) + 1
        row["last_seen_utc"] = utc_stamp_iso()

    def observe_dark_candidate(self, cand: Dict[str, Any], source: str, reason: str = "") -> None:
        try:
            zbits = int(cand.get("zbits", 0) or 0)
            self.highest_z = max(self.highest_z, zbits)
            pool_response = cand.get("pool_response") if isinstance(cand.get("pool_response"), dict) else {}
            pool_error = pool_response.get("error") or cand.get("stale_guard_reason") or reason or source
            group = self.group_name(cand.get("lane", "unknown"), cand.get("strategy"))
            lane_key = self.lane_key(cand.get("lane", "unknown"), cand.get("strategy"), cand.get("sector", 0), cand.get("cfg_name", "canonical"))
            for row in (
                self._row(self.rows, group, "group"),
                self._row(self.rows, lane_key, "lane"),
                self._row(self.sources, str(source or "unknown"), "source"),
                self._row(self.errors, str(pool_error or "unknown"), "error"),
            ):
                self._touch(row, zbits, str(pool_error or "unknown"))
            ev = {
                "ts_utc": utc_stamp_iso(),
                "source": str(source or "unknown"),
                "reason": str(reason or ""),
                "pool_error": str(pool_error or "unknown"),
                "group": group,
                "lane_key": lane_key,
                "zbits": zbits,
                "job_id": cand.get("job_id"),
                "job_seq": cand.get("job_seq"),
                "strategy": cand.get("strategy"),
                "lane": cand.get("lane"),
                "sector": cand.get("sector"),
                "worker_id": cand.get("worker_id"),
                "nonce_submit_hex": cand.get("nonce_submit_hex"),
                "display_hash": cand.get("display_hash"),
                "wire_change_required": False,
                "scheduler_effect": "observe_only",
            }
            self.events.append(ev)
            if zbits >= self.min_event_z:
                Path(self.events_path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.events_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
            self.write()
        except Exception as e:
            log("witchhunter", f"observe failed: {e}")

    def observe_rejected(self, cand: Dict[str, Any]) -> None:
        self.observe_dark_candidate(cand, "pool_reject", "pool_response_reject")

    def observe_stale_drop(self, cand: Dict[str, Any], reason: str = "stale_guard_drop") -> None:
        self.observe_dark_candidate(cand, "stale_drop", reason)

    def observe_reconnect_drop(self, cand: Dict[str, Any], reason: str = "reconnect_old_round_drop") -> None:
        self.observe_dark_candidate(cand, "reconnect_drop", reason)

    def _decorated_rows(self, rows: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for row in rows.values():
            r = dict(row)
            r["tails"] = dict(row.get("tails", {}) or {})
            r["pool_errors"] = dict(row.get("pool_errors", {}) or {})
            out.append(r)
        out.sort(key=lambda r: (int(r.get("best_z", 0)), int(r.get("events", 0))), reverse=True)
        return out

    def summary(self) -> Dict[str, Any]:
        janus_rows = [
            self.rows.get("janus_bunnyhop_scout"),
            self.rows.get("janus_bunnyhop_rescout"),
            self.rows.get("janus_broad_mixture"),
        ]
        janus_events = sum(int((r or {}).get("events", 0) or 0) for r in janus_rows)
        mirror_events = int((self.rows.get("randomized_traversal_mirror") or {}).get("events", 0) or 0)
        return {
            "version": VERSION,
            "sentinel": SENTINEL,
            "schema": "a9-11-witchhunter-dark-tail-observer-1",
            "objective": "Observer-only dark-tail corpus for rejected/stale/dropped candidates. Accepted shares are intentionally ignored.",
            "written_at_utc": utc_stamp_iso(),
            "started_at_utc": self.started_at_utc,
            "uptime_seconds": max(0.0, time.time() - self.started_wall),
            "wire_change_required": False,
            "scheduler_effect": "observe_only",
            "submit_pressure_changed": False,
            "accepted_policy": "ignored",
            "dashboard_path": self.dashboard_path,
            "events_path": self.events_path,
            "highest_dark_z": int(self.highest_z),
            "janus_dark_events": janus_events,
            "mirror_dark_events": mirror_events,
            "top_groups": self._decorated_rows(self.rows)[:20],
            "top_sources": self._decorated_rows(self.sources)[:20],
            "top_errors": self._decorated_rows(self.errors)[:20],
            "recent_dark_events": list(self.events)[-50:],
        }

    def write(self) -> None:
        try:
            atomic_json(self.dashboard_path, self.summary())
        except Exception as e:
            log("witchhunter", f"dashboard write failed: {e}")

    def line(self) -> str:
        s = self.summary()
        return (
            f"dark_z={s.get('highest_dark_z', 0)} "
            f"janus_dark={s.get('janus_dark_events', 0)} mirror_dark={s.get('mirror_dark_events', 0)} "
            f"events={self.events_path}"
        )


class DualLockMemory:
    """V31 scheduler-only Dual Lock lane memory.

    Proven A4 pattern from Codex report:
      - sector 6 lock: zim_reverse/s6 and linear/s6
      - sector 11 deep-tail probe: knight/s11
    No wire/header/submit byte is changed here.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.counts = {"linear_s6": 0, "zim_reverse_s6": 0, "knight_s11": 0}
        self.accepted = {"linear_s6": 0, "zim_reverse_s6": 0, "knight_s11": 0}
        self.best_z = {"linear_s6": 0, "zim_reverse_s6": 0, "knight_s11": 0}
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                for name in ("counts", "accepted", "best_z"):
                    if isinstance(obj.get(name), dict):
                        getattr(self, name).update(obj[name])
        except FileNotFoundError:
            pass
        except Exception as e:
            log("v31", f"dual lock memory load skipped: {e}")

    def choose(self, rng: random.Random, cfg: BuildConfig, linear_w: float = 0.40, zim_w: float = 0.35, knight_w: float = 0.25) -> Tuple[str, int, BuildConfig, str]:
        total = max(1e-9, float(linear_w) + float(zim_w) + float(knight_w))
        x = rng.random() * total
        if x < float(linear_w):
            self.counts["linear_s6"] = int(self.counts.get("linear_s6", 0)) + 1
            return "linear", 6, cfg, "dual_lock:linear_s6"
        if x < float(linear_w) + float(zim_w):
            self.counts["zim_reverse_s6"] = int(self.counts.get("zim_reverse_s6", 0)) + 1
            return "zim_reverse", 6, cfg, "dual_lock:zim_reverse_s6"
        self.counts["knight_s11"] = int(self.counts.get("knight_s11", 0)) + 1
        return "knight", 11, cfg, "dual_lock:knight_s11"

    def observe_accepted(self, cand: Dict[str, Any]) -> None:
        lane = str(cand.get("lane", ""))
        if not lane.startswith("dual_lock:"):
            return
        k = lane.split(":", 1)[1]
        self.accepted[k] = int(self.accepted.get(k, 0)) + 1
        self.best_z[k] = max(int(self.best_z.get(k, 0)), int(cand.get("zbits", 0) or 0))
        self.save()

    def save(self) -> None:
        try:
            atomic_json(self.path, {
                "version": VERSION,
                "sentinel": SENTINEL,
                "schema": "v31-dual-lock-memory-1",
                "updated_at_utc": utc_stamp_iso(),
                "counts": self.counts,
                "accepted": self.accepted,
                "best_z": self.best_z,
                "wire_change_required": False,
            })
        except Exception as e:
            log("v31", f"dual lock memory save failed: {e}")

    def line(self) -> str:
        return f"linear_s6={self.counts.get('linear_s6',0)}/acc{self.accepted.get('linear_s6',0)} zim_s6={self.counts.get('zim_reverse_s6',0)}/acc{self.accepted.get('zim_reverse_s6',0)} knight_s11={self.counts.get('knight_s11',0)}/acc{self.accepted.get('knight_s11',0)}"


def broad_mixture_lane_weights(args: argparse.Namespace) -> List[Tuple[str, float]]:
    """Original A9 JANUS broad-mixture proportions, excluding the mirror half."""
    vals = [
        ("linear_proof", max(0.0, float(getattr(args, "linear_proof_weight", 35.0)))),
        ("janus_dispatcher", max(0.0, float(getattr(args, "janus_weight", 25.0)))),
        ("dual_lock", max(0.0, float(getattr(args, "dual_lock_weight", 20.0))) if getattr(args, "enable_dual_lock_lane", True) else 0.0),
        ("zim_reverse_s6", max(0.0, float(getattr(args, "zim_s6_weight", 15.0)))),
    ]
    total = sum(v for _, v in vals)
    if total <= 0:
        vals = [("janus_dispatcher", 1.0)]
        total = 1.0
    return [(k, v / total) for k, v in vals if v > 0]


def normalized_lane_weights(args: argparse.Namespace) -> List[Tuple[str, float]]:
    if bool(getattr(args, "strict_50_50_random_control", True)):
        broad = broad_mixture_lane_weights(args)
        return [(k, w * 0.50) for k, w in broad] + [("randomized_traversal_mirror", 0.50)]
    vals = [
        ("linear_proof", max(0.0, float(getattr(args, "linear_proof_weight", 35.0)))),
        ("janus_dispatcher", max(0.0, float(getattr(args, "janus_weight", 25.0)))),
        ("dual_lock", max(0.0, float(getattr(args, "dual_lock_weight", 20.0))) if getattr(args, "enable_dual_lock_lane", True) else 0.0),
        ("zim_reverse_s6", max(0.0, float(getattr(args, "zim_s6_weight", 15.0)))),
        ("randomized_traversal_mirror", max(0.0, float(getattr(args, "random_baseline_weight", 5.0)))),
    ]
    total = sum(v for _, v in vals)
    if total <= 0:
        vals = [("janus_dispatcher", 1.0)]
        total = 1.0
    return [(k, v / total) for k, v in vals if v > 0]


def pick_lane_from_weights(weights: List[Tuple[str, float]], rng: random.Random) -> str:
    if not weights:
        return "janus_dispatcher"
    x = rng.random()
    acc = 0.0
    lane = weights[-1][0]
    for k, w in weights:
        acc += w
        if x <= acc:
            lane = k
            break
    return lane


def pick_dual_lock_branch(rng: random.Random, linear_w: float, zim_w: float, knight_w: float) -> str:
    total = max(1e-9, float(linear_w) + float(zim_w) + float(knight_w))
    x = rng.random() * total
    if x < float(linear_w):
        return "linear_s6"
    if x < float(linear_w) + float(zim_w):
        return "zim_reverse_s6"
    return "knight_s11"


def choose_randomized_traversal_mirror_task(
    args: argparse.Namespace,
    rng: random.Random,
    cfg: BuildConfig,
    round_id: int,
    worker_id: int,
    lane_prefix: str = "random_mirror",
) -> Tuple[str, int, BuildConfig, str]:
    """Random nonce traversal inside JANUS-shaped lane/sector scaffolds.

    This is the shaped-random control: it borrows the traversal shape from JANUS, then
    removes JANUS strategy choice, ProofMind steering, and DualLock memory
    mutation. The only hash strategy returned here is random.
    """
    lane = pick_lane_from_weights(broad_mixture_lane_weights(args), rng)

    if lane == "linear_proof":
        sector = (int(round_id) * 3 + int(worker_id)) % SECTORS
        return "random", sector, cfg, f"{lane_prefix}:linear_proof"

    if lane == "dual_lock":
        branch = pick_dual_lock_branch(
            rng,
            getattr(args, "dual_lock_linear_s6_weight", 40.0),
            getattr(args, "dual_lock_zim_s6_weight", 35.0),
            getattr(args, "dual_lock_knight_s11_weight", 25.0),
        )
        if branch == "knight_s11":
            return "random", 11, cfg, f"{lane_prefix}:dual_lock_knight_s11"
        if branch == "zim_reverse_s6":
            return "random", 6, cfg, f"{lane_prefix}:dual_lock_zim_reverse_s6"
        return "random", 6, cfg, f"{lane_prefix}:dual_lock_linear_s6"

    if lane == "zim_reverse_s6":
        return "random", 6, cfg, f"{lane_prefix}:zim_reverse_s6"

    sector = (int(round_id) * 7 + int(worker_id) * 5 + rng.randrange(SECTORS)) % SECTORS
    return "random", sector, cfg, f"{lane_prefix}:janus_dispatcher"


def choose_janus_bunnyhop_rescout_task(
    args: argparse.Namespace,
    proofmind: JanusProofMind,
    endurance: Any,
    memory: KombuchaMemory,
    rng: random.Random,
    cfgs: List[BuildConfig],
    cfg: BuildConfig,
    round_id: int,
    worker_id: int,
) -> Tuple[str, int, BuildConfig, str]:
    """JANUS-shaped re-scout after wake stalls.

    This is deliberately not the mirror. It may use randomness to choose a
    JANUS branch, but the returned strategies are the JANUS strategy set
    rather than pure random traversal.
    """
    lane = pick_lane_from_weights(broad_mixture_lane_weights(args), rng)

    if lane == "linear_proof":
        sector = (int(round_id) * 3 + int(worker_id)) % SECTORS
        return "linear", sector, cfg, "janus_bunnyhop_rescout:linear_proof"

    if lane == "dual_lock":
        branch = pick_dual_lock_branch(
            rng,
            getattr(args, "dual_lock_linear_s6_weight", 40.0),
            getattr(args, "dual_lock_zim_s6_weight", 35.0),
            getattr(args, "dual_lock_knight_s11_weight", 25.0),
        )
        if branch == "knight_s11":
            return "knight", 11, cfg, "janus_bunnyhop_rescout:dual_lock_knight_s11"
        if branch == "zim_reverse_s6":
            return "zim_reverse", 6, cfg, "janus_bunnyhop_rescout:dual_lock_zim_reverse_s6"
        return "linear", 6, cfg, "janus_bunnyhop_rescout:dual_lock_linear_s6"

    if lane == "zim_reverse_s6":
        return "zim_reverse", 6, cfg, "janus_bunnyhop_rescout:zim_reverse_s6"

    st, sec, cfg2 = proofmind.choose(memory, rng, cfgs, round_id, worker_id)
    if not getattr(args, "disable_endurance_oracle", False):
        st, sec, cfg2 = endurance.maybe_adjust_choice(st, sec, cfg2, rng, cfgs)
    return st, sec, cfg2, "janus_bunnyhop_rescout:janus_dispatcher"


def bunnyhop_phase(args: argparse.Namespace) -> str:
    acct = globals().get("A9_ACCOUNTING")
    if acct is not None and hasattr(acct, "bunnyhop_status"):
        try:
            return str(acct.bunnyhop_status(args).get("phase") or "BUNNYHOP_SCOUT")
        except Exception:
            return "BUNNYHOP_SCOUT"
    if bool(getattr(args, "bunnyhop_force_wake", False)):
        return "JANUS_WAKE"
    return "BUNNYHOP_SCOUT"


def choose_v31_task(args: argparse.Namespace, proofmind: JanusProofMind, endurance: Any, memory: KombuchaMemory, dual_lock: DualLockMemory, rng: random.Random, cfgs: List[BuildConfig], round_id: int, worker_id: int) -> Tuple[str, int, BuildConfig, str]:
    cfg = next((c for c in cfgs if c.name == "canonical"), cfgs[0])
    if bool(getattr(args, "strict_50_50_random_control", True)):
        # Strict comparison mode: half of equal-size worker tasks are the always
        # randomized traversal mirror. The JANUS half starts as BunnyHop Scout
        # and wakes into the original broad JANUS mixture after a fresh anchor.
        # With an odd worker count the parity flips every round, so checked MH
        # stays balanced over time.
        if ((int(round_id) + int(worker_id)) & 1) == 0:
            return choose_randomized_traversal_mirror_task(args, rng, cfg, round_id, worker_id)
        phase = bunnyhop_phase(args)
        if phase == "BUNNYHOP_SCOUT":
            return choose_randomized_traversal_mirror_task(args, rng, cfg, round_id, worker_id, lane_prefix="janus_bunnyhop_scout")
        if phase == "JANUS_RESCOUT":
            return choose_janus_bunnyhop_rescout_task(args, proofmind, endurance, memory, rng, cfgs, cfg, round_id, worker_id)
        lane = pick_lane_from_weights(broad_mixture_lane_weights(args), rng)
    else:
        lane = pick_lane_from_weights(normalized_lane_weights(args), rng)

    if lane == "linear_proof":
        # A1 proved best accepted/MH. Spread linear across all sectors for proof farming.
        return "linear", (round_id * 3 + worker_id) % SECTORS, cfg, "linear_proof"

    if lane == "dual_lock":
        return dual_lock.choose(rng, cfg, getattr(args, "dual_lock_linear_s6_weight", 40.0), getattr(args, "dual_lock_zim_s6_weight", 35.0), getattr(args, "dual_lock_knight_s11_weight", 25.0))

    if lane == "zim_reverse_s6":
        return "zim_reverse", 6, cfg, "zim_reverse_s6"

    if lane == "randomized_traversal_mirror":
        return choose_randomized_traversal_mirror_task(args, rng, cfg, round_id, worker_id)

    # Janus dispatcher lane retains V29/V30 adaptive behavior.
    st, sec, cfg2 = proofmind.choose(memory, rng, cfgs, round_id, worker_id)
    if not getattr(args, "disable_endurance_oracle", False):
        st, sec, cfg2 = endurance.maybe_adjust_choice(st, sec, cfg2, rng, cfgs)
    return st, sec, cfg2, "janus_dispatcher"


class EnduranceOracle:
    """V31 endurance layer.

    This oracle never changes Stratum wire bytes or block-header construction. It only
    regulates how much work is launched, which scheduler choices receive CPU time, and
    what dashboard/summary artifacts are written for long unattended runs.
    """

    def __init__(
        self,
        dashboard_path: str,
        max_batch_factor: float = 1.35,
        min_batch_factor: float = 0.70,
        cooldown_drop_ratio: float = 0.82,
        prune_after_observations: int = 160,
        prune_min_best_z: int = 24,
        sector_lock: bool = True,
    ) -> None:
        self.dashboard_path = dashboard_path
        self.max_batch_factor = max(0.20, float(max_batch_factor))
        self.min_batch_factor = max(0.10, float(min_batch_factor))
        self.cooldown_drop_ratio = min(0.99, max(0.40, float(cooldown_drop_ratio)))
        self.prune_after_observations = max(10, int(prune_after_observations))
        self.prune_min_best_z = max(1, int(prune_min_best_z))
        self.sector_lock = bool(sector_lock)
        self.started_wall = time.time()
        self.hps_ewma = 0.0
        self.best_hps_ewma = 0.0
        self.recent_hps: Deque[float] = deque(maxlen=24)
        self.recent_acc: Deque[int] = deque(maxlen=24)
        self.recent_rej: Deque[int] = deque(maxlen=24)
        self.total_checked = 0
        self.cooldown = False
        self.cooldown_rounds_left = 0
        self.last_factor = 1.0
        self.last_reason = "warmup"
        self.pruned_replacements = 0
        self.sector_lock_hits = 0

    def _top_combo(self) -> Optional[Dict[str, Any]]:
        rows = top_strategy_scoreboard(1)
        return rows[0] if rows else None

    def accepted_per_mh(self, accepted: int) -> float:
        if self.total_checked <= 0:
            return 0.0
        return float(accepted) * 1_000_000.0 / float(self.total_checked)

    def observe_round(self, round_id: int, total_checked: int, total_hps: float, accepted: int, rejected: int, best_z: int, proofmind: JanusProofMind) -> None:
        self.total_checked += max(0, int(total_checked or 0))
        hps = max(0.0, float(total_hps or 0.0))
        self.recent_hps.append(hps)
        self.recent_acc.append(int(accepted))
        self.recent_rej.append(int(rejected))
        alpha = 0.12
        if self.hps_ewma <= 0:
            self.hps_ewma = hps
        else:
            self.hps_ewma = (1.0 - alpha) * self.hps_ewma + alpha * hps
        self.best_hps_ewma = max(self.best_hps_ewma, self.hps_ewma)

        reject_rate = float(rejected) / max(1.0, float(accepted + rejected))
        hps_drop = self.best_hps_ewma > 0 and self.hps_ewma < self.best_hps_ewma * self.cooldown_drop_ratio
        if reject_rate > 0.02 or hps_drop:
            self.cooldown = True
            self.cooldown_rounds_left = max(self.cooldown_rounds_left, 8)
            self.last_reason = "cooldown:hps_drop" if hps_drop else "cooldown:reject_rate"
            # Push only scheduler instinct, not wire. SURVIVE reduces batch_factor and risk.
            if proofmind.mode != "SURVIVE":
                proofmind.mode = "SURVIVE"
                proofmind.mode_strength = max(proofmind.mode_strength, 0.65)
            proofmind.pso["batch_pressure"] = max(self.min_batch_factor, float(proofmind.pso.get("batch_pressure", 1.0)) * 0.94)
        elif self.cooldown_rounds_left > 0:
            self.cooldown_rounds_left -= 1
            self.last_reason = "cooldown:recovering"
            if self.cooldown_rounds_left <= 0:
                self.cooldown = False
        else:
            self.last_reason = "stable"

    def factor_multiplier(self, proofmind: JanusProofMind) -> float:
        base = float(proofmind.batch_factor())
        cap = self.max_batch_factor
        floor = self.min_batch_factor
        if self.cooldown:
            cap = min(cap, max(floor, 0.95))
        factor = max(floor, min(cap, base))
        self.last_factor = factor
        return factor

    def should_prune(self, strategy: str, sector: int, cfg_name: str, rng: random.Random) -> bool:
        if rng.random() > 0.72:
            return False
        e = STRATEGY_SCOREBOARD.get(scoreboard_key(strategy, sector, cfg_name))
        if not e:
            return False
        return (
            int(e.get("observations", 0)) >= self.prune_after_observations
            and int(e.get("accepted", 0)) <= 0
            and int(e.get("best_z", 0)) < self.prune_min_best_z
        )

    def replacement_choice(self, rng: random.Random, cfgs: List[BuildConfig]) -> Tuple[str, int, BuildConfig]:
        cfg = next((c for c in cfgs if c.name == "canonical"), cfgs[0])
        top = self._top_combo()
        if top:
            st = str(top.get("strategy") or "zim_reverse")
            sec = int(top.get("sector") or 0) % SECTORS
            if self.sector_lock and st in ("zim_reverse", "zim_bandit") and rng.random() < 0.80:
                sec = 6
                self.sector_lock_hits += 1
            return st, sec, cfg
        return "zim_reverse", 6 if self.sector_lock else rng.randrange(SECTORS), cfg

    def maybe_adjust_choice(self, st: str, sec: int, cfg: BuildConfig, rng: random.Random, cfgs: List[BuildConfig]) -> Tuple[str, int, BuildConfig]:
        if self.should_prune(st, sec, cfg.name, rng):
            self.pruned_replacements += 1
            return self.replacement_choice(rng, cfgs)
        # Zim sector lock: if the live scoreboard proves sector 6, keep more Zim work there.
        top = self._top_combo()
        if self.sector_lock and top and str(top.get("strategy")) in ("zim_reverse", "zim_bandit"):
            if st in ("zim_reverse", "zim_bandit") and rng.random() < 0.55:
                self.sector_lock_hits += 1
                return st, 6, cfg
        return st, sec, cfg

    def dashboard(self, args: argparse.Namespace, client: Any, round_id: int, total_hps: float, best_z: int, proofmind: JanusProofMind) -> Dict[str, Any]:
        uptime = max(0.0, time.time() - self.started_wall)
        top = top_strategy_scoreboard(10)
        return {
            "version": VERSION,
            "sentinel": SENTINEL,
            "schema": "v31-endurance-dashboard-1",
            "written_at_utc": utc_stamp_iso(),
            "round": int(round_id),
            "uptime_seconds": uptime,
            "host": f"{getattr(args, 'host', '')}:{getattr(args, 'port', '')}",
            "user": getattr(args, "user", ""),
            "submitted": int(getattr(client, "submitted", 0)),
            "accepted": int(getattr(client, "accepted", 0)),
            "rejected": int(getattr(client, "rejected", 0)),
            "reject_rate": float(getattr(client, "rejected", 0)) / max(1.0, float(getattr(client, "submitted", 0))),
            "accepted_per_mh": self.accepted_per_mh(int(getattr(client, "accepted", 0))),
            "best_z": int(best_z),
            "hps_last": int(total_hps or 0),
            "hps_ewma": int(self.hps_ewma or 0),
            "best_hps_ewma": int(self.best_hps_ewma or 0),
            "endurance": {
                "cooldown": self.cooldown,
                "cooldown_rounds_left": self.cooldown_rounds_left,
                "last_batch_factor": self.last_factor,
                "last_reason": self.last_reason,
                "pruned_replacements": self.pruned_replacements,
                "sector_lock_hits": self.sector_lock_hits,
                "total_checked": self.total_checked,
            },
            "proofmind": {
                "mode": proofmind.mode,
                "mode_strength": proofmind.mode_strength,
                "hunger": proofmind.hunger,
                "best_z_seen": proofmind.best_z_seen,
                "best_combo": proofmind.best_combo,
                "elite": len(proofmind.elite),
                "bad": len(proofmind.bad),
            },
            "top_strategy_scoreboard": top,
            "wire_lock": {
                "nonce_submit_big_endian_uint32_hex": True,
                "nonce_header_little_endian_bytes": True,
                "prevhash_word_reverse": True,
                "extranonce2_little_endian": True,
            },
            "v31_duallock_oracle": {
                "enabled": bool(getattr(args, "enable_dual_lock_lane", True)),
                "strategy_mix": dict(normalized_lane_weights(args)) if "normalized_lane_weights" in globals() else {},
                "strategy_rates_path": getattr(args, "strategy_rates", ""),
                "tail_events_path": getattr(args, "tail_events", ""),
                "tail_tracker": V31_TAIL_TRACKER.summary() if V31_TAIL_TRACKER is not None else {},
                "ratebook_top": V31_RATEBOOK.rows_list()[:10] if V31_RATEBOOK is not None else [],
                "dual_lock_memory": {
                    "path": getattr(args, "dual_lock_memory", ""),
                    "line": V31_DUALLOCK_MEMORY.line() if V31_DUALLOCK_MEMORY is not None else "",
                },
                "wire_change_required": False,
            },
            "v32_network_recovery": V32_NETWORK_RECOVERY.snapshot(client) if V32_NETWORK_RECOVERY is not None else {},
            "v32_tachyon_backlog": {
                "tachyon_enabled": False,
                "tail_density_oracle": "backlog",
                "resonance_bandit": "backlog",
                "entropy_gate": "backlog",
                "memory_matrix": "backlog",
                "wire_change_required": False,
            },
        }

    def write_dashboard(self, args: argparse.Namespace, client: Any, round_id: int, total_hps: float, best_z: int, proofmind: JanusProofMind) -> None:
        try:
            atomic_json(self.dashboard_path, self.dashboard(args, client, round_id, total_hps, best_z, proofmind))
        except Exception as e:
            try:
                log("endurance", f"dashboard write failed: {e}")
            except Exception:
                pass

    def line(self) -> str:
        return (
            f"hps_ewma~{self.hps_ewma:,.0f} best_hps~{self.best_hps_ewma:,.0f} "
            f"factor={self.last_factor:.2f} cooldown={self.cooldown} reason={self.last_reason} "
            f"acc/MH={self.accepted_per_mh(int(SESSION_STATE.get('accepted', 0) or 0)):.4f} "
            f"pruned={self.pruned_replacements} sector_lock={self.sector_lock_hits}"
        )


def sovereign_triad_candidate_labels(cand: Dict[str, Any]) -> Dict[str, Any]:
    lane = str(cand.get("lane", "") or "")
    strategy = str(cand.get("strategy", "") or "")
    group = A99SovereignTriadAccounting.group_name(lane, strategy)
    face = "gold_sovereign"
    role = "stability_hold"
    if group == "janus_bunnyhop_scout":
        face = "red_trickster"
        role = "exploration_scout"
    elif group == "janus_bunnyhop_rescout":
        face = "blue_shadow"
        role = "recovery_rejump"
    elif group == "janus_broad_mixture":
        face = "nexus_janus_mix"
        role = "wake_broad_mixture"
    elif group == "randomized_traversal_mirror":
        face = "mirror_control"
        role = "randomized_traversal_control"
    return {
        "schema": "a9-11-sovereign-triad-candidate-label-1",
        "observer_only": True,
        "scheduler_effect": "none",
        "wire_change_required": False,
        "group": group,
        "triad_face": face,
        "nexus_role": role,
        "lane": lane,
        "strategy": strategy,
        "sector": cand.get("sector"),
        "zbits": cand.get("zbits"),
    }


def kombucha_cell_candidate_labels(cand: Dict[str, Any]) -> Dict[str, Any]:
    nuclei = 12
    try:
        acct = globals().get("A9_ACCOUNTING")
        cells = getattr(acct, "kombucha_cells", None)
        if cells is not None:
            nuclei = int(getattr(cells, "nuclei", nuclei) or nuclei)
    except Exception:
        nuclei = 12
    return KombuchaCellMicrokernel.label_for_candidate(cand, nuclei)


def triune_atomic_clock_candidate_labels(cand: Dict[str, Any]) -> Dict[str, Any]:
    lane = str(cand.get("lane", "") or "")
    strategy = str(cand.get("strategy", "") or "")
    group = A99SovereignTriadAccounting.group_name(lane, strategy)
    snapshot: Dict[str, Any] = {
        "schema": "a9-11-triune-atomic-clock-observer-1",
        "enabled": False,
        "observer_only": True,
        "scheduler_effect": "none",
        "wire_change_required": False,
        "wire_hash_function": "double_sha256",
        "state": "UNAVAILABLE",
    }
    try:
        acct = globals().get("A9_ACCOUNTING")
        clock = getattr(acct, "atomic_clock", None)
        if clock is not None:
            snapshot = dict(clock.snapshot())
    except Exception:
        pass
    return {
        "schema": "a9-11-triune-atomic-clock-candidate-label-1",
        "observer_only": True,
        "scheduler_effect": "none",
        "wire_change_required": False,
        "wire_hash_function": "double_sha256",
        "third_face_policy": "measurement_axis_only",
        "group": group,
        "lane": lane,
        "strategy": strategy,
        "sector": cand.get("sector"),
        "zbits": cand.get("zbits"),
        "triune_axes": ["hash_result", "traversal_path", "time_entropy_phase"],
        "janus_particle_boundary": {
            "fixed_chemistry": "frozen wire",
            "orientation": "candidate observed at pool/job/time boundary",
            "all_surfaces_contact_medium": True,
        },
        "clock_snapshot": {
            "state": snapshot.get("state"),
            "clock_phase": snapshot.get("clock_phase"),
            "phase_bucket": snapshot.get("phase_bucket"),
            "battery_charge": snapshot.get("battery_charge"),
            "purity_score": snapshot.get("purity_score"),
            "timing_jitter_ema_ms": snapshot.get("timing_jitter_ema_ms"),
            "hardware_entropy_sample": snapshot.get("hardware_entropy_sample"),
        },
    }


def proof_filename(cand: Dict[str, Any]) -> str:
    z = int(cand.get("zbits", 0))
    nonce = int(cand.get("nonce_int", 0)) & 0xFFFFFFFF
    job_id = str(cand.get("job_id", "job"))[:16]
    return f"accepted_{utc_stamp_file()}_z{z}_nonce0x{nonce:08x}_job{job_id}.json"


def build_proof(cand: Dict[str, Any]) -> Dict[str, Any]:
    """Create an audit-friendly immutable proof snapshot for one accepted share."""
    return {
        "proof_type": "accepted_share",
        "created_at_utc": utc_stamp_iso(),
        "version": VERSION,
        "sentinel": SENTINEL,
        "miner": {
            "lane": cand.get("lane"),
            "strategy": cand.get("strategy"),
            "sector": cand.get("sector"),
            "worker_id": cand.get("worker_id"),
            "round_id": cand.get("round_id"),
            "cfg_name": cand.get("cfg_name"),
            "cfg": cand.get("cfg"),
            "wire_lock": {
                "nonce_submit_big_endian_uint32_hex": True,
                "nonce_header_little_endian_bytes": True,
                "prevhash_word_reverse": True,
                "extranonce2_endian": "little",
                "noncanonical_submit": False,
            },
        },
        "observer_labels": {
            "sovereign_triad": sovereign_triad_candidate_labels(cand),
            "kombucha_cell_microkernel": kombucha_cell_candidate_labels(cand),
            "triune_atomic_clock": triune_atomic_clock_candidate_labels(cand),
        },
        "pool": {
            "pool_diff": cand.get("pool_diff"),
            "pool_z_approx": cand.get("pool_z_approx"),
            "pool_target_hex": cand.get("pool_target_hex"),
            "pool_response": cand.get("pool_response"),
        },
        "job": cand.get("job") or {
            "job_id": cand.get("job_id"),
            "prevhash": cand.get("prevhash"),
            "coinb1": cand.get("coinb1"),
            "coinb2": cand.get("coinb2"),
            "merkle_branch": cand.get("merkle_branch"),
            "version": cand.get("version_hex"),
            "nbits": cand.get("nbits"),
            "ntime": cand.get("ntime"),
            "clean": cand.get("clean"),
            "seq": cand.get("job_seq"),
        },
        "nonce": {
            "int": cand.get("nonce_int"),
            "int_hex": f"{int(cand.get('nonce_int', 0)) & 0xFFFFFFFF:08x}",
            "header_le_hex": cand.get("nonce_header_hex"),
            "submit_be_hex": cand.get("nonce_submit_hex"),
            "extranonce1": cand.get("extranonce1"),
            "extranonce2": cand.get("extranonce2"),
            "ntime": cand.get("ntime"),
        },
        "header": {
            "hex": cand.get("header_hex"),
            "len": cand.get("header_len"),
            "coinbase_hash_raw": cand.get("coinbase_hash_raw"),
            "merkle_root_raw": cand.get("merkle_root_raw"),
            "merkle_root_header": cand.get("merkle_root_header"),
        },
        "hash": {
            "double_sha256_raw_hex": cand.get("raw_hash_hex"),
            "double_sha256_display_hex": cand.get("display_hash"),
            "hash_int_le_hex": cand.get("hash_int_le_hex"),
            "zbits": cand.get("zbits"),
            "target_pass": cand.get("target_pass"),
        },
        "submit": {
            "params": cand.get("submit_params"),
            "mirror_ok": cand.get("mirror_ok"),
            "mirror_reason": cand.get("mirror_reason"),
            "nonce_wire_rule": cand.get("nonce_wire_rule"),
        },
        "raw_candidate": cand,
    }


def append_accepted_index(proof_dir: str, proof_path: str, cand: Dict[str, Any]) -> None:
    index_path = os.path.join(proof_dir, "accepted_index.json")
    try:
        idx: Dict[str, Any]
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            idx = old if isinstance(old, dict) else {"accepted": []}
        else:
            idx = {"version": VERSION, "sentinel": SENTINEL, "accepted": []}
        entry = {
            "created_at_utc": utc_stamp_iso(),
            "proof_path": proof_path,
            "job_id": cand.get("job_id"),
            "zbits": cand.get("zbits"),
            "nonce_submit_hex": cand.get("nonce_submit_hex"),
            "nonce_int_hex": f"{int(cand.get('nonce_int', 0)) & 0xFFFFFFFF:08x}",
            "hash": cand.get("display_hash"),
            "pool_diff": cand.get("pool_diff"),
            "lane": cand.get("lane"),
            "strategy": cand.get("strategy"),
            "sector": cand.get("sector"),
            "worker_id": cand.get("worker_id"),
            "cfg_name": cand.get("cfg_name"),
            "observer_labels": {
                "sovereign_triad": sovereign_triad_candidate_labels(cand),
                "kombucha_cell_microkernel": kombucha_cell_candidate_labels(cand),
                "triune_atomic_clock": triune_atomic_clock_candidate_labels(cand),
            },
        }
        idx.setdefault("accepted", []).append(entry)
        idx["count"] = len(idx.get("accepted", []))
        idx["updated_at_utc"] = utc_stamp_iso()
        atomic_json(index_path, idx)
    except Exception as e:
        log("proof", f"accepted_index update failed: {e}")


def write_v31_proof_registry_artifacts(proof_dir: str, proof_path: str, cand: Dict[str, Any], proof: Dict[str, Any]) -> None:
    """Write Janus meta-registry layers without changing the accepted proof format."""
    try:
        # raw_accepted: exact accepted proof snapshot.
        raw_dir = os.path.join(proof_dir, "raw_accepted")
        reg_dir = os.path.join(proof_dir, "registry")
        inf_dir = os.path.join(proof_dir, "inferred")
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(reg_dir, exist_ok=True)
        os.makedirs(inf_dir, exist_ok=True)
        base = os.path.basename(proof_path)
        atomic_json(os.path.join(raw_dir, base), proof)
        registry_event = {
            "schema": PROOFMIND_SCHEMA_VERSION,
            "kind": "accepted_share",
            "created_at_utc": utc_stamp_iso(),
            "empirical_layer": {
                "proof_path": proof_path,
                "job_id": cand.get("job_id"),
                "zbits": cand.get("zbits"),
                "nonce_submit_hex": cand.get("nonce_submit_hex"),
                "display_hash": cand.get("display_hash"),
                "pool_diff": cand.get("pool_diff"),
                "strategy": cand.get("strategy"),
                "sector": cand.get("sector"),
                "cfg_name": cand.get("cfg_name"),
                "pool_response": cand.get("pool_response"),
                "observer_labels": {
                    "sovereign_triad": sovereign_triad_candidate_labels(cand),
                    "kombucha_cell_microkernel": kombucha_cell_candidate_labels(cand),
                    "triune_atomic_clock": triune_atomic_clock_candidate_labels(cand),
                },
            },
            "hypothesis_layer": {},
            "correlation_analysis": {},
            "meta_rules": {"wire_bytes_frozen_from_v26": True},
        }
        atomic_json(os.path.join(reg_dir, "accepted_" + base), registry_event)
        inferred = {
            "schema": PROOFMIND_SCHEMA_VERSION,
            "kind": "accepted_share_inference",
            "created_at_utc": utc_stamp_iso(),
            "observed": {
                "zbits": cand.get("zbits"),
                "strategy": cand.get("strategy"),
                "sector": cand.get("sector"),
                "cfg_name": cand.get("cfg_name"),
            },
            "inferred": {
                "rarity_signal_only": True,
                "sha_direction_claim": False,
                "scheduler_reward_hint": "accepted + high z increases future allocation to this combo",
                "sovereign_triad": sovereign_triad_candidate_labels(cand),
                "kombucha_cell_microkernel": kombucha_cell_candidate_labels(cand),
                "triune_atomic_clock": triune_atomic_clock_candidate_labels(cand),
            },
        }
        atomic_json(os.path.join(inf_dir, "accepted_inferred_" + base), inferred)
    except Exception as e:
        log("proofmind", f"proof registry artifact write failed: {e}")


def dump_reject_registry_artifact(proof_dir: str, cand: Dict[str, Any]) -> None:
    try:
        reg_dir = os.path.join(proof_dir, "registry")
        os.makedirs(reg_dir, exist_ok=True)
        nonce = int(cand.get("nonce_int", 0)) & 0xFFFFFFFF
        path = os.path.join(reg_dir, f"rejected_{utc_stamp_file()}_nonce0x{nonce:08x}_{now_ms()}.json")
        event = {
            "schema": PROOFMIND_SCHEMA_VERSION,
            "kind": "rejected_share",
            "created_at_utc": utc_stamp_iso(),
            "empirical_layer": {
                "job_id": cand.get("job_id"),
                "job_seq": cand.get("job_seq"),
                "zbits": cand.get("zbits"),
                "nonce_submit_hex": cand.get("nonce_submit_hex"),
                "display_hash": cand.get("display_hash"),
                "pool_diff": cand.get("pool_diff"),
                "strategy": cand.get("strategy"),
                "sector": cand.get("sector"),
                "cfg_name": cand.get("cfg_name"),
                "pool_response": cand.get("pool_response"),
                "observer_labels": {
                    "sovereign_triad": sovereign_triad_candidate_labels(cand),
                    "kombucha_cell_microkernel": kombucha_cell_candidate_labels(cand),
                    "triune_atomic_clock": triune_atomic_clock_candidate_labels(cand),
                },
            },
            "hypothesis_layer": {
                "possible_causes": ["stale job", "pool-side target rule", "network race"],
                "wire_bytes_changed": False,
            },
            "meta_rules": {"wire_bytes_frozen_from_v26": True},
        }
        atomic_json(path, event)
    except Exception as e:
        log("proofmind", f"reject registry artifact failed: {e}")


def dump_accepted_proof(proof_dir: str, cand: Dict[str, Any]) -> Optional[str]:
    try:
        os.makedirs(proof_dir, exist_ok=True)
        path = os.path.join(proof_dir, proof_filename(cand))
        proof = build_proof(cand)
        atomic_json(path, proof)
        append_accepted_index(proof_dir, path, cand)
        write_v31_proof_registry_artifacts(proof_dir, path, cand, proof)
        score_observe_accepted(cand)
        try:
            if V31_RATEBOOK is not None:
                V31_RATEBOOK.observe_accepted(cand)
                V31_RATEBOOK.save()
            if V31_TAIL_TRACKER is not None:
                V31_TAIL_TRACKER.observe_candidate(cand, accepted=True)
            if RARE_TAIL_TIMING_MONITOR is not None:
                RARE_TAIL_TIMING_MONITOR.observe_accepted(cand, proof_path=path)
            if JANUS_GLYPH_OBSERVER is not None:
                JANUS_GLYPH_OBSERVER.observe_accepted(cand, proof_path=path)
            if V31_DUALLOCK_MEMORY is not None:
                V31_DUALLOCK_MEMORY.observe_accepted(cand)
            if A9_ACCOUNTING is not None:
                A9_ACCOUNTING.observe_accepted(cand)
        except Exception as e:
            log("v31", f"accepted observer failed: {e}")
        log("proof", f"accepted proof saved: {path}")
        return path
    except Exception as e:
        log("proof", f"failed to save accepted proof: {e}")
        return None


def write_lockbox(path: str, args: argparse.Namespace, cfgs: List[BuildConfig], workers: int, source_sha16: str = "") -> None:
    obj = {
        "version": VERSION,
        "sentinel": SENTINEL,
        "source_sha256_16": source_sha16,
        "started_at_utc": utc_stamp_iso(),
        "host": f"{args.host}:{args.port}",
        "tls": bool(args.tls),
        "user": args.user,
        "subscribe_tag": args.subscribe_tag,
        "workers": workers,
        "batch": args.batch,
        "matrix": args.matrix,
        "csv_log": args.csv_log,
        "proofs_dir": args.proofs_dir,
        "fresh_session_id": getattr(args, "fresh_session_id", ""),
        "fresh_started_at_utc": getattr(args, "fresh_started_at_utc", ""),
        "previous_accepted_proof_files": int(getattr(args, "previous_accepted_proof_files", 0) or 0),
        "previous_latest_accepted_proof_mtime_utc": getattr(args, "previous_latest_accepted_proof_mtime_utc", ""),
        "fresh_session_boundary": getattr(args, "fresh_session_boundary", ""),
        "fresh_session_boundary_archive": getattr(args, "fresh_session_boundary_archive", ""),
        "mode": args.mode,
        "requested_local_submit_z": args.local_submit_z,
        "auto_escalate_local_z": bool(args.auto_escalate_local_z),
        "lowdiff_jump_to_floor": bool(args.lowdiff_jump_to_floor),
        "canonical_cfg": {
            "prevhash_word_reverse": True,
            "prevhash_full_reverse": False,
            "nonce_header_little_endian": True,
            "nonce_submit_big_int": True,
            "nonce_submit_from_header_bytes": False,
            "extranonce2_endian": "little",
            "ntime_little": True,
            "nbits_little": True,
            "version_little": True,
            "merkle_branch_reverse": False,
            "merkle_header_reverse": False,
        },
        "wire_do_not_touch": [
            "nonce submit must be big-endian uint32 hex",
            "nonce header bytes must be uint32 little-endian",
            "prevhash must use reverse_word_bytes / word-swap32",
            "extranonce2 must remain little-endian for Zim/NerdMiner path",
            "non-canonical configs are telemetry only unless explicitly forced",
        ],
        "cfgs": [asdict(c) for c in cfgs],
    }
    try:
        atomic_json(path, obj)
        log("lockbox", f"wrote {path}")
    except Exception as e:
        log("lockbox", f"write failed {path}: {e}")


def dump_json(path: str, obj: Dict[str, Any]) -> None:
    try:
        atomic_json(path, obj)
    except Exception as e:
        log("dump", f"failed {path}: {e}")


class CsvLog:
    def __init__(self, path: str):
        self.path = path
        self.header_written = os.path.exists(path) and os.path.getsize(path) > 0

    def write_round(self, row: Dict[str, Any]) -> None:
        keys = [
            "ts",
            "round",
            "job",
            "seq",
            "pool_diff",
            "pool_z",
            "requested_local_z",
            "effective_submit_z",
            "effective_submit_diff",
            "matrix",
            "workers",
            "batch",
            "checked",
            "hps",
            "best_z",
            "best_strategy",
            "best_sector",
            "best_worker",
            "best_cfg",
            "submitted",
            "accepted",
            "rejected",
        ]
        try:
            with open(self.path, "a", encoding="utf-8", newline="") as f:
                if not self.header_written:
                    f.write(",".join(keys) + "\n")
                    self.header_written = True
                vals = []
                for k in keys:
                    v = row.get(k, "")
                    s = str(v).replace('"', '""')
                    if "," in s or "\n" in s:
                        s = f'"{s}"'
                    vals.append(s)
                f.write(",".join(vals) + "\n")
                f.flush()
        except Exception as e:
            log("csv", f"write failed: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="RblganulA9_11V32ActiveTriuneSovereignGate5050")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--tls", action="store_true", default=DEFAULT_TLS)
    p.add_argument("--user", default=os.environ.get("RBLGANUL_USER", DEFAULT_USER))
    p.add_argument("--password", default=os.environ.get("RBLGANUL_PASSWORD", DEFAULT_PASSWORD))
    p.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    p.add_argument("--reserve-cores", type=int, default=0)
    p.add_argument("--batch", type=int, default=100_000)
    p.add_argument("--matrix", choices=["canonical", "extended"], default="canonical")
    p.add_argument("--mode", choices=["lab", "proof", "lottery"], default="proof",
                   help="V31 gate policy: lab=pool_z for max proof frequency; proof=fixed local gate; lottery=fixed local gate reserved for high-z policies")
    p.add_argument("--submit-limit-per-worker", type=int, default=2)
    p.add_argument("--signal-z", type=int, default=28)
    p.add_argument("--csv-log", default="rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_lab.csv")
    p.add_argument("--proofs-dir", default="proofs", help="directory for accepted-share proof JSON files")
    p.add_argument("--lockbox", default="a9_11_v32_active_triune_sovereign_gate_50_50_lockbox.json", help="startup configuration lockbox JSON")
    p.add_argument("--session-summary", default="session_summary_a9_11_v32_active_triune_sovereign_gate_50_50.json", help="periodic/exit A9.11 session summary JSON")
    p.add_argument("--janus-brain", default="rblganul_a9_11_v32_best_brain.json", help="persistent A9.11 ProofMind elite/bad memory")
    p.add_argument("--registry-dir", default="proofs", help="Janus meta-registry root; defaults to proofs/ so artifacts stay together")
    p.add_argument("--proof-dashboard", default="rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_dashboard.json", help="A9.11/V32 live dashboard JSON for long unattended runs")
    p.add_argument("--disable-endurance-oracle", action="store_true", help="disable V31 batch governor / pruning / sector lock; wire is unchanged either way")
    p.add_argument("--max-batch-factor", type=float, default=1.35, help="V31 upper bound for adaptive batch pressure")
    p.add_argument("--min-batch-factor", type=float, default=0.70, help="V31 lower bound for cooldown batch pressure")
    p.add_argument("--cooldown-drop-ratio", type=float, default=0.82, help="enter SURVIVE/cooldown if HPS EWMA drops below this fraction of best EWMA")
    p.add_argument("--prune-after-observations", type=int, default=160, help="after this many observations, cold strategy/sector combos can be deprioritized")
    p.add_argument("--prune-min-best-z", type=int, default=24, help="cold combos with best_z below this and zero accepted are deprioritized")
    p.add_argument("--no-sector-lock", dest="sector_lock", action="store_false", default=True, help="disable V31 bias toward proven Zim sector 6")
    p.add_argument("--stale-guard", dest="stale_guard", action="store_true", default=True, help="drop candidates if a clean newer Stratum job arrived before submit")
    p.add_argument("--no-stale-guard", dest="stale_guard", action="store_false", help="disable V31 stale guard")
    p.add_argument("--longrun", dest="longrun", action="store_true", default=True, help="reduce console noise for multi-day lottery runs; default ON in V31")
    p.add_argument("--no-longrun", dest="longrun", action="store_false", help="debug mode: show per-worker lab logs again")
    p.add_argument("--quiet", action="store_true", help="suppress per-worker lab logs; accepted/rejected/proof logs still print")
    p.add_argument("--summary-every-rounds", type=int, default=10)
    p.add_argument("--summary-every-seconds", type=int, default=300)
    p.add_argument("--watchdog-minutes", type=float, default=30.0, help="warn if no accepted shares for this many minutes; never changes wire config")
    p.add_argument("--no-suggest-diff", action="store_true", default=False)
    p.add_argument("--suggest-diff", type=float, default=1.0)
    p.add_argument("--local-submit-z", type=int, default=0,
                   help="internal submit floor; AutoStart default 0 = submit anything that passes pool target")
    p.add_argument("--auto-escalate-local-z", action="store_true", default=False,
                   help="enable raising the internal submit gate after low-difficulty rejects; default OFF in NoEscalate build")
    p.add_argument("--no-auto-escalate-local-z", dest="auto_escalate_local_z", action="store_false",
                   help="keep internal submit gate fixed; embedded default in this build")
    p.add_argument("--escalate-step-z", type=int, default=2)
    p.add_argument("--escalate-after-rejects", type=int, default=1)
    p.add_argument("--max-local-submit-z", type=int, default=64)
    p.add_argument("--no-suggest-local-diff", action="store_true",
                   help="do not send mining.suggest_difficulty when local z is escalated")
    p.add_argument("--lowdiff-floor-diff", type=float, default=100000.0,
                   help="assumed real pool floor after Difficulty too low; public-pool often behaves like diff=100000")
    p.add_argument("--lowdiff-jump-to-floor", dest="lowdiff_jump_to_floor", action="store_true", default=False,
                   help="enable the old V24 jump from low local z to pool-floor z after Difficulty too low; default OFF in NoEscalate build")
    p.add_argument("--no-lowdiff-jump-to-floor", dest="lowdiff_jump_to_floor", action="store_false",
                   help="keep the old V24 pool-floor jump disabled; embedded default in this build")
    p.add_argument("--allow-noncanonical-submit", action="store_true",
                   help="dangerous lab mode: also submit non-canonical byte-probe headers; default skips them")
    p.add_argument("--max-rounds", type=int, default=0, help="0 = infinite")
    p.add_argument("--read-timeout", type=float, default=0.2)
    p.add_argument("--enable-reconnect", dest="enable_reconnect", action="store_true", default=True,
                   help="V32: automatically reconnect Stratum socket on recoverable network errors")
    p.add_argument("--disable-reconnect", dest="enable_reconnect", action="store_false",
                   help="V32: disable automatic reconnect and raise on socket errors")
    p.add_argument("--reconnect-initial-backoff", type=float, default=1.0,
                   help="V32: initial reconnect backoff in seconds")
    p.add_argument("--reconnect-max-backoff", type=float, default=30.0,
                   help="V32: max reconnect backoff in seconds")
    p.add_argument("--drop-round-candidates-after-reconnect", dest="drop_round_candidates_after_reconnect", action="store_true", default=True,
                   help="V32: if reconnect happens while workers hash an old job, drop those candidates before submit")
    p.add_argument("--keep-round-candidates-after-reconnect", dest="drop_round_candidates_after_reconnect", action="store_false",
                   help="Dangerous lab mode: keep old round candidates after reconnect; stale guard still applies")
    p.add_argument("--subscribe-tag", default=DEFAULT_SUBSCRIBE_TAG)
    p.add_argument("--stride-memory", default="rblganul_a9_11_v32_zim_stride_memory.json")
    p.add_argument("--disable-notify-oracle", action="store_true")
    p.add_argument("--notify-pause-window-ms", type=int, default=450)
    # V31 DualLock Oracle flags. A9.11 strict mode uses these as internal JANUS-half
    # proportions after BunnyHop wake, while the mirror stays 50%.
    p.add_argument("--strict-50-50-randomized-traversal-mirror", dest="strict_50_50_random_control", action="store_true", default=True,
                   help="default ON: deterministic 50% BunnyHop JANUS scout/wake vs 50% randomized JANUS-shaped traversal mirror")
    p.add_argument("--no-strict-50-50-randomized-traversal-mirror", dest="strict_50_50_random_control", action="store_false",
                   help="disable strict split and fall back to weighted A9.11 lane scheduling")
    p.add_argument("--strict-50-50-random-control", dest="strict_50_50_random_control", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--no-strict-50-50-random-control", dest="strict_50_50_random_control", action="store_false", help=argparse.SUPPRESS)
    p.add_argument("--enable-dual-lock-lane", dest="enable_dual_lock_lane", action="store_true", default=True)
    p.add_argument("--disable-dual-lock-lane", dest="enable_dual_lock_lane", action="store_false")
    p.add_argument("--linear-proof-weight", type=float, default=35.0)
    p.add_argument("--janus-weight", type=float, default=25.0)
    p.add_argument("--dual-lock-weight", type=float, default=20.0)
    p.add_argument("--zim-s6-weight", type=float, default=15.0)
    p.add_argument("--random-mirror-weight", dest="random_baseline_weight", type=float, default=5.0)
    p.add_argument("--random-baseline-weight", dest="random_baseline_weight", type=float, help=argparse.SUPPRESS)
    p.add_argument("--dual-lock-linear-s6-weight", type=float, default=40.0)
    p.add_argument("--dual-lock-zim-s6-weight", type=float, default=35.0)
    p.add_argument("--dual-lock-knight-s11-weight", type=float, default=25.0)
    p.add_argument("--tail-z", type=int, default=30)
    p.add_argument("--tail-z33", type=int, default=33)
    p.add_argument("--v31-rate-window", type=int, default=256)
    p.add_argument("--strategy-rates", default="rblganul_a9_11_v32_strategy_rates.json")
    p.add_argument("--tail-events", default="rblganul_a9_11_v32_tail_events.jsonl")
    p.add_argument("--rare-tail-timing-dashboard", default="rblganul_a9_11_v32_rare_tail_timing_summary.json",
                   help="observer-only accepted rare-tail timing dashboard for pool hour/window analysis")
    p.add_argument("--rare-tail-timing-events", default="rblganul_a9_11_v32_rare_tail_timing_z32_plus.jsonl",
                   help="observer-only z32+ accepted rare-tail timing event stream")
    p.add_argument("--rare-tail-timing-csv", default="rblganul_a9_11_v32_rare_tail_timing_z32_plus.csv",
                   help="observer-only z32+ accepted rare-tail timing table")
    p.add_argument("--rare-tail-timing-min-z", type=int, default=32,
                   help="minimum accepted zbits written to rare-tail timing telemetry")
    p.add_argument("--disable-rare-tail-timing-monitor", action="store_true",
                   help="disable accepted rare-tail timing telemetry; scheduler and wire are unchanged")
    p.add_argument("--janus-glyph-summary", default="rblganul_a9_11_v32_janus_glyph_summary.json",
                   help="observer-only pre-hash coinbase/job glyph summary")
    p.add_argument("--janus-glyph-events", default="rblganul_a9_11_v32_janus_glyph_events.jsonl",
                   help="observer-only pre-hash coinbase/job glyph event stream")
    p.add_argument("--janus-glyph-csv", default="rblganul_a9_11_v32_janus_glyph_events.csv",
                   help="observer-only pre-hash coinbase/job glyph CSV table")
    p.add_argument("--janus-glyph-min-len", type=int, default=4,
                   help="minimum printable string length for JanusGlyphObserver")
    p.add_argument("--janus-glyph-accepted-link-min-z", type=int, default=32,
                   help="accepted shares at or above this z are linked to glyph strings even without explicit keyword hits")
    p.add_argument("--janus-glyph-keywords", default="",
                   help="optional comma-separated keyword override/addition for JanusGlyphObserver")
    p.add_argument("--disable-janus-glyph-observer", action="store_true",
                   help="disable pre-hash coinbase/job glyph observer; scheduler and wire are unchanged")
    p.add_argument("--dual-lock-memory", default="rblganul_a9_11_v32_dual_lock_memory.json")
    p.add_argument("--a9-accounting-dashboard", default="rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_accounting.json",
                   help="fresh-only A9.11 strict 50/50 BunnyHop-JANUS-vs-randomized-traversal-mirror accounting dashboard")
    p.add_argument("--disable-a9-accounting", action="store_true",
                   help="disable A9 accounting layer; scheduler/wire are unchanged")
    p.add_argument("--witchhunter-dashboard", default="rblganul_a9_11_v32_witchhunter_dark_tail.json",
                   help="observer-only rejected/stale/drop dark-tail dashboard JSON")
    p.add_argument("--witchhunter-events", default="rblganul_a9_11_v32_witchhunter_dark_tail_events.jsonl",
                   help="observer-only rejected/stale/drop dark-tail event stream JSONL")
    p.add_argument("--witchhunter-min-event-z", type=int, default=23,
                   help="minimum dark-tail zbits written to WitchHunter JSONL; dashboard counts all dark events")
    p.add_argument("--disable-witchhunter", action="store_true",
                   help="disable WitchHunter observer; scheduler and wire are unchanged either way")
    p.add_argument("--kombucha-cell-nuclei", type=int, default=12,
                   help="observer-only Kombucha Cell Microkernel nuclei count; no scheduler or wire effect")
    p.add_argument("--disable-kombucha-cell-microkernel-observer", action="store_true",
                   help="disable Kombucha Cell Microkernel observer labels; scheduler and wire are unchanged")
    p.add_argument("--disable-triune-atomic-clock-observer", action="store_true",
                   help="disable Triune Atomic Clock observer labels; scheduler and wire are unchanged")
    p.add_argument("--enable-active-sovereign-gate", dest="active_sovereign_gate", action="store_true", default=True,
                   help="A9.11 default ON: allow Red/Blue/Gold to change only JANUS-half BunnyHop phase")
    p.add_argument("--disable-active-sovereign-gate", dest="active_sovereign_gate", action="store_false",
                   help="turn A9.11 back into A9.10-style observer-only phase behavior")
    p.add_argument("--sovereign-active-after-accepted", type=int, default=250,
                   help="minimum JANUS accepted shares before active SovereignGate can wake JANUS early")
    p.add_argument("--sovereign-tail-gap-z", type=int, default=32,
                   help="tail level used for mirror-pressure wake/re-scout decisions")
    p.add_argument("--sovereign-wake-best-gap", type=int, default=2,
                   help="wake/re-scout JANUS if mirror best_z leads JANUS by at least this gap")
    p.add_argument("--sovereign-rescout-tail-gap", type=int, default=1,
                   help="re-scout JANUS if mirror has this many more z-tail hits at sovereign-tail-gap-z")
    p.add_argument("--a9-min-random-control-mh", type=float, default=250.0,
                   help="comparison gate waits until randomized traversal mirror has this many checked MH")
    p.add_argument("--a9-min-fresh-proofs", type=int, default=5000,
                   help="recommended fresh accepted-share corpus before publishing comparison")
    p.add_argument("--bunnyhop-scout-min-accepted", type=int, default=500,
                   help="accepted scout proofs in JANUS arm before waking into broad JANUS")
    p.add_argument("--bunnyhop-wake-z", type=int, default=32,
                   help="accepted JANUS scout rare-tail anchor that wakes broad JANUS immediately")
    p.add_argument("--bunnyhop-force-scout", action="store_true",
                   help="keep JANUS arm in BunnyHop Scout regardless of corpus/anchor")
    p.add_argument("--bunnyhop-force-wake", action="store_true",
                   help="force JANUS arm into broad JANUS wake immediately")
    p.add_argument("--enable-bunnyhop-rescout", dest="bunnyhop_rescout_enable", action="store_true", default=True,
                   help="A9.11 default ON: after wake stalls, briefly re-enter JANUS-shaped re-scout instead of staying only in broad mixture")
    p.add_argument("--disable-bunnyhop-rescout", dest="bunnyhop_rescout_enable", action="store_false",
                   help="disable A9.11 Memory ReJump and behave like A9.6 scout/wake")
    p.add_argument("--bunnyhop-rescout-after-accepted", type=int, default=250,
                   help="wake-phase JANUS accepted proofs before each Memory ReJump window can open")
    p.add_argument("--bunnyhop-rescout-burst-accepted", type=int, default=160,
                   help="accepted-proof width of each Memory ReJump burst")
    p.add_argument("--bunnyhop-rescout-cycle-accepted", type=int, default=420,
                   help="accepted-proof cycle length for Memory ReJump windows")
    p.add_argument("--bunnyhop-rescout-target-z", type=int, default=34,
                   help="if JANUS best_z is below this value after wake, Memory ReJump windows are allowed")
    p.add_argument("--import-v30-state", dest="import_v30_state", action="store_true", default=False, help="import older dashboard/session/proof index at startup; default OFF for clean A9.11 evidence")
    p.add_argument("--no-import-v30-state", dest="import_v30_state", action="store_false")
    p.add_argument("--v30-proof-dashboard", default="proof_dashboard.json")
    p.add_argument("--v30-session-summary", default="session_summary.json")
    p.add_argument("--v30-janus-brain", default="rblganul_v30_best_brain.json")
    p.add_argument("--v30-stride-memory", default="rblganul_v30_zim_stride_memory.json")
    p.add_argument("--v30-proofs-dir", default="", help="optional V30 proofs dir to import accepted_index.json from")
    # IO-path mode: like Janus Io supervisor, keep all V31 outputs next to this script
    # under janus_io_o1_runs/<run-name>, independent of the PowerShell current directory.
    p.add_argument("--io-output-root", default="", help="output root; default = script_dir/janus_io_o1_runs")
    p.add_argument("--io-run-name", default="A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_AFTER_A9_10", help="subfolder for this A9.11 BunnyHop scout/wake run")
    p.add_argument("--io-chdir", dest="io_chdir", action="store_true", default=True, help="chdir into IO run dir before writing artifacts; default ON")
    p.add_argument("--no-io-chdir", dest="io_chdir", action="store_false", help="disable IO chdir and use raw relative paths")
    p.add_argument("--resume-fresh-session-boundary", action="store_true",
                   help="reuse an existing a9_11_fresh_session_boundary.json cutoff in the run dir; reporting/corpus-resume only, wire unchanged")
    p.add_argument("--selfcheck", action="store_true", help="print embedded profile and exit")
    return p.parse_args()



def v31_io_script_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path(os.getcwd()).resolve()


def v31_io_output_root(value: str = "") -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return v31_io_script_dir() / "janus_io_o1_runs"


def v31_io_first_existing(candidates: List[Path]) -> str:
    for p in candidates:
        try:
            if p.exists():
                return str(p.resolve())
        except Exception:
            pass
    return ""


def v31_io_was_default_path(value: str, default_name: str) -> bool:
    try:
        return (not value) or (str(value).replace("\\", "/").rstrip("/").split("/")[-1] == default_name and not os.path.isabs(str(value)))
    except Exception:
        return False


def v31_io_prepare_paths(args: argparse.Namespace) -> Dict[str, Any]:
    """Make V31 behave like the Janus IO build: every new artifact lives next to the script.

    This fixes the Windows/PowerShell confusion where the miner is started from one
    folder but writes relative JSON/proofs somewhere else. In IO mode we chdir into:
        <script_dir>/janus_io_o1_runs/A5_V31_AFTER_V30_IMPORT

    Wire/header/submit code is not touched. This is output-path/reporting only.
    """
    script_dir = v31_io_script_dir()
    root = v31_io_output_root(getattr(args, "io_output_root", ""))
    run_name = str(getattr(args, "io_run_name", "A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_AFTER_A9_10") or "A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_AFTER_A9_10")
    run_dir = (root / run_name).resolve()
    proofs_dir = run_dir / "proofs"
    run_dir.mkdir(parents=True, exist_ok=True)
    proofs_dir.mkdir(parents=True, exist_ok=True)
    latest_boundary_path = run_dir / "a9_11_fresh_session_boundary.json"
    fresh_boundary = None
    if bool(getattr(args, "resume_fresh_session_boundary", False)):
        fresh_boundary = a9_11_load_fresh_session_boundary(latest_boundary_path, run_dir, proofs_dir)
    if fresh_boundary is None:
        fresh_boundary = a9_11_fresh_session_boundary(run_dir, proofs_dir)
    session_boundary_path = run_dir / f"a9_11_fresh_session_boundary_{fresh_boundary['session_id']}.json"
    try:
        if not bool(fresh_boundary.get("resume_mode", False)):
            atomic_json(str(latest_boundary_path), fresh_boundary)
            atomic_json(str(session_boundary_path), fresh_boundary)
    except Exception:
        pass
    args.fresh_session_id = fresh_boundary.get("session_id", "")
    args.fresh_started_at_utc = fresh_boundary.get("fresh_started_at_utc", "")
    args.previous_accepted_proof_files = fresh_boundary.get("previous_accepted_proof_files", 0)
    args.previous_latest_accepted_proof_mtime_utc = fresh_boundary.get("previous_latest_accepted_proof_mtime_utc", "")
    args.fresh_session_boundary = str(latest_boundary_path)
    args.fresh_session_boundary_archive = str(session_boundary_path)

    # Discover V30 artifacts before changing CWD. Supports both old root run and Janus IO agent folders.
    old_roots = [
        script_dir / "janus_io_o1_runs" / "A5_V31_AFTER_V30_IMPORT",
        script_dir,
        Path(os.getcwd()).resolve(),
        script_dir / "janus_io_o1_runs" / "A3_JANUS_FULL",
        script_dir / "janus_io_o1_runs" / "A4_DUAL_LOCK_TEST",
        script_dir / "janus_io_o1_runs" / "A1_LINEAR_PURE",
    ]
    v30_dashboard = v31_io_first_existing([
        old_roots[0] / "rblganul_v31_duallock_dashboard.json",
        old_roots[1] / "proof_dashboard.json",
        old_roots[2] / "proof_dashboard.json",
        old_roots[3] / "a3_janus_full_proof_dashboard.json",
        old_roots[4] / "a4_dual_lock_test_proof_dashboard.json",
        old_roots[5] / "a1_linear_pure_proof_dashboard.json",
    ])
    v30_summary = v31_io_first_existing([
        old_roots[0] / "session_summary_v31.json",
        old_roots[1] / "session_summary.json",
        old_roots[2] / "session_summary.json",
        old_roots[3] / "a3_janus_full_session_summary.json",
        old_roots[4] / "a4_dual_lock_test_session_summary.json",
        old_roots[5] / "a1_linear_pure_session_summary.json",
    ])
    v30_brain = v31_io_first_existing([
        old_roots[0] / "rblganul_v31_best_brain.json",
        old_roots[1] / "rblganul_v30_best_brain.json",
        old_roots[2] / "rblganul_v30_best_brain.json",
        old_roots[3] / "a3_janus_full_best_brain.json",
        old_roots[4] / "a4_dual_lock_test_best_brain.json",
    ])
    v30_stride = v31_io_first_existing([
        old_roots[0] / "rblganul_v31_zim_stride_memory.json",
        old_roots[1] / "rblganul_v30_zim_stride_memory.json",
        old_roots[2] / "rblganul_v30_zim_stride_memory.json",
        old_roots[3] / "a3_janus_full_stride_memory.json",
        old_roots[4] / "a4_dual_lock_test_stride_memory.json",
    ])
    v30_proofs = v31_io_first_existing([
        old_roots[0] / "proofs",
        old_roots[1] / "proofs",
        old_roots[2] / "proofs",
        old_roots[3] / "proofs",
        old_roots[4] / "proofs",
    ])

    # Preserve explicit CLI paths. Only rewrite defaults to IO run dir names.
    if v31_io_was_default_path(getattr(args, "proofs_dir", ""), "proofs"):
        args.proofs_dir = str(proofs_dir)
    if v31_io_was_default_path(getattr(args, "registry_dir", ""), "proofs"):
        args.registry_dir = str(proofs_dir)
    defaults = {
        "csv_log": "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_lab.csv",
        "lockbox": "a9_11_v32_active_triune_sovereign_gate_50_50_lockbox.json",
        "session_summary": "session_summary_a9_11_v32_active_triune_sovereign_gate_50_50.json",
        "janus_brain": "rblganul_a9_11_v32_best_brain.json",
        "proof_dashboard": "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_dashboard.json",
        "stride_memory": "rblganul_a9_11_v32_zim_stride_memory.json",
        "strategy_rates": "rblganul_a9_11_v32_strategy_rates.json",
        "tail_events": "rblganul_a9_11_v32_tail_events.jsonl",
        "rare_tail_timing_dashboard": "rblganul_a9_11_v32_rare_tail_timing_summary.json",
        "rare_tail_timing_events": "rblganul_a9_11_v32_rare_tail_timing_z32_plus.jsonl",
        "rare_tail_timing_csv": "rblganul_a9_11_v32_rare_tail_timing_z32_plus.csv",
        "janus_glyph_summary": "rblganul_a9_11_v32_janus_glyph_summary.json",
        "janus_glyph_events": "rblganul_a9_11_v32_janus_glyph_events.jsonl",
        "janus_glyph_csv": "rblganul_a9_11_v32_janus_glyph_events.csv",
        "dual_lock_memory": "rblganul_a9_11_v32_dual_lock_memory.json",
        "a9_accounting_dashboard": "rblganul_a9_11_v32_active_triune_sovereign_gate_50_50_accounting.json",
        "witchhunter_dashboard": "rblganul_a9_11_v32_witchhunter_dark_tail.json",
        "witchhunter_events": "rblganul_a9_11_v32_witchhunter_dark_tail_events.jsonl",
    }
    for attr, name in defaults.items():
        if v31_io_was_default_path(getattr(args, attr, ""), name):
            setattr(args, attr, str(run_dir / name))

    # Auto-wire V30 import sources if the user did not override them.
    if v31_io_was_default_path(getattr(args, "v30_proof_dashboard", ""), "proof_dashboard.json") and v30_dashboard:
        args.v30_proof_dashboard = v30_dashboard
    if v31_io_was_default_path(getattr(args, "v30_session_summary", ""), "session_summary.json") and v30_summary:
        args.v30_session_summary = v30_summary
    if v31_io_was_default_path(getattr(args, "v30_janus_brain", ""), "rblganul_v30_best_brain.json") and v30_brain:
        args.v30_janus_brain = v30_brain
    if v31_io_was_default_path(getattr(args, "v30_stride_memory", ""), "rblganul_v30_zim_stride_memory.json") and v30_stride:
        args.v30_stride_memory = v30_stride
    if not getattr(args, "v30_proofs_dir", "") and v30_proofs:
        args.v30_proofs_dir = v30_proofs

    info = {
        "schema": "v31-io-path-bootstrap-1",
        "version": VERSION,
        "sentinel": SENTINEL,
        "created_at_utc": utc_stamp_iso(),
        "script_dir": str(script_dir),
        "original_cwd": os.getcwd(),
        "io_output_root": str(root),
        "io_run_dir": str(run_dir),
        "proofs_dir": args.proofs_dir,
        "proof_dashboard": args.proof_dashboard,
        "session_summary": args.session_summary,
        "strategy_rates": args.strategy_rates,
        "tail_events": args.tail_events,
        "rare_tail_timing_dashboard": getattr(args, "rare_tail_timing_dashboard", ""),
        "rare_tail_timing_events": getattr(args, "rare_tail_timing_events", ""),
        "rare_tail_timing_csv": getattr(args, "rare_tail_timing_csv", ""),
        "janus_glyph_summary": getattr(args, "janus_glyph_summary", ""),
        "janus_glyph_events": getattr(args, "janus_glyph_events", ""),
        "janus_glyph_csv": getattr(args, "janus_glyph_csv", ""),
        "dual_lock_memory": args.dual_lock_memory,
        "a9_accounting_dashboard": getattr(args, "a9_accounting_dashboard", ""),
        "witchhunter_dashboard": getattr(args, "witchhunter_dashboard", ""),
        "witchhunter_events": getattr(args, "witchhunter_events", ""),
        "fresh_session_boundary": fresh_boundary,
        "fresh_session_boundary_path": str(latest_boundary_path),
        "fresh_session_boundary_archive_path": str(session_boundary_path),
        "v30_import": {
            "proof_dashboard": getattr(args, "v30_proof_dashboard", ""),
            "session_summary": getattr(args, "v30_session_summary", ""),
            "janus_brain": getattr(args, "v30_janus_brain", ""),
            "stride_memory": getattr(args, "v30_stride_memory", ""),
            "proofs_dir": getattr(args, "v30_proofs_dir", ""),
        },
        "wire_change_required": False,
    }
    try:
        atomic_json(str(run_dir / "v31_io_bootstrap.json"), info)
    except Exception:
        pass

    if bool(getattr(args, "io_chdir", True)):
        os.chdir(str(run_dir))
        info["active_cwd_after_chdir"] = os.getcwd()
        try:
            atomic_json(str(run_dir / "v31_io_bootstrap.json"), info)
        except Exception:
            pass
    return info

def effective_workers(args: argparse.Namespace) -> int:
    w = args.workers
    if args.reserve_cores > 0:
        w = max(1, (os.cpu_count() or w) - args.reserve_cores)
    return max(1, w)


def wait_initial_job(client: StratumClient, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        client.read_available(max_messages=50, timeout=0.5)
        if client.extranonce1 and client.extranonce2_size and client.authorized and client.job:
            return
    raise TimeoutError(
        "No initial job/authorization. Check host/port/user/network. "
        f"authorized={client.authorized} en1={client.extranonce1!r} en2_size={client.extranonce2_size} job={client.job}"
    )



def v31_copy_seed_file(src: str, dst: str, label: str) -> None:
    if not src or not dst or os.path.abspath(src) == os.path.abspath(dst):
        return
    if os.path.exists(dst) or not os.path.exists(src):
        return
    try:
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(data)
        log("v31", f"seeded {label}: {src} -> {dst}")
    except Exception as e:
        log("v31", f"seed {label} skipped: {e}")


def v31_import_previous_state(args: argparse.Namespace, client: Optional[StratumClient] = None) -> Dict[str, Any]:
    """Import already collected V30 evidence into V31 counters.

    This lets V31 continue a run after V30 without touching V30's wire path.
    If V30 is still running, this function reads a point-in-time snapshot only;
    launch V31 after stopping V30 when you want a clean single-writer proof index.
    """
    info: Dict[str, Any] = {"enabled": bool(getattr(args, "import_v30_state", False)), "items": []}
    if not info["enabled"]:
        return info
    global V31_RATEBOOK
    try:
        # Seed V31 memory files from V30 only if the V31 files do not exist yet.
        v31_copy_seed_file(getattr(args, "v30_janus_brain", ""), getattr(args, "janus_brain", ""), "ProofMind brain")
        v31_copy_seed_file(getattr(args, "v30_stride_memory", ""), getattr(args, "stride_memory", ""), "Zim stride memory")
        if V31_RATEBOOK is not None:
            info["items"].append(V31_RATEBOOK.import_dashboard(getattr(args, "v30_proof_dashboard", "")))
            info["items"].append(V31_RATEBOOK.import_dashboard(getattr(args, "proof_dashboard", "")))
            # Import old V30 proof index from its original folder, but write new V31 proofs to args.proofs_dir.
            if getattr(args, "v30_proofs_dir", ""):
                info["items"].append(V31_RATEBOOK.import_accepted_index(getattr(args, "v30_proofs_dir", "")))
            info["items"].append(V31_RATEBOOK.import_accepted_index(getattr(args, "proofs_dir", "proofs")))
            V31_RATEBOOK.save(force=True)
        # Continue visible counters from the best snapshot we can read.
        max_acc = max_rej = max_sub = max_best = 0
        for path in (getattr(args, "v30_proof_dashboard", ""), getattr(args, "v30_session_summary", ""), getattr(args, "proof_dashboard", ""), getattr(args, "session_summary", "")):
            if not path or not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    obj = json.load(f)
                if isinstance(obj, dict):
                    max_acc = max(max_acc, int(obj.get("accepted", 0) or 0))
                    max_rej = max(max_rej, int(obj.get("rejected", 0) or 0))
                    max_sub = max(max_sub, int(obj.get("submitted", 0) or 0))
                    max_best = max(max_best, int(obj.get("best_z", obj.get("proofmind_best_z", 0)) or 0))
            except Exception:
                pass
        if V31_RATEBOOK is not None:
            max_acc = max(max_acc, int(V31_RATEBOOK.imported.get("accepted", 0) or 0))
            max_rej = max(max_rej, int(V31_RATEBOOK.imported.get("rejected", 0) or 0))
            max_sub = max(max_sub, int(V31_RATEBOOK.imported.get("submitted", 0) or 0))
            max_best = max(max_best, int(V31_RATEBOOK.imported.get("best_z", 0) or 0))
        if client is not None:
            client.accepted = max(client.accepted, max_acc)
            client.rejected = max(client.rejected, max_rej)
            client.submitted = max(client.submitted, max_sub)
        update_session_state(v30_imported_accepted=max_acc, v30_imported_rejected=max_rej, v30_imported_submitted=max_sub, v30_imported_best_z=max_best)
        info.update({"accepted": max_acc, "rejected": max_rej, "submitted": max_sub, "best_z": max_best})
        log("v31", f"imported V30 state: accepted={max_acc} rejected={max_rej} submitted={max_sub} best_z={max_best}")
    except Exception as e:
        info["error"] = str(e)
        log("v31", f"V30 import failed: {e}")
    return info


def submit_candidates(client: StratumClient, job_snapshot: Job, candidates: List[Dict[str, Any]], cfg_by_name: Dict[str, BuildConfig], allow_noncanonical_submit: bool = False, stale_guard: bool = True) -> None:
    # Submit strongest first.
    candidates.sort(key=lambda c: (int(c.get("zbits", 0)), c.get("display_hash", "")), reverse=True)

    for cand in candidates:
        cfg = cfg_by_name.get(cand.get("cfg_name"))
        if not cfg:
            continue

        if (not cfg.submit_compatible) and (not allow_noncanonical_submit):
            cand["mirror_ok"] = False
            cand["mirror_reason"] = "non_submit_compatible_cfg"
            log("truthgate", f"skip non-submit-compatible cfg={cfg.name} z={cand.get('zbits')} hash={mask_hex(cand.get('display_hash',''), 32)}")
            continue

        # V31 StaleGuard: if a clean newer job arrived while workers were hashing,
        # do not submit the old candidate. This protects proof statistics without
        # changing header/submit bytes.
        if stale_guard and client.job:
            try:
                cand_seq = int(cand.get("job_seq", -1))
                cur_seq = int(client.job.seq)
            except Exception:
                cand_seq, cur_seq = -1, -2
            if client.job.clean and (client.job.job_id != cand["job_id"] or cur_seq != cand_seq):
                cand["stale_guard_dropped"] = True
                cand["stale_guard_reason"] = f"clean newer job current={client.job.job_id}/seq{cur_seq} candidate={cand.get('job_id')}/seq{cand_seq}"
                log("stale_guard", f"candidate dropped: {cand['stale_guard_reason']} z={cand.get('zbits')} nonce={cand.get('nonce_submit_hex')}")
                dump_json("rblganul_v31_endurance_stale_drop.json", cand)
                try:
                    if WITCH_HUNTER is not None:
                        WITCH_HUNTER.observe_stale_drop(cand, cand.get("stale_guard_reason", "stale_guard_drop"))
                except Exception as e:
                    log("witchhunter", f"stale drop observe failed: {e}")
                continue

        ok, reason = verify_submit_mirror(job_snapshot, client.extranonce1, cand, cfg)
        cand["mirror_ok"] = ok
        cand["mirror_reason"] = reason
        if not ok:
            log("mirror", f"skip cfg={cfg.name} reason={reason}")
            dump_json("rblganul_v31_endurance_mirror_fail.json", cand)
            continue

        # Strong pre-submit line. If this says pool_pass=True and pool rejects,
        # the dumped JSON is enough to audit exact reconstruction.
        log(
            "truth",
            "pool_pass=True local_z={} z={} cfg={} nonce_int={:08x} nonce_header={} nonce_submit={} en2={} ntime={} merkle={}".format(
                cand.get("local_submit_z"),
                cand["zbits"],
                cand["cfg_name"],
                int(cand["nonce_int"]),
                cand["nonce_header_hex"],
                cand["nonce_submit_hex"],
                cand["extranonce2"],
                cand["ntime"],
                mask_hex(cand["merkle_root_header"], 40),
            ),
        )
        dump_json("rblganul_v31_endurance_last_candidate.json", cand)
        client.submit(cand)
        # Read immediate response if pool is fast.
        client.read_available(max_messages=20, timeout=0.05)


def main() -> None:
    args = parse_args()
    source_path = Path(sys.argv[0]).resolve()
    io_info = v31_io_prepare_paths(args)
    workers = effective_workers(args)
    cfgs = build_configs(args.matrix)
    cfg_by_name = {c.name: c for c in cfgs}

    print(f"[Rblganul] {VERSION}", flush=True)
    log("selfcheck", f"sentinel={SENTINEL}")
    log("selfcheck", f"file={source_path}")
    source_sha16 = ""
    try:
        with open(source_path, "rb") as f:
            source_sha16 = hashlib.sha256(f.read()).hexdigest()[:16]
        log("selfcheck", f"sha256_16={source_sha16}")
    except Exception:
        pass

    log("io", f"output_root={io_info.get('io_output_root')} run_dir={io_info.get('io_run_dir')} cwd={os.getcwd()}")
    log("io", f"proofs_dir={args.proofs_dir} dashboard={args.proof_dashboard} session_summary={args.session_summary}")
    log("io", f"v30_import_dashboard={getattr(args, 'v30_proof_dashboard', '')} v30_proofs_dir={getattr(args, 'v30_proofs_dir', '')}")
    log(
        "fresh_boundary",
        f"session_id={getattr(args, 'fresh_session_id', '')} cutoff_utc={getattr(args, 'fresh_started_at_utc', '')} previous_accepted_proofs={getattr(args, 'previous_accepted_proof_files', 0)} marker={getattr(args, 'fresh_session_boundary', '')}",
    )
    log(
        "fresh_boundary",
        "repeat-run rule: dashboard/accounting are process-fresh; proof directory totals are archive totals unless filtered by cutoff_utc",
    )

    log("doctrine", "honest mode: zbits are rarity logs; proof is accepted shares and reproducible dumps")
    log("zimcore", "Zim mechanics active: NerdMiner subscribe tag, LE extranonce2, reverse odd-stride walk, stride bandit, notify oracle")
    log("power", f"workers={workers} batch={args.batch:,} matrix={args.matrix} cfgs={','.join(c.name for c in cfgs)}")
    log("proofmind", f"mode={args.mode} Janus Codex scheduler active; wire bytes are locked to accepted V26/V27/V28/V29/V30")
    log("endurance", f"V31 oracle active: dynamic batch governor, strategy pruning, sector_lock={args.sector_lock}, proof_dashboard={args.proof_dashboard}")
    log("v31", f"DualLock lane enabled={args.enable_dual_lock_lane} mix={dict(normalized_lane_weights(args))} internal=linear_s6:{args.dual_lock_linear_s6_weight} zim_s6:{args.dual_lock_zim_s6_weight} knight_s11:{args.dual_lock_knight_s11_weight}")
    log("autostart", f"embedded profile: host={args.host} port={args.port} tls={args.tls} user={args.user} password={args.password} suggest_diff={args.suggest_diff:g} no_suggest={args.no_suggest_diff} subscribe_tag={args.subscribe_tag} local_submit_z={args.local_submit_z} auto_escalate={args.auto_escalate_local_z} lowdiff_jump={args.lowdiff_jump_to_floor}")
    log("autostart", "NerdMiner lottery endpoint preset: pool.nerdminers.org:3333")
    log("run", "no long command needed: python RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py")
    log("v32_net", f"NetworkRecovery enabled={args.enable_reconnect} backoff={args.reconnect_initial_backoff:g}->{args.reconnect_max_backoff:g}s; stale old-round candidates are dropped after reconnect")
    log("v32_tachyon", "TachyonMicroAgent is design/backlog only in this V32-A build; scheduler remains V31-compatible")
    log("witchhunter", f"enabled={not args.disable_witchhunter} dashboard={args.witchhunter_dashboard} events={args.witchhunter_events} min_event_z={args.witchhunter_min_event_z} effect=observe_only")
    log("glyph", f"enabled={not args.disable_janus_glyph_observer} summary={args.janus_glyph_summary} events={args.janus_glyph_events} csv={args.janus_glyph_csv} accepted_link_min_z={args.janus_glyph_accepted_link_min_z} effect=observe_only")
    log("sovereign", f"ActiveSovereignGate enabled={args.active_sovereign_gate}: Red/Blue/Gold may change JANUS-half phase only; mirror_effect=none wire_change_required=False")
    log("kombucha_cell", f"microkernel_observer enabled={not args.disable_kombucha_cell_microkernel_observer} nuclei={args.kombucha_cell_nuclei} scheduler_effect=none wire_change_required=False")
    log("triune_clock", f"enabled={not args.disable_triune_atomic_clock_observer} faces=red/blue/gold axes=hash_result/traversal_path/time_entropy_phase scheduler_effect=none wire_change_required=False")

    if getattr(args, "selfcheck", False):
        log("proofpack", f"proofs_dir={args.proofs_dir} lockbox={args.lockbox} session_summary={args.session_summary} mode={args.mode} longrun={args.longrun} quiet={args.quiet}")
        log("proofmind", f"janus_brain={args.janus_brain} registry_dir={args.registry_dir} stale_guard={args.stale_guard}")
        log("endurance", f"dashboard={args.proof_dashboard} disabled={args.disable_endurance_oracle} max_batch_factor={args.max_batch_factor} min_batch_factor={args.min_batch_factor}")
        log("v31", f"strategy_rates={args.strategy_rates} tail_events={args.tail_events} dual_lock_memory={args.dual_lock_memory} import_v30_state={args.import_v30_state}")
        log("a9", f"accounting_enabled={not args.disable_a9_accounting} dashboard={args.a9_accounting_dashboard} min_mirror_mh={args.a9_min_random_control_mh} min_fresh_proofs={args.a9_min_fresh_proofs} bunnyhop_min_acc={args.bunnyhop_scout_min_accepted} wake_z={args.bunnyhop_wake_z}")
        log("witchhunter", f"dashboard={args.witchhunter_dashboard} events={args.witchhunter_events} accepted_policy=ignored wire_change_required=False")
        log("rare_tail_time", f"observer_only=True min_z={args.rare_tail_timing_min_z} dashboard={args.rare_tail_timing_dashboard} events={args.rare_tail_timing_events} csv={args.rare_tail_timing_csv} disable={args.disable_rare_tail_timing_monitor}")
        log("glyph", f"observer_only=True min_len={args.janus_glyph_min_len} accepted_link_min_z={args.janus_glyph_accepted_link_min_z} summary={args.janus_glyph_summary} events={args.janus_glyph_events} csv={args.janus_glyph_csv} disable={args.disable_janus_glyph_observer}")
        log("sovereign", f"active_gate={args.active_sovereign_gate} after_acc={args.sovereign_active_after_accepted} tail_gap_z={args.sovereign_tail_gap_z} best_gap={args.sovereign_wake_best_gap} rescout_tail_gap={args.sovereign_rescout_tail_gap} effect=janus_half_phase_only")
        log("kombucha_cell", f"observer_only=True nuclei={args.kombucha_cell_nuclei} disable={args.disable_kombucha_cell_microkernel_observer} cell_labels=accepted/rejected/dashboard")
        log("triune_clock", f"observer_only=True disable={args.disable_triune_atomic_clock_observer} clock_labels=runtime/accepted/rejected/dashboard fixed_chemistry=double_sha256_frozen_wire")
        log("v31", f"strategy_mix={dict(normalized_lane_weights(args))} dual_lock_internal=linear_s6:{args.dual_lock_linear_s6_weight} zim_s6:{args.dual_lock_zim_s6_weight} knight_s11:{args.dual_lock_knight_s11_weight}")
        log("v32_net", f"enable_reconnect={args.enable_reconnect} initial_backoff={args.reconnect_initial_backoff} max_backoff={args.reconnect_max_backoff} drop_round_candidates_after_reconnect={args.drop_round_candidates_after_reconnect}")
        log("io", f"bootstrap={Path(args.lockbox).parent / 'v31_io_bootstrap.json'}")
        log("fresh_boundary", f"archive_marker={getattr(args, 'fresh_session_boundary_archive', '')}")
        return

    global V31_RATEBOOK, V31_TAIL_TRACKER, V31_DUALLOCK_MEMORY, A9_ACCOUNTING, WITCH_HUNTER, RARE_TAIL_TIMING_MONITOR, JANUS_GLYPH_OBSERVER
    V31_RATEBOOK = StrategyRateBook(args.strategy_rates, args.v31_rate_window)
    V31_TAIL_TRACKER = TailTracker(args.tail_events, args.tail_z, args.tail_z33)
    V31_DUALLOCK_MEMORY = DualLockMemory(args.dual_lock_memory)
    A9_ACCOUNTING = None if bool(args.disable_a9_accounting) else A99SovereignTriadAccounting(
        args.a9_accounting_dashboard,
        kombucha_nuclei=args.kombucha_cell_nuclei,
        kombucha_enabled=not bool(args.disable_kombucha_cell_microkernel_observer),
        atomic_clock_enabled=not bool(args.disable_triune_atomic_clock_observer),
    )
    WITCH_HUNTER = None if bool(args.disable_witchhunter) else WitchHunter(args.witchhunter_dashboard, args.witchhunter_events, args.witchhunter_min_event_z)
    if WITCH_HUNTER is not None:
        WITCH_HUNTER.write()
    RARE_TAIL_TIMING_MONITOR = None if bool(args.disable_rare_tail_timing_monitor) else RareTailTimingMonitor(
        args.rare_tail_timing_events,
        args.rare_tail_timing_csv,
        args.rare_tail_timing_dashboard,
        args.rare_tail_timing_min_z,
        args.proofs_dir,
    )
    if RARE_TAIL_TIMING_MONITOR is not None:
        RARE_TAIL_TIMING_MONITOR.write_summary()
    glyph_keywords = None
    if str(getattr(args, "janus_glyph_keywords", "") or "").strip():
        merged = list(JanusGlyphObserver.DEFAULT_KEYWORDS)
        merged.extend(x.strip() for x in str(args.janus_glyph_keywords).split(",") if x.strip())
        glyph_keywords = merged
    JANUS_GLYPH_OBSERVER = None if bool(args.disable_janus_glyph_observer) else JanusGlyphObserver(
        args.janus_glyph_events,
        args.janus_glyph_csv,
        args.janus_glyph_summary,
        args.janus_glyph_min_len,
        args.janus_glyph_accepted_link_min_z,
        glyph_keywords,
        args.proofs_dir,
    )
    if JANUS_GLYPH_OBSERVER is not None:
        JANUS_GLYPH_OBSERVER.write_summary()
    v31_import_previous_state(args, None)

    write_lockbox(args.lockbox, args, cfgs, workers, source_sha16)
    csvlog = CsvLog(args.csv_log)
    install_session_atexit()
    update_session_state(
        active=True,
        summary_path=args.session_summary,
        started_wall=time.time(),
        started_at_utc=utc_stamp_iso(),
        version=VERSION,
        sentinel=SENTINEL,
        source_sha256_16=source_sha16,
        mode=args.mode,
        host=f"{args.host}:{args.port}",
        user=args.user,
        workers=workers,
        batch=args.batch,
        matrix=args.matrix,
        requested_local_submit_z=args.local_submit_z,
        proofs_dir=args.proofs_dir,
        janus_brain=args.janus_brain,
        registry_dir=args.registry_dir,
        stale_guard=bool(args.stale_guard),
        csv_log=args.csv_log,
        proof_dashboard=args.proof_dashboard,
        rare_tail_timing_monitor=not bool(args.disable_rare_tail_timing_monitor),
        rare_tail_timing_dashboard=args.rare_tail_timing_dashboard,
        rare_tail_timing_events=args.rare_tail_timing_events,
        rare_tail_timing_csv=args.rare_tail_timing_csv,
        rare_tail_timing_min_z=args.rare_tail_timing_min_z,
        janus_glyph_observer=not bool(args.disable_janus_glyph_observer),
        janus_glyph_summary=args.janus_glyph_summary,
        janus_glyph_events=args.janus_glyph_events,
        janus_glyph_csv=args.janus_glyph_csv,
        janus_glyph_min_len=args.janus_glyph_min_len,
        janus_glyph_accepted_link_min_z=args.janus_glyph_accepted_link_min_z,
        endurance_oracle=not bool(args.disable_endurance_oracle),
        v31_strategy_mix=dict(normalized_lane_weights(args)),
        v31_strategy_rates=args.strategy_rates,
        v31_tail_events=args.tail_events,
        v31_dual_lock_memory=args.dual_lock_memory,
        v31_import_v30_state=bool(args.import_v30_state),
        a9_accounting_dashboard=args.a9_accounting_dashboard,
        a9_accounting_enabled=not bool(args.disable_a9_accounting),
        witchhunter_dashboard=args.witchhunter_dashboard,
        witchhunter_events=args.witchhunter_events,
        witchhunter_enabled=not bool(args.disable_witchhunter),
    )

    client = StratumClient(args.host, args.port, args.tls, args.user, args.password, args.subscribe_tag, proof_dir=args.proofs_dir)

    global V32_NETWORK_RECOVERY
    V32_NETWORK_RECOVERY = V32NetworkRecovery(args.reconnect_initial_backoff, args.reconnect_max_backoff)
    V32_NETWORK_RECOVERY.enabled = bool(args.enable_reconnect)
    if args.enable_reconnect:
        V32_NETWORK_RECOVERY.connect_sequence(client, args, reason="startup")
    else:
        client.connect()
        client.subscribe()
        if not args.no_suggest_diff:
            client.suggest_difficulty(args.suggest_diff)
        client.authorize()
        wait_initial_job(client)

    # After Stratum init, continue local counters from V30 snapshots so V31 does not
    # start its dashboard/proof-rate view from zero. Protocol state is unaffected.
    v31_import_previous_state(args, client)

    memory = KombuchaMemory(STRATEGIES, SECTORS, [c.name for c in cfgs])
    stride_bandit = ZimStrideBandit(path=args.stride_memory)
    notify_oracle = NotifyOracle()
    proofmind = JanusProofMind(args.janus_brain, args.registry_dir, args.mode)
    proofmind.write_meta_rules(args, cfgs)
    endurance = EnduranceOracle(
        dashboard_path=args.proof_dashboard,
        max_batch_factor=args.max_batch_factor,
        min_batch_factor=args.min_batch_factor,
        cooldown_drop_ratio=args.cooldown_drop_ratio,
        prune_after_observations=args.prune_after_observations,
        prune_min_best_z=args.prune_min_best_z,
        sector_lock=bool(args.sector_lock),
    )
    # IO-path build: create visible V31 files immediately, not after round 5/100.
    try:
        endurance.write_dashboard(args, client, 0, 0.0, int(SESSION_STATE.get("v30_imported_best_z", 0) or 0), proofmind)
        if V31_RATEBOOK is not None:
            V31_RATEBOOK.save(force=True)
        if V31_DUALLOCK_MEMORY is not None:
            V31_DUALLOCK_MEMORY.save(force=True)
        if A9_ACCOUNTING is not None:
            A9_ACCOUNTING.set_runtime_state(0, 0.0, endurance, proofmind)
            A9_ACCOUNTING.write_dashboard(args, client, endurance, proofmind)
        write_session_summary(args.session_summary)
        log("io", "initial dashboard/session/ratebook/a9-accounting files written")
    except Exception as e:
        log("io", f"initial artifact write skipped: {e}")
    rng = random.Random(stable_seed(SENTINEL, time.time_ns(), os.getpid()))

    round_id = 0
    base_batch = int(args.batch)
    local_submit_z = max(0, int(args.local_submit_z))
    last_reject_seen = client.rejected
    last_accept_seen = client.accepted
    last_accept_wall = time.time()
    last_watchdog_wall = 0.0
    last_summary_wall = 0.0
    learned_floor_z = 0
    floor_z_hint = difficulty_to_z_ceiling(args.lowdiff_floor_diff) if args.lowdiff_floor_diff > 0 else 0

    if args.auto_escalate_local_z or args.lowdiff_jump_to_floor:
        log("autodiff", f"V24 submit gate starts at local_submit_z={local_submit_z}; auto_escalate={args.auto_escalate_local_z} lowdiff_jump={args.lowdiff_jump_to_floor} floor_diff={args.lowdiff_floor_diff:g} floor_z~{floor_z_hint}")
    else:
        log("autodiff", f"NoEscalate mode={args.mode}: requested_local_submit_z={local_submit_z}; auto_escalate=False lowdiff_jump=False. Effective submit gate still follows the pool target, so if pool_diff=65536 then effective_z~48 and z<48 will not be submitted.")
    log("truthgate", "default submit path is canonical/pool-reconstructable only; extended cfgs may mine for telemetry but are skipped before submit")
    log("noncewire", "canonical submit nonce is big-endian uint32 hex; pool mirror verifies reconstructed LE header bytes before submit")
    log("zimcore", "V31 lock: prevhash mirror remains NerdMiner/Zim reverse_word_bytes(prevhash); header/submit bytes are not changed from accepted V26/V27/V28/V29/V30")
    log("endurance", "V31 oracle touches only scheduler lanes, DualLock weights, batch pressure, pruning, tail metrics, dashboard; wire bytes remain frozen")

    # On Windows, every function used by ProcessPoolExecutor must be top-level.
    with cf.ProcessPoolExecutor(max_workers=workers) as pool:
        while True:
            round_id += 1
            if args.max_rounds and round_id > args.max_rounds:
                log("done", f"max_rounds={args.max_rounds}")
                write_session_summary(args.session_summary)
                return

            # Keep the Stratum side alive.
            network_recovered_this_round = False
            try:
                client.read_available(max_messages=100, timeout=args.read_timeout)
            except Exception as e:
                log("v32_net", f"read failed: {e}; reconnect needed")
                if not args.enable_reconnect:
                    raise
                V32_NETWORK_RECOVERY.recover(client, args, reason=f"read_failed:{type(e).__name__}:{e}")
                network_recovered_this_round = True
                continue

            if not client.job:
                log("stratum", "no job yet")
                time.sleep(0.5)
                continue

            job = client.job
            if JANUS_GLYPH_OBSERVER is not None:
                JANUS_GLYPH_OBSERVER.observe_job(job, extranonce1=client.extranonce1)
            if not args.disable_notify_oracle:
                notify_oracle.update(job)
                if notify_oracle.should_pause(args.notify_pause_window_ms):
                    log("notify", f"oracle pause before expected clean job; {notify_oracle.line()}")
                    time.sleep(0.01)
                    continue
            pool_target = difficulty_to_target(client.pool_diff)
            pool_z = target_to_z_approx(pool_target)
            net_target = compact_bits_to_target(job.nbits)
            net_z = target_to_z_approx(net_target) if net_target else 0.0

            proofmind.update_mode(client.accepted, client.rejected, round_id, client.pool_diff)
            raw_batch = memory.next_batch(base_batch, client.accepted, client.rejected)
            if args.disable_endurance_oracle:
                batch_factor = proofmind.batch_factor()
            else:
                batch_factor = endurance.factor_multiplier(proofmind)
            batch = max(10_000, min(2_000_000, int(raw_batch * batch_factor)))

            effective_submit_z = compute_effective_submit_z(args.mode, local_submit_z, learned_floor_z, pool_z)
            prelog_round = (not args.quiet) and ((not args.longrun) or (round_id % max(1, args.summary_every_rounds) == 1))
            if prelog_round:
                log(
                    "round",
                    f"id={round_id} job={job.job_id} seq={job.seq} pool_diff={client.pool_diff:g} "
                    f"pool_z~{pool_z:.2f} requested_local_z={local_submit_z} effective_submit_z={effective_submit_z} "
                    f"effective_diff~{z_to_difficulty(effective_submit_z):.6g} "
                    f"net_z~{net_z:.2f} tasks={workers} batch={batch:,}",
                )

            tasks: List[MineTask] = []
            for wid in range(workers):
                st, sec, cfg, lane = choose_v31_task(args, proofmind, endurance, memory, V31_DUALLOCK_MEMORY, rng, cfgs, round_id, wid)
                seed = stable_seed(job.job_id, job.seq, round_id, wid, st, sec, cfg.name, lane)
                stride_arm, stride = stride_bandit.choose(rng, seed) if st in ("zim_reverse", "zim_bandit") else (-1, 0)
                tasks.append(
                    MineTask(
                        round_id=round_id,
                        worker_id=wid,
                        job=job,
                        extranonce1=client.extranonce1,
                        extranonce2_size=client.extranonce2_size,
                        pool_diff=client.pool_diff,
                        batch=batch,
                        strategy=st,
                        sector=sec,
                        cfg=cfg,
                        seed=seed,
                        submit_limit=max(0, int(args.submit_limit_per_worker)),
                        signal_z=args.signal_z,
                        local_submit_z=effective_submit_z,
                        lane=lane,
                        stride=stride,
                        stride_arm=stride_arm,
                    )
                )

            futs = [pool.submit(mine_task, t) for t in tasks]
            results: List[MineResult] = []
            candidates: List[Dict[str, Any]] = []

            # While CPU workers run, periodically read stratum messages.
            pending = set(futs)
            while pending:
                done, pending = cf.wait(pending, timeout=0.2, return_when=cf.FIRST_COMPLETED)
                try:
                    client.read_available(max_messages=20, timeout=0.0)
                except Exception as e:
                    log("v32_net", f"read during round failed: {e}")
                    if not args.enable_reconnect:
                        raise
                    V32_NETWORK_RECOVERY.recover(client, args, reason=f"round_read_failed:{type(e).__name__}:{e}")
                    network_recovered_this_round = True
                for fut in done:
                    r = fut.result()
                    results.append(r)
                    memory.update_result(r)
                    score_observe_result(r)
                    if V31_RATEBOOK is not None:
                        V31_RATEBOOK.observe_result(r)
                    proofmind.observe_result(r)
                    stride_bandit.observe(r.stride_arm, r.best_z, len(r.candidates), 0, 0)
                    candidates.extend(r.candidates)
                    if V31_TAIL_TRACKER is not None:
                        for _cand in r.candidates:
                            V31_TAIL_TRACKER.observe_candidate(_cand, accepted=None)

                    if r.error:
                        log("worker", f"worker={r.worker_id} cfg={r.cfg_name} error={r.error.splitlines()[-1]}")
                    if not (args.longrun or args.quiet):
                        log(
                            "lab",
                            f"lane={getattr(r, 'lane', 'unknown')} strategy={r.strategy} cfg={r.cfg_name} sector={r.sector} worker={r.worker_id} "
                            f"checked={r.checked:,} best_z={r.best_z} stride={r.stride if r.stride else 0} arm={r.stride_arm} hps={r.hps:,.0f}",
                        )

            total_checked = sum(r.checked for r in results)
            total_hps = sum(r.hps for r in results)
            if results:
                best = max(results, key=lambda r: r.best_z)
            else:
                best = MineResult(round_id=round_id, worker_id=-1, strategy="none", sector=-1, cfg_name="none", lane="none", checked=0, best_z=0, best_hash="", best_nonce=0, hps=0.0, candidates=[])

            if A9_ACCOUNTING is not None:
                A9_ACCOUNTING.set_runtime_state(round_id, total_hps, endurance, proofmind)
                for _r in results:
                    A9_ACCOUNTING.observe_result(_r)

            if candidates and network_recovered_this_round and bool(getattr(args, "drop_round_candidates_after_reconnect", True)):
                if V32_NETWORK_RECOVERY is not None:
                    V32_NETWORK_RECOVERY.stale_round_drops += len(candidates)
                log("v32_net", f"dropped {len(candidates)} old-round candidates after reconnect; waiting for fresh notify/job")
                if WITCH_HUNTER is not None:
                    for _cand in candidates:
                        WITCH_HUNTER.observe_reconnect_drop(_cand, "old_round_after_reconnect")
                candidates = []

            if candidates:
                before_acc = client.accepted
                before_rej = client.rejected
                try:
                    submit_candidates(client, job, candidates, cfg_by_name, allow_noncanonical_submit=bool(args.allow_noncanonical_submit), stale_guard=bool(args.stale_guard))
                except Exception as e:
                    log("v32_net", f"submit/read response failed: {e}; reconnecting and dropping pending submits")
                    if not args.enable_reconnect:
                        raise
                    V32_NETWORK_RECOVERY.recover(client, args, reason=f"submit_failed:{type(e).__name__}:{e}")
                    candidates = []
                    before_acc = client.accepted
                    before_rej = client.rejected
                # Let submit responses arrive.
                t_end = time.time() + 2.0
                while time.time() < t_end and client.pending_submits:
                    try:
                        client.read_available(max_messages=50, timeout=0.2)
                    except Exception as e:
                        log("v32_net", f"read submit response failed: {e}; reconnecting and clearing pending submits")
                        if not args.enable_reconnect:
                            raise
                        V32_NETWORK_RECOVERY.recover(client, args, reason=f"submit_response_read_failed:{type(e).__name__}:{e}")
                        break
                # Update memory on what happened.
                acc_delta = client.accepted - before_acc
                rej_delta = client.rejected - before_rej
                proofmind.observe_submit_delta(acc_delta, rej_delta, best)
                if acc_delta > 0:
                    last_accept_wall = time.time()
                    for _ in range(acc_delta):
                        memory.on_submit_result(True)
                        stride_bandit.observe(stride_bandit.last_arm, best.best_z, 1, 1, 0)
                    stride_bandit.save(force=True)
                    log("proofpack", f"accepted_delta={acc_delta}; stride memory saved immediately")
                    # V31 ProofMind: accepted shares never raise/relax the submit gate in lab/proof/lottery.
                    # The gate only changes on explicit reject-driven auto-escalation.
                    log("proofmind", f"accepted_delta={acc_delta}; gate unchanged mode={args.mode} local_submit_z={local_submit_z}; {proofmind.line()}")
                if rej_delta > 0:
                    for _ in range(rej_delta):
                        memory.on_submit_result(False)
                        stride_bandit.observe(stride_bandit.last_arm, best.best_z, 0, 0, 1)
                    if args.auto_escalate_local_z:
                        steps = max(1, math.ceil(rej_delta / max(1, int(args.escalate_after_rejects))))
                        old_z = local_submit_z
                        floor_z = difficulty_to_z_ceiling(args.lowdiff_floor_diff) if args.lowdiff_floor_diff > 0 else 0
                        if args.lowdiff_jump_to_floor and floor_z > local_submit_z:
                            learned_floor_z = max(learned_floor_z, floor_z)
                            local_submit_z = min(int(args.max_local_submit_z), max(local_submit_z, learned_floor_z))
                            reason = f"jump_to_pool_floor diff~{args.lowdiff_floor_diff:g}"
                        else:
                            local_submit_z = min(int(args.max_local_submit_z), local_submit_z + int(args.escalate_step_z) * steps)
                            reason = "step"
                        if local_submit_z != old_z:
                            approx_diff = z_to_difficulty(local_submit_z)
                            log("autodiff", f"Difficulty too low x{rej_delta}: {reason}; local_submit_z {old_z}->{local_submit_z} local_diff~{approx_diff:.6g}")
                            eta = fmt_duration(expected_share_seconds(max(1.0, approx_diff), max(1.0, total_hps)))
                            log("autodiff", f"at current hps~{total_hps:,.0f}, expected share at local_diff~{approx_diff:.6g} is about {eta}")
                            if not args.no_suggest_local_diff and not args.no_suggest_diff and math.isfinite(approx_diff):
                                try:
                                    client.suggest_difficulty(max(float(client.pool_diff), float(approx_diff)))
                                    log("autodiff", f"sent mining.suggest_difficulty {max(float(client.pool_diff), float(approx_diff)):.6g}")
                                except Exception as e:
                                    log("autodiff", f"suggest_difficulty failed: {e}")

            if not args.disable_endurance_oracle:
                endurance.observe_round(round_id, total_checked, total_hps, client.accepted, client.rejected, best.best_z, proofmind)

            if A9_ACCOUNTING is not None:
                A9_ACCOUNTING.set_runtime_state(round_id, total_hps, endurance, proofmind)
                A9_ACCOUNTING.write_dashboard(args, client, endurance, proofmind)

            if (client.accepted != last_accept_seen) or (client.rejected != last_reject_seen) or (round_id % 10 == 0):
                proofmind.save(force=True)
                last_accept_seen = client.accepted
                last_reject_seen = client.rejected

            now_wall = time.time()
            watchdog_seconds = max(1.0, float(args.watchdog_minutes) * 60.0)
            if args.watchdog_minutes > 0 and (now_wall - last_accept_wall) >= watchdog_seconds and (now_wall - last_watchdog_wall) >= min(300.0, watchdog_seconds):
                log(
                    "watchdog",
                    f"WARN: no accepted shares for {(now_wall-last_accept_wall)/60.0:.1f} minutes. "
                    f"Wire config unchanged. Current effective_submit_z={compute_effective_submit_z(args.mode, local_submit_z, learned_floor_z, pool_z)} "
                    f"pool_diff={client.pool_diff:g} acc={client.accepted} rej={client.rejected}.",
                )
                last_watchdog_wall = now_wall

            should_summary = (not args.quiet) and (
                (not args.longrun)
                or (round_id % max(1, args.summary_every_rounds) == 0)
                or ((now_wall - last_summary_wall) >= max(1, args.summary_every_seconds))
            )
            if should_summary:
                active_gate_z = compute_effective_submit_z(args.mode, local_submit_z, learned_floor_z, pool_z)
                top3 = top_strategy_scoreboard(3)
                top3_s = "; ".join(f"{x.get('key')} acc={x.get('accepted')} best_z={x.get('best_z')}" for x in top3) or "none"
                log(
                    "summary",
                    f"round={round_id} checked={total_checked:,} hps~{total_hps:,.0f} "
                    f"best_z={best.best_z} requested_local_z={local_submit_z} effective_submit_z={active_gate_z} "
                    f"best={best.strategy}/s{best.sector}/w{best.worker_id}/{best.cfg_name} "
                    f"hash={mask_hex(best.best_hash, 40)} sub={client.submitted} acc={client.accepted} rej={client.rejected}",
                )
                log("scoreboard", f"top3 {top3_s}")
                if V31_RATEBOOK is not None:
                    log("v31_rates", V31_RATEBOOK.line())
                if V31_DUALLOCK_MEMORY is not None:
                    log("duallock", V31_DUALLOCK_MEMORY.line())
                if A9_ACCOUNTING is not None:
                    log("a9", A9_ACCOUNTING.line())
                log("proofmind", proofmind.line())
                if not args.disable_endurance_oracle:
                    log("endurance", endurance.line())
                if total_hps > 0:
                    eta_pool = fmt_duration(expected_share_seconds(max(1e-12, float(client.pool_diff)), total_hps))
                    gate_diff = max(1e-12, z_to_difficulty(active_gate_z))
                    eta_gate = fmt_duration(expected_share_seconds(gate_diff, total_hps))
                    log("eta", f"pool_eta@diff={client.pool_diff:g}~{eta_pool}; gate_eta@z={active_gate_z}/diff~{gate_diff:.6g}~{eta_gate}; hps~{total_hps:,.0f}")
                next_batch = memory.next_batch(base_batch, client.accepted, client.rejected)
                log("kombucha", memory.line(next_batch))
                log("zimcore", f"{stride_bandit.line()} {notify_oracle.line()}")
                last_summary_wall = now_wall

            stride_bandit.save()

            update_session_state(
                round=round_id,
                pool_diff=client.pool_diff,
                pool_z=f"{pool_z:.3f}",
                effective_submit_z=effective_submit_z,
                requested_local_submit_z=local_submit_z,
                submitted=client.submitted,
                accepted=client.accepted,
                rejected=client.rejected,
                best_z=max(int(SESSION_STATE.get("best_z", 0) or 0), int(best.best_z or 0)),
                last_hps=int(total_hps),
                top_strategy_scoreboard=top_strategy_scoreboard(10),
                janus_mode=proofmind.mode,
                janus_mode_strength=f"{proofmind.mode_strength:.3f}",
                janus_hunger=f"{proofmind.hunger:.3f}",
                proofmind_best_combo=proofmind.best_combo,
                proofmind_best_z=proofmind.best_z_seen,
                endurance_hps_ewma=int(endurance.hps_ewma) if not args.disable_endurance_oracle else 0,
                endurance_best_hps_ewma=int(endurance.best_hps_ewma) if not args.disable_endurance_oracle else 0,
                endurance_cooldown=bool(endurance.cooldown) if not args.disable_endurance_oracle else False,
                accepted_per_mh=endurance.accepted_per_mh(client.accepted) if not args.disable_endurance_oracle else 0.0,
                proof_dashboard=args.proof_dashboard,
                v31_strategy_rates=args.strategy_rates,
                v31_tail_events=args.tail_events,
                rare_tail_timing_monitor=not bool(args.disable_rare_tail_timing_monitor),
                rare_tail_timing_dashboard=getattr(args, "rare_tail_timing_dashboard", ""),
                rare_tail_timing_events=getattr(args, "rare_tail_timing_events", ""),
                rare_tail_timing_csv=getattr(args, "rare_tail_timing_csv", ""),
                rare_tail_timing=RARE_TAIL_TIMING_MONITOR.summary() if RARE_TAIL_TIMING_MONITOR is not None else {},
                janus_glyph_observer=not bool(args.disable_janus_glyph_observer),
                janus_glyph_summary=getattr(args, "janus_glyph_summary", ""),
                janus_glyph_events=getattr(args, "janus_glyph_events", ""),
                janus_glyph_csv=getattr(args, "janus_glyph_csv", ""),
                janus_glyph=JANUS_GLYPH_OBSERVER.summary() if JANUS_GLYPH_OBSERVER is not None else {},
                v31_strategy_mix=dict(normalized_lane_weights(args)),
                v31_tail_tracker=V31_TAIL_TRACKER.summary() if V31_TAIL_TRACKER is not None else {},
                v31_ratebook_top=V31_RATEBOOK.rows_list()[:10] if V31_RATEBOOK is not None else [],
                v31_dual_lock_memory=V31_DUALLOCK_MEMORY.line() if V31_DUALLOCK_MEMORY is not None else "",
                a9_accounting_dashboard=getattr(args, "a9_accounting_dashboard", ""),
                a9_accounting=A9_ACCOUNTING.summary(args, client, endurance, proofmind).get("comparison_gate", {}) if A9_ACCOUNTING is not None else {},
                witchhunter_dashboard=getattr(args, "witchhunter_dashboard", ""),
                witchhunter=WITCH_HUNTER.summary() if WITCH_HUNTER is not None else {},
                v32_network_recovery=V32_NETWORK_RECOVERY.snapshot(client) if V32_NETWORK_RECOVERY is not None else {},
                v32_tachyon_backlog="design_only_not_enabled",
            )
            if not args.disable_endurance_oracle and ((round_id % 5 == 0) or (client.accepted != last_accept_seen) or should_summary):
                endurance.write_dashboard(args, client, round_id, total_hps, int(SESSION_STATE.get("best_z", best.best_z) or best.best_z), proofmind)
            if V31_RATEBOOK is not None and ((round_id % 5 == 0) or should_summary):
                V31_RATEBOOK.save()
            if V31_DUALLOCK_MEMORY is not None and ((round_id % 25 == 0) or should_summary):
                V31_DUALLOCK_MEMORY.save()
            if WITCH_HUNTER is not None and ((round_id % 5 == 0) or should_summary):
                WITCH_HUNTER.write()
            if round_id % 100 == 0:
                write_session_summary(args.session_summary)

            csvlog.write_round(
                {
                    "ts": int(time.time()),
                    "round": round_id,
                    "job": job.job_id,
                    "seq": job.seq,
                    "pool_diff": client.pool_diff,
                    "pool_z": f"{pool_z:.3f}",
                    "requested_local_z": local_submit_z,
                    "effective_submit_z": compute_effective_submit_z(args.mode, local_submit_z, learned_floor_z, pool_z),
                    "effective_submit_diff": f"{z_to_difficulty(compute_effective_submit_z(args.mode, local_submit_z, learned_floor_z, pool_z)):.6g}",
                    "matrix": args.matrix,
                    "mode": args.mode,
                    "pool_eta_seconds": expected_share_seconds(max(1e-12, float(client.pool_diff)), max(1.0, total_hps)),
                    "gate_eta_seconds": expected_share_seconds(max(1e-12, z_to_difficulty(effective_submit_z)), max(1.0, total_hps)),
                    "workers": workers,
                    "batch": batch,
                    "checked": total_checked,
                    "hps": int(total_hps),
                    "best_z": best.best_z,
                    "best_lane": getattr(best, "lane", "unknown"),
                    "best_strategy": best.strategy,
                    "best_sector": best.sector,
                    "best_worker": best.worker_id,
                    "best_cfg": best.cfg_name,
                    "submitted": client.submitted,
                    "accepted": client.accepted,
                    "rejected": client.rejected,
                }
            )


if __name__ == "__main__":
    # Required for Windows multiprocessing.
    try:
        import multiprocessing as mp
        mp.freeze_support()
    except Exception:
        pass

    try:
        main()
    except KeyboardInterrupt:
        print("\n[Rblganul] stopped by user", flush=True)
