# A18.11 Historic Tail Revival Public Checkpoint

This folder preserves the public-safe profile metadata for the A18.11 scheduler
run. It intentionally excludes raw logs, private local paths, wallet-like
labels, pool credentials, LAN hosts, and runtime device dumps.

Files:

- `profile.public.json` - scheduler profile knobs and safety boundaries.
- `snapshot.public.json` - sanitized telemetry snapshot from the early run.
- `launch-template.ps1` - non-runnable public template showing the intended
  argument shape with placeholders only.

Use this as a reproducibility marker, not as a standalone public mining runner.
