import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("janus_io_o1_runs") / "A5_V31_AFTER_V30_IMPORT"
OUT = Path("experiments") / "o1-01" / "v31_io_summary.md"
OUT.parent.mkdir(parents=True, exist_ok=True)

def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8", errors="replace"))

dash = load_json(ROOT / "rblganul_v31_duallock_dashboard.json") or {}
dl = load_json(ROOT / "rblganul_v31_dual_lock_memory.json") or {}
rates = load_json(ROOT / "rblganul_v31_strategy_rates.json") or {}

proofs_dir = ROOT / "proofs"
def is_accepted_proof_file(path):
    name = path.name
    return name.startswith("accepted_20") and "_z" in name and "_nonce0x" in name

proofs = (
    sorted(
        (p for p in proofs_dir.glob("accepted_*.json") if is_accepted_proof_file(p)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if proofs_dir.exists()
    else []
)

tail_file = ROOT / "rblganul_v31_tail_events.jsonl"
tail_events = []
if tail_file.exists():
    for line in tail_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tail_events.append(json.loads(line))
        except Exception:
            pass

def g(obj, key, default=""):
    return obj.get(key, default) if isinstance(obj, dict) else default

endurance = g(dash, "endurance", {}) or {}
proofmind = g(dash, "proofmind", {}) or {}
wire = g(dash, "wire_lock", {}) or {}
v31 = g(dash, "v31_duallock_oracle", {}) or {}

accepted = g(dash, "accepted", 0)
rejected = g(dash, "rejected", 0)
submitted = g(dash, "submitted", 0)
best_z = g(dash, "best_z", 0)
proof_count = len(proofs)

# Imported V30 baseline from the handoff design/logs.
base_accepted = 2027
base_rejected = 8
base_submitted = 1419
base_best_z = 32

# Dashboard totals are inherited/imported counters, not a clean IO-run delta.
# Use accepted proof files as the clean IO-run accepted/proof count.
dash_acc_minus_import = accepted - base_accepted
dash_rej_minus_import = rejected - base_rejected
dash_sub_minus_import = submitted - base_submitted
clean_io_reject_rate_hint = (dash_rej_minus_import / max(1, proof_count)) if proof_count else 0

def count_tail_from_names(threshold):
    c = 0
    for p in proofs:
        name = p.name
        marker = "_z"
        if marker in name:
            try:
                z = int(name.split(marker, 1)[1].split("_", 1)[0])
                if z >= threshold:
                    c += 1
            except Exception:
                pass
    return c

tail_counts = {
    "z24+": count_tail_from_names(24),
    "z25+": count_tail_from_names(25),
    "z26+": count_tail_from_names(26),
    "z28+": count_tail_from_names(28),
    "z30+": count_tail_from_names(30),
    "z32+": count_tail_from_names(32),
    "z33+": count_tail_from_names(33),
}

top = g(dash, "top_strategy_scoreboard", []) or []
top_rows = []
for item in top[:10]:
    top_rows.append(
        f"| `{g(item,'key', g(item,'strategy','?'))}` | {g(item,'accepted',0)} | {g(item,'best_z',0)} | {g(item,'observations',0)} | {g(item,'last_hps',0)} |"
    )

DUALLOCK_LANES = [
    ("linear_s6", "linear/s6/canonical"),
    ("zim_reverse_s6", "zim_reverse/s6/canonical"),
    ("knight_s11", "knight/s11/canonical"),
]

def as_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default

def nonzero_lane_rows(rows):
    for row in rows:
        if any(as_int(row.get(k, 0)) for k in ("attempts", "accepted", "best_z")):
            return True
    return False

def scoreboard_index():
    idx = {}
    if isinstance(top, list):
        for item in top:
            if isinstance(item, dict):
                key = item.get("key")
                if key:
                    idx[key] = item
    if isinstance(rates, dict):
        for key, item in rates.items():
            if isinstance(item, dict):
                idx.setdefault(key, {"key": key, **item})
    return idx

def dual_lock_rows_from_memory(memory):
    rows = []
    if not isinstance(memory, dict):
        return rows

    lanes = [lane for lane, _ in DUALLOCK_LANES]
    counts = memory.get("counts")
    accepted_map = memory.get("accepted")
    best_map = memory.get("best_z")
    if isinstance(counts, dict) or isinstance(accepted_map, dict) or isinstance(best_map, dict):
        for lane in lanes:
            rows.append(
                {
                    "lane": lane,
                    "attempts": as_int(g(counts, lane, 0)),
                    "accepted": as_int(g(accepted_map, lane, 0)),
                    "best_z": as_int(g(best_map, lane, 0)),
                    "source": "dual_lock_memory",
                }
            )
        if nonzero_lane_rows(rows):
            return rows

    rows = []
    for lane in lanes:
        item = memory.get(lane)
        if isinstance(item, dict):
            rows.append(
                {
                    "lane": lane,
                    "attempts": as_int(g(item, "attempts", g(item, "count", 0))),
                    "accepted": as_int(g(item, "accepted", 0)),
                    "best_z": as_int(g(item, "best_z", 0)),
                    "source": "dual_lock_memory",
                }
            )
    if nonzero_lane_rows(rows):
        return rows

    return []

def dual_lock_rows_from_scoreboard():
    idx = scoreboard_index()
    rows = []
    for lane, key in DUALLOCK_LANES:
        item = idx.get(key)
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "lane": lane,
                "attempts": as_int(g(item, "observations", g(item, "checked", 0))),
                "accepted": as_int(g(item, "accepted", 0)),
                "best_z": as_int(g(item, "best_z", 0)),
                "source": "top_strategy_scoreboard",
            }
        )
    return rows

dl_row_data = dual_lock_rows_from_memory(dl)
dl_fallback_note = ""
if not dl_row_data:
    dl_row_data = dual_lock_rows_from_scoreboard()
    dl_fallback_note = (
        "DualLock memory was empty, zeroed, or schema-mismatched; "
        "lane status fell back to `top_strategy_scoreboard`."
    )

dl_rows = [
    f"| `{row['lane']}` | {row['attempts']} | {row['accepted']} | {row['best_z']} | `{row['source']}` |"
    for row in dl_row_data
]

latest_proofs = []
for p in proofs[:15]:
    latest_proofs.append(f"| {datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec='seconds')} | `{p.name}` |")

md = f"""# V31 IO Summary

Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}
Input root: `{ROOT}`

## Main status

| Metric | Value |
|---|---:|
| Accepted | {accepted} |
| Rejected | {rejected} |
| Submitted | {submitted} |
| Reject rate total | {g(dash, 'reject_rate', 0)} |
| Best z | {best_z} |
| Clean IO accepted/proof files | {proof_count} |
| HPS last | {g(dash, 'hps_last', 0)} |
| HPS EWMA | {g(dash, 'hps_ewma', 0)} |
| Best HPS EWMA | {g(dash, 'best_hps_ewma', 0)} |
| Accepted/MH | {g(dash, 'accepted_per_mh', 0)} |
| Round | {g(dash, 'round', 0)} |
| Uptime seconds | {g(dash, 'uptime_seconds', 0)} |
| Written UTC | {g(dash, 'written_at_utc', '')} |

## Clean IO-run interpretation

Do not treat dashboard `accepted - imported_accepted` as pure new IO accepted. The dashboard accepted counter is inherited/imported state. The clean IO-run accepted/proof count is the number of accepted proof files in this IO output directory.

| Metric | Value |
|---|---:|
| Imported accepted | {base_accepted} |
| Imported rejected | {base_rejected} |
| Imported submitted | {base_submitted} |
| Imported best z | {base_best_z} |
| Clean IO accepted/proofs | {proof_count} |
| Clean IO/dashboard best z | {best_z} |
| Dashboard accepted minus import | {dash_acc_minus_import} |
| Dashboard rejected minus import | {dash_rej_minus_import} |
| Dashboard submitted minus import | {dash_sub_minus_import} |
| Reject/proof hint | {clean_io_reject_rate_hint:.6f} |

## Endurance

| Field | Value |
|---|---:|
| Cooldown | {g(endurance, 'cooldown', '')} |
| Cooldown rounds left | {g(endurance, 'cooldown_rounds_left', '')} |
| Batch factor | {g(endurance, 'last_batch_factor', '')} |
| Last reason | {g(endurance, 'last_reason', '')} |
| Pruned replacements | {g(endurance, 'pruned_replacements', '')} |
| Sector lock hits | {g(endurance, 'sector_lock_hits', '')} |
| Total checked | {g(endurance, 'total_checked', '')} |

## ProofMind

| Field | Value |
|---|---:|
| Mode | {g(proofmind, 'mode', '')} |
| Mode strength | {g(proofmind, 'mode_strength', '')} |
| Hunger | {g(proofmind, 'hunger', '')} |
| Elite | {g(proofmind, 'elite', '')} |
| Bad | {g(proofmind, 'bad', '')} |
| Best z seen | {g(proofmind, 'best_z_seen', '')} |
| Best combo | `{g(proofmind, 'best_combo', '')}` |

## Wire lock

| Invariant | Value |
|---|---:|
| nonce submit big-endian uint32 hex | {g(wire, 'nonce_submit_big_endian_uint32_hex', '')} |
| nonce header little-endian bytes | {g(wire, 'nonce_header_little_endian_bytes', '')} |
| prevhash word reverse | {g(wire, 'prevhash_word_reverse', '')} |
| extranonce2 little-endian | {g(wire, 'extranonce2_little_endian', '')} |
| wire change required | {g(v31, 'wire_change_required', False)} |

## DualLock memory

{dl_fallback_note}

| Lane | Attempts/Observations | Accepted | Best z | Source |
|---|---:|---:|---:|---|
{chr(10).join(dl_rows) if dl_rows else '| no data | 0 | 0 | 0 | `none` |'}

## Top strategy scoreboard

| Strategy | Accepted | Best z | Observations | Last HPS |
|---|---:|---:|---:|---:|
{chr(10).join(top_rows) if top_rows else '| no data | 0 | 0 | 0 | 0 |'}

## Tail counts from proof filenames

| Threshold | Count |
|---|---:|
| z24+ | {tail_counts['z24+']} |
| z25+ | {tail_counts['z25+']} |
| z26+ | {tail_counts['z26+']} |
| z28+ | {tail_counts['z28+']} |
| z30+ | {tail_counts['z30+']} |
| z32+ | {tail_counts['z32+']} |
| z33+ | {tail_counts['z33+']} |

## Latest proofs

| Modified | File |
|---|---|
{chr(10).join(latest_proofs) if latest_proofs else '| no proofs | no file |'}

## Decision

`KEEP RUNNING` if accepted grows and rejected does not grow fast. Wire remains frozen.
"""

OUT.write_text(md, encoding="utf-8")
print(f"Written: {OUT}")
print(md)
