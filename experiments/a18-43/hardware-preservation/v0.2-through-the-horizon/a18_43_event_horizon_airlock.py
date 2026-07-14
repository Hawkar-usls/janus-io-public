from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA = "JANUS/A18.43/event-horizon-airlock/v0.2.0"
ZERO_HASH = "0" * 64


class AirlockState(str, Enum):
    OPEN = "OPEN"
    FREEZE_REQUESTED = "FREEZE_REQUESTED"
    FROZEN = "FROZEN"
    SNAPSHOT_SEALED = "SNAPSHOT_SEALED"
    GATE_CLOSE_REQUESTED = "GATE_CLOSE_REQUESTED"
    GATE_CLOSED = "GATE_CLOSED"
    HORIZON_COMMITTED = "HORIZON_COMMITTED"
    THAWED_DRAINING = "THAWED_DRAINING"
    VACUUM_CANDIDATE = "VACUUM_CANDIDATE"
    VACUUM_VALLEY_CONFIRMED = "VACUUM_VALLEY_CONFIRMED"
    REOPENED = "REOPENED"
    TOO_LATE_ABORTED = "TOO_LATE_ABORTED"
    FAIL_CLOSED = "FAIL_CLOSED"


class AirlockError(RuntimeError):
    pass


@dataclass(frozen=True)
class RuntimeIdentity:
    pid: int
    session_id: str
    reconnect_count: int


@dataclass(frozen=True)
class FrozenSnapshot:
    submitted: int
    finalized: int
    exposure: int
    admitted: int
    in_flight: int
    queued: int
    wave_epoch: int
    latest_safe_finalized: int
    cpu_package_power_w: Optional[float] = None
    cpu_package_temp_c: Optional[float] = None

    @property
    def is_too_late(self) -> bool:
        return self.finalized > self.latest_safe_finalized


@dataclass(frozen=True)
class DrainObservation:
    admitted_total: int
    submitted_total: int
    finalized_total: int
    completed_total: int
    in_flight: int
    queued: int
    wave_epoch: int
    reconnect_count: int


@dataclass(frozen=True)
class LedgerEvent:
    seq: int
    control_epoch: int
    wave_epoch: int
    action_id: str
    event_type: str
    state_before: str
    state_after: str
    payload: Dict[str, Any]
    previous_hash: str
    event_hash: str

    @staticmethod
    def compute_hash(data: Dict[str, Any]) -> str:
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return sha256(encoded).hexdigest()

    @classmethod
    def create(
        cls,
        *,
        seq: int,
        control_epoch: int,
        wave_epoch: int,
        action_id: str,
        event_type: str,
        state_before: AirlockState,
        state_after: AirlockState,
        payload: Dict[str, Any],
        previous_hash: str,
    ) -> "LedgerEvent":
        base = {
            "seq": seq,
            "control_epoch": control_epoch,
            "wave_epoch": wave_epoch,
            "action_id": action_id,
            "event_type": event_type,
            "state_before": state_before.value,
            "state_after": state_after.value,
            "payload": payload,
            "previous_hash": previous_hash,
        }
        return cls(event_hash=cls.compute_hash(base), **base)


@dataclass
class EventHorizonAirlock:
    """Offline protocol core for the Undina-TimeShift airlock.

    This object does not launch a miner or control hardware. It validates the
    ordering, identity, acknowledgements, drain invariants and event chain that
    a future live adapter must obey.
    """

    identity: RuntimeIdentity
    control_epoch: int = 0
    wave_epoch: int = 0
    state: AirlockState = AirlockState.OPEN
    ledger: List[LedgerEvent] = field(default_factory=list)
    frozen_snapshot: Optional[FrozenSnapshot] = None
    gate_closed_ack: bool = False
    frozen_ack: bool = False
    horizon_committed: bool = False
    admission_total_at_gate_close: Optional[int] = None
    last_drain: Optional[DrainObservation] = None
    vacuum_zero_observations: int = 0
    accepted_action_ids: Dict[str, str] = field(default_factory=dict)

    def _append(
        self,
        action_id: str,
        event_type: str,
        next_state: AirlockState,
        payload: Optional[Dict[str, Any]] = None,
    ) -> LedgerEvent:
        payload = payload or {}
        previous_hash = self.ledger[-1].event_hash if self.ledger else ZERO_HASH
        event = LedgerEvent.create(
            seq=len(self.ledger) + 1,
            control_epoch=self.control_epoch,
            wave_epoch=self.wave_epoch,
            action_id=action_id,
            event_type=event_type,
            state_before=self.state,
            state_after=next_state,
            payload=payload,
            previous_hash=previous_hash,
        )
        self.ledger.append(event)
        self.accepted_action_ids[action_id] = event.event_hash
        self.state = next_state
        return event

    def _require_state(self, *allowed: AirlockState) -> None:
        if self.state not in allowed:
            raise AirlockError(f"state={self.state.value}; expected one of {[s.value for s in allowed]}")

    def _require_epoch(self, control_epoch: int, wave_epoch: int) -> None:
        if control_epoch != self.control_epoch:
            raise AirlockError(f"stale control epoch {control_epoch}; active={self.control_epoch}")
        if wave_epoch != self.wave_epoch:
            raise AirlockError(f"stale wave epoch {wave_epoch}; active={self.wave_epoch}")

    def _require_identity(self, identity: RuntimeIdentity) -> None:
        if identity.pid != self.identity.pid:
            self.fail_closed("PID_CHANGED", {"expected": self.identity.pid, "actual": identity.pid})
            raise AirlockError("runtime PID changed")
        if identity.session_id != self.identity.session_id:
            self.fail_closed("SESSION_CHANGED", {"expected": self.identity.session_id, "actual": identity.session_id})
            raise AirlockError("runtime session changed")
        if identity.reconnect_count != self.identity.reconnect_count:
            self.fail_closed(
                "RECONNECT_DELTA_NONZERO",
                {"expected": self.identity.reconnect_count, "actual": identity.reconnect_count},
            )
            raise AirlockError("reconnect count changed")

    def _idempotent(self, action_id: str, event_type: str) -> Optional[LedgerEvent]:
        if action_id not in self.accepted_action_ids:
            return None
        for event in self.ledger:
            if event.action_id == action_id:
                if event.event_type != event_type:
                    raise AirlockError(f"action_id collision: {action_id}")
                return event
        raise AirlockError("internal action ledger inconsistency")

    def begin_cycle(self, action_id: str) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "BEGIN_CYCLE")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.OPEN, AirlockState.REOPENED, AirlockState.TOO_LATE_ABORTED)
        if self.state in {AirlockState.REOPENED, AirlockState.TOO_LATE_ABORTED}:
            self.control_epoch += 1
        self.frozen_snapshot = None
        self.gate_closed_ack = False
        self.frozen_ack = False
        self.horizon_committed = False
        self.admission_total_at_gate_close = None
        self.last_drain = None
        self.vacuum_zero_observations = 0
        return self._append(action_id, "BEGIN_CYCLE", AirlockState.OPEN)

    def request_freeze(self, action_id: str) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "FREEZE_REQUEST")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.OPEN)
        return self._append(action_id, "FREEZE_REQUEST", AirlockState.FREEZE_REQUESTED)

    def ack_frozen(
        self,
        action_id: str,
        *,
        control_epoch: int,
        wave_epoch: int,
        identity: RuntimeIdentity,
        no_exposure_advance: bool,
        no_finalized_advance: bool,
        no_submitted_advance: bool,
        delay_ms: int = 0,
    ) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "FROZEN_ACK")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.FREEZE_REQUESTED)
        self._require_epoch(control_epoch, wave_epoch)
        self._require_identity(identity)
        if not (no_exposure_advance and no_finalized_advance and no_submitted_advance):
            self.fail_closed(
                "FREEZE_QUIESCENCE_FAILED",
                {
                    "no_exposure_advance": no_exposure_advance,
                    "no_finalized_advance": no_finalized_advance,
                    "no_submitted_advance": no_submitted_advance,
                },
            )
            raise AirlockError("freeze quiescence proof failed")
        self.frozen_ack = True
        return self._append(action_id, "FROZEN_ACK", AirlockState.FROZEN, {"delay_ms": delay_ms})

    def seal_snapshot(
        self,
        action_id: str,
        snapshot: FrozenSnapshot,
        *,
        identity: RuntimeIdentity,
    ) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "SNAPSHOT_SEALED")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.FROZEN)
        self._require_identity(identity)
        if snapshot.wave_epoch != self.wave_epoch:
            raise AirlockError("snapshot wave epoch mismatch")
        self.frozen_snapshot = snapshot
        payload = {
            "submitted": snapshot.submitted,
            "finalized": snapshot.finalized,
            "exposure": snapshot.exposure,
            "admitted": snapshot.admitted,
            "in_flight": snapshot.in_flight,
            "queued": snapshot.queued,
            "latest_safe_finalized": snapshot.latest_safe_finalized,
            "too_late": snapshot.is_too_late,
            "cpu_package_power_w": snapshot.cpu_package_power_w,
            "cpu_package_temp_c": snapshot.cpu_package_temp_c,
        }
        return self._append(action_id, "SNAPSHOT_SEALED", AirlockState.SNAPSHOT_SEALED, payload)

    def abort_if_too_late(self, action_id: str) -> Optional[LedgerEvent]:
        duplicate = self._idempotent(action_id, "TOO_LATE_ABORT")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.SNAPSHOT_SEALED)
        if self.frozen_snapshot is None:
            raise AirlockError("missing frozen snapshot")
        if not self.frozen_snapshot.is_too_late:
            return None
        return self._append(
            action_id,
            "TOO_LATE_ABORT",
            AirlockState.TOO_LATE_ABORTED,
            {
                "finalized": self.frozen_snapshot.finalized,
                "latest_safe_finalized": self.frozen_snapshot.latest_safe_finalized,
                "gate_closed": False,
                "required_live_action": "IMMEDIATE_THAW_WITHOUT_POLICY_CHANGE",
            },
        )

    def request_gate_close(self, action_id: str) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "GATE_CLOSE_REQUEST")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.SNAPSHOT_SEALED)
        if self.frozen_snapshot is None:
            raise AirlockError("missing frozen snapshot")
        if self.frozen_snapshot.is_too_late:
            raise AirlockError("cannot close gate after latest-safe horizon; abort first")
        return self._append(action_id, "GATE_CLOSE_REQUEST", AirlockState.GATE_CLOSE_REQUESTED)

    def ack_gate_closed(
        self,
        action_id: str,
        *,
        control_epoch: int,
        wave_epoch: int,
        identity: RuntimeIdentity,
        admissions_enabled: bool,
        admitted_total: int,
        delay_ms: int = 0,
    ) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "GATE_CLOSED_ACK")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.GATE_CLOSE_REQUESTED)
        self._require_epoch(control_epoch, wave_epoch)
        self._require_identity(identity)
        if admissions_enabled:
            self.fail_closed("GATE_ACK_BUT_ADMISSIONS_ENABLED")
            raise AirlockError("gate close acknowledgement contradicted by enabled admissions")
        self.gate_closed_ack = True
        self.admission_total_at_gate_close = admitted_total
        return self._append(
            action_id,
            "GATE_CLOSED_ACK",
            AirlockState.GATE_CLOSED,
            {"admitted_total": admitted_total, "delay_ms": delay_ms},
        )

    def commit_horizon(self, action_id: str) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "HORIZON_COMMIT")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.GATE_CLOSED)
        if not (self.frozen_ack and self.gate_closed_ack and self.frozen_snapshot is not None):
            raise AirlockError("horizon commit prerequisites incomplete")
        self.horizon_committed = True
        return self._append(
            action_id,
            "HORIZON_COMMIT",
            AirlockState.HORIZON_COMMITTED,
            {"frozen_ack": True, "snapshot_sealed": True, "gate_closed_ack": True},
        )

    def thaw_to_drain(self, action_id: str, *, identity: RuntimeIdentity) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "THAW_TO_DRAIN")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.HORIZON_COMMITTED)
        self._require_identity(identity)
        if not self.horizon_committed or not self.gate_closed_ack:
            raise AirlockError("cannot thaw to drain before horizon commit and gate closure")
        return self._append(action_id, "THAW_TO_DRAIN", AirlockState.THAWED_DRAINING)

    def observe_drain(
        self,
        action_id: str,
        observation: DrainObservation,
        *,
        identity: RuntimeIdentity,
    ) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "DRAIN_OBSERVATION")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.THAWED_DRAINING, AirlockState.VACUUM_CANDIDATE)
        self._require_identity(identity)
        if observation.wave_epoch != self.wave_epoch:
            self.fail_closed("DRAIN_WAVE_EPOCH_CHANGED")
            raise AirlockError("drain observation wave epoch changed")
        if observation.reconnect_count != self.identity.reconnect_count:
            self.fail_closed("DRAIN_RECONNECT_DELTA_NONZERO")
            raise AirlockError("reconnect during drain")
        if self.admission_total_at_gate_close is None:
            raise AirlockError("missing gate-close admission baseline")
        if observation.admitted_total != self.admission_total_at_gate_close:
            self.fail_closed(
                "NEW_ADMISSION_DURING_DECOMPRESSION",
                {"at_gate_close": self.admission_total_at_gate_close, "observed": observation.admitted_total},
            )
            raise AirlockError("new admission during controlled decompression")
        if self.last_drain is not None:
            if observation.in_flight > self.last_drain.in_flight:
                self.fail_closed(
                    "IN_FLIGHT_INCREASE_DURING_DECOMPRESSION",
                    {"previous": self.last_drain.in_flight, "current": observation.in_flight},
                )
                raise AirlockError("in-flight increased during decompression")
            if observation.queued > self.last_drain.queued:
                self.fail_closed(
                    "QUEUE_INCREASE_DURING_DECOMPRESSION",
                    {"previous": self.last_drain.queued, "current": observation.queued},
                )
                raise AirlockError("queue increased during decompression")
        self.last_drain = observation
        is_zero = observation.in_flight == 0 and observation.queued == 0
        self.vacuum_zero_observations = self.vacuum_zero_observations + 1 if is_zero else 0
        next_state = AirlockState.VACUUM_CANDIDATE if is_zero else AirlockState.THAWED_DRAINING
        return self._append(
            action_id,
            "DRAIN_OBSERVATION",
            next_state,
            {
                "admitted_total": observation.admitted_total,
                "submitted_total": observation.submitted_total,
                "finalized_total": observation.finalized_total,
                "completed_total": observation.completed_total,
                "in_flight": observation.in_flight,
                "queued": observation.queued,
                "vacuum_zero_observations": self.vacuum_zero_observations,
            },
        )

    def confirm_vacuum_valley(self, action_id: str, *, required_zero_observations: int = 2) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "VACUUM_VALLEY_CONFIRMED")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.VACUUM_CANDIDATE)
        if self.vacuum_zero_observations < required_zero_observations:
            raise AirlockError(
                f"vacuum requires {required_zero_observations} stable zero observations; have={self.vacuum_zero_observations}"
            )
        return self._append(
            action_id,
            "VACUUM_VALLEY_CONFIRMED",
            AirlockState.VACUUM_VALLEY_CONFIRMED,
            {"stable_zero_observations": self.vacuum_zero_observations},
        )

    def reopen(
        self,
        action_id: str,
        *,
        control_epoch: int,
        wave_epoch: int,
        identity: RuntimeIdentity,
        new_wave_epoch: int,
    ) -> LedgerEvent:
        duplicate = self._idempotent(action_id, "REOPEN")
        if duplicate:
            return duplicate
        self._require_state(AirlockState.VACUUM_VALLEY_CONFIRMED)
        self._require_epoch(control_epoch, wave_epoch)
        self._require_identity(identity)
        if new_wave_epoch != self.wave_epoch + 1:
            raise AirlockError("new wave epoch must increment exactly by one")
        old_wave_epoch = self.wave_epoch
        self.wave_epoch = new_wave_epoch
        return self._append(
            action_id,
            "REOPEN",
            AirlockState.REOPENED,
            {"old_wave_epoch": old_wave_epoch, "new_wave_epoch": new_wave_epoch},
        )

    def timeout(self, action_id: str, awaited_ack: str, elapsed_ms: int, timeout_ms: int) -> LedgerEvent:
        if elapsed_ms < timeout_ms:
            raise AirlockError("timeout called before timeout threshold")
        return self.fail_closed(
            "ACK_TIMEOUT",
            {"awaited_ack": awaited_ack, "elapsed_ms": elapsed_ms, "timeout_ms": timeout_ms},
            action_id=action_id,
        )

    def fail_closed(
        self,
        reason: str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        action_id: Optional[str] = None,
    ) -> LedgerEvent:
        if self.state == AirlockState.FAIL_CLOSED and self.ledger:
            return self.ledger[-1]
        action_id = action_id or f"fail-{len(self.ledger)+1}-{reason}"
        merged = {"reason": reason}
        if payload:
            merged.update(payload)
        return self._append(action_id, "FAIL_CLOSED", AirlockState.FAIL_CLOSED, merged)

    def verify_ledger(self) -> Tuple[bool, Optional[str]]:
        previous_hash = ZERO_HASH
        for expected_seq, event in enumerate(self.ledger, start=1):
            if event.seq != expected_seq:
                return False, f"sequence mismatch at {expected_seq}"
            if event.previous_hash != previous_hash:
                return False, f"previous hash mismatch at {expected_seq}"
            base = {
                "seq": event.seq,
                "control_epoch": event.control_epoch,
                "wave_epoch": event.wave_epoch,
                "action_id": event.action_id,
                "event_type": event.event_type,
                "state_before": event.state_before,
                "state_after": event.state_after,
                "payload": event.payload,
                "previous_hash": event.previous_hash,
            }
            if LedgerEvent.compute_hash(base) != event.event_hash:
                return False, f"event hash mismatch at {expected_seq}"
            previous_hash = event.event_hash
        return True, None

    def export(self) -> Dict[str, Any]:
        ok, error = self.verify_ledger()
        return {
            "schema": SCHEMA,
            "state": self.state.value,
            "control_epoch": self.control_epoch,
            "wave_epoch": self.wave_epoch,
            "runtime_identity": {
                "pid": self.identity.pid,
                "session_id": self.identity.session_id,
                "reconnect_count": self.identity.reconnect_count,
            },
            "ledger_valid": ok,
            "ledger_error": error,
            "ledger_final_hash": self.ledger[-1].event_hash if self.ledger else ZERO_HASH,
            "event_count": len(self.ledger),
            "events": [event.__dict__ for event in self.ledger],
        }


def replay_ledger(events: Iterable[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    previous_hash = ZERO_HASH
    for expected_seq, raw in enumerate(events, start=1):
        if raw.get("seq") != expected_seq:
            return False, f"sequence mismatch at {expected_seq}"
        if raw.get("previous_hash") != previous_hash:
            return False, f"previous hash mismatch at {expected_seq}"
        base = {
            "seq": raw["seq"],
            "control_epoch": raw["control_epoch"],
            "wave_epoch": raw["wave_epoch"],
            "action_id": raw["action_id"],
            "event_type": raw["event_type"],
            "state_before": raw["state_before"],
            "state_after": raw["state_after"],
            "payload": raw["payload"],
            "previous_hash": raw["previous_hash"],
        }
        expected_hash = LedgerEvent.compute_hash(base)
        if raw.get("event_hash") != expected_hash:
            return False, f"event hash mismatch at {expected_seq}"
        previous_hash = expected_hash
    return True, None
