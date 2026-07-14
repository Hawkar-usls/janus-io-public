JANUS A18.43 — HARDWARE PRESERVATION CHALLENGE
V0.1.2 SENSOR MAPPING HOTFIX — PREFLIGHT ONLY

МИССИЯ
JANUS I0 разрабатывает проверяемые методы измерения и управления, направленные на
сокращение ненужных PoW-вычислений, тепловой нагрузки, расхода энергии и износа
оборудования без изменения стандартной проверки SHA-256 и правил валидного доказательства работы.

Мы не стремимся заставить машину работать быстрее любой ценой.
Мы стремимся убрать работу, которую ей никогда не следовало выполнять.

ПОЧЕМУ ПОЯВИЛАСЬ V0.1.2
Первый живой V0.1.1 preflight технически прошёл чисто: package manifest и self-tests PASS,
28 сэмплов, стабильная identity и изменяющиеся реальные датчики.

Fail-closed обнаружил ошибку canonical mapping: единственный Power sensor CPU Package
был ошибочно выбран также как GPU Power и System Total Power.

V0.1.2 исправляет это принципиально:
- CPU Package Power может принадлежать только /amdcpu/;
- GPU Power может принадлежать только /nvidiagpu/, NVML или nvidia-smi;
- System Total Power не может происходить из CPU или GPU component sensor;
- совпадение одного identifier для CPU и GPU power блокируется;
- mapping validation выполняется на каждом сэмпле;
- для стабильного baseline достаточно 20 сэмплов.

ОЖИДАЕМЫЙ SCOPE НА ТЕКУЩЕЙ МАШИНЕ
- CPU Package energy: ДОСТУПНО;
- CPU/GPU temperature: ДОСТУПНО;
- GPU load и fan RPM/duty: ДОСТУПНО;
- GPU component power: ПОКА НЕТ;
- wall/system power: НЕТ.

Это достаточно для CPU-focused Hardware Preservation Challenge.
GPU-телеметрия будет использоваться как контроль среды.

ЭТОТ ПАКЕТ НЕ ЗАПУСКАЕТ МАЙНЕР И НИЧЕМ НЕ УПРАВЛЯЕТ.

ПОРЯДОК
1. Запусти OpenHardwareMonitor.exe от имени администратора.
2. Оставь его открытым.
3. Распакуй полный V0.1.2 ZIP в отдельную папку.
4. Запусти PREFLIGHT_ONLY.cmd.
5. Пришли новые файлы из output.

Короткий тест не доказывает продление срока службы. Для этого нужен Hardware Health Passport.
