# A18.1 HRain Swarm Overlay

A18.1 is a standalone display-only overlay module for HRain/A17.

```text
A18 bridge
  -> a18_hrain_swarm_overlay.json
  -> HRain UI reads it
  -> draws home-swarm layer
  -> miner untouched
```

This pack does not patch a live HRain pack by itself. It provides a reader,
styles, sample data, and integration notes for a later A17.8 candidate.

Hard boundaries:

- Display-only.
- No NAS commands.
- No Buzz commands.
- No miner control.
- No WIRE / HASH / SUBMIT changes.
- No mirror control.
- No Tranception or bio telemetry in PoW scoring.
- No profit or superiority claims.

Expected runtime source:

```text
A17_7_HRAIN_LIVE_READY_SYNC_PACK/A17_HRAIN_DEMIURGE_SHELL/a18_hrain_swarm_overlay.json
```

That JSON is runtime data and must not be committed.
