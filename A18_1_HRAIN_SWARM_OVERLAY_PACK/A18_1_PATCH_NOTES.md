# A18.1 Patch Notes

Status: standalone overlay module, not yet injected into A17.7.

Added:

- `hrain_overlay/a18_hrain_overlay_reader.js`
- `hrain_overlay/a18_hrain_overlay_style.css`
- sample `a18_hrain_swarm_overlay.sample.json`
- integration notes for a future A17.8 candidate

Behavior:

- Fetches `a18_hrain_swarm_overlay.json`.
- Handles missing/offline A18 bridge gracefully.
- Checks observer safety sentinels.
- Prepares swarm nodes, alerts, events and summary for HRain display.
- Creates optional DOM widgets if a host page exposes target containers.

Non-behavior:

- Does not write files.
- Does not call NAS control endpoints.
- Does not modify miner behavior.
- Does not touch submit, mirror, WIRE, HASH, or Stratum.
