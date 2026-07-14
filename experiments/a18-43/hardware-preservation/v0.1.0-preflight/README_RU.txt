JANUS A18.43 — HARDWARE PRESERVATION CHALLENGE
V0.1.0 PREFLIGHT ONLY

МИССИЯ
JANUS не пытается выжать из машины максимальную производительность любой ценой.
Он должен обнаруживать и предотвращать работу, которую машине никогда не следовало выполнять,
уменьшая ненужный нагрев, расход энергии и износ оборудования.

ЭТОТ ПАКЕТ НЕ ЗАПУСКАЕТ МАЙНЕР.
Он не меняет SHA-256, verifier, nonce traversal, WIRE/HASH/SUBMIT и не управляет нагрузкой.
Его задача — проверить доступность реальных датчиков перед Frozen Hardware Preservation Challenge.

ЧТО ПРОВЕРЯЕТСЯ
- Windows и Python;
- запущен ли OpenHardwareMonitor;
- доступен ли WMI namespace root/OpenHardwareMonitor;
- присутствуют ли Temperature / Load / Power / Fan / Control / Clock / Voltage sensors;
- меняются ли значения во времени;
- можно ли честно измерять энергию в джоулях;
- можно ли измерять тепловой стресс и стабильность вентиляторов.

ПОРЯДОК
1. Запусти OpenHardwareMonitor.exe от имени администратора.
2. В OpenHardwareMonitor включи нужные категории CPU/GPU/Mainboard.
3. Оставь окно программы открытым.
4. Запусти PREFLIGHT_ONLY.cmd.
5. Пришли:
   output\A18_43_PREFLIGHT_REPORT.json
   output\SENSOR_INVENTORY.json
   output\HARDWARE_SAMPLES.jsonl

ВАЖНО
- PASS не означает, что JANUS уже экономит энергию.
- Если нет Power sensor, energy claim остаётся BLOCKED.
- Температура без мощности позволяет готовить thermal-stress challenge, но не joules-per-proof claim.
- Отрицательный результат является допустимым результатом.

КАНОНИЧЕСКАЯ ФОРМУЛА
We do not seek to make the machine work faster at any cost.
We seek to remove work it should never have had to perform.
