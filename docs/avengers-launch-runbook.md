# Avengers A10.3 Private Launch Runbook

Status: public-safe operator runbook. Local operator paths, LAN addresses, and
private NAS share names are represented as placeholders.

Goal: run JANUS Stress Kombucha versus the randomized traversal mirror as the
first Avengers private comparison, without contaminating the A9.11 7000-gate
corpus.

Launch host: local PC, same style as the previous A9.11 PC runs. NAS and ESP32
Swarm are Avengers context/corpus/telemetry layers; the benchmark runner itself
is still the local PC runner.

Swarm priority: JANUS first. NAS/ESP32 data may later feed JANUS-side scheduler
priors and display/directive context, but it must not feed the randomized
traversal mirror or change submit/wire policy.

Corpus storage: the PC remains the hot runner. For full Avengers stages, the
launcher may start a private NAS corpus mirror sidecar that copies accepted
proof JSON, registry artifacts, and run dashboards into:

```text
<NAS Janus root>/avengers_corpus/<run name>/
```

The mirror is best-effort archival output only. If NAS is asleep, slow, or
temporarily unreachable, the PC runner keeps working. The sidecar never deletes
destination files, never feeds randomized traversal mirror hints, and never
changes Stratum submit behavior.

This runbook does not change V30 wire policy. It does not claim a SHA-256
break. It keeps the comparison as:

```text
JANUS structured traversal + stress Kombucha half
vs
randomized traversal mirror half
same runner
same machine
same pool job stream
same submit policy
same frozen wire
```

## Deadpool Rule

Avengers is not a replacement for Bitcoin, Primecoin, Cuckoo Cycle, Equihash,
Hashcash, or the earlier JANUS work. The run carries those ideas forward:

- Bitcoin: keep proof verification and wire rules explicit.
- Primecoin: let work have a second meaning, but keep proof validity separate.
- Cuckoo Cycle: respect structure, memory, and traversal as first-class signals.
- Equihash: track memory/corpus pressure and time-space tradeoff thinking.
- JANUS A9.11: keep strict 50/50 randomized mirror accounting.

The Avengers addition is the outer command discipline: corpus manifest,
NAS/Swarm preflight, new run namespace, and publication-safe boundaries.

Avengers lineage note: `docs/avengers-lineage.md`.

JANUS-first swarm policy: `docs/janus-first-swarm-policy.md`.

Rare-tail timing monitor: `docs/rare-tail-timing-monitor.md`. A10.3 writes the
monitor directly from the accepted-share path, so the run preserves z32+ timing,
pool job age, Kyiv hour, and JANUS-vs-mirror branch as derived telemetry. It is
observer-only in this stage and does not feed scheduler policy.

Janus glyph observer: `docs/janus-glyph-observer.md`. A10.3 scans pre-hash
coinbase/job bytes for readable strings, dates, and keyword echoes, then links
accepted z32+ shares to those glyphs. It is observer-only and does not change
header construction, submit policy, or the randomized traversal mirror.

A10 Encoding Archaeology extends that observer with entropy baselines,
mirror-glyph scoring, encoded-fragment classification, and a z28 rare-tail link
floor for glyph-family discovery. Public checkpoint:
`docs/a10-encoding-archaeology-status-2026-06-09.md`.

## Do Not Reuse The A9.11 Gate Run

Do not run the live benchmark inside:

```text
A9_11_V32_ACTIVE_TRIUNE_SOVEREIGN_GATE_50_50_AFTER_A9_10
```

Use a fresh Avengers run name:

```text
A10_AVENGERS_KOMBUCHA_STRESS_JANUS_VS_RANDOM_50_50_PRIVATE
```

This keeps the 7000-gate publication snapshot intact and makes the Avengers
corpus auditable as a new phase.

## Preflight

From the I0 repository root:

```powershell
python .\scripts\avengers_corpus_manifest.py --output .\output\avengers\avengers_corpus_manifest.json
python .\scripts\avengers_preflight.py --nas-url http://<nas-host>:5000 --output .\output\avengers\avengers_preflight_report.json
```

For NAS corpus mirroring, map the private NAS Janus share to an operator-chosen
drive letter or pass an explicit root:

```powershell
cmd /c "net use <drive-letter>: \\<nas-host>\Janus /persistent:yes"
$env:AVENGERS_NAS_JANUS_ROOT = "<NAS_JANUS_ROOT>"
$env:AVENGERS_RESUME_CORPUS = "1"
```

An operator launcher may set `AVENGERS_RESUME_CORPUS=1` by default and
auto-enable `AVENGERS_NAS_JANUS_ROOT` when the private NAS drive exists. Direct
Python launches can use a placeholder root:

```powershell
python .\START_A10_AVENGERS_PC.py --resume-corpus --nas-janus-root <NAS_JANUS_ROOT>
```

Expected current finding:

```text
NAS gateway answers /api/status, but /health and /api/swarm/status may be 404.
Treat this as gateway health only until the full NAS Brain swarm API is mapped.
Until then, A10.3 treats NAS/ESP32 as context/corpus/telemetry only.
```

## Dry Launch Command

From the I0 root, the operator-friendly launcher is:

```powershell
.\START_A10_AVENGERS_PC.bat
```

It asks for the exact launch phrase:

```text
The Avengers
```

Pressing Enter without the phrase prints the dry-run command only.

If your personal launcher calls files through `python "%~dp0<file>"`, use the
Python twin instead:

```powershell
python .\START_A10_AVENGERS_PC.py
```

Print the exact command without starting the miner:

```powershell
.\avengers\Start-AvengersJanusVsRandom.ps1
```

If Windows blocks `.ps1` execution, use the same dry launch via:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\avengers\Start-AvengersJanusVsRandom.ps1
```

## Live Private Launch

Only the operator should run this. It connects the A10.3 wrapper runner to its
configured Stratum pool and starts benchmark work. The wrapper reuses the A9.11
wire/mining implementation and patches only scheduler-side Kombucha memory:

```powershell
.\avengers\Start-AvengersJanusVsRandom.ps1 -Run -IUnderstandThisConnectsToPool
```

With Execution Policy bypass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\avengers\Start-AvengersJanusVsRandom.ps1 -Run -IUnderstandThisConnectsToPool
```

The `.bat` launcher uses this bypass internally after the operator enters
`The Avengers`.

The launcher keeps these guardrails:

- new Avengers run name;
- optional accepted-share corpus resume via the existing fresh-session boundary;
- optional private NAS corpus mirror sidecar;
- strict 50/50 randomized traversal mirror enabled;
- canonical matrix only;
- A10.3 stress Kombucha scheduler-side molecule enabled;
- JanusGlyphObserver pre-hash coinbase/job scanner enabled;
- no auto-escalate local z;
- no lowdiff jump to floor;
- stale guard enabled;
- active sovereign gate limited to JANUS-half phase changes;
- JANUS-first swarm policy: future NAS/ESP32 hints can target only JANUS-side priors;
- randomized mirror remains untouched;
- V30 frozen wire remains unchanged.

## A10 Encoding Archaeology Public Snapshot

The public-safe snapshot is:

```text
RBLGANUL_A10_ENCODING_ARCHAEOLOGY_V32_ACTIVE_TRIUNE_50_50_IO_SINGLE.py
Yaksa_A10_ENCODING_ARCHAEOLOGY_ISOLATED.bat
```

The `.bat` file is intentionally guarded in the public repository. It requires:

```text
JANUS_PUBLIC_LIVE_ACK=YES
RBLGANUL_USER=<operator worker>
```

This preserves the launcher shape without publishing an operator worker label
or silently connecting a reviewer machine to a Stratum pool.

## First Gate

Recommended first Avengers checkpoint:

```text
fresh accepted-share corpus: 1000
then 2000
then 7000
```

At each gate, generate a public-safe summary and compare:

- JANUS accepted-share corpus count;
- randomized traversal mirror count;
- JANUS best_z versus mirror best_z;
- z32+, z33+, z34+, z35+, z36+ tails;
- reject rate;
- WitchHunter dark-tail summary;
- JanusGlyphObserver glyph summary;
- frozen wire / wire_change_required status.

## Stop Conditions

Stop and inspect instead of continuing if:

- wire_change_required becomes true;
- reject pressure jumps unexpectedly;
- reconnect/stale drops explain the rare-tail pattern;
- randomized mirror accounting disappears;
- NAS/ESP32 telemetry begins changing submit pressure;
- NAS/ESP32 telemetry begins feeding randomized traversal mirror hints;
- output starts landing in the old A9.11 gate run.
