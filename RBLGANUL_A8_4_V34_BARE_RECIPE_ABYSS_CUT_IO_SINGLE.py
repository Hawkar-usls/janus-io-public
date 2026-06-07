#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBLGANUL V33 TACHYON SHADOW ORACLE SINGLE
2026-05-28

Goal:
  1) Use all CPU cores by default.
  2) Mine Stratum V1 work from a lottery-style NerdMiner solo pool by default.
  3) Treat zbits as rarity logs, not as SHA direction signals.
  4) Fix/diagnose the core problem seen in V19/V20/V22 logs:
       local "pool_pass=True" but pool rejects with "Difficulty too low".
  5) V24 NonceWire: canonical header still uses LE nonce bytes, but Stratum submit
     sends nonce as big-endian integer hex so the pool reconstructs the same header.
  6) V24 TruthGate: submit only pool-reconstructable canonical headers by default.
  7) AutoStart profile: pool.nerdminers.org:3333, wallet worker RblganulV31,
     no forced pool-diff suggestion, local_submit_z=0, with auto-escalation disabled.
  8) ZimCore imports the useful mechanics from Zim.ino: NerdMiner subscribe tag,
     LE extranonce2 sequence, reverse odd-stride nonce walk, online stride bandit,
     notify-cadence pause, canonical NonceWire TruthGate, and persistent stride memory.

Run on PC:
  python RBLGANUL_V33_ALLOCATOR_REVIEW_IO_SINGLE.py

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
  --host pool.nerdminers.org --port 3333 --user JANUS_PUBLIC_WORKER.RblganulV31 --password x
  --suggest-diff 1.0 --local-submit-z 0 --no-auto-escalate-local-z --no-lowdiff-jump-to-floor --matrix canonical

Optional:
  python RBLGANUL_V31_DUALLOCK_ORACLE_SINGLE.py --workers 16 --batch 100000

Important:
  This is an experimental harness. It does not break SHA-256.
  It measures and submits shares according to Stratum job data.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import decimal
import hashlib
import json
import math
import os
import random
import select
import socket
import ssl
import struct
import sys
import time
import traceback
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


VERSION = "Rblganul A8.4/V34 Bare Recipe Abyss Cut IO SINGLE 20260602_BARE_RECIPE_ABYSS"
SENTINEL = "RBLGANUL_A8_4_V34_BARE_RECIPE_ABYSS_CUT_IO_SINGLE_20260602_BARE_RECIPE_ABYSS"

DEFAULT_HOST = "pool.nerdminers.org"
DEFAULT_PORT = 3333
DEFAULT_TLS = False

# From your previous logs.
DEFAULT_USER = "JANUS_PUBLIC_WORKER.RblganulV34"
DEFAULT_PASSWORD = "x"
DIAGNOSTIC_LABEL = "zimcore"

U256_MAX = (1 << 256) - 1

# Bitcoin difficulty-1 target.
DIFF1_TARGET = int(
    "00000000ffff0000000000000000000000000000000000000000000000000000", 16
)

STRATEGIES = ("zim_reverse", "zim_bandit", "linear", "random", "janus", "knight", "bitrev")
SECTORS = 12

DEFAULT_SUBSCRIBE_TAG = "NerdMinerV2/RblganulV34-BareRecipeAbyssCut"
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
V32_NETWORK_RECOVERY = None
V33_TACHYON_SHADOW = None
V33_ALLOCATOR_REVIEW = None
V34_FRESH_TAILGEX_REVIEW = None
V34_PROTECTED_EXPOSURE = None
V34_RECIPE_FOCUS = None
V34_DUPLICATE_SUBMIT_GUARD = None

JANUS_MODES = ("EXPLORE", "EXPLOIT", "SURVIVE", "CHAOS", "HUNT")
PROOFMIND_SCHEMA_VERSION = "v33-tachyon-shadow-registry-1"


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
        return "∞"
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
                        if V33_TACHYON_SHADOW is not None:
                            V33_TACHYON_SHADOW.observe_rejected(cand2)
                            V33_TACHYON_SHADOW.save()
                        if V34_FRESH_TAILGEX_REVIEW is not None:
                            V34_FRESH_TAILGEX_REVIEW.observe_rejected(cand2)
                            V34_FRESH_TAILGEX_REVIEW.save(V33_TACHYON_SHADOW, self)
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


class TachyonShadowMode:
    """V33 Tachyon Shadow Mode.

    Shadow means observe-only:
      - no scheduler weight changes
      - no header/nonce/extranonce2/prevhash/TruthGate/submit changes
      - no allocator decisions

    It measures tail density, signed tail excess, divergence magnitude, and a
    gamma-like feedback signal for lanes. The goal is to prepare a future V33/V34
    allocator without touching the live mining/wire path.
    """

    def __init__(
        self,
        path: str,
        window: int = 512,
        baseline_z: int = 23,
        thresholds: Optional[Iterable[int]] = None,
    ) -> None:
        self.path = str(path)
        self.window = max(32, int(window or 512))
        self.baseline_z = max(0, min(256, int(baseline_z or 23)))
        base = list(thresholds or (24, 25, 26, 28, 30, 32, 33, 34, 35, 36, 37, 38, 39, 40, 48, 64, 80, 96, 128, 160, 192, 224, 256))
        self.thresholds = tuple(sorted(set(max(0, min(256, int(x))) for x in base)))
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.recent: Deque[Dict[str, Any]] = deque(maxlen=self.window)
        self.accepted_total = 0
        self.rejected_total = 0
        self.candidate_total = 0
        self.result_observations = 0
        self.total_checked = 0
        self.best_z = 0
        self.started_at_utc = utc_stamp_iso()
        self.updated_at_utc = ""
        self.imported_paths: List[str] = []
        self.seen_accept_keys: set = set()
        self.load()

    @staticmethod
    def _safe_int(x: Any, default: int = 0) -> int:
        try:
            return int(x)
        except Exception:
            return default

    @staticmethod
    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _key(self, lane: Any, strategy: Any, sector: Any, cfg_name: Any, stride_arm: Any = None) -> str:
        lane_s = str(lane or "unknown")
        st_s = str(strategy or "unknown")
        cfg_s = str(cfg_name or "canonical")
        sec = self._safe_int(sector, 0) % SECTORS
        arm = self._safe_int(stride_arm, -999) if stride_arm is not None else -999
        if arm == -999:
            return f"{lane_s}::{st_s}/s{sec}/{cfg_s}"
        return f"{lane_s}::{st_s}/s{sec}/{cfg_s}/a{arm}"

    def _row(self, lane: Any, strategy: Any, sector: Any, cfg_name: Any, stride_arm: Any = None) -> Dict[str, Any]:
        key = self._key(lane, strategy, sector, cfg_name, stride_arm)
        if key not in self.rows:
            row = {
                "key": key,
                "lane": str(lane or "unknown"),
                "strategy": str(strategy or "unknown"),
                "sector": self._safe_int(sector, 0) % SECTORS,
                "cfg_name": str(cfg_name or "canonical"),
                "stride_arm": self._safe_int(stride_arm, -1) if stride_arm is not None else -1,
                "checked": 0,
                "observations": 0,
                "candidate_count": 0,
                "accepted": 0,
                "rejected": 0,
                "best_z": 0,
                "hps_ewma": 0.0,
                "last_seen_utc": "",
            }
            for t in self.thresholds:
                row[f"result_z{t}"] = 0
                row[f"candidate_z{t}"] = 0
                row[f"accepted_z{t}"] = 0
            self.rows[key] = row
        return self.rows[key]

    def _accept_key(self, cand: Dict[str, Any]) -> str:
        return "|".join([
            str(cand.get("proof_path", "")),
            str(cand.get("job_id", "")),
            str(cand.get("nonce_submit_hex", "")),
            str(cand.get("zbits", cand.get("z", ""))),
            str(cand.get("hash", cand.get("display_hash", "")))[:24],
        ])

    def _touch_tail_counters(self, row: Dict[str, Any], prefix: str, z: int) -> None:
        for t in self.thresholds:
            if int(z) >= int(t):
                row[f"{prefix}_z{t}"] = int(row.get(f"{prefix}_z{t}", 0)) + 1

    def observe_result(self, r: Any) -> None:
        try:
            row = self._row(getattr(r, "lane", "unknown"), getattr(r, "strategy", "unknown"), getattr(r, "sector", 0), getattr(r, "cfg_name", "canonical"), getattr(r, "stride_arm", -1))
            checked = max(0, self._safe_int(getattr(r, "checked", 0), 0))
            z = max(0, min(256, self._safe_int(getattr(r, "best_z", 0), 0)))
            hps = max(0.0, self._safe_float(getattr(r, "hps", 0.0), 0.0))
            row["checked"] = int(row.get("checked", 0)) + checked
            row["observations"] = int(row.get("observations", 0)) + 1
            row["best_z"] = max(int(row.get("best_z", 0)), z)
            row["hps_ewma"] = hps if float(row.get("hps_ewma", 0.0)) <= 0 else float(row.get("hps_ewma", 0.0)) * 0.88 + hps * 0.12
            row["last_seen_utc"] = utc_stamp_iso()
            self._touch_tail_counters(row, "result", z)
            self.result_observations += 1
            self.total_checked += checked
            self.best_z = max(self.best_z, z)
            self.updated_at_utc = utc_stamp_iso()
            self.recent.append({"kind": "result", "key": row["key"], "z": z, "checked": checked, "hps": int(hps), "ts_utc": self.updated_at_utc})
        except Exception as e:
            try:
                log("tachyon", f"shadow observe_result skipped: {e}")
            except Exception:
                pass

    def observe_candidate(self, cand: Dict[str, Any], accepted: Optional[bool] = None) -> None:
        try:
            row = self._row(cand.get("lane", "unknown"), cand.get("strategy", "unknown"), cand.get("sector", 0), cand.get("cfg_name", "canonical"), cand.get("stride_arm", -1))
            z = max(0, min(256, self._safe_int(cand.get("zbits", cand.get("z", 0)), 0)))
            row["candidate_count"] = int(row.get("candidate_count", 0)) + 1
            row["best_z"] = max(int(row.get("best_z", 0)), z)
            row["last_seen_utc"] = utc_stamp_iso()
            self._touch_tail_counters(row, "candidate", z)
            self.candidate_total += 1
            self.best_z = max(self.best_z, z)
            self.updated_at_utc = utc_stamp_iso()
            self.recent.append({"kind": "candidate", "accepted": accepted, "key": row["key"], "z": z, "ts_utc": self.updated_at_utc})
        except Exception as e:
            try:
                log("tachyon", f"shadow observe_candidate skipped: {e}")
            except Exception:
                pass

    def observe_accepted(self, cand: Dict[str, Any]) -> None:
        try:
            key = self._accept_key(cand)
            if key in self.seen_accept_keys:
                return
            self.seen_accept_keys.add(key)
            row = self._row(cand.get("lane", "unknown"), cand.get("strategy", "unknown"), cand.get("sector", 0), cand.get("cfg_name", "canonical"), cand.get("stride_arm", -1))
            z = max(0, min(256, self._safe_int(cand.get("zbits", cand.get("z", 0)), 0)))
            row["accepted"] = int(row.get("accepted", 0)) + 1
            row["best_z"] = max(int(row.get("best_z", 0)), z)
            event_utc = str(cand.get("created_at_utc") or cand.get("accepted_at_utc") or utc_stamp_iso())
            row["last_seen_utc"] = event_utc
            self._touch_tail_counters(row, "accepted", z)
            self.accepted_total += 1
            self.best_z = max(self.best_z, z)
            self.updated_at_utc = utc_stamp_iso()
            self.recent.append({"kind": "accepted", "key": row["key"], "z": z, "ts_utc": event_utc, "imported": bool(cand.get("imported", False))})
        except Exception as e:
            try:
                log("tachyon", f"shadow observe_accepted skipped: {e}")
            except Exception:
                pass

    def observe_rejected(self, cand: Dict[str, Any]) -> None:
        try:
            row = self._row(cand.get("lane", "unknown"), cand.get("strategy", "unknown"), cand.get("sector", 0), cand.get("cfg_name", "canonical"), cand.get("stride_arm", -1))
            row["rejected"] = int(row.get("rejected", 0)) + 1
            row["last_seen_utc"] = utc_stamp_iso()
            self.rejected_total += 1
            self.updated_at_utc = utc_stamp_iso()
        except Exception:
            pass

    def import_accepted_index(self, proof_dir: str, label: str = "previous") -> Dict[str, Any]:
        out = {"label": label, "proof_dir": proof_dir, "imported": 0, "skipped": 0, "error": ""}
        try:
            if not proof_dir:
                return out
            proof_dir_s = str(Path(proof_dir).expanduser().resolve())
            if proof_dir_s in self.imported_paths:
                out["skipped"] = 1
                return out
            idx_path = Path(proof_dir_s) / "accepted_index.json"
            if not idx_path.exists():
                out["error"] = "accepted_index.json not found"
                return out
            obj = json.loads(idx_path.read_text(encoding="utf-8"))
            entries = obj.get("accepted", []) if isinstance(obj, dict) else []
            for ent in entries:
                if not isinstance(ent, dict):
                    continue
                cand = dict(ent)
                cand["zbits"] = cand.get("zbits", cand.get("z", 0))
                cand["imported"] = True
                self.observe_accepted(cand)
                out["imported"] += 1
            self.imported_paths.append(proof_dir_s)
            self.updated_at_utc = utc_stamp_iso()
        except Exception as e:
            out["error"] = str(e)
            try:
                log("tachyon", f"shadow import skipped: {e}")
            except Exception:
                pass
        return out

    def _global_tail_counts(self) -> Dict[str, int]:
        counts = {f"z{t}+": 0 for t in self.thresholds}
        for row in self.rows.values():
            for t in self.thresholds:
                counts[f"z{t}+"] += int(row.get(f"accepted_z{t}", 0) or 0)
        return counts

    def _tail_ratios(self) -> Dict[str, Dict[str, Any]]:
        counts = self._global_tail_counts()
        total = max(0, int(self.accepted_total))
        ratios: Dict[str, Dict[str, Any]] = {}
        for t in self.thresholds:
            actual = int(counts.get(f"z{t}+", 0))
            expected = 0.0
            if total > 0 and t >= self.baseline_z:
                expected = float(total) / float(2 ** (t - self.baseline_z))
            ratio = float(actual) / expected if expected > 0 else 0.0
            ratios[f"z{t}+"] = {
                "actual": actual,
                "expected": expected,
                "ratio": ratio,
                "signed_tail_excess": float(actual) - expected,
                "tail_divergence_magnitude": abs(float(actual) - expected),
            }
        return ratios

    def tail_signal_count(self) -> int:
        ratios = self._tail_ratios()
        sig = 0
        def ratio(name: str) -> float:
            return float(ratios.get(name, {}).get("ratio", 0.0) or 0.0)
        def actual(name: str) -> int:
            return int(ratios.get(name, {}).get("actual", 0) or 0)
        if ratio("z30+") >= 1.15: sig += 1
        if ratio("z32+") >= 1.20: sig += 1
        if ratio("z33+") >= 1.20: sig += 1
        if ratio("z34+") >= 1.20: sig += 1
        if ratio("z35+") >= 1.20 or actual("z35+") >= 1: sig += 1
        if actual("z36+") >= 1: sig += 1
        if actual("z37+") >= 1: sig += 1
        if actual("z38+") >= 1: sig += 1
        return sig

    def rows_list(self, limit: int = 20) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for row in self.rows.values():
            x = dict(row)
            mh = max(0.0, float(x.get("checked", 0) or 0) / 1_000_000.0)
            x["mh"] = mh
            x["accepted_per_mh"] = float(x.get("accepted", 0) or 0) / mh if mh > 0 else 0.0
            for t in self.thresholds:
                x[f"accepted_z{t}_per_mh"] = float(x.get(f"accepted_z{t}", 0) or 0) / mh if mh > 0 else 0.0
            rows.append(x)
        rows.sort(key=lambda r: (int(r.get("accepted_z38", 0)), int(r.get("accepted_z37", 0)), int(r.get("accepted_z36", 0)), int(r.get("accepted_z35", 0)), int(r.get("accepted_z34", 0)), int(r.get("accepted_z33", 0)), int(r.get("best_z", 0)), float(r.get("accepted_per_mh", 0.0))), reverse=True)
        return rows[:max(1, int(limit))]

    def snapshot(self, client: Optional[Any] = None, limit: int = 20) -> Dict[str, Any]:
        ratios = self._tail_ratios()
        return {
            "schema": "v33-tachyon-shadow-1",
            "enabled": True,
            "mode": "shadow_only",
            "changes_scheduler": False,
            "changes_wire": False,
            "wire_change_required": False,
            "path": self.path,
            "started_at_utc": self.started_at_utc,
            "updated_at_utc": self.updated_at_utc or utc_stamp_iso(),
            "baseline_z": self.baseline_z,
            "thresholds": list(self.thresholds),
            "total_checked": int(self.total_checked),
            "result_observations": int(self.result_observations),
            "candidate_total": int(self.candidate_total),
            "accepted_total_shadow": int(self.accepted_total),
            "rejected_total_shadow": int(self.rejected_total),
            "client_accepted": int(getattr(client, "accepted", 0)) if client is not None else None,
            "client_rejected": int(getattr(client, "rejected", 0)) if client is not None else None,
            "best_z": int(self.best_z),
            "tail_counts": self._global_tail_counts(),
            "tail_ratios": ratios,
            "tail_signal_count": self.tail_signal_count(),
            "top_lanes": self.rows_list(limit),
            "rows": self.rows,
            "recent": list(self.recent)[-min(32, len(self.recent)):],
            "imported_paths": list(self.imported_paths),
            "seen_accept_keys_count": len(self.seen_accept_keys),
            "allocator_enabled": False,
            "shadow_rule": "observe lane/tail/MH only; never alter scheduler or wire in V33-A",
        }

    def save(self, client: Optional[Any] = None, force: bool = False) -> None:
        try:
            obj = self.snapshot(client, limit=32)
            # Persist dedupe keys so restart/import does not double count previous proof indexes.
            obj["seen_accept_keys"] = sorted(list(self.seen_accept_keys))[-200000:]
            atomic_json(self.path, obj)
        except Exception as e:
            try:
                log("tachyon", f"shadow save failed: {e}")
            except Exception:
                pass

    def load(self) -> None:
        try:
            p = Path(self.path)
            if not p.exists():
                return
            obj = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(obj, dict):
                return
            self.started_at_utc = str(obj.get("started_at_utc") or self.started_at_utc)
            self.updated_at_utc = str(obj.get("updated_at_utc") or "")
            self.total_checked = int(obj.get("total_checked", self.total_checked) or 0)
            self.result_observations = int(obj.get("result_observations", self.result_observations) or 0)
            self.candidate_total = int(obj.get("candidate_total", self.candidate_total) or 0)
            self.accepted_total = int(obj.get("accepted_total_shadow", self.accepted_total) or 0)
            self.rejected_total = int(obj.get("rejected_total_shadow", self.rejected_total) or 0)
            self.best_z = int(obj.get("best_z", self.best_z) or 0)
            rows_obj = obj.get("rows")
            if isinstance(rows_obj, dict):
                for key, row in rows_obj.items():
                    if isinstance(row, dict):
                        self.rows[str(key)] = dict(row)
            else:
                rows = obj.get("top_lanes")
                if isinstance(rows, list):
                    for row in rows:
                        if isinstance(row, dict) and row.get("key"):
                            self.rows[str(row["key"])] = dict(row)
            self.imported_paths = list(obj.get("imported_paths", [])) if isinstance(obj.get("imported_paths", []), list) else []
            seen = obj.get("seen_accept_keys", [])
            if isinstance(seen, list):
                self.seen_accept_keys = set(str(x) for x in seen)
            log("tachyon", f"loaded shadow path={self.path} acc={self.accepted_total} best_z={self.best_z} lanes={len(self.rows)}")
        except FileNotFoundError:
            pass
        except Exception as e:
            try:
                log("tachyon", f"shadow load skipped: {e}")
            except Exception:
                pass

    def line(self) -> str:
        counts = self._global_tail_counts()
        return (
            f"shadow=ON acc={self.accepted_total} best_z={self.best_z} "
            f"signals={self.tail_signal_count()} "
            f"z33+={counts.get('z33+',0)} z34+={counts.get('z34+',0)} "
            f"z35+={counts.get('z35+',0)} z36+={counts.get('z36+',0)} "
            f"z37+={counts.get('z37+',0)} z38+={counts.get('z38+',0)} "
            "allocator=OFF wire=FROZEN"
        )



class AllocatorReviewOnly:
    """V33 allocator-review layer.

    IMPORTANT: review-only means:
      - allocator is NOT enabled
      - scheduler weights are NOT changed here
      - Stratum wire/header/nonce/extranonce/TruthGate are NOT changed
      - this class only reads Tachyon Shadow rows and writes a review artifact

    The output is a TailGEX-style ranking for a future manual allocator plan.
    """

    REVIEW_SCHEMA = "v33-allocator-review-only-1"

    def __init__(
        self,
        path: str,
        min_proofs: int = 15000,
        min_lane_accepted: int = 24,
        top_limit: int = 16,
        baseline_z: int = 23,
    ) -> None:
        self.path = str(path)
        self.min_proofs = max(1, int(min_proofs or 15000))
        self.min_lane_accepted = max(1, int(min_lane_accepted or 24))
        self.top_limit = max(1, int(top_limit or 16))
        self.baseline_z = max(0, min(256, int(baseline_z or 23)))
        self.started_at_utc = utc_stamp_iso()
        self.last_snapshot: Dict[str, Any] = {}
        self.last_written_at_utc = ""

    @staticmethod
    def _i(x: Any, default: int = 0) -> int:
        try:
            return int(x)
        except Exception:
            return default

    @staticmethod
    def _f(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _expected(self, accepted: int, z: int) -> float:
        if accepted <= 0 or z < self.baseline_z:
            return 0.0
        return float(accepted) / float(2 ** (int(z) - self.baseline_z))

    def _lane_metric(self, row: Dict[str, Any]) -> Dict[str, Any]:
        accepted = max(0, self._i(row.get("accepted", 0)))
        rejected = max(0, self._i(row.get("rejected", 0)))
        checked = max(0, self._i(row.get("checked", 0)))
        mh = float(checked) / 1_000_000.0 if checked > 0 else 0.0
        best_z = max(0, self._i(row.get("best_z", 0)))
        reject_rate = float(rejected) / max(1.0, float(accepted + rejected))

        # Weighted rare-tail score: z33..z38 matter most for allocator review.
        # z38 is not treated as magic; it is a strong but low-sample anchor.
        weights = {33: 1.0, 34: 1.35, 35: 1.85, 36: 2.60, 37: 3.60, 38: 5.00, 39: 7.00, 40: 9.00}
        tail_rows: Dict[str, Any] = {}
        weighted_excess = 0.0
        weighted_ratio_excess = 0.0
        high_tail_points = 0.0

        for z, w in weights.items():
            actual = max(0, self._i(row.get(f"accepted_z{z}", 0)))
            expected = self._expected(accepted, z)
            ratio = (float(actual) / expected) if expected > 0 else 0.0
            excess = float(actual) - expected
            if actual > 0:
                high_tail_points += w * math.log1p(actual)
            weighted_excess += w * excess
            if expected > 0:
                weighted_ratio_excess += w * (ratio - 1.0)
            tail_rows[f"z{z}+"] = {
                "actual": actual,
                "expected": expected,
                "ratio": ratio,
                "excess": excess,
            }

        # Confidence grows with sample size but never becomes absolute.
        confidence = min(1.0, math.sqrt(float(accepted) / float(max(1, self.min_lane_accepted * 4))))
        exposure = math.log1p(accepted) + 0.15 * math.log1p(mh)

        # TailGEX is a signed review signal, not an allocator command.
        tail_gamma = (weighted_excess / max(1.0, math.sqrt(float(max(1, accepted))))) + 0.10 * weighted_ratio_excess
        risk_penalty = 3.0 * reject_rate
        sample_penalty = 0.35 if accepted < self.min_lane_accepted else 0.0
        tail_gex = confidence * tail_gamma + 0.05 * exposure + 0.08 * high_tail_points - risk_penalty - sample_penalty

        if accepted < self.min_lane_accepted and best_z < 35:
            sign = "LOW_SAMPLE"
        elif tail_gex >= 0.75:
            sign = "POSITIVE"
        elif tail_gex <= -0.35:
            sign = "NEGATIVE"
        else:
            sign = "NEUTRAL"

        # Future manual test recommendation. This is not applied by the script.
        proposed = 0.0
        if sign == "POSITIVE":
            proposed = min(15.0, max(5.0, 5.0 + min(10.0, tail_gex * 2.0)))
        elif sign == "NEUTRAL" and best_z >= 36:
            proposed = 3.0

        return {
            "key": row.get("key", ""),
            "lane": row.get("lane", "unknown"),
            "strategy": row.get("strategy", "unknown"),
            "sector": self._i(row.get("sector", 0)),
            "cfg_name": row.get("cfg_name", "canonical"),
            "stride_arm": self._i(row.get("stride_arm", -1)),
            "accepted": accepted,
            "rejected": rejected,
            "reject_rate": reject_rate,
            "checked": checked,
            "mh": mh,
            "accepted_per_mh": float(accepted) / mh if mh > 0 else 0.0,
            "best_z": best_z,
            "confidence": confidence,
            "exposure": exposure,
            "tail_gamma": tail_gamma,
            "tail_gex": tail_gex,
            "sign": sign,
            "proposed_future_test_weight_percent": proposed,
            "apply_now": False,
            "tail": tail_rows,
            "wire_change_required": False,
        }

    def snapshot(self, shadow: Optional[TachyonShadowMode], client: Optional[Any] = None, endurance: Optional[Any] = None) -> Dict[str, Any]:
        now = utc_stamp_iso()
        shadow_snapshot: Dict[str, Any] = {}
        if shadow is not None:
            try:
                shadow_snapshot = shadow.snapshot(client, limit=max(32, self.top_limit))
            except Exception:
                shadow_snapshot = {}

        accepted_total = self._i(shadow_snapshot.get("accepted_total_shadow", 0))
        best_z = self._i(shadow_snapshot.get("best_z", 0))
        tail_counts = shadow_snapshot.get("tail_counts", {}) if isinstance(shadow_snapshot.get("tail_counts", {}), dict) else {}
        tail_ratios = shadow_snapshot.get("tail_ratios", {}) if isinstance(shadow_snapshot.get("tail_ratios", {}), dict) else {}

        rows_obj = shadow_snapshot.get("rows", {})
        if isinstance(rows_obj, dict):
            raw_rows = [r for r in rows_obj.values() if isinstance(r, dict)]
        else:
            raw_rows = [r for r in shadow_snapshot.get("top_lanes", []) if isinstance(r, dict)]

        lane_metrics = [self._lane_metric(r) for r in raw_rows]
        lane_metrics.sort(
            key=lambda r: (
                1 if r.get("sign") == "POSITIVE" else 0,
                float(r.get("tail_gex", 0.0)),
                int(r.get("best_z", 0)),
                int(r.get("accepted", 0)),
            ),
            reverse=True,
        )

        positive = [r for r in lane_metrics if r.get("sign") == "POSITIVE"]
        negative = [r for r in lane_metrics if r.get("sign") == "NEGATIVE"]
        low_sample = [r for r in lane_metrics if r.get("sign") == "LOW_SAMPLE"]

        # Review readiness is not allocator permission. It only means enough proof
        # material exists to write a dry plan.
        dashboard_reject_rate = float(getattr(client, "rejected", 0)) / max(1.0, float(getattr(client, "submitted", 0))) if client is not None else 0.0
        cooldown = bool(getattr(endurance, "cooldown", False)) if endurance is not None else False
        health_ok = (dashboard_reject_rate < 0.01) and (not cooldown)
        ready_for_review = bool(accepted_total >= self.min_proofs and health_ok)

        plan = {
            "mode": "review_only",
            "allocator_enabled": False,
            "ready_for_review": ready_for_review,
            "apply_any_weight_change_now": False,
            "wire_change_required": False,
            "min_proofs": self.min_proofs,
            "current_shadow_proofs": accepted_total,
            "missing_proofs_for_review": max(0, self.min_proofs - accepted_total),
            "recommended_action": (
                "WRITE DRY ALLOCATOR PLAN ONLY - KEEP V33 SHADOW RUNNING"
                if ready_for_review else
                "KEEP RUNNING V33 SHADOW MODE UNTIL REVIEW THRESHOLD"
            ),
            "future_manual_allocator_guardrails": {
                "initial_total_allocator_weight_percent": "5-10%, max 15%",
                "entropy_floor_percent": ">=35%",
                "single_lane_cap_percent": "<=8% at first test",
                "stop_if_reject_rate_above_percent": 1.0,
                "stop_if_cooldown_true": True,
                "stop_if_wire_change_required": True,
                "do_not_change": [
                    "header bytes",
                    "nonce endian",
                    "extranonce2 endian",
                    "prevhash word reverse",
                    "TruthGate",
                    "submit format",
                ],
            },
            "top_positive_candidates": positive[: self.top_limit],
            "top_ranked_lanes": lane_metrics[: self.top_limit],
            "negative_candidates": negative[: self.top_limit],
            "low_sample_watchlist": low_sample[: self.top_limit],
        }

        obj = {
            "schema": self.REVIEW_SCHEMA,
            "version": VERSION,
            "sentinel": SENTINEL,
            "enabled": True,
            "created_at_utc": self.started_at_utc,
            "written_at_utc": now,
            "path": self.path,
            "allocator_enabled": False,
            "allocator_review_only": True,
            "changes_scheduler": False,
            "changes_wire": False,
            "wire_change_required": False,
            "shadow_summary": {
                "accepted_total_shadow": accepted_total,
                "best_z": best_z,
                "tail_counts": tail_counts,
                "tail_ratios": tail_ratios,
                "tail_signal_count": shadow_snapshot.get("tail_signal_count"),
            },
            "health": {
                "dashboard_reject_rate": dashboard_reject_rate,
                "cooldown": cooldown,
                "health_ok_for_review": health_ok,
                "client_accepted": int(getattr(client, "accepted", 0)) if client is not None else None,
                "client_rejected": int(getattr(client, "rejected", 0)) if client is not None else None,
                "client_submitted": int(getattr(client, "submitted", 0)) if client is not None else None,
            },
            "allocator_review": plan,
        }
        self.last_snapshot = obj
        return obj

    def save(self, shadow: Optional[TachyonShadowMode], client: Optional[Any] = None, endurance: Optional[Any] = None, force: bool = False) -> None:
        try:
            obj = self.snapshot(shadow, client, endurance)
            atomic_json(self.path, obj)
            self.last_written_at_utc = obj.get("written_at_utc", utc_stamp_iso())
        except Exception as e:
            try:
                log("allocator_review", f"save failed: {e}")
            except Exception:
                pass

    def line(self) -> str:
        obj = self.last_snapshot or {}
        review = obj.get("allocator_review", {}) if isinstance(obj, dict) else {}
        shadow = obj.get("shadow_summary", {}) if isinstance(obj, dict) else {}
        top = review.get("top_ranked_lanes", []) if isinstance(review, dict) else []
        top_s = "none"
        if top:
            t = top[0]
            top_s = f"{t.get('strategy')}/s{t.get('sector')}/{t.get('cfg_name')} sign={t.get('sign')} gex={float(t.get('tail_gex', 0.0)):.3f} best_z={t.get('best_z')} acc={t.get('accepted')}"
        return (
            f"review=ON ready={bool(review.get('ready_for_review', False))} "
            f"proofs={int(shadow.get('accepted_total_shadow', 0) or 0)} "
            f"best_z={int(shadow.get('best_z', 0) or 0)} "
            f"allocator=OFF wire=FROZEN top={top_s}"
        )


class DuplicateSubmitGuard:
    """A8.2 pre-submit duplicate guard.

    Wire-neutral: it only prevents sending the exact same Stratum submit tuple
    twice inside the same live process/session.
    """

    def __init__(self, max_keys: int = 250000) -> None:
        self.max_keys = max(1024, int(max_keys or 250000))
        self.seen: set = set()
        self.order: Deque[str] = deque(maxlen=self.max_keys)
        self.dropped = 0

    def key(self, cand: Dict[str, Any]) -> str:
        return "|".join([
            str(cand.get("job_id", "")),
            str(cand.get("extranonce2", "")),
            str(cand.get("ntime", "")),
            str(cand.get("nonce_submit_hex", "")),
        ])

    def allow(self, cand: Dict[str, Any]) -> Tuple[bool, str]:
        k = self.key(cand)
        if k in self.seen:
            self.dropped += 1
            return False, k
        if len(self.order) >= self.max_keys and self.order:
            old = self.order.popleft()
            self.seen.discard(old)
        self.seen.add(k)
        self.order.append(k)
        return True, k

    def snapshot(self) -> Dict[str, Any]:
        return {
            "schema": "a8-2-duplicate-submit-guard-1",
            "enabled": True,
            "seen_keys": len(self.seen),
            "dropped_duplicates": int(self.dropped),
            "wire_change_required": False,
        }


class ProtectedExposureReview:
    """A8.3 / V34 lane-key unified fresh-only TailGEX + recipe audit layer.

    Observe-only:
      - no scheduler weight changes
      - no allocator enable
      - no header/nonce/extranonce2/submit/wire changes

    Purpose:
      - separate fresh_gex from imported/global_gex
      - expose actual checked/hash exposure per lane
      - watch historical champions like zim_reverse/s6/canonical
      - prevent stale imported lanes from becoming allocator candidates
    """

    SCHEMA = "a8-3-v34-lanekey-recipe-review-1"

    def __init__(
        self,
        path: str,
        baseline_z: int = 23,
        fresh_window_seconds: int = 6 * 3600,
        fresh_window_count: int = 2000,
        min_lane_accepted: int = 50,
        champion_exposure_floor: float = 0.15,
        stale_after_seconds: int = 6 * 3600,
        max_result_events: int = 50000,
        max_accept_events: int = 50000,
    ) -> None:
        self.path = str(path)
        self.baseline_z = max(0, min(256, int(baseline_z or 23)))
        self.fresh_window_seconds = max(60, int(fresh_window_seconds or 21600))
        self.fresh_window_count = max(100, int(fresh_window_count or 2000))
        self.min_lane_accepted = max(1, int(min_lane_accepted or 50))
        self.champion_exposure_floor = max(0.0, min(1.0, float(champion_exposure_floor or 0.15)))
        self.stale_after_seconds = max(60, int(stale_after_seconds or 21600))
        self.result_events: Deque[Dict[str, Any]] = deque(maxlen=max(1000, int(max_result_events or 50000)))
        self.accept_events: Deque[Dict[str, Any]] = deque(maxlen=max(1000, int(max_accept_events or 50000)))
        self.reject_events: Deque[Dict[str, Any]] = deque(maxlen=10000)
        self.accept_seen: set = set()
        self.started_at_utc = utc_stamp_iso()
        self.updated_at_utc = ""
        self.last_snapshot: Dict[str, Any] = {}
        self.load()

    @staticmethod
    def _i(x: Any, default: int = 0) -> int:
        try:
            return int(x)
        except Exception:
            return default

    @staticmethod
    def _f(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    @staticmethod
    def _utc_to_epoch(s: Any) -> float:
        try:
            txt = str(s or "").strip()
            if not txt:
                return 0.0
            return float(time.mktime(time.strptime(txt, "%Y-%m-%dT%H:%M:%SZ")))
        except Exception:
            return 0.0

    def _canonical_key(self, strategy: Any, sector: Any, cfg_name: Any = "canonical") -> str:
        st_s = str(strategy or "unknown")
        cfg_s = str(cfg_name or "canonical")
        sec = self._i(sector, 0) % SECTORS
        return f"{st_s}/s{sec}/{cfg_s}"

    def _recipe_key(self, lane: Any, strategy: Any, sector: Any, cfg_name: Any, worker_id: Any = -1, stride_arm: Any = -1, stride: Any = 0) -> str:
        # A8.3 Anti-Dispersion fix: recipe identity must include source lane,
        # strategy, sector, cfg, worker, stride arm, and concrete stride.
        # It is telemetry/scheduler-only and never changes Stratum wire bytes.
        lane_s = str(lane or "unknown")
        st_s = str(strategy or "unknown")
        cfg_s = str(cfg_name or "canonical")
        sec = self._i(sector, 0) % SECTORS
        wid = self._i(worker_id, -1)
        arm = self._i(stride_arm, -1)
        try:
            stride_i = int(stride or 0) & 0xFFFFFFFF
        except Exception:
            stride_i = 0
        return f"{lane_s}/{st_s}/s{sec}/{cfg_s}/w{wid}/a{arm}/stride{stride_i}"

    def _key(self, lane: Any, strategy: Any, sector: Any, cfg_name: Any, stride_arm: Any = None) -> str:
        # A8.3 fix: fresh TailGEX, ChampionWatch, and ProtectedExposure must agree
        # on the same canonical lane key. A8.1/A8.2 accidentally split the same
        # lane by source label/stride arm, which produced fake LOW_EXPOSURE and
        # top_fresh rows with acc=0. Recipe-level detail is preserved separately.
        return self._canonical_key(strategy, sector, cfg_name)

    def _accept_key(self, cand: Dict[str, Any]) -> str:
        return "|".join([
            str(cand.get("proof_path", "")),
            str(cand.get("job_id", "")),
            str(cand.get("extranonce2", "")),
            str(cand.get("ntime", "")),
            str(cand.get("nonce_submit_hex", "")),
            str(cand.get("display_hash", cand.get("hash", "")))[:32],
        ])

    def observe_result(self, r: Any) -> None:
        try:
            utc = utc_stamp_iso()
            ev = {
                "ts": time.time(),
                "ts_utc": utc,
                "key": self._key(getattr(r, "lane", "unknown"), getattr(r, "strategy", "unknown"), getattr(r, "sector", 0), getattr(r, "cfg_name", "canonical"), getattr(r, "stride_arm", -1)),
                "canonical_key": self._canonical_key(getattr(r, "strategy", "unknown"), getattr(r, "sector", 0), getattr(r, "cfg_name", "canonical")),
                "recipe_key": self._recipe_key(getattr(r, "lane", "unknown"), getattr(r, "strategy", "unknown"), getattr(r, "sector", 0), getattr(r, "cfg_name", "canonical"), getattr(r, "worker_id", -1), getattr(r, "stride_arm", -1), getattr(r, "stride", 0)),
                "selected_by": str(getattr(r, "selected_by", getattr(r, "lane", "unknown"))),
                "recipe_focus": bool(getattr(r, "recipe_focus", False)),
                "recipe_focus_name": str(getattr(r, "recipe_focus_name", "")),
                "source_recipe_key": str(getattr(r, "source_recipe_key", "")),
                "exact_worker_match": bool(getattr(r, "exact_worker_match", False)),
                "lane": str(getattr(r, "lane", "unknown")),
                "strategy": str(getattr(r, "strategy", "unknown")),
                "sector": self._i(getattr(r, "sector", 0)),
                "worker_id": self._i(getattr(r, "worker_id", -1)),
                "cfg_name": str(getattr(r, "cfg_name", "canonical")),
                "stride": self._i(getattr(r, "stride", 0)),
                "stride_arm": self._i(getattr(r, "stride_arm", -1)),
                "checked": max(0, self._i(getattr(r, "checked", 0))),
                "best_z": max(0, min(256, self._i(getattr(r, "best_z", 0)))),
                "hps": max(0.0, self._f(getattr(r, "hps", 0.0))),
            }
            self.result_events.append(ev)
            self.updated_at_utc = utc
        except Exception as e:
            try:
                log("fresh_tailgex", f"observe_result skipped: {e}")
            except Exception:
                pass

    def observe_accepted(self, cand: Dict[str, Any], proof_path: str = "") -> None:
        try:
            cand2 = dict(cand)
            if proof_path:
                cand2["proof_path"] = proof_path
            ak = self._accept_key(cand2)
            if ak in self.accept_seen:
                return
            self.accept_seen.add(ak)
            utc = utc_stamp_iso()
            ev = {
                "ts": time.time(),
                "ts_utc": utc,
                "key": self._key(cand2.get("lane", "unknown"), cand2.get("strategy", "unknown"), cand2.get("sector", 0), cand2.get("cfg_name", "canonical"), cand2.get("stride_arm", -1)),
                "canonical_key": self._canonical_key(cand2.get("strategy", "unknown"), cand2.get("sector", 0), cand2.get("cfg_name", "canonical")),
                "recipe_key": self._recipe_key(cand2.get("lane", "unknown"), cand2.get("strategy", "unknown"), cand2.get("sector", 0), cand2.get("cfg_name", "canonical"), cand2.get("worker_id", -1), cand2.get("stride_arm", -1), cand2.get("stride", 0)),
                "lane": str(cand2.get("lane", "unknown")),
                "strategy": str(cand2.get("strategy", "unknown")),
                "sector": self._i(cand2.get("sector", 0)),
                "worker_id": self._i(cand2.get("worker_id", -1)),
                "cfg_name": str(cand2.get("cfg_name", "canonical")),
                "stride": self._i(cand2.get("stride", 0)),
                "stride_arm": self._i(cand2.get("stride_arm", -1)),
                "protected_forced": bool(cand2.get("protected_forced", False)),
                "source_lane": str(cand2.get("source_lane", cand2.get("lane", "unknown"))),
                "selected_by": str(cand2.get("selected_by", cand2.get("lane", "unknown"))),
                "recipe_focus": bool(cand2.get("recipe_focus", False)),
                "recipe_focus_name": str(cand2.get("recipe_focus_name", "")),
                "source_recipe_key": str(cand2.get("source_recipe_key", "")),
                "exact_worker_match": bool(cand2.get("exact_worker_match", False)),
                "job_age_ms": self._i(cand2.get("job_age_ms", 0)),
                "z": max(0, min(256, self._i(cand2.get("zbits", cand2.get("z", 0))))),
                "job_id": cand2.get("job_id"),
                "nonce_submit_hex": cand2.get("nonce_submit_hex"),
                "proof_path": proof_path or cand2.get("proof_path", ""),
            }
            self.accept_events.append(ev)
            self.updated_at_utc = utc
        except Exception as e:
            try:
                log("fresh_tailgex", f"observe_accepted skipped: {e}")
            except Exception:
                pass

    def observe_rejected(self, cand: Dict[str, Any]) -> None:
        try:
            utc = utc_stamp_iso()
            ev = {
                "ts": time.time(),
                "ts_utc": utc,
                "key": self._key(cand.get("lane", "unknown"), cand.get("strategy", "unknown"), cand.get("sector", 0), cand.get("cfg_name", "canonical"), cand.get("stride_arm", -1)),
                "lane": str(cand.get("lane", "unknown")),
                "strategy": str(cand.get("strategy", "unknown")),
                "sector": self._i(cand.get("sector", 0)),
                "cfg_name": str(cand.get("cfg_name", "canonical")),
                "stride_arm": self._i(cand.get("stride_arm", -1)),
                "z": max(0, min(256, self._i(cand.get("zbits", cand.get("z", 0))))),
                "pool_response": cand.get("pool_response"),
            }
            self.reject_events.append(ev)
            self.updated_at_utc = utc
        except Exception:
            pass

    def _fresh_accept_events(self) -> List[Dict[str, Any]]:
        now = time.time()
        xs = [e for e in self.accept_events if (now - float(e.get("ts", now))) <= self.fresh_window_seconds]
        if len(xs) > self.fresh_window_count:
            xs = xs[-self.fresh_window_count:]
        return xs

    def _fresh_result_events(self) -> List[Dict[str, Any]]:
        now = time.time()
        return [e for e in self.result_events if (now - float(e.get("ts", now))) <= self.fresh_window_seconds]

    def _expected(self, accepted: int, z: int) -> float:
        if accepted <= 0 or z < self.baseline_z:
            return 0.0
        return float(accepted) / float(2 ** (int(z) - self.baseline_z))

    def _empty_row(self, ev: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "key": ev.get("key", ""),
            "canonical_key": ev.get("canonical_key", ev.get("key", "")),
            "recipe_key": ev.get("recipe_key", ""),
            "lane": ev.get("lane", "unknown"),
            "strategy": ev.get("strategy", "unknown"),
            "sector": self._i(ev.get("sector", 0)),
            "worker_id": self._i(ev.get("worker_id", -1)),
            "cfg_name": ev.get("cfg_name", "canonical"),
            "stride": self._i(ev.get("stride", 0)),
            "stride_arm": self._i(ev.get("stride_arm", -1)),
            "fresh_checked": 0,
            "fresh_observations": 0,
            "fresh_accepted": 0,
            "fresh_rejected": 0,
            "fresh_best_z": 0,
            "fresh_hps_ewma": 0.0,
            "last_seen_utc": "",
        }

    def _fresh_rows(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        rows: Dict[str, Dict[str, Any]] = {}
        now = time.time()
        results = self._fresh_result_events()
        accepts = self._fresh_accept_events()
        rejects = [e for e in self.reject_events if (now - float(e.get("ts", now))) <= self.fresh_window_seconds]

        for ev in results:
            key = str(ev.get("key", ""))
            row = rows.setdefault(key, self._empty_row(ev))
            row["fresh_checked"] = int(row.get("fresh_checked", 0)) + max(0, self._i(ev.get("checked", 0)))
            row["fresh_observations"] = int(row.get("fresh_observations", 0)) + 1
            row["fresh_best_z"] = max(int(row.get("fresh_best_z", 0)), self._i(ev.get("best_z", 0)))
            hps = max(0.0, self._f(ev.get("hps", 0.0)))
            row["fresh_hps_ewma"] = hps if float(row.get("fresh_hps_ewma", 0.0)) <= 0 else float(row.get("fresh_hps_ewma", 0.0)) * 0.88 + hps * 0.12
            row["last_seen_utc"] = ev.get("ts_utc", row.get("last_seen_utc", ""))

        for ev in accepts:
            key = str(ev.get("key", ""))
            row = rows.setdefault(key, self._empty_row(ev))
            z = max(0, min(256, self._i(ev.get("z", 0))))
            row["fresh_accepted"] = int(row.get("fresh_accepted", 0)) + 1
            row["fresh_best_z"] = max(int(row.get("fresh_best_z", 0)), z)
            row["last_seen_utc"] = ev.get("ts_utc", row.get("last_seen_utc", ""))
            for t in (23,24,25,26,28,30,32,33,34,35,36,37,38,39,40,48,64,128,256):
                if z >= t:
                    row[f"fresh_z{t}"] = int(row.get(f"fresh_z{t}", 0)) + 1

        for ev in rejects:
            key = str(ev.get("key", ""))
            row = rows.setdefault(key, self._empty_row(ev))
            row["fresh_rejected"] = int(row.get("fresh_rejected", 0)) + 1
            row["last_seen_utc"] = ev.get("ts_utc", row.get("last_seen_utc", ""))

        total_checked = sum(int(r.get("fresh_checked", 0)) for r in rows.values())
        total_accepted = len(accepts)
        total_rejected = len(rejects)
        for row in rows.values():
            accepted = max(0, self._i(row.get("fresh_accepted", 0)))
            checked = max(0, self._i(row.get("fresh_checked", 0)))
            rejected = max(0, self._i(row.get("fresh_rejected", 0)))
            row["fresh_exposure"] = float(checked) / float(total_checked) if total_checked > 0 else 0.0
            row["fresh_reject_rate"] = float(rejected) / max(1.0, float(accepted + rejected))
            weighted = 0.0
            weighted_ratio = 0.0
            tail = {}
            weights = {32:0.70, 33:1.00, 34:1.35, 35:1.85, 36:2.60, 37:3.60, 38:5.00, 39:7.00, 40:9.00}
            for z, w in weights.items():
                actual = int(row.get(f"fresh_z{z}", 0) or 0)
                exp = self._expected(accepted, z)
                ratio = (float(actual) / exp) if exp > 0 else 0.0
                excess = float(actual) - exp
                tail[f"z{z}+"] = {"actual": actual, "expected": exp, "ratio": ratio, "excess": excess}
                weighted += w * excess
                if exp > 0:
                    weighted_ratio += w * (ratio - 1.0)
            confidence = min(1.0, math.sqrt(float(accepted) / float(max(1, self.min_lane_accepted * 4))))
            gex = confidence * ((weighted / max(1.0, math.sqrt(float(max(1, accepted))))) + 0.10 * weighted_ratio)
            gex += 0.10 * math.log1p(checked / 1_000_000.0)
            gex -= 2.50 * float(row.get("fresh_reject_rate", 0.0))
            row["fresh_tail"] = tail
            row["fresh_confidence"] = confidence
            row["fresh_gex"] = gex
            if accepted < self.min_lane_accepted:
                row["fresh_sign"] = "LOW_SAMPLE"
            elif gex >= 0.20:
                row["fresh_sign"] = "POSITIVE"
            elif gex <= -0.20:
                row["fresh_sign"] = "NEGATIVE"
            else:
                row["fresh_sign"] = "NEUTRAL"
            row["allocator_candidate_fresh_only"] = bool(
                row["fresh_sign"] == "POSITIVE"
                and accepted >= self.min_lane_accepted
                and row.get("last_seen_utc")
                and float(row.get("fresh_reject_rate", 0.0)) < 0.01
            )

        meta = {
            "fresh_result_events": len(results),
            "fresh_accept_events": total_accepted,
            "fresh_reject_events": total_rejected,
            "fresh_total_checked": total_checked,
            "fresh_best_z": max([self._i(e.get("z", 0)) for e in accepts] + [self._i(e.get("best_z", 0)) for e in results] + [0]),
            "fresh_window_seconds": self.fresh_window_seconds,
            "fresh_window_count": self.fresh_window_count,
            "baseline_z": self.baseline_z,
        }
        out = list(rows.values())
        # A8.3 fix: rows with accepted=0 can no longer outrank real accepted lanes
        # merely because they have checked exposure. High tails and accepted sample
        # come first; fresh_gex remains a secondary diagnostic score.
        out.sort(key=lambda r: (
            1 if int(r.get("fresh_accepted", 0) or 0) > 0 else 0,
            int(r.get("fresh_z38", 0) or 0),
            int(r.get("fresh_z36", 0) or 0),
            int(r.get("fresh_z34", 0) or 0),
            int(r.get("fresh_z33", 0) or 0),
            int(r.get("fresh_best_z", 0) or 0),
            int(r.get("fresh_accepted", 0) or 0),
            float(r.get("fresh_gex", 0.0) or 0.0),
            float(r.get("fresh_exposure", 0.0) or 0.0),
        ), reverse=True)
        return out, meta

    def _fresh_recipe_rows(self) -> List[Dict[str, Any]]:
        rows: Dict[str, Dict[str, Any]] = {}
        now = time.time()
        results = self._fresh_result_events()
        accepts = self._fresh_accept_events()
        rejects = [e for e in self.reject_events if (now - float(e.get("ts", now))) <= self.fresh_window_seconds]

        def row_for(ev: Dict[str, Any]) -> Dict[str, Any]:
            rk = str(ev.get("recipe_key") or self._recipe_key(ev.get("lane"), ev.get("strategy"), ev.get("sector", 0), ev.get("cfg_name", "canonical"), ev.get("worker_id", -1), ev.get("stride_arm", -1), ev.get("stride", 0)))
            if rk not in rows:
                rows[rk] = {
                    "recipe_key": rk,
                    "canonical_key": ev.get("canonical_key") or self._canonical_key(ev.get("strategy"), ev.get("sector", 0), ev.get("cfg_name", "canonical")),
                    "lane": ev.get("lane", "unknown"),
                    "strategy": ev.get("strategy", "unknown"),
                    "sector": self._i(ev.get("sector", 0)),
                    "worker_id": self._i(ev.get("worker_id", -1)),
                    "cfg_name": ev.get("cfg_name", "canonical"),
                    "stride": self._i(ev.get("stride", 0)),
                    "stride_arm": self._i(ev.get("stride_arm", -1)),
                    "fresh_checked": 0,
                    "fresh_observations": 0,
                    "fresh_accepted": 0,
                    "fresh_rejected": 0,
                    "fresh_best_z": 0,
                    "fresh_z32": 0, "fresh_z33": 0, "fresh_z34": 0, "fresh_z35": 0, "fresh_z36": 0, "fresh_z38": 0,
                    "protected_forced_accepts": 0,
                    "job_age_ms_sum": 0,
                    "job_age_ms_count": 0,
                }
            return rows[rk]

        for ev in results:
            r = row_for(ev)
            r["fresh_checked"] += max(0, self._i(ev.get("checked", 0)))
            r["fresh_observations"] += 1
            r["fresh_best_z"] = max(r["fresh_best_z"], self._i(ev.get("best_z", 0)))

        for ev in accepts:
            r = row_for(ev)
            z = max(0, min(256, self._i(ev.get("z", 0))))
            r["fresh_accepted"] += 1
            r["fresh_best_z"] = max(r["fresh_best_z"], z)
            if bool(ev.get("protected_forced", False)):
                r["protected_forced_accepts"] += 1
            age = self._i(ev.get("job_age_ms", 0))
            if age > 0:
                r["job_age_ms_sum"] += age
                r["job_age_ms_count"] += 1
            for t in (32, 33, 34, 35, 36, 38):
                if z >= t:
                    r[f"fresh_z{t}"] += 1

        for ev in rejects:
            r = row_for(ev)
            r["fresh_rejected"] += 1

        total_checked = sum(int(x.get("fresh_checked", 0) or 0) for x in rows.values())
        out = []
        for r in rows.values():
            r["fresh_exposure"] = float(r.get("fresh_checked", 0) or 0) / float(total_checked) if total_checked > 0 else 0.0
            cnt = int(r.pop("job_age_ms_count", 0) or 0)
            sm = int(r.pop("job_age_ms_sum", 0) or 0)
            r["avg_job_age_ms"] = round(float(sm) / float(cnt), 1) if cnt > 0 else 0.0
            out.append(r)
        out.sort(key=lambda r: (
            int(r.get("fresh_z38", 0) or 0),
            int(r.get("fresh_z36", 0) or 0),
            int(r.get("fresh_z34", 0) or 0),
            int(r.get("fresh_z33", 0) or 0),
            int(r.get("fresh_best_z", 0) or 0),
            int(r.get("fresh_accepted", 0) or 0),
            float(r.get("fresh_exposure", 0.0) or 0.0),
        ), reverse=True)
        return out

    def _global_metrics_from_shadow(self, shadow: Optional[TachyonShadowMode]) -> List[Dict[str, Any]]:
        if shadow is None:
            return []
        try:
            rows = list(getattr(shadow, "rows", {}).values())
        except Exception:
            rows = []
        out = []
        now = time.time()
        for row in rows:
            if not isinstance(row, dict):
                continue
            accepted = max(0, self._i(row.get("accepted", 0)))
            if accepted <= 0:
                continue
            best_z = max(0, self._i(row.get("best_z", 0)))
            checked = max(0, self._i(row.get("checked", 0)))
            last_seen = str(row.get("last_seen_utc", "") or "")
            last_epoch = self._utc_to_epoch(last_seen)
            age = (now - last_epoch) if last_epoch > 0 else float("inf")
            weighted = 0.0
            for z, w in {33:1.0,34:1.35,35:1.85,36:2.6,37:3.6,38:5.0,39:7.0,40:9.0}.items():
                actual = max(0, self._i(row.get(f"accepted_z{z}", 0)))
                exp = self._expected(accepted, z)
                weighted += w * (float(actual) - exp)
            gex = weighted / max(1.0, math.sqrt(float(max(1, accepted)))) + 0.05 * math.log1p(checked / 1_000_000.0)
            out.append({
                "key": row.get("key", ""),
                "lane": row.get("lane", "unknown"),
                "strategy": row.get("strategy", "unknown"),
                "sector": self._i(row.get("sector", 0)),
                "cfg_name": row.get("cfg_name", "canonical"),
                "stride_arm": self._i(row.get("stride_arm", -1)),
                "accepted": accepted,
                "checked": checked,
                "best_z": best_z,
                "global_gex": gex,
                "last_seen_utc": last_seen,
                "age_seconds": age if math.isfinite(age) else None,
                "stale": bool((not last_seen) or (math.isfinite(age) and age > self.stale_after_seconds) or (not math.isfinite(age))),
                "checked_observations": self._i(row.get("observations", 0)),
            })
        out.sort(key=lambda r: (float(r.get("global_gex", 0.0)), int(r.get("best_z", 0)), int(r.get("accepted", 0))), reverse=True)
        return out

    def _champion_watch(self, fresh_rows: List[Dict[str, Any]], global_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        champs = [
            {"name": "zim_reverse/s6/canonical", "strategy": "zim_reverse", "sector": 6, "cfg_name": "canonical", "historical_reason": "A7 z38 carrier"},
            {"name": "dual_lock:zim_reverse_s6", "strategy": "zim_reverse", "sector": 6, "cfg_name": "canonical", "historical_reason": "A7 z38 lane family"},
        ]
        out = []
        for ch in champs:
            rows = [r for r in fresh_rows if str(r.get("strategy")) == ch["strategy"] and self._i(r.get("sector", -1)) == ch["sector"] and str(r.get("cfg_name")) == ch["cfg_name"]]
            rows.sort(key=lambda r: (float(r.get("fresh_exposure", 0.0)), int(r.get("fresh_accepted", 0)), int(r.get("fresh_best_z", 0))), reverse=True)
            r = rows[0] if rows else {}
            exposure = float(r.get("fresh_exposure", 0.0) or 0.0)
            accepted = self._i(r.get("fresh_accepted", 0))
            best_z = self._i(r.get("fresh_best_z", 0))
            status = "OK"
            if not rows:
                status = "NO_FRESH_EXPOSURE"
            elif exposure < self.champion_exposure_floor:
                status = "LOW_EXPOSURE"
            elif accepted >= self.min_lane_accepted and best_z < 33:
                status = "ENOUGH_EXPOSURE_LOW_TAIL"
            out.append({
                "champion": ch["name"],
                "historical_reason": ch["historical_reason"],
                "status": status,
                "fresh_key": r.get("key", ""),
                "fresh_exposure": exposure,
                "fresh_exposure_percent": round(exposure * 100.0, 3),
                "fresh_checked": self._i(r.get("fresh_checked", 0)),
                "fresh_accepted": accepted,
                "fresh_best_z": best_z,
                "fresh_z33+": self._i(r.get("fresh_z33", 0)),
                "fresh_z34+": self._i(r.get("fresh_z34", 0)),
                "fresh_z35+": self._i(r.get("fresh_z35", 0)),
                "fresh_z36+": self._i(r.get("fresh_z36", 0)),
                "fresh_z38+": self._i(r.get("fresh_z38", 0)),
            })
        return out

    def snapshot(self, shadow: Optional[TachyonShadowMode] = None, client: Optional[Any] = None) -> Dict[str, Any]:
        fresh_rows, meta = self._fresh_rows()
        global_rows = self._global_metrics_from_shadow(shadow)
        top_fresh = fresh_rows[:16]
        top_recipes = self._fresh_recipe_rows()[:32]
        candidates = [r for r in fresh_rows if r.get("allocator_candidate_fresh_only")]
        candidates.sort(key=lambda r: (float(r.get("fresh_gex", 0.0)), int(r.get("fresh_best_z", 0)), int(r.get("fresh_accepted", 0))), reverse=True)
        top_global = global_rows[:16]
        stale_top = [r for r in top_global if r.get("stale")]
        champion = self._champion_watch(fresh_rows, global_rows)
        obj = {
            "schema": self.SCHEMA,
            "version": VERSION,
            "sentinel": SENTINEL,
            "enabled": True,
            "mode": "fresh_tailgex_review_only",
            "created_at_utc": self.started_at_utc,
            "written_at_utc": utc_stamp_iso(),
            "updated_at_utc": self.updated_at_utc or utc_stamp_iso(),
            "path": self.path,
            "allocator_enabled": False,
            "allocator_review_only": True,
            "fresh_only_gate": True,
            "changes_scheduler": False,
            "changes_wire": False,
            "wire_change_required": False,
            "baseline_z": self.baseline_z,
            "fresh_meta": meta,
            "client": {
                "accepted": int(getattr(client, "accepted", 0)) if client is not None else None,
                "rejected": int(getattr(client, "rejected", 0)) if client is not None else None,
                "submitted": int(getattr(client, "submitted", 0)) if client is not None else None,
            },
            "top_fresh_lanes": top_fresh,
            "top_recipe_lanes": top_recipes,
            "fresh_allocator_candidates_passive": candidates[:16],
            "top_global_lanes_imported_allowed_for_history_only": top_global,
            "stale_global_top_lanes_excluded_from_allocator": stale_top[:16],
            "champion_watch": champion,
            "rules": {
                "global_gex_use": "history_only",
                "fresh_gex_use": "diagnostic_gate_only",
                "allocator_candidate_requires": "fresh_only, min samples, recent last_seen, no reject risk",
                "do_not_change": ["header", "nonce", "extranonce2", "ntime", "nbits", "prevhash", "TruthGate"],
                "a8_3_fix": "unified canonical lane keys for top_fresh/champion/protected plus recipe-level telemetry",
            },
        }
        self.last_snapshot = obj
        return obj

    def save(self, shadow: Optional[TachyonShadowMode] = None, client: Optional[Any] = None, force: bool = False) -> None:
        try:
            obj = self.snapshot(shadow, client)
            obj["persisted_result_events"] = list(self.result_events)[-50000:]
            obj["persisted_accept_events"] = list(self.accept_events)[-50000:]
            obj["persisted_reject_events"] = list(self.reject_events)[-10000:]
            obj["accept_seen"] = sorted(list(self.accept_seen))[-200000:]
            atomic_json(self.path, obj)
        except Exception as e:
            try:
                log("fresh_tailgex", f"save failed: {e}")
            except Exception:
                pass

    def load(self) -> None:
        try:
            p = Path(self.path)
            if not p.exists():
                return
            obj = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(obj, dict):
                return
            self.started_at_utc = str(obj.get("created_at_utc") or self.started_at_utc)
            for ev in obj.get("persisted_result_events", []) or []:
                if isinstance(ev, dict):
                    self.result_events.append(ev)
            for ev in obj.get("persisted_accept_events", []) or []:
                if isinstance(ev, dict):
                    self.accept_events.append(ev)
            for ev in obj.get("persisted_reject_events", []) or []:
                if isinstance(ev, dict):
                    self.reject_events.append(ev)
            seen = obj.get("accept_seen", [])
            if isinstance(seen, list):
                self.accept_seen = set(str(x) for x in seen)
            log("fresh_tailgex", f"loaded path={self.path} result_events={len(self.result_events)} accepted_events={len(self.accept_events)}")
        except FileNotFoundError:
            pass
        except Exception as e:
            try:
                log("fresh_tailgex", f"load skipped: {e}")
            except Exception:
                pass

    def line(self) -> str:
        obj = self.last_snapshot or self.snapshot(None, None)
        meta = obj.get("fresh_meta", {}) if isinstance(obj, dict) else {}
        top = obj.get("top_fresh_lanes", []) if isinstance(obj, dict) else []
        recipes = obj.get("top_recipe_lanes", []) if isinstance(obj, dict) else []
        top_s = "none"
        if top:
            t = top[0]
            top_s = f"{t.get('strategy')}/s{t.get('sector')}/{t.get('cfg_name')} sign={t.get('fresh_sign')} fresh_gex={float(t.get('fresh_gex',0.0)):.3f} best_z={t.get('fresh_best_z')} acc={t.get('fresh_accepted')} exp={float(t.get('fresh_exposure',0.0))*100.0:.1f}%"
        recipe_s = ""
        if recipes:
            rr = recipes[0]
            recipe_s = f" recipe_top={rr.get('recipe_key')} best_z={rr.get('fresh_best_z')} acc={rr.get('fresh_accepted')}"
        champs = obj.get("champion_watch", []) if isinstance(obj, dict) else []
        champ_s = ""
        if champs:
            c = champs[0]
            champ_s = f" champion={c.get('champion')} status={c.get('status')} exp={float(c.get('fresh_exposure_percent',0.0)):.1f}% acc={c.get('fresh_accepted')} best_z={c.get('fresh_best_z')}"
        return (
            f"fresh_tailgex=ON fresh_acc={int(meta.get('fresh_accept_events',0) or 0)} "
            f"fresh_checked={int(meta.get('fresh_total_checked',0) or 0)} "
            f"fresh_best_z={int(meta.get('fresh_best_z',0) or 0)} "
            f"top_fresh={top_s}{recipe_s}{champ_s} allocator=OFF wire=FROZEN"
        )


class ProtectedChampionExposureFloor:
    """A8.2 controlled protected checked-exposure floor.

    This is NOT a Tachyon allocator and NOT a fresh-gex auto-weight system.
    It only protects a fixed minimum of real checked nonce exposure for selected
    lanes, while keeping Stratum wire/header/nonce/extranonce2/submit frozen.
    """

    SCHEMA = "a8-3-v34-protected-champion-exposure-floor-1"

    def __init__(
        self,
        zim_floor: float = 0.12,
        knight_floor: float = 0.05,
        deficit_boost: float = 2.25,
        max_force_prob: float = 0.45,
        log_every_rounds: int = 10,
    ) -> None:
        self.protected = {
            "zim_reverse/s6/canonical": {
                "strategy": "zim_reverse",
                "sector": 6,
                "cfg_name": "canonical",
                "floor": max(0.0, min(0.95, float(zim_floor or 0.12))),
                "lane_label": "protected:zim_reverse_s6",
                "reason": "A7 z38 carrier; A8.1 low exposure around 1%",
            },
            "knight/s11/canonical": {
                "strategy": "knight",
                "sector": 11,
                "cfg_name": "canonical",
                "floor": max(0.0, min(0.95, float(knight_floor or 0.05))),
                "lane_label": "protected:knight_s11",
                "reason": "A8.1 fresh z36 carrier; keep-alive floor",
            },
        }
        self.control = {
            "linear/s6/canonical": {
                "strategy": "linear",
                "sector": 6,
                "cfg_name": "canonical",
                "floor": 0.0,
                "lane_label": "control:linear_s6",
                "reason": "control line; monitor only",
            }
        }
        self.deficit_boost = max(0.0, float(deficit_boost or 2.25))
        self.max_force_prob = max(0.0, min(1.0, float(max_force_prob or 0.45)))
        self.log_every_rounds = max(1, int(log_every_rounds or 10))
        self.enabled = True
        self.forced_counts: Dict[str, int] = {k: 0 for k in self.protected}
        self.last_decision: Dict[str, Any] = {"forced": False, "reason": "init"}
        self.last_snapshot: Dict[str, Any] = {}

    @staticmethod
    def _i(x: Any, default: int = 0) -> int:
        try:
            return int(x)
        except Exception:
            return default

    @staticmethod
    def _f(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _canonical_key(self, strategy: Any, sector: Any, cfg_name: Any = "canonical") -> str:
        return f"{strategy}/s{int(sector) % SECTORS}/{cfg_name or 'canonical'}"

    def _aggregate_rows(self, review: Optional[Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        meta: Dict[str, Any] = {}
        try:
            if review is not None:
                rows, meta = review._fresh_rows()  # local diagnostic aggregation; no wire/scheduler mutation
            else:
                rows, meta = [], {}
        except Exception as e:
            rows, meta = [], {"error": str(e)}

        all_specs = dict(self.protected)
        all_specs.update(self.control)
        for key, spec in all_specs.items():
            out[key] = {
                "key": key,
                "strategy": spec["strategy"],
                "sector": int(spec["sector"]),
                "cfg_name": spec.get("cfg_name", "canonical"),
                "floor": float(spec.get("floor", 0.0)),
                "lane_label": spec.get("lane_label", key.replace("/", "_")),
                "reason": spec.get("reason", ""),
                "fresh_checked": 0,
                "fresh_observations": 0,
                "fresh_accepted": 0,
                "fresh_rejected": 0,
                "fresh_best_z": 0,
                "fresh_z32+": 0,
                "fresh_z33+": 0,
                "fresh_z34+": 0,
                "fresh_z35+": 0,
                "fresh_z36+": 0,
                "fresh_z38+": 0,
                "fresh_exposure": 0.0,
                "deficit": 0.0,
                "status": "NO_FRESH_EXPOSURE",
            }

        total_checked = 0
        try:
            total_checked = int(meta.get("fresh_total_checked", 0) or 0)
        except Exception:
            total_checked = 0

        for r in rows:
            try:
                key = self._canonical_key(r.get("strategy", "unknown"), self._i(r.get("sector", 0)), r.get("cfg_name", "canonical"))
            except Exception:
                continue
            if key not in out:
                continue
            dst = out[key]
            dst["fresh_checked"] += self._i(r.get("fresh_checked", 0))
            dst["fresh_observations"] += self._i(r.get("fresh_observations", 0))
            dst["fresh_accepted"] += self._i(r.get("fresh_accepted", 0))
            dst["fresh_rejected"] += self._i(r.get("fresh_rejected", 0))
            dst["fresh_best_z"] = max(self._i(dst.get("fresh_best_z", 0)), self._i(r.get("fresh_best_z", 0)))
            for z in (32, 33, 34, 35, 36, 38):
                dst[f"fresh_z{z}+"] += self._i(r.get(f"fresh_z{z}", 0))

        if total_checked <= 0:
            total_checked = sum(self._i(v.get("fresh_checked", 0)) for v in out.values())

        for key, row in out.items():
            checked = self._i(row.get("fresh_checked", 0))
            floor = self._f(row.get("floor", 0.0))
            exposure = float(checked) / float(total_checked) if total_checked > 0 else 0.0
            row["fresh_exposure"] = exposure
            row["fresh_exposure_percent"] = round(exposure * 100.0, 3)
            row["floor_percent"] = round(floor * 100.0, 3)
            row["deficit"] = max(0.0, floor - exposure)
            row["deficit_percent"] = round(row["deficit"] * 100.0, 3)
            if floor <= 0:
                row["status"] = "CONTROL"
            elif checked <= 0:
                row["status"] = "NO_FRESH_EXPOSURE"
            elif exposure < floor:
                row["status"] = "UNDER_FLOOR"
            else:
                row["status"] = "FLOOR_OK"
            row["forced_count"] = int(self.forced_counts.get(key, 0))

        meta2 = dict(meta or {})
        meta2["protected_total_checked"] = total_checked
        meta2["protected_floor_enabled"] = bool(self.enabled)
        return out, meta2

    def snapshot(self, review: Optional[Any] = None) -> Dict[str, Any]:
        lanes, meta = self._aggregate_rows(review)
        obj = {
            "schema": self.SCHEMA,
            "version": VERSION,
            "sentinel": SENTINEL,
            "enabled": bool(self.enabled),
            "mode": "protected_checked_exposure_floor_test",
            "allocator_enabled": False,
            "changes_wire": False,
            "wire_change_required": False,
            "changes_scheduler": True,
            "scheduler_change_kind": "fixed checked-exposure floor only; no fresh-gex auto allocator",
            "written_at_utc": utc_stamp_iso(),
            "protected_lanes": {k: lanes.get(k, {}) for k in self.protected},
            "control_lanes": {k: lanes.get(k, {}) for k in self.control},
            "meta": meta,
            "last_decision": dict(self.last_decision),
            "rules": {
                "allocator": "OFF",
                "wire": "FROZEN",
                "floors": "fixed constants, not learned from fresh_gex",
                "protected": "zim_reverse/s6 12%; knight/s11 5% keep-alive by default",
                "do_not_change": ["header", "nonce", "extranonce2", "ntime", "nbits", "prevhash", "TruthGate", "SubmitGate"],
            },
        }
        self.last_snapshot = obj
        return obj

    def choose(
        self,
        rng: random.Random,
        cfg: BuildConfig,
        review: Optional[Any],
        round_id: int,
        worker_id: int,
    ) -> Optional[Tuple[str, int, BuildConfig, str]]:
        if not self.enabled:
            self.last_decision = {"forced": False, "reason": "disabled", "round_id": round_id, "worker_id": worker_id}
            return None
        lanes, meta = self._aggregate_rows(review)
        deficits = {k: max(0.0, float(lanes.get(k, {}).get("deficit", 0.0))) for k in self.protected}
        total_deficit = sum(deficits.values())
        if total_deficit <= 0.0:
            self.last_decision = {"forced": False, "reason": "all_floors_ok", "round_id": round_id, "worker_id": worker_id, "deficits": deficits}
            return None
        force_prob = min(self.max_force_prob, total_deficit * self.deficit_boost)
        if rng.random() >= force_prob:
            self.last_decision = {"forced": False, "reason": "soft_skip", "round_id": round_id, "worker_id": worker_id, "force_prob": force_prob, "deficits": deficits}
            return None
        pick = rng.random() * total_deficit
        acc = 0.0
        chosen_key = None
        for k, d in sorted(deficits.items(), key=lambda kv: kv[1], reverse=True):
            if d <= 0:
                continue
            acc += d
            if pick <= acc:
                chosen_key = k
                break
        if chosen_key is None:
            chosen_key = max(deficits.items(), key=lambda kv: kv[1])[0]
        spec = self.protected[chosen_key]
        self.forced_counts[chosen_key] = int(self.forced_counts.get(chosen_key, 0)) + 1
        row = lanes.get(chosen_key, {})
        self.last_decision = {
            "forced": True,
            "round_id": round_id,
            "worker_id": worker_id,
            "forced_lane": chosen_key,
            "lane_label": spec["lane_label"],
            "strategy": spec["strategy"],
            "sector": spec["sector"],
            "cfg_name": cfg.name,
            "reason": "UNDER_FLOOR",
            "force_prob": force_prob,
            "deficit": deficits.get(chosen_key, 0.0),
            "actual_exposure": row.get("fresh_exposure", 0.0),
            "floor": spec.get("floor", 0.0),
            "allocator": "OFF",
            "wire": "FROZEN",
        }
        return str(spec["strategy"]), int(spec["sector"]) % SECTORS, cfg, str(spec["lane_label"])

    def line(self, review: Optional[Any] = None) -> str:
        snap = self.snapshot(review)
        parts = []
        for key, row in snap.get("protected_lanes", {}).items():
            parts.append(
                f"{key} exp={float(row.get('fresh_exposure_percent',0.0)):.1f}%/floor={float(row.get('floor_percent',0.0)):.1f}% "
                f"acc={row.get('fresh_accepted')} best_z={row.get('fresh_best_z')} "
                f"z34+={row.get('fresh_z34+',0)} z36+={row.get('fresh_z36+',0)} status={row.get('status')} forced={row.get('forced_count')}"
            )
        dec = snap.get("last_decision", {})
        dec_s = "forced=" + str(dec.get("forced"))
        if dec.get("forced"):
            dec_s += f" lane={dec.get('forced_lane')} prob={float(dec.get('force_prob',0.0)):.2f}"
        return "protected_exposure=ON allocator=OFF wire=FROZEN " + " | ".join(parts) + " | " + dec_s

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
    selected_by: str = ""
    scheduler_source: str = ""
    proofmind_mode: str = ""
    recipe_focus: bool = False
    recipe_focus_name: str = ""
    source_recipe_key: str = ""
    exact_worker_match: bool = False
    batch_factor: float = 1.0
    task_id: str = ""
    arm_weight: Optional[float] = None
    arm_reward_ema: Optional[float] = None


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
    selected_by: str = ""
    scheduler_source: str = ""
    proofmind_mode: str = ""
    recipe_focus: bool = False
    recipe_focus_name: str = ""
    source_recipe_key: str = ""
    exact_worker_match: bool = False
    batch_factor: float = 1.0
    task_id: str = ""
    arm_weight: Optional[float] = None
    arm_reward_ema: Optional[float] = None
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
                        "source_lane": task.lane,
                        "strategy": task.strategy,
                        "sector": task.sector,
                        "canonical_lane_key": f"{task.strategy}/s{int(task.sector) % SECTORS}/{task.cfg.name}",
                        "recipe_key": f"{task.lane}/{task.strategy}/s{int(task.sector) % SECTORS}/{task.cfg.name}/w{task.worker_id}/a{task.stride_arm}/stride{int(task.stride or 0) & 0xFFFFFFFF}",
                        "recipe_key_legacy_hex_stride": f"{task.strategy}/s{int(task.sector) % SECTORS}/{task.cfg.name}/w{task.worker_id}/a{task.stride_arm}/stride0x{int(task.stride or 0) & 0xFFFFFFFF:08x}",
                        "selected_by": task.selected_by or task.lane,
                        "scheduler_source": task.scheduler_source or task.selected_by or task.lane,
                        "proofmind_mode": task.proofmind_mode,
                        "recipe_focus": bool(task.recipe_focus),
                        "recipe_focus_name": task.recipe_focus_name,
                        "source_recipe_key": task.source_recipe_key,
                        "exact_worker_match": bool(task.exact_worker_match),
                        "batch_factor": float(task.batch_factor),
                        "task_id": task.task_id,
                        "arm_weight": task.arm_weight,
                        "arm_reward_ema": task.arm_reward_ema,
                        "protected_forced": str(task.lane).startswith("protected:") or bool(task.recipe_focus),
                        "protected_lane_label": task.lane if (str(task.lane).startswith("protected:") or bool(task.recipe_focus)) else "",
                        "job_age_ms": max(0, now_ms() - int(getattr(task.job, "received_ms", 0) or now_ms())),
                        "clean_job_flag": bool(getattr(task.job, "clean", False)),
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
            selected_by=task.selected_by,
            scheduler_source=task.scheduler_source,
            proofmind_mode=task.proofmind_mode,
            recipe_focus=task.recipe_focus,
            recipe_focus_name=task.recipe_focus_name,
            source_recipe_key=task.source_recipe_key,
            exact_worker_match=task.exact_worker_match,
            batch_factor=task.batch_factor,
            task_id=task.task_id,
            arm_weight=task.arm_weight,
            arm_reward_ema=task.arm_reward_ema,
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
    """Atomic JSON write with Windows/OneDrive-friendly unique tmp + replace retry."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}.{time.time_ns()}.{random.getrandbits(32):08x}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass
    last_err = None
    for i in range(6):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last_err = e
            time.sleep(0.05 + 0.025 * i)
        except OSError as e:
            last_err = e
            time.sleep(0.05 + 0.025 * i)
    try:
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception:
        pass
    if last_err is not None:
        raise last_err



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
            "recipe_key": cand.get("recipe_key"),
            "selected_by": cand.get("selected_by"),
            "recipe_focus_name": cand.get("recipe_focus_name"),
            "source_recipe_key": cand.get("source_recipe_key"),
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

    def save(self, force: bool = False) -> None:
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




class RecipeFocusOracle:
    """A8.3 Anti-Dispersion Recipe Focus.

    This is not allocator mode. It narrows scheduler attention to exact historical
    recipes and their worker-safe sibling recipes while keeping wire/header/submit
    frozen. It fixes the A8.2 failure mode where a broad family floor fed
    zim_reverse/s6 but not the A7 z38 recipe w9/a11/stride521.
    """

    SCHEMA = "a8-3-v34-anti-dispersion-recipe-focus-1"

    def __init__(self, enabled: bool = True, focus_share: float = 0.82, a7_weight: float = 0.70, knight_weight: float = 0.25, log_every_rounds: int = 10) -> None:
        self.enabled = bool(enabled)
        self.focus_share = max(0.0, min(0.95, float(focus_share or 0.82)))
        self.log_every_rounds = max(1, int(log_every_rounds or 10))
        self.recipes: List[Dict[str, Any]] = [
            {
                "name": "A7_Z38_ZIM_W9_A11_STRIDE521",
                "source_recipe_key": "dual_lock:zim_reverse_s6/zim_reverse/s6/canonical/w9/a11/stride521",
                "source_lane": "dual_lock:zim_reverse_s6",
                "strategy": "zim_reverse",
                "sector": 6,
                "cfg_name": "canonical",
                "worker_id": 9,
                "stride_arm": 11,
                "stride": 521,
                "weight": max(0.0, float(a7_weight or 0.70)),
                "reason": "A7 z38 exact recipe seed; restored as anti-dispersion focus",
            },
            {
                "name": "A8_1_Z36_KNIGHT_W1_A_NEG1_STRIDE0",
                "source_recipe_key": "dual_lock:knight_s11/knight/s11/canonical/w1/a-1/stride0",
                "source_lane": "dual_lock:knight_s11",
                "strategy": "knight",
                "sector": 11,
                "cfg_name": "canonical",
                "worker_id": 1,
                "stride_arm": -1,
                "stride": 0,
                "weight": max(0.0, float(knight_weight or 0.25)),
                "reason": "A8.1 z36 exact recipe seed; keep as fresh challenger",
            },
        ]
        self.forced_counts: Dict[str, int] = {r["name"]: 0 for r in self.recipes}
        self.exact_worker_hits: Dict[str, int] = {r["name"]: 0 for r in self.recipes}
        self.last_decision: Dict[str, Any] = {"forced": False, "reason": "init"}
        self.last_snapshot: Dict[str, Any] = {}

    def _cfg_by_name(self, cfgs: List[BuildConfig], name: str) -> BuildConfig:
        return next((c for c in cfgs if c.name == name), cfgs[0])

    def _pick_recipe(self, rng: random.Random) -> Dict[str, Any]:
        total = sum(max(0.0, float(r.get("weight", 0.0))) for r in self.recipes)
        if total <= 0:
            return self.recipes[0]
        x = rng.random() * total
        acc = 0.0
        for r in self.recipes:
            acc += max(0.0, float(r.get("weight", 0.0)))
            if x <= acc:
                return r
        return self.recipes[-1]

    def choose(self, rng: random.Random, cfgs: List[BuildConfig], round_id: int, worker_id: int) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            self.last_decision = {"forced": False, "reason": "disabled", "round_id": round_id, "worker_id": worker_id}
            return None
        if rng.random() >= self.focus_share:
            self.last_decision = {"forced": False, "reason": "exploration_share", "round_id": round_id, "worker_id": worker_id, "focus_share": self.focus_share}
            return None
        r = self._pick_recipe(rng)
        exact = (int(worker_id) == int(r.get("worker_id", -999)))
        self.forced_counts[r["name"]] = int(self.forced_counts.get(r["name"], 0)) + 1
        if exact:
            self.exact_worker_hits[r["name"]] = int(self.exact_worker_hits.get(r["name"], 0)) + 1
        cfg = self._cfg_by_name(cfgs, str(r.get("cfg_name", "canonical")))
        self.last_decision = {
            "forced": True,
            "round_id": round_id,
            "worker_id": worker_id,
            "recipe_name": r["name"],
            "source_recipe_key": r["source_recipe_key"],
            "exact_worker_match": exact,
            "strategy": r["strategy"],
            "sector": r["sector"],
            "cfg_name": cfg.name,
            "stride_arm": r["stride_arm"],
            "stride": r["stride"],
            "focus_share": self.focus_share,
            "allocator": "OFF",
            "wire": "FROZEN",
            "reason": "ANTI_DISPERSION_RECIPE_FOCUS",
        }
        return {
            "strategy": str(r["strategy"]),
            "sector": int(r["sector"]) % SECTORS,
            "cfg": cfg,
            "lane": str(r["source_lane"]),
            "stride_arm": int(r["stride_arm"]),
            "stride": int(r["stride"]),
            "selected_by": "recipe_focus",
            "recipe_focus": True,
            "recipe_focus_name": str(r["name"]),
            "source_recipe_key": str(r["source_recipe_key"]),
            "exact_worker_match": bool(exact),
        }

    def snapshot(self) -> Dict[str, Any]:
        obj = {
            "schema": self.SCHEMA,
            "version": VERSION,
            "sentinel": SENTINEL,
            "enabled": bool(self.enabled),
            "mode": "anti_dispersion_recipe_focus",
            "allocator_enabled": False,
            "changes_wire": False,
            "wire_change_required": False,
            "changes_scheduler": True,
            "scheduler_change_kind": "fixed recipe focus; no fresh-gex auto allocator",
            "focus_share": self.focus_share,
            "exploration_share": round(max(0.0, 1.0 - self.focus_share), 4),
            "recipes": [dict(r) for r in self.recipes],
            "forced_counts": dict(self.forced_counts),
            "exact_worker_hits": dict(self.exact_worker_hits),
            "last_decision": dict(self.last_decision),
            "rules": {
                "allocator": "OFF",
                "wire": "FROZEN",
                "purpose": "reduce scheduler dispersion; restore exact A7/A8.1 recipes as seeds",
                "do_not_change": ["header", "nonce", "extranonce2", "ntime", "nbits", "prevhash", "TruthGate", "SubmitGate"],
            },
            "written_at_utc": utc_stamp_iso(),
        }
        self.last_snapshot = obj
        return obj

    def line(self) -> str:
        snap = self.snapshot()
        dec = snap.get("last_decision", {})
        return (
            f"recipe_focus=ON allocator=OFF wire=FROZEN focus={self.focus_share*100.0:.1f}% "
            f"last_forced={dec.get('forced')} recipe={dec.get('recipe_name')} exact_worker={dec.get('exact_worker_match')} "
            f"forced_counts={snap.get('forced_counts')}"
        )


# ---------------------------------------------------------------------------
# A8.4 Bare Recipe Abyss Cut
# ---------------------------------------------------------------------------

BARE_RECIPE_RUNS = ("off", "a7_solo", "knight_solo", "duel_50_50", "random_control")


def bare_recipe_active(args: argparse.Namespace) -> bool:
    return str(getattr(args, "bare_recipe_run", "off") or "off") != "off"


def bare_recipe_snapshot(args: argparse.Namespace, workers: int = 0) -> Dict[str, Any]:
    mode = str(getattr(args, "bare_recipe_run", "off") or "off")
    return {
        "schema": "a8-4-v34-bare-recipe-abyss-cut-1",
        "version": VERSION,
        "sentinel": SENTINEL,
        "enabled": mode != "off",
        "mode": mode,
        "allocator_enabled": False,
        "changes_wire": False,
        "wire_change_required": False,
        "changes_scheduler": mode != "off",
        "scheduler_change_kind": "bare exact recipe generator; no fallback lanes; old adaptive layers disabled",
        "active_workers_rule": "solo/duel uses only exact seed workers; random_control uses random-only baseline",
        "workers_total": int(workers or 0),
        "recipes": {
            "a7_solo": {
                "name": "A7_Z38_ZIM_W9_A11_STRIDE521",
                "source_recipe_key": "bare:a7_solo/zim_reverse/s6/canonical/w9/a11/stride521",
                "source_lane": "bare:a7_solo",
                "strategy": "zim_reverse",
                "sector": 6,
                "cfg_name": "canonical",
                "worker_id": int(getattr(args, "bare_a7_worker", 9)),
                "stride_arm": 11,
                "stride": 521,
            },
            "knight_solo": {
                "name": "A8_1_Z36_KNIGHT_W1_A_NEG1_STRIDE0",
                "source_recipe_key": "bare:knight_solo/knight/s11/canonical/w1/a-1/stride0",
                "source_lane": "bare:knight_solo",
                "strategy": "knight",
                "sector": 11,
                "cfg_name": "canonical",
                "worker_id": int(getattr(args, "bare_knight_worker", 1)),
                "stride_arm": -1,
                "stride": 0,
            },
        },
        "rules": {
            "wire": "FROZEN",
            "allocator": "OFF",
            "theta": "OFF",
            "proofmind_adaptive_choice": "OFF",
            "kombucha_choice": "OFF",
            "protected_exposure": "OFF",
            "fresh_tailgex": "OFF",
            "tachyon_shadow_imports": "OFF",
            "fallback_lanes": "OFF",
            "validity_guards_kept": ["TruthGate", "SubmitGate", "DuplicateSubmitGuard", "StaleGuard", "ReconnectGuard"],
        },
    }


def bare_recipe_pick(args: argparse.Namespace, cfgs: List[BuildConfig], round_id: int, worker_id: int, rng: random.Random) -> Optional[Dict[str, Any]]:
    """Return one bare task descriptor or None for an idle worker.

    A8.4 intentionally has no ProofMind/Kombucha/dual_lock/janus fallback.
    """
    mode = str(getattr(args, "bare_recipe_run", "off") or "off")
    if mode == "off":
        return None
    cfg = next((c for c in cfgs if c.name == "canonical"), cfgs[0])
    a7_worker = int(getattr(args, "bare_a7_worker", 9))
    knight_worker = int(getattr(args, "bare_knight_worker", 1))

    def a7() -> Dict[str, Any]:
        return {
            "strategy": "zim_reverse",
            "sector": 6,
            "cfg": cfg,
            "lane": "bare:a7_solo",
            "stride_arm": 11,
            "stride": 521,
            "selected_by": "bare_recipe_a7_solo",
            "recipe_focus": True,
            "recipe_focus_name": "A7_Z38_ZIM_W9_A11_STRIDE521",
            "source_recipe_key": "bare:a7_solo/zim_reverse/s6/canonical/w9/a11/stride521",
            "exact_worker_match": int(worker_id) == a7_worker,
        }

    def knight() -> Dict[str, Any]:
        return {
            "strategy": "knight",
            "sector": 11,
            "cfg": cfg,
            "lane": "bare:knight_solo",
            "stride_arm": -1,
            "stride": 0,
            "selected_by": "bare_recipe_knight_solo",
            "recipe_focus": True,
            "recipe_focus_name": "A8_1_Z36_KNIGHT_W1_A_NEG1_STRIDE0",
            "source_recipe_key": "bare:knight_solo/knight/s11/canonical/w1/a-1/stride0",
            "exact_worker_match": int(worker_id) == knight_worker,
        }

    if mode == "a7_solo":
        return a7() if int(worker_id) == a7_worker else None
    if mode == "knight_solo":
        return knight() if int(worker_id) == knight_worker else None
    if mode == "duel_50_50":
        if int(worker_id) == a7_worker:
            return a7()
        if int(worker_id) == knight_worker:
            return knight()
        return None
    if mode == "random_control":
        sector = (int(worker_id) * 5 + int(round_id) * 3) % SECTORS
        return {
            "strategy": "random",
            "sector": sector,
            "cfg": cfg,
            "lane": "bare:random_control",
            "stride_arm": -1,
            "stride": 0,
            "selected_by": "bare_recipe_random_control",
            "recipe_focus": False,
            "recipe_focus_name": "RANDOM_CONTROL",
            "source_recipe_key": f"bare:random_control/random/s{sector}/canonical/w{worker_id}/a-1/stride0",
            "exact_worker_match": True,
        }
    return None


def validate_bare_recipe_workers(args: argparse.Namespace, workers: int) -> None:
    mode = str(getattr(args, "bare_recipe_run", "off") or "off")
    if mode == "off" or mode == "random_control":
        return
    a7_worker = int(getattr(args, "bare_a7_worker", 9))
    knight_worker = int(getattr(args, "bare_knight_worker", 1))
    required: List[int] = []
    if mode in ("a7_solo", "duel_50_50"):
        required.append(a7_worker)
    if mode in ("knight_solo", "duel_50_50"):
        required.append(knight_worker)
    if mode == "duel_50_50" and a7_worker == knight_worker:
        raise SystemExit("bare duel_50_50 requires distinct --bare-a7-worker and --bare-knight-worker")
    if required and max(required) >= int(workers):
        raise SystemExit(
            f"bare_recipe_run={mode} requires workers > {max(required)} "
            f"for required worker ids {required}; got --workers {workers}"
        )


def normalized_lane_weights(args: argparse.Namespace) -> List[Tuple[str, float]]:
    vals = [
        ("linear_proof", max(0.0, float(getattr(args, "linear_proof_weight", 35.0)))),
        ("janus_dispatcher", max(0.0, float(getattr(args, "janus_weight", 25.0)))),
        ("dual_lock", max(0.0, float(getattr(args, "dual_lock_weight", 20.0))) if getattr(args, "enable_dual_lock_lane", True) else 0.0),
        ("zim_reverse_s6", max(0.0, float(getattr(args, "zim_s6_weight", 15.0)))),
        ("random_baseline", max(0.0, float(getattr(args, "random_baseline_weight", 5.0)))),
    ]
    total = sum(v for _, v in vals)
    if total <= 0:
        vals = [("janus_dispatcher", 1.0)]
        total = 1.0
    return [(k, v / total) for k, v in vals if v > 0]


def choose_v31_task(args: argparse.Namespace, proofmind: JanusProofMind, endurance: Any, memory: KombuchaMemory, dual_lock: DualLockMemory, rng: random.Random, cfgs: List[BuildConfig], round_id: int, worker_id: int) -> Tuple[str, int, BuildConfig, str]:
    cfg = next((c for c in cfgs if c.name == "canonical"), cfgs[0])
    # A8.2 Protected Champion Exposure: fixed checked-exposure floor only.
    # This is not allocator mode and never touches header/nonce/extranonce2/submit wire.
    try:
        if bool(getattr(args, "enable_protected_exposure", False)) and V34_PROTECTED_EXPOSURE is not None:
            forced = V34_PROTECTED_EXPOSURE.choose(rng, cfg, V34_FRESH_TAILGEX_REVIEW, round_id, worker_id)
            if forced is not None:
                return forced
    except Exception as e:
        try:
            log("protected_exposure", f"choose skipped: {e}")
        except Exception:
            pass
    weights = normalized_lane_weights(args)
    x = rng.random()
    acc = 0.0
    lane = weights[-1][0]
    for k, w in weights:
        acc += w
        if x <= acc:
            lane = k
            break

    if lane == "linear_proof":
        # A1 proved best accepted/MH. Spread linear across all sectors for proof farming.
        return "linear", (round_id * 3 + worker_id) % SECTORS, cfg, "linear_proof"

    if lane == "dual_lock":
        return dual_lock.choose(rng, cfg, getattr(args, "dual_lock_linear_s6_weight", 40.0), getattr(args, "dual_lock_zim_s6_weight", 35.0), getattr(args, "dual_lock_knight_s11_weight", 25.0))

    if lane == "zim_reverse_s6":
        return "zim_reverse", 6, cfg, "zim_reverse_s6"

    if lane == "random_baseline":
        return "random", rng.randrange(SECTORS), cfg, "random_baseline"

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
            "schema": "v33-tachyon-shadow-dashboard-1",
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
            "v33_tachyon_shadow": V33_TACHYON_SHADOW.snapshot(client) if V33_TACHYON_SHADOW is not None else {"enabled": False, "wire_change_required": False},
            "v33_allocator_review": V33_ALLOCATOR_REVIEW.snapshot(V33_TACHYON_SHADOW, client, self) if V33_ALLOCATOR_REVIEW is not None else {"enabled": False, "wire_change_required": False},
            "v34_fresh_tailgex_review": V34_FRESH_TAILGEX_REVIEW.snapshot(V33_TACHYON_SHADOW, client) if V34_FRESH_TAILGEX_REVIEW is not None else {"enabled": False, "wire_change_required": False},
            "v34_protected_exposure_floor": V34_PROTECTED_EXPOSURE.snapshot(V34_FRESH_TAILGEX_REVIEW) if V34_PROTECTED_EXPOSURE is not None else {"enabled": False, "wire_change_required": False},
            "v34_recipe_focus": V34_RECIPE_FOCUS.snapshot() if V34_RECIPE_FOCUS is not None else {"enabled": False, "wire_change_required": False},
            "v34_bare_recipe_abyss_cut": bare_recipe_snapshot(args, int(getattr(args, "workers", 0) or 0)),
            "v33_tachyon_allocator": {
                "enabled": False,
                "allocator_review_enabled": bool(V33_ALLOCATOR_REVIEW is not None),
                "reason": "Allocator Review only; allocator intentionally disabled, scheduler/wire unchanged",
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
            f"hps_ewma≈{self.hps_ewma:,.0f} best_hps≈{self.best_hps_ewma:,.0f} "
            f"factor={self.last_factor:.2f} cooldown={self.cooldown} reason={self.last_reason} "
            f"acc/MH={self.accepted_per_mh(int(SESSION_STATE.get('accepted', 0) or 0)):.4f} "
            f"pruned={self.pruned_replacements} sector_lock={self.sector_lock_hits}"
        )


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
            "stride": cand.get("stride"),
            "stride_arm": cand.get("stride_arm"),
            "canonical_lane_key": cand.get("canonical_lane_key"),
            "recipe_key": cand.get("recipe_key"),
            "source_lane": cand.get("source_lane", cand.get("lane")),
            "protected_forced": cand.get("protected_forced"),
            "protected_lane_label": cand.get("protected_lane_label"),
            "selected_by": cand.get("selected_by"),
            "recipe_focus": cand.get("recipe_focus"),
            "recipe_focus_name": cand.get("recipe_focus_name"),
            "source_recipe_key": cand.get("source_recipe_key"),
            "exact_worker_match": cand.get("exact_worker_match"),
            "recipe_key_legacy_hex_stride": cand.get("recipe_key_legacy_hex_stride"),
            "job_age_ms": cand.get("job_age_ms"),
            "wire_lock": {
                "nonce_submit_big_endian_uint32_hex": True,
                "nonce_header_little_endian_bytes": True,
                "prevhash_word_reverse": True,
                "extranonce2_endian": "little",
                "noncanonical_submit": False,
            },
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
            "recipe_key": cand.get("recipe_key"),
            "selected_by": cand.get("selected_by"),
            "recipe_focus_name": cand.get("recipe_focus_name"),
            "source_recipe_key": cand.get("source_recipe_key"),
            "pool_diff": cand.get("pool_diff"),
            "lane": cand.get("lane"),
            "strategy": cand.get("strategy"),
            "sector": cand.get("sector"),
            "worker_id": cand.get("worker_id"),
            "cfg_name": cand.get("cfg_name"),
            "stride": cand.get("stride"),
            "stride_arm": cand.get("stride_arm"),
            "canonical_lane_key": cand.get("canonical_lane_key"),
            "recipe_key": cand.get("recipe_key"),
            "source_lane": cand.get("source_lane", cand.get("lane")),
            "protected_forced": cand.get("protected_forced"),
            "selected_by": cand.get("selected_by"),
            "recipe_focus": cand.get("recipe_focus"),
            "recipe_focus_name": cand.get("recipe_focus_name"),
            "source_recipe_key": cand.get("source_recipe_key"),
            "exact_worker_match": cand.get("exact_worker_match"),
            "job_age_ms": cand.get("job_age_ms"),
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
                "worker_id": cand.get("worker_id"),
                "stride": cand.get("stride"),
                "stride_arm": cand.get("stride_arm"),
                "canonical_lane_key": cand.get("canonical_lane_key"),
                "recipe_key": cand.get("recipe_key"),
                "source_lane": cand.get("source_lane", cand.get("lane")),
                "protected_forced": cand.get("protected_forced"),
                "job_age_ms": cand.get("job_age_ms"),
                "pool_response": cand.get("pool_response"),
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
                "worker_id": cand.get("worker_id"),
                "stride": cand.get("stride"),
                "stride_arm": cand.get("stride_arm"),
                "canonical_lane_key": cand.get("canonical_lane_key"),
                "recipe_key": cand.get("recipe_key"),
                "protected_forced": cand.get("protected_forced"),
            },
            "inferred": {
                "rarity_signal_only": True,
                "sha_direction_claim": False,
                "scheduler_reward_hint": "accepted + high z increases future allocation to this combo",
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
                "worker_id": cand.get("worker_id"),
                "stride": cand.get("stride"),
                "stride_arm": cand.get("stride_arm"),
                "canonical_lane_key": cand.get("canonical_lane_key"),
                "recipe_key": cand.get("recipe_key"),
                "source_lane": cand.get("source_lane", cand.get("lane")),
                "protected_forced": cand.get("protected_forced"),
                "job_age_ms": cand.get("job_age_ms"),
                "pool_response": cand.get("pool_response"),
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
            if V31_DUALLOCK_MEMORY is not None:
                V31_DUALLOCK_MEMORY.observe_accepted(cand)
            if V33_TACHYON_SHADOW is not None:
                V33_TACHYON_SHADOW.observe_accepted(cand)
                V33_TACHYON_SHADOW.save()
            if V34_FRESH_TAILGEX_REVIEW is not None:
                V34_FRESH_TAILGEX_REVIEW.observe_accepted(cand, proof_path=path)
                V34_FRESH_TAILGEX_REVIEW.save(V33_TACHYON_SHADOW, None)
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
    p = argparse.ArgumentParser(prog="RblganulA8_4V34BareRecipeAbyssCut")
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
                   help="V33 gate policy: lab=pool_z for max proof frequency; proof=fixed local gate; lottery=fixed local gate reserved for high-z policies")
    p.add_argument("--submit-limit-per-worker", type=int, default=2)
    p.add_argument("--signal-z", type=int, default=28)
    p.add_argument("--csv-log", default="rblganul_a8_4_v34_bare_recipe_abyss_lab.csv")
    p.add_argument("--proofs-dir", default="proofs", help="directory for accepted-share proof JSON files")
    p.add_argument("--lockbox", default="a8_4_v34_bare_recipe_abyss_lockbox.json", help="startup configuration lockbox JSON")
    p.add_argument("--session-summary", default="session_summary_a8_4_v34_bare_recipe_abyss.json", help="periodic/exit A8.4/V34 bare-recipe session summary JSON")
    p.add_argument("--janus-brain", default="rblganul_a8_4_v34_bare_recipe_disabled_brain.json", help="A8.4 disabled ProofMind compatibility file")
    p.add_argument("--registry-dir", default="proofs", help="Janus meta-registry root; defaults to proofs/ so artifacts stay together")
    p.add_argument("--proof-dashboard", default="rblganul_a8_4_v34_bare_recipe_abyss_dashboard.json", help="A8.4/V34 bare-recipe live dashboard JSON for long unattended runs")
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
    p.add_argument("--stride-memory", default="rblganul_a8_4_v34_bare_recipe_disabled_stride_memory.json")
    p.add_argument("--disable-notify-oracle", action="store_true")
    p.add_argument("--notify-pause-window-ms", type=int, default=450)
    # V31 DualLock Oracle flags. Defaults are the Codex-recommended mix:
    # 35% linear proof lane, 25% Janus dispatcher, 20% Dual Lock, 15% Zim s6, 5% random baseline.
    p.add_argument("--enable-dual-lock-lane", dest="enable_dual_lock_lane", action="store_true", default=True)
    p.add_argument("--disable-dual-lock-lane", dest="enable_dual_lock_lane", action="store_false")
    p.add_argument("--linear-proof-weight", type=float, default=35.0)
    p.add_argument("--janus-weight", type=float, default=25.0)
    p.add_argument("--dual-lock-weight", type=float, default=20.0)
    p.add_argument("--zim-s6-weight", type=float, default=15.0)
    p.add_argument("--random-baseline-weight", type=float, default=5.0)
    p.add_argument("--dual-lock-linear-s6-weight", type=float, default=40.0)
    p.add_argument("--dual-lock-zim-s6-weight", type=float, default=35.0)
    p.add_argument("--dual-lock-knight-s11-weight", type=float, default=25.0)
    p.add_argument("--tail-z", type=int, default=30)
    p.add_argument("--tail-z33", type=int, default=33)
    p.add_argument("--v31-rate-window", type=int, default=256)
    p.add_argument("--strategy-rates", default="rblganul_a8_4_v34_bare_recipe_rates.json")
    p.add_argument("--tail-events", default="rblganul_a8_4_v34_bare_recipe_tail_events.jsonl")
    p.add_argument("--dual-lock-memory", default="rblganul_a8_4_v34_bare_recipe_disabled_dual_lock.json")
    p.add_argument("--enable-tachyon-shadow", dest="enable_tachyon_shadow", action="store_true", default=False,
                   help="V33: enable Tachyon Shadow Mode telemetry; observe-only, no scheduler/wire changes")
    p.add_argument("--disable-tachyon-shadow", dest="enable_tachyon_shadow", action="store_false",
                   help="V33: disable Tachyon Shadow telemetry")
    p.add_argument("--tachyon-shadow-path", default="rblganul_a8_4_v34_tachyon_shadow_disabled.json",
                   help="V33 Tachyon Shadow telemetry JSON")
    p.add_argument("--tachyon-shadow-window", type=int, default=512,
                   help="V33 Tachyon recent event window size")
    p.add_argument("--tachyon-baseline-z", type=int, default=23,
                   help="V33 Tachyon expected-tail baseline; accepted proof corpus usually starts at z23+")
    p.add_argument("--tachyon-shadow-save-every-rounds", type=int, default=5,
                   help="save V33 Tachyon Shadow JSON every N rounds")
    p.add_argument("--enable-allocator-review", dest="enable_allocator_review", action="store_true", default=False,
                   help="V33: enable allocator review artifact; review-only, no scheduler/wire changes")
    p.add_argument("--disable-allocator-review", dest="enable_allocator_review", action="store_false",
                   help="V33: disable allocator review artifact")
    p.add_argument("--allocator-review-path", default="rblganul_a8_4_v34_allocator_review_disabled.json",
                   help="V33 allocator-review JSON; dry analysis only")
    p.add_argument("--allocator-review-min-proofs", type=int, default=15000,
                   help="minimum shadow accepted proofs before READY FOR ALLOCATOR REVIEW ONLY")
    p.add_argument("--allocator-review-min-lane-accepted", type=int, default=24,
                   help="minimum accepted proofs for a lane before TailGEX is trusted")
    p.add_argument("--allocator-review-top-limit", type=int, default=16,
                   help="number of lanes written into allocator review shortlist")
    p.add_argument("--enable-protected-exposure-review", dest="enable_fresh_tailgex_review", action="store_true", default=False,
                   help="A8.3/V34: enable fresh-only TailGEX review; observe-only, no scheduler/wire changes")
    p.add_argument("--disable-protected-exposure-review", dest="enable_fresh_tailgex_review", action="store_false",
                   help="A8.3/V34: disable fresh-only TailGEX review")
    p.add_argument("--protected-exposure-path", "--fresh-tailgex-path", dest="fresh_tailgex_path", default="rblganul_a8_4_v34_fresh_tailgex_disabled.json",
                   help="A8.3/V34 fresh-only TailGEX review JSON")
    p.add_argument("--protected-exposure-window-seconds", "--fresh-tailgex-window-seconds", dest="fresh_tailgex_window_seconds", type=int, default=21600,
                   help="ProtectedExposure window in seconds; default 6 hours")
    p.add_argument("--protected-exposure-window-count", "--fresh-tailgex-window-count", dest="fresh_tailgex_window_count", type=int, default=2000,
                   help="ProtectedExposure window accepted-proof count cap")
    p.add_argument("--protected-exposure-min-lane-accepted", "--fresh-tailgex-min-lane-accepted", dest="fresh_tailgex_min_lane_accepted", type=int, default=50,
                   help="minimum fresh accepted proofs for a lane before fresh_gex is trusted")
    p.add_argument("--fresh-champion-exposure-floor", type=float, default=0.12,
                   help="champion watch low-exposure threshold, e.g. 0.12 = 12%")
    p.add_argument("--enable-protected-exposure", dest="enable_protected_exposure", action="store_true", default=False,
                   help="A8.3: enable protected checked-exposure floor test; allocator remains OFF and wire remains FROZEN")
    p.add_argument("--disable-protected-exposure", dest="enable_protected_exposure", action="store_false",
                   help="A8.2: disable protected checked-exposure floor and fall back to pure A8.1 review behavior")
    p.add_argument("--protected-zim-s6-floor", type=float, default=0.12,
                   help="A8.3 real checked-exposure floor for zim_reverse/s6/canonical, e.g. 0.12 = 12%")
    p.add_argument("--protected-knight-s11-floor", type=float, default=0.05,
                   help="A8.3 keep-alive checked-exposure floor for knight/s11/canonical, e.g. 0.05 = 5%")
    p.add_argument("--protected-deficit-boost", type=float, default=2.25,
                   help="A8.3 soft enforcement boost applied to total floor deficit")
    p.add_argument("--protected-max-force-prob", type=float, default=0.45,
                   help="A8.3 max probability per worker task to force an under-floor lane")
    p.add_argument("--protected-log-every-rounds", type=int, default=10,
                   help="A8.3 log protected exposure summary every N rounds")
    p.add_argument("--enable-recipe-focus", dest="enable_recipe_focus", action="store_true", default=False,
                   help="A8.3 Anti-Dispersion: enable exact recipe focus scheduler, allocator OFF, wire FROZEN")
    p.add_argument("--disable-recipe-focus", dest="enable_recipe_focus", action="store_false",
                   help="Disable A8.3 recipe focus and fall back to A8.2 broad floor")
    p.add_argument("--recipe-focus-share", type=float, default=0.82,
                   help="Fraction of worker tasks assigned to anti-dispersion recipe focus; default 82%")
    p.add_argument("--recipe-focus-a7-weight", type=float, default=0.70,
                   help="Weight for A7 z38 recipe seed w9/a11/stride521")
    p.add_argument("--recipe-focus-knight-weight", type=float, default=0.25,
                   help="Weight for A8.1 z36 knight recipe seed")
    p.add_argument("--recipe-focus-log-every-rounds", type=int, default=10,
                   help="A8.3 log recipe focus summary every N rounds")
    p.add_argument("--protected-exposure-stale-hours", "--fresh-tailgex-stale-hours", dest="fresh_tailgex_stale_hours", type=float, default=6.0,
                   help="global/imported lane is stale for decision use after this many hours")
    p.add_argument("--tachyon-import-previous-proofs", dest="tachyon_import_previous_proofs", action="store_true", default=False,
                   help="import previous accepted_index.json into Tachyon Shadow at startup")
    p.add_argument("--no-tachyon-import-previous-proofs", dest="tachyon_import_previous_proofs", action="store_false")
    p.add_argument("--import-v30-state", dest="import_v30_state", action="store_true", default=False, help="import V30 dashboard/session/proof index at startup and continue counters")
    p.add_argument("--no-import-v30-state", dest="import_v30_state", action="store_false")
    p.add_argument("--v30-proof-dashboard", default="proof_dashboard.json")
    p.add_argument("--v30-session-summary", default="session_summary.json")
    p.add_argument("--v30-janus-brain", default="rblganul_v30_best_brain.json")
    p.add_argument("--v30-stride-memory", default="rblganul_v30_zim_stride_memory.json")
    p.add_argument("--v30-proofs-dir", default="", help="optional V30 proofs dir to import accepted_index.json from")
    p.add_argument("--bare-recipe-run", choices=list(BARE_RECIPE_RUNS), default="duel_50_50",
                   help="A8.4 Bare Recipe Abyss Cut mode: off/a7_solo/knight_solo/duel_50_50/random_control")
    p.add_argument("--bare-a7-worker", type=int, default=9, help="worker id for A7 exact recipe w9/a11/stride521")
    p.add_argument("--bare-knight-worker", type=int, default=1, help="worker id for A8.1 knight exact recipe w1/a-1/stride0")
    p.add_argument("--bare-disable-old-layers", action="store_true", default=True,
                   help="force ProofMind/Kombucha/Tachyon/FreshGEX/ProtectedExposure/Allocator imports OFF in bare mode")
    p.add_argument("--no-bare-disable-old-layers", dest="bare_disable_old_layers", action="store_false",
                   help="dangerous debug mode: do not force old layers off")

    # IO-path mode: like Janus Io supervisor, keep all V31 outputs next to this script
    # under janus_io_o1_runs/<run-name>, independent of the PowerShell current directory.
    p.add_argument("--io-output-root", default="", help="output root; default = script_dir/janus_io_o1_runs")
    p.add_argument("--io-run-name", default="A8_4_V34_BARE_RECIPE_ABYSS_CUT_AFTER_A8_3", help="subfolder for this A8.4/V34 Bare Recipe Abyss Cut run")
    p.add_argument("--io-chdir", dest="io_chdir", action="store_true", default=True, help="chdir into IO run dir before writing artifacts; default ON")
    p.add_argument("--no-io-chdir", dest="io_chdir", action="store_false", help="disable IO chdir and use raw relative paths")
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
    run_name = str(getattr(args, "io_run_name", "A8_4_V34_BARE_RECIPE_ABYSS_CUT_AFTER_A8_3") or "A8_4_V34_BARE_RECIPE_ABYSS_CUT_AFTER_A8_3")
    run_dir = (root / run_name).resolve()
    proofs_dir = run_dir / "proofs"
    run_dir.mkdir(parents=True, exist_ok=True)
    proofs_dir.mkdir(parents=True, exist_ok=True)

    # Discover previous artifacts before changing CWD. A8.2 must prefer the last A8
    # allocator-review run for import, then fall back to A7/V32/V31.
    a8_1_previous_root = script_dir / "janus_io_o1_runs" / "A8_1_V34_FRESH_TAILGEX_REVIEW_AFTER_A8"
    a8_previous_root = script_dir / "janus_io_o1_runs" / "A8_V33_ALLOCATOR_REVIEW_AFTER_V33_SHADOW"
    old_roots = [
        script_dir / "janus_io_o1_runs" / "A7_V33_TACHYON_SHADOW_AFTER_V32",
        script_dir / "janus_io_o1_runs" / "A6_V32_NETWORKRECOVERY_AFTER_V31",
        script_dir / "janus_io_o1_runs" / "A5_V31_AFTER_V30_IMPORT",
        script_dir,
        Path(os.getcwd()).resolve(),
        script_dir / "janus_io_o1_runs" / "A3_JANUS_FULL",
        script_dir / "janus_io_o1_runs" / "A4_DUAL_LOCK_TEST",
        script_dir / "janus_io_o1_runs" / "A1_LINEAR_PURE",
    ]
    previous_dashboard = v31_io_first_existing([
        a8_1_previous_root / "rblganul_a8_1_v34_fresh_tailgex_dashboard.json",
        a8_previous_root / "rblganul_v33_allocator_review_dashboard.json",
        a8_previous_root / "rblganul_a8_3_v34_recipe_focus_dashboard.json",
        old_roots[0] / "rblganul_v33_tachyon_shadow_dashboard.json",
        old_roots[1] / "rblganul_v32_networkrecovery_dashboard.json",
        old_roots[2] / "rblganul_v31_duallock_dashboard.json",
        old_roots[2] / "proof_dashboard.json",
        old_roots[3] / "proof_dashboard.json",
        old_roots[4] / "proof_dashboard.json",
        old_roots[5] / "a3_janus_full_proof_dashboard.json",
        old_roots[6] / "a4_dual_lock_test_proof_dashboard.json",
        old_roots[7] / "a1_linear_pure_proof_dashboard.json",
    ])
    previous_summary = v31_io_first_existing([
        a8_1_previous_root / "session_summary_a8_1_v34_fresh_tailgex.json",
        a8_previous_root / "session_summary_v33_allocator_review.json",
        a8_previous_root / "session_summary_a8_3_v34_recipe_focus.json",
        old_roots[0] / "session_summary_v33.json",
        old_roots[1] / "session_summary_v32.json",
        old_roots[2] / "session_summary_v31.json",
        old_roots[2] / "session_summary.json",
        old_roots[3] / "session_summary.json",
        old_roots[4] / "session_summary.json",
        old_roots[5] / "a3_janus_full_session_summary.json",
        old_roots[6] / "a4_dual_lock_test_session_summary.json",
        old_roots[7] / "a1_linear_pure_session_summary.json",
    ])
    previous_brain = v31_io_first_existing([
        a8_1_previous_root / "rblganul_a8_1_v34_best_brain.json",
        a8_previous_root / "rblganul_v33_best_brain.json",
        a8_previous_root / "rblganul_a8_3_v34_recipe_focus_best_brain.json",
        old_roots[0] / "rblganul_v33_best_brain.json",
        old_roots[1] / "rblganul_v32_best_brain.json",
        old_roots[2] / "rblganul_v31_best_brain.json",
        old_roots[2] / "rblganul_v30_best_brain.json",
        old_roots[3] / "rblganul_v30_best_brain.json",
        old_roots[4] / "rblganul_v30_best_brain.json",
        old_roots[5] / "a3_janus_full_best_brain.json",
        old_roots[6] / "a4_dual_lock_test_best_brain.json",
    ])
    previous_stride = v31_io_first_existing([
        a8_1_previous_root / "rblganul_a8_1_v34_zim_stride_memory.json",
        a8_previous_root / "rblganul_v33_zim_stride_memory.json",
        a8_previous_root / "rblganul_a8_3_v34_zim_stride_memory.json",
        old_roots[0] / "rblganul_v33_zim_stride_memory.json",
        old_roots[1] / "rblganul_v32_zim_stride_memory.json",
        old_roots[2] / "rblganul_v31_zim_stride_memory.json",
        old_roots[2] / "rblganul_v30_zim_stride_memory.json",
        old_roots[3] / "rblganul_v30_zim_stride_memory.json",
        old_roots[4] / "rblganul_v30_zim_stride_memory.json",
        old_roots[5] / "a3_janus_full_stride_memory.json",
        old_roots[6] / "a4_dual_lock_test_stride_memory.json",
    ])
    previous_proofs = v31_io_first_existing([
        a8_1_previous_root / "proofs",
        a8_previous_root / "proofs",
        old_roots[0] / "proofs",
        old_roots[1] / "proofs",
        old_roots[2] / "proofs",
        old_roots[3] / "proofs",
        old_roots[4] / "proofs",
        old_roots[5] / "proofs",
        old_roots[6] / "proofs",
    ])


    # Preserve explicit CLI paths. Only rewrite defaults to IO run dir names.
    if v31_io_was_default_path(getattr(args, "proofs_dir", ""), "proofs"):
        args.proofs_dir = str(proofs_dir)
    if v31_io_was_default_path(getattr(args, "registry_dir", ""), "proofs"):
        args.registry_dir = str(proofs_dir)
    defaults = {
        "csv_log": "rblganul_a8_4_v34_bare_recipe_abyss_lab.csv",
        "lockbox": "a8_4_v34_bare_recipe_abyss_lockbox.json",
        "session_summary": "session_summary_a8_4_v34_bare_recipe_abyss.json",
        "janus_brain": "rblganul_a8_4_v34_bare_recipe_disabled_brain.json",
        "proof_dashboard": "rblganul_a8_4_v34_bare_recipe_abyss_dashboard.json",
        "stride_memory": "rblganul_a8_4_v34_bare_recipe_disabled_stride_memory.json",
        "strategy_rates": "rblganul_a8_4_v34_bare_recipe_rates.json",
        "tail_events": "rblganul_a8_4_v34_bare_recipe_tail_events.jsonl",
        "dual_lock_memory": "rblganul_a8_4_v34_bare_recipe_disabled_dual_lock.json",
        "tachyon_shadow_path": "rblganul_a8_4_v34_tachyon_shadow_disabled.json",
        "allocator_review_path": "rblganul_a8_4_v34_allocator_review_disabled.json",
        "fresh_tailgex_path": "rblganul_a8_4_v34_fresh_tailgex_disabled.json",
    }
    for attr, name in defaults.items():
        if v31_io_was_default_path(getattr(args, attr, ""), name):
            setattr(args, attr, str(run_dir / name))

    # Auto-wire V30 import sources if the user did not override them.
    if v31_io_was_default_path(getattr(args, "v30_proof_dashboard", ""), "proof_dashboard.json") and previous_dashboard:
        args.v30_proof_dashboard = previous_dashboard
    if v31_io_was_default_path(getattr(args, "v30_session_summary", ""), "session_summary.json") and previous_summary:
        args.v30_session_summary = previous_summary
    if v31_io_was_default_path(getattr(args, "v30_janus_brain", ""), "rblganul_v30_best_brain.json") and previous_brain:
        args.v30_janus_brain = previous_brain
    if v31_io_was_default_path(getattr(args, "v30_stride_memory", ""), "rblganul_v30_zim_stride_memory.json") and previous_stride:
        args.v30_stride_memory = previous_stride
    if not getattr(args, "v30_proofs_dir", "") and previous_proofs:
        args.v30_proofs_dir = previous_proofs

    info = {
        "schema": "a8-2-v34-protected-exposure-io-path-bootstrap-1",
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
        "dual_lock_memory": args.dual_lock_memory,
        "tachyon_shadow_path": getattr(args, "tachyon_shadow_path", ""),
        "allocator_review_path": getattr(args, "allocator_review_path", ""),
        "fresh_tailgex_path": getattr(args, "fresh_tailgex_path", ""),
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
        atomic_json(str(run_dir / "a8_4_v34_bare_recipe_io_bootstrap.json"), info)
    except Exception:
        pass

    if bool(getattr(args, "io_chdir", True)):
        os.chdir(str(run_dir))
        info["active_cwd_after_chdir"] = os.getcwd()
        try:
            atomic_json(str(run_dir / "a8_4_v34_bare_recipe_io_bootstrap.json"), info)
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
    info: Dict[str, Any] = {"enabled": bool(getattr(args, "import_v30_state", True)), "items": []}
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
                continue

        ok, reason = verify_submit_mirror(job_snapshot, client.extranonce1, cand, cfg)
        cand["mirror_ok"] = ok
        cand["mirror_reason"] = reason
        if not ok:
            log("mirror", f"skip cfg={cfg.name} reason={reason}")
            dump_json("rblganul_v31_endurance_mirror_fail.json", cand)
            continue

        if V34_DUPLICATE_SUBMIT_GUARD is not None:
            allowed, dedupe_key = V34_DUPLICATE_SUBMIT_GUARD.allow(cand)
            cand["duplicate_submit_guard_key"] = dedupe_key
            if not allowed:
                cand["duplicate_submit_guard_dropped"] = True
                log("dedupe", f"skip duplicate submit key={dedupe_key} z={cand.get('zbits')} nonce={cand.get('nonce_submit_hex')}")
                dump_json("rblganul_a8_4_v34_duplicate_submit_drop.json", cand)
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
    if bare_recipe_active(args) and bool(getattr(args, "bare_disable_old_layers", True)):
        args.enable_recipe_focus = False
        args.enable_protected_exposure = False
        args.enable_fresh_tailgex_review = False
        args.enable_tachyon_shadow = False
        args.enable_allocator_review = False
        args.import_v30_state = False
        args.tachyon_import_previous_proofs = False
        args.enable_dual_lock_lane = False
        args.linear_proof_weight = 0.0
        args.janus_weight = 0.0
        args.dual_lock_weight = 0.0
        args.zim_s6_weight = 0.0
        args.random_baseline_weight = 0.0
    io_info = v31_io_prepare_paths(args)
    workers = effective_workers(args)
    validate_bare_recipe_workers(args, workers)
    cfgs = build_configs(args.matrix)
    cfg_by_name = {c.name: c for c in cfgs}

    print(f"[Rblganul] {VERSION}", flush=True)
    log("selfcheck", f"sentinel={SENTINEL}")
    log("selfcheck", f"file={os.path.abspath(sys.argv[0])}")
    source_sha16 = ""
    try:
        with open(sys.argv[0], "rb") as f:
            source_sha16 = hashlib.sha256(f.read()).hexdigest()[:16]
        log("selfcheck", f"sha256_16={source_sha16}")
    except Exception:
        pass

    log("io", f"output_root={io_info.get('io_output_root')} run_dir={io_info.get('io_run_dir')} cwd={os.getcwd()}")
    log("io", f"proofs_dir={args.proofs_dir} dashboard={args.proof_dashboard} session_summary={args.session_summary}")
    log("io", f"v30_import_dashboard={getattr(args, 'v30_proof_dashboard', '')} v30_proofs_dir={getattr(args, 'v30_proofs_dir', '')}")

    log("doctrine", "honest mode: zbits are rarity logs; proof is accepted shares and reproducible dumps")
    log("zimcore", "Zim mechanics active: NerdMiner subscribe tag, LE extranonce2, reverse odd-stride walk, stride bandit, notify oracle")
    log("power", f"workers={workers} batch={args.batch:,} matrix={args.matrix} cfgs={','.join(c.name for c in cfgs)}")
    log("proofmind", f"mode={args.mode} ProofMind object exists for compatibility; adaptive choice is OFF when bare_recipe_run={getattr(args, 'bare_recipe_run', 'off')}; wire bytes are locked")
    log("endurance", f"dashboard/reconnect telemetry active; batch pressure/pruning are bypassed in bare mode; proof_dashboard={args.proof_dashboard}")
    log("v31", f"fallback lanes enabled={args.enable_dual_lock_lane}; ignored when bare_recipe_run={getattr(args, 'bare_recipe_run', 'off')}; mix={dict(normalized_lane_weights(args))}")
    log("autostart", f"embedded profile: host={args.host} port={args.port} tls={args.tls} user={args.user} password={args.password} suggest_diff={args.suggest_diff:g} no_suggest={args.no_suggest_diff} subscribe_tag={args.subscribe_tag} local_submit_z={args.local_submit_z} auto_escalate={args.auto_escalate_local_z} lowdiff_jump={args.lowdiff_jump_to_floor}")
    log("autostart", "NerdMiner lottery endpoint preset: pool.nerdminers.org:3333")
    log("run", "no long command needed: python RBLGANUL_A8_4_V34_BARE_RECIPE_ABYSS_CUT_IO_SINGLE.py")
    log("v32_net", f"NetworkRecovery enabled={args.enable_reconnect} backoff={args.reconnect_initial_backoff:g}->{args.reconnect_max_backoff:g}s; stale old-round candidates are dropped after reconnect")
    log("v33_tachyon", f"Tachyon Shadow Mode enabled={args.enable_tachyon_shadow}; observe-only, allocator=OFF, wire=FROZEN, path={args.tachyon_shadow_path}")
    log("allocator_review", f"Allocator Review enabled={args.enable_allocator_review}; REVIEW ONLY, allocator=OFF, wire=FROZEN, path={args.allocator_review_path}, min_proofs={args.allocator_review_min_proofs}")
    log("fresh_tailgex", f"A8.3/V34 Protected Champion Exposure review enabled={args.enable_fresh_tailgex_review}; FRESH-ONLY REVIEW, allocator=OFF, wire=FROZEN, path={getattr(args, 'fresh_tailgex_path', '')} window={getattr(args, 'fresh_tailgex_window_seconds', 0)}s/{getattr(args, 'fresh_tailgex_window_count', 0)} proofs")
    log("protected_exposure", f"A8.3 floor+recipe audit test enabled={getattr(args, 'enable_protected_exposure', True)} allocator=OFF wire=FROZEN zim_floor={getattr(args, 'protected_zim_s6_floor', 0.12):.3f} knight_floor={getattr(args, 'protected_knight_s11_floor', 0.05):.3f} max_force_prob={getattr(args, 'protected_max_force_prob', 0.45):.2f}")
    log("abyss", f"A8.4 Bare Recipe Abyss Cut mode={getattr(args, 'bare_recipe_run', 'off')} allocator=OFF wire=FROZEN old_layers_disabled={getattr(args, 'bare_disable_old_layers', True)} A7_worker={getattr(args, 'bare_a7_worker', 9)} knight_worker={getattr(args, 'bare_knight_worker', 1)}")

    if getattr(args, "selfcheck", False):
        log("proofpack", f"proofs_dir={args.proofs_dir} lockbox={args.lockbox} session_summary={args.session_summary} mode={args.mode} longrun={args.longrun} quiet={args.quiet}")
        log("proofmind", f"janus_brain={args.janus_brain} registry_dir={args.registry_dir} stale_guard={args.stale_guard}")
        log("endurance", f"dashboard={args.proof_dashboard} disabled={args.disable_endurance_oracle} max_batch_factor={args.max_batch_factor} min_batch_factor={args.min_batch_factor}")
        log("v31", f"strategy_rates={args.strategy_rates} tail_events={args.tail_events} dual_lock_memory={args.dual_lock_memory} import_v30_state={args.import_v30_state}")
        log("v31", f"strategy_mix={dict(normalized_lane_weights(args))} dual_lock_internal=linear_s6:{args.dual_lock_linear_s6_weight} zim_s6:{args.dual_lock_zim_s6_weight} knight_s11:{args.dual_lock_knight_s11_weight}")
        log("v32_net", f"enable_reconnect={args.enable_reconnect} initial_backoff={args.reconnect_initial_backoff} max_backoff={args.reconnect_max_backoff} drop_round_candidates_after_reconnect={args.drop_round_candidates_after_reconnect}")
        log("v33_tachyon", f"enable_shadow={args.enable_tachyon_shadow} shadow_path={args.tachyon_shadow_path} window={args.tachyon_shadow_window} baseline_z={args.tachyon_baseline_z} import_previous={args.tachyon_import_previous_proofs}")
        log("allocator_review", f"enable_review={args.enable_allocator_review} path={args.allocator_review_path} min_proofs={args.allocator_review_min_proofs} min_lane_accepted={args.allocator_review_min_lane_accepted}")
        log("fresh_tailgex", f"enable_fresh_tailgex={args.enable_fresh_tailgex_review} path={args.fresh_tailgex_path} window_seconds={args.fresh_tailgex_window_seconds} window_count={args.fresh_tailgex_window_count} min_lane_accepted={args.fresh_tailgex_min_lane_accepted}")
        log("protected_exposure", f"enabled={args.enable_protected_exposure} zim_floor={args.protected_zim_s6_floor} knight_floor={args.protected_knight_s11_floor} boost={args.protected_deficit_boost} max_force_prob={args.protected_max_force_prob}")
        log("abyss", f"bare_recipe_run={args.bare_recipe_run} bare_disable_old_layers={args.bare_disable_old_layers} a7_worker={args.bare_a7_worker} knight_worker={args.bare_knight_worker}")
        log("abyss", f"bare_snapshot={bare_recipe_snapshot(args, workers)}")
        log("io", f"bootstrap={Path(args.lockbox).parent / 'a8_4_v34_bare_recipe_io_bootstrap.json'}")
        return

    global V31_RATEBOOK, V31_TAIL_TRACKER, V31_DUALLOCK_MEMORY, V33_TACHYON_SHADOW, V33_ALLOCATOR_REVIEW, V34_FRESH_TAILGEX_REVIEW, V34_PROTECTED_EXPOSURE, V34_RECIPE_FOCUS, V34_DUPLICATE_SUBMIT_GUARD
    V31_RATEBOOK = StrategyRateBook(args.strategy_rates, args.v31_rate_window)
    V31_TAIL_TRACKER = TailTracker(args.tail_events, args.tail_z, args.tail_z33)
    V31_DUALLOCK_MEMORY = None if bare_recipe_active(args) else DualLockMemory(args.dual_lock_memory)
    V33_TACHYON_SHADOW = TachyonShadowMode(args.tachyon_shadow_path, args.tachyon_shadow_window, args.tachyon_baseline_z) if args.enable_tachyon_shadow else None
    V33_ALLOCATOR_REVIEW = AllocatorReviewOnly(args.allocator_review_path, args.allocator_review_min_proofs, args.allocator_review_min_lane_accepted, args.allocator_review_top_limit, args.tachyon_baseline_z) if args.enable_allocator_review else None
    V34_FRESH_TAILGEX_REVIEW = ProtectedExposureReview(
        args.fresh_tailgex_path,
        baseline_z=args.tachyon_baseline_z,
        fresh_window_seconds=args.fresh_tailgex_window_seconds,
        fresh_window_count=args.fresh_tailgex_window_count,
        min_lane_accepted=args.fresh_tailgex_min_lane_accepted,
        champion_exposure_floor=args.fresh_champion_exposure_floor,
        stale_after_seconds=int(float(args.fresh_tailgex_stale_hours) * 3600.0),
    ) if args.enable_fresh_tailgex_review else None
    V34_PROTECTED_EXPOSURE = ProtectedChampionExposureFloor(
        zim_floor=getattr(args, "protected_zim_s6_floor", 0.12),
        knight_floor=getattr(args, "protected_knight_s11_floor", 0.05),
        deficit_boost=getattr(args, "protected_deficit_boost", 2.25),
        max_force_prob=getattr(args, "protected_max_force_prob", 0.45),
        log_every_rounds=getattr(args, "protected_log_every_rounds", 10),
    ) if bool(getattr(args, "enable_protected_exposure", True)) else None
    V34_RECIPE_FOCUS = RecipeFocusOracle(
        enabled=bool(getattr(args, "enable_recipe_focus", True)),
        focus_share=getattr(args, "recipe_focus_share", 0.82),
        a7_weight=getattr(args, "recipe_focus_a7_weight", 0.70),
        knight_weight=getattr(args, "recipe_focus_knight_weight", 0.25),
        log_every_rounds=getattr(args, "recipe_focus_log_every_rounds", 10),
    ) if bool(getattr(args, "enable_recipe_focus", True)) else None
    V34_DUPLICATE_SUBMIT_GUARD = DuplicateSubmitGuard()
    if not bare_recipe_active(args):
        v31_import_previous_state(args, None)
    else:
        log("abyss", "old corpus/brain/stride imports disabled for bare recipe run")
    if V33_TACHYON_SHADOW is not None and bool(getattr(args, "tachyon_import_previous_proofs", True)):
        imp = V33_TACHYON_SHADOW.import_accepted_index(getattr(args, "v30_proofs_dir", ""), label="previous_v32_or_v31")
        log("v33_tachyon", f"previous proof import: {imp}")
        V33_TACHYON_SHADOW.save()

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
        endurance_oracle=not bool(args.disable_endurance_oracle),
        v31_strategy_mix=dict(normalized_lane_weights(args)),
        v31_strategy_rates=args.strategy_rates,
        v31_tail_events=args.tail_events,
        v31_dual_lock_memory=args.dual_lock_memory,
        v31_import_v30_state=bool(args.import_v30_state),
        v33_tachyon_shadow_enabled=bool(args.enable_tachyon_shadow),
        v33_tachyon_shadow_path=args.tachyon_shadow_path,
        v33_tachyon_allocator_enabled=False,
        v33_allocator_review_enabled=bool(args.enable_allocator_review),
        v33_allocator_review_path=args.allocator_review_path,
        v34_fresh_tailgex_review_enabled=bool(args.enable_fresh_tailgex_review),
        v34_fresh_tailgex_review_path=args.fresh_tailgex_path,
        v34_protected_exposure_enabled=bool(getattr(args, "enable_protected_exposure", True)),
        v34_recipe_focus_enabled=bool(getattr(args, "enable_recipe_focus", True)),
        v34_recipe_focus_share=float(getattr(args, "recipe_focus_share", 0.82)),
        v34_bare_recipe_abyss_cut=bare_recipe_snapshot(args, workers),
        v34_bare_recipe_run=str(getattr(args, "bare_recipe_run", "off")),
        v34_protected_zim_s6_floor=float(getattr(args, "protected_zim_s6_floor", 0.12)),
        v34_protected_knight_s11_floor=float(getattr(args, "protected_knight_s11_floor", 0.05)),
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
    if not bare_recipe_active(args):
        v31_import_previous_state(args, client)
    else:
        log("abyss", "post-Stratum historical imports skipped; client counters start from live session")

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
        if V33_TACHYON_SHADOW is not None:
            V33_TACHYON_SHADOW.save(client, force=True)
        if V33_ALLOCATOR_REVIEW is not None:
            V33_ALLOCATOR_REVIEW.save(V33_TACHYON_SHADOW, client, endurance, force=True)
        if V34_FRESH_TAILGEX_REVIEW is not None:
            V34_FRESH_TAILGEX_REVIEW.save(V33_TACHYON_SHADOW, client, force=True)
        write_session_summary(args.session_summary)
        log("io", "initial dashboard/session/ratebook files written")
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
        log("autodiff", f"V24 submit gate starts at local_submit_z={local_submit_z}; auto_escalate={args.auto_escalate_local_z} lowdiff_jump={args.lowdiff_jump_to_floor} floor_diff={args.lowdiff_floor_diff:g} floor_z≈{floor_z_hint}")
    else:
        log("autodiff", f"NoEscalate mode={args.mode}: requested_local_submit_z={local_submit_z}; auto_escalate=False lowdiff_jump=False. Effective submit gate still follows the pool target, so if pool_diff=65536 then effective_z≈48 and z<48 will not be submitted.")
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

            if bare_recipe_active(args):
                raw_batch = base_batch
                batch_factor = 1.0
                batch = max(1_000, min(2_000_000, int(base_batch)))
            else:
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
                    f"pool_z≈{pool_z:.2f} requested_local_z={local_submit_z} effective_submit_z={effective_submit_z} "
                    f"effective_diff≈{z_to_difficulty(effective_submit_z):.6g} "
                    f"net_z≈{net_z:.2f} tasks={workers} batch={batch:,}",
                )

            tasks: List[MineTask] = []
            active_bare_workers = 0
            for wid in range(workers):
                if bare_recipe_active(args):
                    bare_pick = bare_recipe_pick(args, cfgs, round_id, wid, rng)
                    if bare_pick is None:
                        continue
                    active_bare_workers += 1
                    st = bare_pick["strategy"]
                    sec = bare_pick["sector"]
                    cfg = bare_pick["cfg"]
                    lane = bare_pick["lane"]
                    stride_arm = int(bare_pick.get("stride_arm", -1))
                    stride = int(bare_pick.get("stride", 0))
                    selected_by = str(bare_pick.get("selected_by", "bare_recipe_abyss_cut"))
                    scheduler_source = selected_by
                    recipe_focus = bool(bare_pick.get("recipe_focus", False))
                    recipe_focus_name = str(bare_pick.get("recipe_focus_name", ""))
                    source_recipe_key = str(bare_pick.get("source_recipe_key", ""))
                    exact_worker_match = bool(bare_pick.get("exact_worker_match", True))
                else:
                    focus_pick = None
                    try:
                        if V34_RECIPE_FOCUS is not None and bool(getattr(args, "enable_recipe_focus", True)):
                            focus_pick = V34_RECIPE_FOCUS.choose(rng, cfgs, round_id, wid)
                    except Exception as e:
                        try:
                            log("recipe_focus", f"choose skipped: {e}")
                        except Exception:
                            pass
                        focus_pick = None

                    if focus_pick is not None:
                        st = focus_pick["strategy"]
                        sec = focus_pick["sector"]
                        cfg = focus_pick["cfg"]
                        lane = focus_pick["lane"]
                        stride_arm = int(focus_pick.get("stride_arm", -1))
                        stride = int(focus_pick.get("stride", 0))
                        selected_by = str(focus_pick.get("selected_by", "recipe_focus"))
                        scheduler_source = selected_by
                        recipe_focus = bool(focus_pick.get("recipe_focus", True))
                        recipe_focus_name = str(focus_pick.get("recipe_focus_name", ""))
                        source_recipe_key = str(focus_pick.get("source_recipe_key", ""))
                        exact_worker_match = bool(focus_pick.get("exact_worker_match", False))
                    else:
                        st, sec, cfg, lane = choose_v31_task(args, proofmind, endurance, memory, V31_DUALLOCK_MEMORY, rng, cfgs, round_id, wid)
                        selected_by = str(lane)
                        scheduler_source = selected_by
                        recipe_focus = False
                        recipe_focus_name = ""
                        source_recipe_key = ""
                        exact_worker_match = False
                        seed_tmp = stable_seed(job.job_id, job.seq, round_id, wid, st, sec, cfg.name, lane)
                        stride_arm, stride = stride_bandit.choose(rng, seed_tmp) if st in ("zim_reverse", "zim_bandit") else (-1, 0)

                arm_weight = None
                try:
                    if 0 <= int(stride_arm) < len(stride_bandit.weights):
                        arm_weight = float(stride_bandit.weights[int(stride_arm)])
                except Exception:
                    arm_weight = None
                arm_reward_ema = float(getattr(stride_bandit, "reward_ema", 0.0))
                task_id = f"r{round_id}:w{wid}:{lane}:{st}:s{sec}:{cfg.name}:a{stride_arm}:stride{int(stride or 0) & 0xFFFFFFFF}"
                seed = stable_seed(job.job_id, job.seq, round_id, wid, st, sec, cfg.name, lane)
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
                        selected_by=selected_by,
                        scheduler_source=scheduler_source,
                        proofmind_mode="BARE" if bare_recipe_active(args) else str(args.mode),
                        recipe_focus=recipe_focus,
                        recipe_focus_name=recipe_focus_name,
                        source_recipe_key=source_recipe_key,
                        exact_worker_match=exact_worker_match,
                        batch_factor=float(batch_factor),
                        task_id=task_id,
                        arm_weight=arm_weight,
                        arm_reward_ema=arm_reward_ema,
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
                    if not bare_recipe_active(args):
                        memory.update_result(r)
                        score_observe_result(r)
                        if V31_RATEBOOK is not None:
                            V31_RATEBOOK.observe_result(r)
                        if V33_TACHYON_SHADOW is not None:
                            V33_TACHYON_SHADOW.observe_result(r)
                        if V34_FRESH_TAILGEX_REVIEW is not None:
                            V34_FRESH_TAILGEX_REVIEW.observe_result(r)
                        proofmind.observe_result(r)
                        stride_bandit.observe(r.stride_arm, r.best_z, len(r.candidates), 0, 0)
                    else:
                        score_observe_result(r)
                        if V31_RATEBOOK is not None:
                            V31_RATEBOOK.observe_result(r)
                    candidates.extend(r.candidates)
                    if V31_TAIL_TRACKER is not None:
                        for _cand in r.candidates:
                            V31_TAIL_TRACKER.observe_candidate(_cand, accepted=None)
                            if V33_TACHYON_SHADOW is not None:
                                V33_TACHYON_SHADOW.observe_candidate(_cand, accepted=None)

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

            if candidates and network_recovered_this_round and bool(getattr(args, "drop_round_candidates_after_reconnect", True)):
                if V32_NETWORK_RECOVERY is not None:
                    V32_NETWORK_RECOVERY.stale_round_drops += len(candidates)
                log("v32_net", f"dropped {len(candidates)} old-round candidates after reconnect; waiting for fresh notify/job")
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
                if not bare_recipe_active(args):
                    proofmind.observe_submit_delta(acc_delta, rej_delta, best)
                if acc_delta > 0:
                    last_accept_wall = time.time()
                    if not bare_recipe_active(args):
                        for _ in range(acc_delta):
                            memory.on_submit_result(True)
                            stride_bandit.observe(stride_bandit.last_arm, best.best_z, 1, 1, 0)
                        stride_bandit.save(force=True)
                        log("proofpack", f"accepted_delta={acc_delta}; stride memory saved immediately")
                        log("proofmind", f"accepted_delta={acc_delta}; gate unchanged mode={args.mode} local_submit_z={local_submit_z}; {proofmind.line()}")
                    else:
                        log("abyss", f"accepted_delta={acc_delta}; adaptive memories unchanged; bare_recipe_run={args.bare_recipe_run}")
                if rej_delta > 0:
                    if not bare_recipe_active(args):
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
                            reason = f"jump_to_pool_floor diff≈{args.lowdiff_floor_diff:g}"
                        else:
                            local_submit_z = min(int(args.max_local_submit_z), local_submit_z + int(args.escalate_step_z) * steps)
                            reason = "step"
                        if local_submit_z != old_z:
                            approx_diff = z_to_difficulty(local_submit_z)
                            log("autodiff", f"Difficulty too low x{rej_delta}: {reason}; local_submit_z {old_z}->{local_submit_z} local_diff≈{approx_diff:.6g}")
                            eta = fmt_duration(expected_share_seconds(max(1.0, approx_diff), max(1.0, total_hps)))
                            log("autodiff", f"at current hps≈{total_hps:,.0f}, expected share at local_diff≈{approx_diff:.6g} is about {eta}")
                            if not args.no_suggest_local_diff and not args.no_suggest_diff and math.isfinite(approx_diff):
                                try:
                                    client.suggest_difficulty(max(float(client.pool_diff), float(approx_diff)))
                                    log("autodiff", f"sent mining.suggest_difficulty {max(float(client.pool_diff), float(approx_diff)):.6g}")
                                except Exception as e:
                                    log("autodiff", f"suggest_difficulty failed: {e}")

            if not args.disable_endurance_oracle:
                endurance.observe_round(round_id, total_checked, total_hps, client.accepted, client.rejected, best.best_z, proofmind)

            if (client.accepted != last_accept_seen) or (client.rejected != last_reject_seen) or (round_id % 10 == 0):
                if not bare_recipe_active(args):
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
                    f"round={round_id} checked={total_checked:,} hps≈{total_hps:,.0f} "
                    f"best_z={best.best_z} requested_local_z={local_submit_z} effective_submit_z={active_gate_z} "
                    f"best={best.strategy}/s{best.sector}/w{best.worker_id}/{best.cfg_name} "
                    f"hash={mask_hex(best.best_hash, 40)} sub={client.submitted} acc={client.accepted} rej={client.rejected}",
                )
                log("scoreboard", f"top3 {top3_s}")
                if V31_RATEBOOK is not None:
                    log("v31_rates", V31_RATEBOOK.line())
                if V31_DUALLOCK_MEMORY is not None:
                    log("duallock", V31_DUALLOCK_MEMORY.line())
                if bare_recipe_active(args):
                    log("proofmind", "OFF in bare mode; no adaptive choice, no memory update, no save")
                else:
                    log("proofmind", proofmind.line())
                if not args.disable_endurance_oracle:
                    log("endurance", endurance.line())
                if total_hps > 0:
                    eta_pool = fmt_duration(expected_share_seconds(max(1e-12, float(client.pool_diff)), total_hps))
                    gate_diff = max(1e-12, z_to_difficulty(active_gate_z))
                    eta_gate = fmt_duration(expected_share_seconds(gate_diff, total_hps))
                    log("eta", f"pool_eta@diff={client.pool_diff:g}≈{eta_pool}; gate_eta@z={active_gate_z}/diff≈{gate_diff:.6g}≈{eta_gate}; hps≈{total_hps:,.0f}")
                if bare_recipe_active(args):
                    log("abyss", f"bare_recipe_run={args.bare_recipe_run} active_workers={active_bare_workers if 'active_bare_workers' in locals() else 0} batch={batch:,} old_layers=OFF wire=FROZEN")
                else:
                    next_batch = memory.next_batch(base_batch, client.accepted, client.rejected)
                    log("kombucha", memory.line(next_batch))
                    log("zimcore", f"{stride_bandit.line()} {notify_oracle.line()}")
                if V33_TACHYON_SHADOW is not None:
                    log("v33_tachyon", V33_TACHYON_SHADOW.line())
                if V33_ALLOCATOR_REVIEW is not None:
                    V33_ALLOCATOR_REVIEW.save(V33_TACHYON_SHADOW, client, endurance)
                    log("allocator_review", V33_ALLOCATOR_REVIEW.line())
                if V34_FRESH_TAILGEX_REVIEW is not None:
                    V34_FRESH_TAILGEX_REVIEW.save(V33_TACHYON_SHADOW, client)
                    log("fresh_tailgex", V34_FRESH_TAILGEX_REVIEW.line())
                if V34_PROTECTED_EXPOSURE is not None:
                    log("protected_exposure", V34_PROTECTED_EXPOSURE.line(V34_FRESH_TAILGEX_REVIEW))
                if V34_RECIPE_FOCUS is not None:
                    log("recipe_focus", V34_RECIPE_FOCUS.line())
                if V34_DUPLICATE_SUBMIT_GUARD is not None:
                    _dg = V34_DUPLICATE_SUBMIT_GUARD.snapshot()
                    log("dedupe", f"submit_guard seen={_dg.get('seen_keys')} dropped={_dg.get('dropped_duplicates')}")
                last_summary_wall = now_wall

            if not bare_recipe_active(args):
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
                v31_strategy_mix=dict(normalized_lane_weights(args)),
                v31_tail_tracker=V31_TAIL_TRACKER.summary() if V31_TAIL_TRACKER is not None else {},
                v31_ratebook_top=V31_RATEBOOK.rows_list()[:10] if V31_RATEBOOK is not None else [],
                v31_dual_lock_memory=V31_DUALLOCK_MEMORY.line() if V31_DUALLOCK_MEMORY is not None else "",
                v32_network_recovery=V32_NETWORK_RECOVERY.snapshot(client) if V32_NETWORK_RECOVERY is not None else {},
                v33_tachyon_shadow=V33_TACHYON_SHADOW.snapshot(client) if V33_TACHYON_SHADOW is not None else {"enabled": False},
                v33_allocator_review=V33_ALLOCATOR_REVIEW.snapshot(V33_TACHYON_SHADOW, client, endurance) if V33_ALLOCATOR_REVIEW is not None else {"enabled": False},
                v34_fresh_tailgex_review=V34_FRESH_TAILGEX_REVIEW.snapshot(V33_TACHYON_SHADOW, client) if V34_FRESH_TAILGEX_REVIEW is not None else {"enabled": False},
                v34_protected_exposure_floor=V34_PROTECTED_EXPOSURE.snapshot(V34_FRESH_TAILGEX_REVIEW) if V34_PROTECTED_EXPOSURE is not None else {"enabled": False},
                v34_recipe_focus=V34_RECIPE_FOCUS.snapshot() if V34_RECIPE_FOCUS is not None else {"enabled": False},
                v34_bare_recipe_abyss_cut=bare_recipe_snapshot(args, workers),
                v34_duplicate_submit_guard=V34_DUPLICATE_SUBMIT_GUARD.snapshot() if V34_DUPLICATE_SUBMIT_GUARD is not None else {"enabled": False},
                v33_tachyon_allocator="disabled_review_only",
            )
            if not args.disable_endurance_oracle and ((round_id % 5 == 0) or (client.accepted != last_accept_seen) or should_summary):
                endurance.write_dashboard(args, client, round_id, total_hps, int(SESSION_STATE.get("best_z", best.best_z) or best.best_z), proofmind)
            if V31_RATEBOOK is not None and ((round_id % 5 == 0) or should_summary):
                V31_RATEBOOK.save()
            if V31_DUALLOCK_MEMORY is not None and ((round_id % 25 == 0) or should_summary):
                V31_DUALLOCK_MEMORY.save()
            if V33_TACHYON_SHADOW is not None and ((round_id % max(1, int(args.tachyon_shadow_save_every_rounds)) == 0) or should_summary):
                V33_TACHYON_SHADOW.save(client)
            if V33_ALLOCATOR_REVIEW is not None and ((round_id % max(1, int(args.tachyon_shadow_save_every_rounds)) == 0) or should_summary):
                V33_ALLOCATOR_REVIEW.save(V33_TACHYON_SHADOW, client, endurance)
            if V34_FRESH_TAILGEX_REVIEW is not None and ((round_id % max(1, int(args.tachyon_shadow_save_every_rounds)) == 0) or should_summary):
                V34_FRESH_TAILGEX_REVIEW.save(V33_TACHYON_SHADOW, client)
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
