from __future__ import annotations

from copy import deepcopy
import json
from typing import Callable, Dict, List

from a18_43_event_horizon_airlock import (
    AirlockError,
    AirlockState,
    DrainObservation,
    EventHorizonAirlock,
    FrozenSnapshot,
    RuntimeIdentity,
    replay_ledger,
)


IDENTITY = RuntimeIdentity(pid=4242, session_id="persistent-session", reconnect_count=2)


def snapshot(finalized: int = 7, latest_safe: int = 7) -> FrozenSnapshot:
    return FrozenSnapshot(
        submitted=16,
        finalized=finalized,
        exposure=finalized,
        admitted=16,
        in_flight=max(0, 16 - finalized),
        queued=0,
        wave_epoch=0,
        latest_safe_finalized=latest_safe,
        cpu_package_power_w=55.0,
        cpu_package_temp_c=58.0,
    )


def build_to_snapshot(*, finalized: int = 7, latest_safe: int = 7, delay_ms: int = 0) -> EventHorizonAirlock:
    airlock = EventHorizonAirlock(identity=IDENTITY)
    airlock.begin_cycle("begin-0")
    airlock.request_freeze("freeze-0")
    airlock.ack_frozen(
        "frozen-0",
        control_epoch=0,
        wave_epoch=0,
        identity=IDENTITY,
        no_exposure_advance=True,
        no_finalized_advance=True,
        no_submitted_advance=True,
        delay_ms=delay_ms,
    )
    airlock.seal_snapshot("snapshot-0", snapshot(finalized, latest_safe), identity=IDENTITY)
    return airlock


def build_to_drain(*, delay_ms: int = 0) -> EventHorizonAirlock:
    airlock = build_to_snapshot(delay_ms=delay_ms)
    airlock.request_gate_close("close-0")
    airlock.ack_gate_closed(
        "closed-0",
        control_epoch=0,
        wave_epoch=0,
        identity=IDENTITY,
        admissions_enabled=False,
        admitted_total=16,
        delay_ms=delay_ms,
    )
    airlock.commit_horizon("commit-0")
    airlock.thaw_to_drain("thaw-0", identity=IDENTITY)
    return airlock


def clean_cycle(delay_ms: int = 0) -> EventHorizonAirlock:
    airlock = build_to_drain(delay_ms=delay_ms)
    airlock.observe_drain(
        "drain-1",
        DrainObservation(16, 16, 10, 10, 6, 0, 0, 2),
        identity=IDENTITY,
    )
    airlock.observe_drain(
        "drain-2",
        DrainObservation(16, 16, 16, 16, 0, 0, 0, 2),
        identity=IDENTITY,
    )
    airlock.observe_drain(
        "drain-3",
        DrainObservation(16, 16, 16, 16, 0, 0, 0, 2),
        identity=IDENTITY,
    )
    airlock.confirm_vacuum_valley("vacuum-0")
    airlock.reopen(
        "reopen-0",
        control_epoch=0,
        wave_epoch=0,
        identity=IDENTITY,
        new_wave_epoch=1,
    )
    return airlock


def expect_error(name: str, fn: Callable[[], None], contains: str | None = None) -> Dict[str, object]:
    try:
        fn()
    except AirlockError as exc:
        if contains and contains not in str(exc):
            return {"name": name, "pass": False, "detail": f"wrong error: {exc}"}
        return {"name": name, "pass": True, "detail": str(exc)}
    except Exception as exc:
        return {"name": name, "pass": False, "detail": f"unexpected {type(exc).__name__}: {exc}"}
    return {"name": name, "pass": False, "detail": "expected AirlockError"}


def run() -> Dict[str, object]:
    results: List[Dict[str, object]] = []

    for delay in (0, 10, 25, 50, 100, 250):
        airlock = clean_cycle(delay)
        ok, error = airlock.verify_ledger()
        results.append({
            "name": f"clean_cycle_delay_{delay}ms",
            "pass": airlock.state == AirlockState.REOPENED and ok,
            "detail": error or airlock.ledger[-1].event_hash,
        })

    airlock = EventHorizonAirlock(identity=IDENTITY)
    airlock.begin_cycle("begin")
    first = airlock.request_freeze("same-freeze")
    second = airlock.request_freeze("same-freeze")
    results.append({
        "name": "duplicate_command_idempotent",
        "pass": first.event_hash == second.event_hash and len(airlock.ledger) == 2,
        "detail": first.event_hash,
    })

    results.append(expect_error(
        "snapshot_before_frozen_rejected",
        lambda: EventHorizonAirlock(identity=IDENTITY).seal_snapshot("bad", snapshot(), identity=IDENTITY),
        "expected one of",
    ))
    results.append(expect_error("stale_frozen_ack_rejected", _stale_frozen_ack, "stale control epoch"))
    results.append(expect_error("gate_close_before_snapshot_rejected", _gate_before_snapshot, "expected one of"))
    results.append(expect_error(
        "thaw_before_gate_ack_rejected",
        lambda: build_to_snapshot().thaw_to_drain("bad", identity=IDENTITY),
        "expected one of",
    ))
    results.append(expect_error(
        "new_admission_during_decompression_fail_closed",
        _new_admission_during_drain,
        "new admission",
    ))
    results.append(expect_error(
        "inflight_increase_during_decompression_fail_closed",
        _inflight_increase,
        "in-flight increased",
    ))
    results.append(expect_error(
        "reopen_before_vacuum_rejected",
        lambda: build_to_drain().reopen(
            "bad", control_epoch=0, wave_epoch=0, identity=IDENTITY, new_wave_epoch=1
        ),
        "expected one of",
    ))
    results.append(expect_error(
        "single_zero_observation_not_enough",
        _single_zero_confirm,
        "vacuum requires",
    ))

    too_late = build_to_snapshot(finalized=8, latest_safe=7)
    event = too_late.abort_if_too_late("late-abort")
    results.append({
        "name": "too_late_abort_without_gate_change",
        "pass": event is not None and too_late.state == AirlockState.TOO_LATE_ABORTED and not too_late.gate_closed_ack,
        "detail": event.payload if event else None,
    })

    results.append(expect_error(
        "stale_gate_ack_from_previous_control_epoch_rejected",
        _stale_gate_ack,
        "stale control epoch",
    ))
    results.append(expect_error("pid_change_fail_closed", _pid_change, "runtime PID changed"))
    results.append(expect_error("reconnect_change_fail_closed", _reconnect_change, "reconnect count changed"))

    timed = EventHorizonAirlock(identity=IDENTITY)
    timed.begin_cycle("begin-t")
    timed.request_freeze("freeze-t")
    timed.timeout("timeout-t", "FROZEN_ACK", elapsed_ms=501, timeout_ms=500)
    results.append({
        "name": "missing_ack_timeout_fail_closed",
        "pass": timed.state == AirlockState.FAIL_CLOSED,
        "detail": timed.ledger[-1].payload,
    })

    valid = clean_cycle().export()
    replay_ok, replay_error = replay_ledger(valid["events"])
    results.append({"name": "ledger_replay_pass", "pass": replay_ok, "detail": replay_error})

    tampered = deepcopy(valid["events"])
    tampered[3]["payload"]["finalized"] = 999
    tamper_ok, tamper_error = replay_ledger(tampered)
    results.append({
        "name": "ledger_tamper_detected",
        "pass": not tamper_ok and tamper_error is not None,
        "detail": tamper_error,
    })

    passed = sum(1 for item in results if item["pass"])
    return {
        "schema": "JANUS/A18.43/event-horizon-airlock-fault-injection/v0.2.0",
        "status": "PASS" if passed == len(results) else "FAIL",
        "tests_passed": passed,
        "tests_total": len(results),
        "delay_matrix_ms": [0, 10, 25, 50, 100, 250],
        "miner_launched": False,
        "network_used": False,
        "hardware_control_performed": False,
        "results": results,
    }


def _stale_frozen_ack() -> None:
    a = EventHorizonAirlock(identity=IDENTITY)
    a.begin_cycle("b")
    a.request_freeze("f")
    a.ack_frozen(
        "ack", control_epoch=99, wave_epoch=0, identity=IDENTITY,
        no_exposure_advance=True, no_finalized_advance=True, no_submitted_advance=True,
    )


def _gate_before_snapshot() -> None:
    a = EventHorizonAirlock(identity=IDENTITY)
    a.begin_cycle("b")
    a.request_freeze("f")
    a.ack_frozen(
        "ack", control_epoch=0, wave_epoch=0, identity=IDENTITY,
        no_exposure_advance=True, no_finalized_advance=True, no_submitted_advance=True,
    )
    a.request_gate_close("close")


def _new_admission_during_drain() -> None:
    a = build_to_drain()
    a.observe_drain("d", DrainObservation(17, 16, 9, 9, 7, 0, 0, 2), identity=IDENTITY)


def _inflight_increase() -> None:
    a = build_to_drain()
    a.observe_drain("d1", DrainObservation(16, 16, 9, 9, 7, 0, 0, 2), identity=IDENTITY)
    a.observe_drain("d2", DrainObservation(16, 16, 10, 10, 8, 0, 0, 2), identity=IDENTITY)


def _single_zero_confirm() -> None:
    a = build_to_drain()
    a.observe_drain("d", DrainObservation(16, 16, 16, 16, 0, 0, 0, 2), identity=IDENTITY)
    a.confirm_vacuum_valley("v")


def _stale_gate_ack() -> None:
    a = build_to_snapshot()
    a.request_gate_close("close")
    a.ack_gate_closed(
        "ack", control_epoch=1, wave_epoch=0, identity=IDENTITY,
        admissions_enabled=False, admitted_total=16,
    )


def _pid_change() -> None:
    a = EventHorizonAirlock(identity=IDENTITY)
    a.begin_cycle("b")
    a.request_freeze("f")
    a.ack_frozen(
        "ack", control_epoch=0, wave_epoch=0,
        identity=RuntimeIdentity(pid=9999, session_id="persistent-session", reconnect_count=2),
        no_exposure_advance=True, no_finalized_advance=True, no_submitted_advance=True,
    )


def _reconnect_change() -> None:
    a = EventHorizonAirlock(identity=IDENTITY)
    a.begin_cycle("b")
    a.request_freeze("f")
    a.ack_frozen(
        "ack", control_epoch=0, wave_epoch=0,
        identity=RuntimeIdentity(pid=4242, session_id="persistent-session", reconnect_count=3),
        no_exposure_advance=True, no_finalized_advance=True, no_submitted_advance=True,
    )


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
