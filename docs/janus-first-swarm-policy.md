# JANUS-First Swarm Policy

The ESP32 Swarm and NAS Brain support JANUS first.

This is a scheduler/corpus/directive priority rule, not a pool-wire rule.
The swarm must help JANUS become a better traversal agent while preserving the
randomized traversal mirror as a clean control arm.

## Priority

Allowed priority:

```text
ESP32 Swarm -> NAS Brain -> JANUS scheduler priors
ESP32 Swarm -> NAS Brain -> JANUS display/directive context
ESP32 Swarm -> NAS Brain -> private corpus summaries
A10/A10.3 local summaries -> NAS Brain curated corpus, when explicitly enabled
A10/A10.3 accepted-share corpus -> NAS Janus private archive, when explicitly enabled
```

Blocked priority:

```text
ESP32 Swarm -> randomized traversal mirror hints
NAS Brain -> randomized traversal mirror hints
NAS Brain -> Stratum submit
NAS Brain -> V30 wire mutation
NAS Brain -> local submit gate change
ESP32 node -> pool submit
swarm corpus -> accepted proof rewrite
NAS corpus archive -> randomized traversal mirror hints
```

## Meaning

The swarm works for JANUS by adding external context that can become
scheduler-side priors:

- device health;
- thermal and power hints;
- radio/ESP-NOW stability;
- local corpus tags;
- route and lane suggestions;
- display/directive state;
- archival memory from NAS Brain.

The randomized traversal mirror remains deliberately under-informed. Its job is
to stay the control branch so JANUS can be judged honestly.

## Current A10.3 Status

A10.3 does not actively use NAS or ESP32 data yet.

Current live behavior:

```text
local PC runner -> Stratum pool
local PC runner -> local private run artifacts
optional local PC sidecar -> NAS Janus private corpus archive
NAS/ESP32 -> advisory/corpus/telemetry context only
```

The next integration step should be a local `JANUS_FIRST_SWARM_ADVISORY` layer:

```text
read-only NAS/Swarm snapshot
-> local advisory JSON
-> JANUS-side scheduler priors only
-> no mirror hints
-> no wire/submit changes
```

Current passive helper:

```powershell
python .\scripts\janus_first_swarm_advisory.py --nas-url http://<nas-host>:5000
```

To save a private local snapshot:

```powershell
python .\scripts\janus_first_swarm_advisory.py --nas-url http://<nas-host>:5000 --output .\output\avengers\janus_first_swarm_advisory.json
```

The helper is GET-only for NAS and local-read-only unless `--output` is passed.
Its advisory target is always `JANUS_ONLY`.

## Endpoint Expectation

Primary NAS Brain URL:

```text
http://<nas-host>:5000
```

Expected useful endpoints when mapped:

```text
/api/status
/api/swarm/status
/api/swarm/nodes
/api/swarm/sense
/api/swarm/telemetry
/api/swarm/heartbeat
/api/swarm/corpus
/api/swarm/archivarius/report
```

If only `/api/status` answers, treat that as gateway health only. It is not
proof that the full JANUS-first swarm API is online.

## Operator Rule

If NAS or ESP32 telemetry begins changing submit pressure, wire policy, or the
randomized traversal mirror, stop and inspect. That is outside JANUS-first
policy.
