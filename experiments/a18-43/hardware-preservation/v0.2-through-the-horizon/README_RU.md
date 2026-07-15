# JANUS A18.43 V0.2 — Through the Horizon

## Event-Horizon Airlock Protocol

Этот этап соединяет уже подтверждённые способности JANUS:

- **TimeShift** умеет кратковременно остановить наблюдаемое движение процесса и доказать quiescence;
- **Undina Native Flow Gate** умеет закрыть новые admissions, дренировать старую когорту и открыть новый epoch в том же процессе без reconnect.

Главная новая идея: они больше не действуют как два независимых контроллера. Они становятся двумя створками одного вычислительного шлюза.

```text
FREEZE_REQUEST
→ FROZEN_ACK
→ SNAPSHOT_SEALED
→ GATE_CLOSE_REQUEST
→ GATE_CLOSED_ACK
→ HORIZON_COMMIT
→ THAW_TO_DRAIN
→ CONTROLLED_DECOMPRESSION
→ VACUUM_VALLEY_CONFIRMED
→ REOPEN(new epoch)
```

## Почему это «шлюз»

```text
входной люк              = Native Admission Gate
камера шлюза             = текущая in-flight когорта
аварийная фиксация       = TimeShift FREEZE
разгерметизация          = THAW_TO_DRAIN при закрытых admissions
вакуумная долина         = стабильные in_flight=0 и queued=0
повторное наполнение     = REOPEN следующего admission epoch
```

Внутри каждой фазы компоненты могут работать асинхронно. Между фазами действует строгая точка рандеву: следующий переход невозможен без подтверждений предыдущего.

## Главная защита

Никакого размораживания для drain до тех пор, пока одновременно не подтверждены:

```text
FROZEN_ACK
+ SNAPSHOT_SEALED
+ GATE_CLOSED_ACK
```

Это называется `HORIZON_COMMIT`.

Никакого `REOPEN`, пока две последовательные проверки не подтвердили чистую вакуумную долину.

## Two-phase TimeShift

Старая последовательность могла создавать lead debt:

```text
посмотреть на движущуюся волну
→ решить остановить
→ пока команда дошла, состояние изменилось
```

Новая последовательность:

```text
сначала заморозить
→ прочитать неподвижное состояние
→ проверить latest-safe horizon
→ TOO_LATE_ABORT или закрыть admission gate
```

## Что уже реализовано в V0.2.0

- офлайн state machine координатора шлюза;
- `control_epoch`, `wave_epoch`, `action_id` и идемпотентные команды;
- защита от запоздавших ACK;
- проверка PID, session и reconnect continuity;
- hash-linked event ledger;
- контролируемая разгерметизация с запретом новых admissions;
- монотонный drain `in_flight` и `queued`;
- двухфазное подтверждение вакуумной долины;
- fail-closed timeout;
- fault-injection и delay matrix `0/10/25/50/100/250 ms`.

## Чего V0.2.0 пока не делает

- не запускает майнер;
- не посылает реальные FREEZE/RESUME;
- не управляет живым Native Gate;
- не меняет SHA-256, verifier, nonce traversal или WIRE/HASH/SUBMIT;
- не заявляет экономию энергии или продление жизни железа.

Следующий подэтап — привязать этот проверенный протокол к frozen A18.42 runtime через отдельные адаптеры, сохранив возможность fail-closed до первого живого BEACON.

Название вдохновлено образом шлюза и управляемой разгерметизации из фильма **Event Horizon** и используется как уважительная культурная отсылка; связи или одобрения со стороны создателей фильма и Сэма Нилла не подразумевается.
