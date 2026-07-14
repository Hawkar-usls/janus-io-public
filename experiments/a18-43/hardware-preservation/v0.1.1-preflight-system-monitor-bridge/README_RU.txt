JANUS A18.43 — HARDWARE PRESERVATION CHALLENGE
V0.1.1 SYSTEM MONITOR BRIDGE — PREFLIGHT ONLY

МИССИЯ
JANUS I0 разрабатывает проверяемые методы измерения и управления, направленные на
сокращение ненужных PoW-вычислений, тепловой нагрузки, расхода энергии и износа
оборудования без изменения стандартной проверки SHA-256 и правил валидного доказательства работы.

Мы не стремимся заставить машину работать быстрее любой ценой.
Мы стремимся убрать работу, которую ей никогда не следовало выполнять.

ЧТО ИЗМЕНИЛОСЬ В V0.1.1
Сенсорный слой теперь следует уже проверенной архитектуре Janus-Demiurge/system_monitor.py:

1. OpenHardwareMonitor WMI — основной источник температуры, нагрузки, мощности,
   вентиляторов, частот и напряжений.
2. NVML — дополнительный источник GPU load / memory / temperature / power / fan.
3. nvidia-smi — fallback, если Python NVML недоступен.
4. psutil — CPU, память и системная нагрузка.

Все источники нормализуются в единый CANONICAL_HARDWARE_METRICS поток с указанием
источника и идентификатора каждого значения.

ЧТО НАМЕРЕННО НЕ ПЕРЕНЕСЕНО ИЗ JANUS DEMIURGE
- CacheProbe, потому что он сам создаёт вычислительную нагрузку;
- аудио, экран, клавиатура и мышь;
- игровой детектор;
- thermal/tachyonic regulator;
- изменение load scale;
- автоматическое управление частотами, напряжением или вентиляторами.

ЭТОТ ПАКЕТ НЕ ЗАПУСКАЕТ МАЙНЕР И НИЧЕМ НЕ УПРАВЛЯЕТ.

ПОРЯДОК
1. Запусти OpenHardwareMonitor.exe от имени администратора.
2. Убедись, что видны CPU и GPU sensors.
3. Оставь OpenHardwareMonitor запущенным.
4. Запусти PREFLIGHT_ONLY.cmd.
5. Пришли файлы из output:
   - A18_43_PREFLIGHT_REPORT.json
   - SENSOR_INVENTORY.json
   - HARDWARE_SAMPLES.jsonl
   - HARDWARE_BASELINE_SUMMARY.json
   - SYSTEM_MONITOR_COMPATIBILITY.json
   - PACKAGE_PREFLIGHT.json

КАК ЧИТАТЬ ЭНЕРГИЮ
- GPU power из NVML/nvidia-smi/OpenHardwareMonitor позволяет считать GPU joules.
- CPU Package power из OpenHardwareMonitor позволяет считать CPU package joules.
- Это ещё не wall power всей фермы.
- Whole-system energy claim остаётся заблокированным без внешнего измерителя или
  достоверного Total/System Power sensor.

КАК ЧИТАТЬ ИЗНОС
Короткий challenge может измерить тепловую нагрузку, fan behavior и hardware errors,
но не может сам доказать продление срока службы. Для этого нужен долгий Hardware Health Passport.
