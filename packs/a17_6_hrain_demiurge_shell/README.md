# A17.6 HRain Demiurge Shell

Repo-ready public-safe package for the JANUS A17.5 HRain Galaxy shell, with A17.6 cleanup.

## What This Is

This pack is an observer-only sidecar and presentation UI around JANUS/A14-style local run artifacts.

It provides:

- HRain bubble/caviar/spore graph UI.
- Hybrid Canvas glow/link layer plus SVG node layer.
- D3 force simulation with cluster LOD.
- `CINEMA`, `NORMAL`, `WIDE`, `DEEP`, and `VIDEO_SAFE` detail modes.
- `VIDEO` presentation mode and `FREEZE` capture mode.
- Output-only route bias, transition matrix, and hypotheses files.

## Safety Boundary

- `WIRE/HASH/SUBMIT` remain frozen.
- The sidecar is not a Stratum proxy.
- The mirror is untouched.
- `temple_route_bias.json` is output-only.
- The A14.2 miner must not read this bias unless a future, separately reviewed experiment explicitly enables it.
- No SHA-256 break claim, nonce prediction claim, or mining-profit claim is made.

## Miner Pack

The public package does not include live run artifacts, proof archives, raw logs, or private pool/wallet/worker configuration.

To run the full local stack, place your local miner pack here:

```text
A14_2_PURE_ROUTE_LOCK_PACK/
  Yaksa_A14_2_PURE_ROUTE_LOCK_MINER.ps1
```

For UI-only review, run:

```powershell
.\RUN_HRAIN_DEMIURGE_ONLY_A17.bat
```

Then open:

```text
http://127.0.0.1:8797/index.html
```

## Runtime Outputs

The sidecar writes local runtime files next to `index.html`:

- `a17_hrain_graph.json`
- `a17_status.json`
- `sidecar_bus.json`
- `temple_route_bias.json`
- `route_transition_matrix.json`
- `janus_demiurge_hypotheses.json`

These are ignored by Git. Curated examples live in `A17_HRAIN_DEMIURGE_SHELL/samples/`.
