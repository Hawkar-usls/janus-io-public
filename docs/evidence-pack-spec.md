# Evidence Pack Specification

An evidence pack is a curated, scrubbed summary of a JANUS run. It is not a raw
`janus_io_o1_runs` dump.

## Required Metadata

- runner filename;
- runner version;
- sentinel;
- run directory name;
- fresh boundary marker;
- fresh start timestamp;
- snapshot timestamp;
- machine class if disclosed;
- pool endpoint class if disclosed;
- local submit threshold;
- wire policy statement.

## Required Health Fields

- accepted-share corpus size;
- rejected count;
- reject rate;
- reconnect count;
- stale drops;
- cooldown state;
- HPS EWMA;
- ProofMind mode if available;
- socket health if available;
- `wire_change_required`.

## Required Comparison Fields

For each compared side:

- side name;
- accepted count;
- checked MH;
- `best_z`;
- `z28+`;
- `z30+`;
- `z32+`;
- `z33+`;
- `z34+`;
- `z36+`;
- `z38+`;
- `z39+`;
- top lanes or groups;
- first `z32+` event if present;
- highest accepted-share event.

## Required Control Statement

Every public A/B result must state whether it is:

```text
inline unequal-exposure random control
strict same-run 50/50 randomized traversal mirror
sequential run comparison
fresh reproduction window
```

A9.11 should be described as:

```text
strict same-run 50/50 randomized traversal mirror
```

## Required Limitations

Every evidence pack must include:

- no SHA-256 break claim;
- no nonce prediction claim;
- no claim that one rare tail proves a deterministic law;
- note that rare-tail telemetry is probabilistic;
- note whether the run is still in progress;
- note whether raw proof artifacts remain private.

## Redaction Requirements

Remove or avoid publishing:

- wallet-like worker labels;
- local filesystem paths;
- private IPs and LAN paths;
- live lockboxes;
- raw logs;
- unreviewed proof archives;
- credentials, tokens, passwords, or API keys.

## Verification Commands

Repository-prep checks should be offline:

```powershell
python scripts\scrub_secrets.py --limit 80 README.md docs experiments
python -m py_compile .\RBLGANUL_A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_IO_SINGLE.py
git diff --check
```

Do not run a miner as part of repository cleanup.
