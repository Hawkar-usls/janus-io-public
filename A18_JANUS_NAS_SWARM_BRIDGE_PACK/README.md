# A18 JANUS NAS Swarm Bridge Pack

A18 is an observer-only bridge between NAS Brain / Buzz / ESP32-M5 swarm telemetry and future HRain/A17 visual overlays.

```text
Buzz / ESP32 / M5Stack nodes
  -> NAS Brain API
  -> A18 swarm bridge observer
  -> sanitized JSON summaries
  -> HRain/A17 sidecar reads summaries later
  -> miner untouched
```

Hard boundaries:

- Not a miner.
- Not a Stratum proxy.
- Does not modify Buzz devices or NAS Brain runtime.
- Does not call `/api/device/command`.
- Does not change WIRE / HASH / SUBMIT.
- Does not touch mirror control.
- Does not mix Tranception/bio telemetry into PoW scoring.
- Tranception is read only as status/placeholder; no inference is run.

Quick dry-run:

```powershell
.\RUN_A18_SWARM_BRIDGE.bat
```

or:

```powershell
python .\A18_SWARM_BRIDGE\a18_swarm_bridge.py --config .\A18_SWARM_BRIDGE\a18_swarm_config.example.json --once --dry-run
```

Runtime outputs are written beside the script and are intentionally ignored by Git:

- `a18_swarm_state.json`
- `a18_swarm_nodes.json`
- `a18_swarm_sense.json`
- `a18_hrain_swarm_overlay.json`
- `a18_status.json`
