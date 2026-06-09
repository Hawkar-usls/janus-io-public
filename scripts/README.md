# Scripts

These scripts are offline repository tools.

- `analyze_o1.py` reads local O1 run artifacts and writes curated summaries.
- `analyze_v31_io.py` inspects later local JANUS IO artifacts.
- `scrub_secrets.py` scans text files for local identifiers and can write
  `.redacted` copies without editing originals.
- `avengers_corpus_manifest.py` builds a private read-only Avengers corpus map
  from local summaries, NAS Brain, ESP32 Swarm sketches, and export metadata.
- `avengers_preflight.py` runs passive Avengers readiness checks. Optional NAS
  checks are GET-only and require an explicit `--nas-url`.
- `avengers_nas_corpus_mirror.py` mirrors private Avengers run dashboards,
  accepted-share proof JSON, and proof registry artifacts into a NAS Janus
  archive. It is a sidecar archiver, not a miner controller.
- `rare_tail_timing_monitor.py` reconstructs rare-tail timing tables from an
  existing run directory. The primary live path is now the embedded runner
  monitor described in `docs/rare-tail-timing-monitor.md`; this script remains
  an offline repair/backfill tool.
- JanusGlyphObserver is embedded in the A9.11/A10.3 runner and documented in
  `docs/janus-glyph-observer.md`. It writes derived pre-hash coinbase/job
  glyph telemetry during live runs; it is not a standalone miner script.
- `janus_first_swarm_advisory.py` builds a passive JANUS-first advisory
  snapshot from the current A10.3 run, NAS GET-only health, and LastSwarm
  presence. It does not write to NAS and never feeds the randomized mirror.

Do not start mining or connect to a pool during repository cleanup.
