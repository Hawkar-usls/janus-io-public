# A18 Schema Notes

Every A18 runtime output carries safety sentinels:

```json
{
  "observer_only": true,
  "stratum_proxy": false,
  "miner_control": false,
  "submit_path_touched": false,
  "mirror_control_touched": false,
  "bias_output_only": true,
  "tranception_inference": false
}
```

`a18_hrain_swarm_overlay.json` is the future HRain entry point. HRain should read it as display data only.

Suggested overlay model:

- `nodes`: current swarm nodes normalized from NAS Brain.
- `events`: recent telemetry observations.
- `alerts`: stale/lost/degraded/thermal/watchdog hints.
- `summary`: counts and high-level health.

This schema is intentionally detached from miner control.
