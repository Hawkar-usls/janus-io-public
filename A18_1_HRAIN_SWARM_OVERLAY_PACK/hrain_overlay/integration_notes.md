# A18.1 HRain Overlay Integration Notes

Do not patch an active A17.5/A17.7 run in place. This module is for a later
A17.8 candidate.

## Static Includes

In a future A17.7/A17.8 `index.html`, add:

```html
<link rel="stylesheet" href="hrain_overlay/a18_hrain_overlay_style.css">
<script src="hrain_overlay/a18_hrain_overlay_reader.js"></script>
```

Suggested DOM targets:

```html
<div data-a18-swarm-badge></div>
<aside data-a18-swarm-panel></aside>
<div data-a18-swarm-ticker></div>
```

Start the reader after the page has loaded:

```html
<script>
  window.JANUS_A18_HRAIN_SWARM_OVERLAY.start({
    url: "a18_hrain_swarm_overlay.json",
    intervalMs: 6500
  });
</script>
```

## Runtime Path Strategy

Configure A18 bridge to write:

```text
A17_7_HRAIN_LIVE_READY_SYNC_PACK/A17_HRAIN_DEMIURGE_SHELL/a18_hrain_swarm_overlay.json
```

This is a runtime file and must not be committed.

HRain only reads this file. Miner does not read it. NAS does not control miner.
A18 does not write commands.

## UI Placement

- Top HUD badge: `SWARM: online/offline`.
- Side panel: Buzz/NAS/ESP nodes.
- Graph layer: small swarm bubbles.
- Alerts layer: warnings.
- Event ticker: latest swarm events.

## Sentinel Handling

The reader checks:

```json
{
  "observer_only": true,
  "miner_untouched": true,
  "wire_hash_submit_frozen": true,
  "mirror_untouched": true
}
```

If any sentinel is missing or false, HRain should show a warning badge, not
crash and not hide the issue.

## A17.8 Candidate

Proposed next patch:

```text
A17.7 -> A17.8 candidate:
Add A18.1 HRain swarm overlay reader.
```

That future patch must remain display-only.
