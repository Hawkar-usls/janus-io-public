JANUS GIFT: UNDINA'S COMB FOR ROSES
A18.42 V0.3.3 — NATIVE FLOW GATE + LIVE CANARY LOCK

Эта версия восстановлена не из предположений, а из реальных операторских архивов:
- JANUS_A18_29_1_WINDOW_RUNNER;
- approved A17.8 miner source;
- V0.3.2 runtime и точные failed logs.

Что было обнаружено в V0.3.2:
1. inherited base.read_json принимает только path, но supervisor передавал второй default-аргумент;
2. после исключения child удерживал raw_runtime.log, поэтому Windows cleanup получал WinError 32;
3. главное: прежний gate блокировал внутри freeze(), а instrumented miner сначала freeze-ил всю группу
   и лишь потом делал bulk executor.submit(). После исчерпания quota это создавало гарантированный deadlock:
   следующий freeze ждал REOPEN, но первый admitted batch ещё не был отправлен worker-у.

Исправления V0.3.3:
1. API_COMPATIBILITY — default-read только через safe_read_json.
2. PROCESS_TREE_CLEANUP — child tree гарантированно останавливается и ожидается; raw log копируется после закрытия handle.
3. EXPLICIT_RUNTIME_EXCEPTION — final_status содержит точный traceback.
4. NATIVE_NONBLOCKING_ADMISSION — gate возвращает DEFER, а не блокирует main thread.
5. IMMEDIATE_SUBMIT_AFTER_ADMISSION — каждый admitted task сразу передаётся executor-у.
6. DEFERRED_WORK_NOT_SUBMITTED — закрытые воротами задачи не отправляются worker-ам.
7. DRAIN_AND_RETRY — после drain следующий scheduler-round снова пытается admission и видит REOPEN epoch.
8. SYSTEMIC_FAIL_FAST — нулевой runtime/systemic crash останавливает suite после первого слота.
9. LIVE_CANARY_LOCK — 10-run calibration заблокирована до успешного CANARY_NATIVE_1_1.
10. CANARY_RECEIPT — привязан к manifest, scenario matrix, approved source и A18.29 supervisor SHA-256.
11. CANARY не является научным run и никогда не объединяется со статистикой calibration.

Точные runtime hashes:
- native hook: 9ce7b6c658d7ee5d80bc94b3bbd8ab0b9a614382fc8d2e78ed4f6b8707dfa245
- base A18.29 instrumented miner: b94f565e9516368c3b461bc15d7677e9ff899fb5d7fea6e6096e15457a6bcde1
- native nonblocking patched miner: 2a9b87ab18aad6667721114310e429d49a7490bf7bba11ebfcbc79bfc0112ee7

Правильный порядок:
1. PREFLIGHT_ONLY.cmd
2. START_CANARY_1_RUN.cmd — ввести CANARY
3. Требовать CANARY_STATUS=PASS и output/A18_42_CANARY_PASS.json
4. Только затем START_CALIBRATION_1_MATRIX.cmd — ввести PUMP
5. Прислать REPORT_FOR_CHATGPT.json и SUITE_STATE.json

Discovery не запускать до анализа calibration.

Граница утверждений:
- approved source byte-for-byte не меняется;
- mine_task, SHA-256, header serialization, per-task nonce traversal, verifier, wire и valid-submit semantics не меняются;
- staged scheduler/admission намеренно меняется: набор и момент допуска работ контролируются native gate;
- Wave Pump ещё не доказан; V0.3.3 сначала обязан пройти один живой mechanical canary.
