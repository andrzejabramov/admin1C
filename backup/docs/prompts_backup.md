# Промпт для разработки сервиса `backup` (создание бэкапов)

## 🎯 Контекст проекта

Разрабатывается консольный оркестратор администрирования 1С `ib1c` с вертикальной доменной архитектурой. Каждый сервис — автономная подсистема с полной изоляцией. Сервис `backup` отвечает за **надёжное создание** резервных копий информационных баз в двух форматах.

## 📌 Требования к сервису `backup`

### Функциональные требования

1. **Поддержка двух форматов**:
   - `dump` — PostgreSQL Custom Format (бинарный, оптимальный для восстановления)
   - `sql` — Архивированный SQL (текстовый, удобен для анализа)
2. **Прогресс-бар в реальном времени** через `pv` (с обёрткой `script` для избежания ошибки `[Errno 1]` при смене пользователя)
3. **Адаптивный таймаут**:
   - Базовый: 5 минут на каждый ГБ данных + 5 минут запаса
   - Минимум: 5 минут даже для самых маленьких ИБ
   - Расчёт на основе реального размера ИБ через `pg_database_size()`
4. **Проверка дискового пространства**:
   - Перед массовым бэкапом (`--all`) или в режиме `--dry-run`
   - Эвристика размера: `.dump` ≈ 45% от размера БД, `.sql.gz` ≈ 25%
   - Запас 0.5 ГБ для метаданных и буферизации
5. **Ранняя валидация ИБ**:
   - Проверка существования ИБ в PostgreSQL **до** создания директории бэкапа
   - Человекочитаемое сообщение при ошибке
6. **Защита от частичных бэкапов**:
   - Автоочистка неполного файла при ошибке записи (через `trap` в bash-скрипте)
   - Проверка целостности файла после записи (существование + ненулевой размер)
7. **Режим симуляции** (`--dry-run`):
   - Только оценка места, без реального бэкапа
   - Вывод расчётного размера для каждой ИБ

### Нефункциональные требования

- **Производительность**: Бэкап 10 ГБ за < 20 минут (при скорости 10 МБ/с)
- **Надёжность**: Никаких частичных/битых файлов при ошибках
- **Юзабилити**: Прогресс-бар в реальном времени, понятные сообщения об ошибках с подсказками
- **Безопасность**: Все операции выполняются от имени `usr1cv8`, без лишних прав

## 📁 Структура проекта (актуальная для сервиса)

```
/opt/1cv8/scripts/
├── core/
│   ├── engine.py          # run_engine(script_path, args, user, capture_output, timeout)
│   ├── exceptions.py      # BackupError, BackupTimeoutError
│   ├── utils.py           # machine_to_human(), parse_timestamp_arg()
│   └── config.py          # BACKUP_TIMEOUT_MINUTES_PER_GB, BACKUP_TIMEOUT_MINIMUM
├── engines/
│   └── config/
│       └── global.sh      # BACKUP_ROOT, PG_HOST, PG_PORT, PG_USER, PGPASS_FILE
└── backup/
    ├── engines/
    │   └── backup.sh      # Bash-скрипт бэкапа (работает от usr1cv8)
    ├── services/
    │   ├── __init__.py
    │   └── backup_service.py  # backup_ib(), backup_multiple(), estimate_backup_size(), check_disk_space()
    └── adapters/
        └── cli/
            ├── __init__.py
            └── backup_adapter.py  # CLI-адаптер (argparse → валидация → сервис)
```

## 🔧 Алгоритм реализации

### 1. CLI-адаптер (`backup_adapter.py`)

- Использовать `argparse` с взаимоисключающими группами:
  ```python
  parser.add_argument("-f", "--format", choices=["dump", "sql"], required=True)
  group = parser.add_mutually_exclusive_group(required=True)
  group.add_argument("-I", "--ib", nargs='+', metavar="ИМЯ")
  group.add_argument("-A", "--all", action="store_true")
  parser.add_argument("-n", "--dry-run", action="store_true")
  ```
- Валидация:
  - Для `--all` или `--dry-run`: вызов `check_disk_space(ib_list, format_type)`
  - Если недостаточно места — прервать выполнение с понятным сообщением
- Вызов: `backup_service.backup_multiple(ib_list, format_type, dry_run)`

### 2. Сервисный слой (`backup_service.py`)

- `get_ib_size(ib_name)`:
  - Запрос к PostgreSQL: `SELECT pg_database_size('$IB_NAME')`
  - Возврат `-1` если ИБ не существует, `None` при ошибке подключения
- `estimate_backup_size(ib_name, format_type)`:
  - Коэффициенты: `dump` = 0.45, `sql` = 0.25 от размера БД
  - Минимум 0.1 ГБ для неопределённых ИБ
- `check_disk_space(ib_list, format_type)`:
  - Суммирование оценок + запас 0.5 ГБ
  - Сравнение со свободным местом через `shutil.disk_usage()`
  - Возврат: `{"sufficient": bool, "required_gb": float, "free_gb": float, "message": str}`
- `backup_ib(ib_name, format_type, dry_run)`:
  - Предварительная проверка: `if get_ib_size(ib_name) == -1: return error`
  - Расчёт таймаута: `estimate_backup_timeout(ib_name, size_bytes)`
  - Вызов: `run_engine("backup/engines/backup.sh", args, timeout=timeout, user="usr1cv8", capture_output=False)`
  - Улучшение диагностики: анализ `stderr` для уточнения типа ошибки
- `backup_multiple(ib_list, format_type, dry_run)`:
  - Последовательная обработка каждой ИБ
  - Сбор результатов для вывода статистики

### 3. Bash-скрипт (`backup/engines/backup.sh`)

- Загрузка конфигурации: `source /opt/1cv8/scripts/engines/config/global.sh`
- Парсинг аргументов:
  ```bash
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --ib) IB_NAME="$2"; shift 2 ;;
      --format) FORMAT="$2"; shift 2 ;;
    esac
  done
  ```
- **КРИТИЧЕСКИ ВАЖНО: Валидация ИБ до создания директории**:
  ```bash
  if ! PGPASSFILE="$PGPASS_FILE" psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '$IB_NAME'" 2>/dev/null | grep -q "1"; then
    echo "❌ ИБ '$IB_NAME' не найдена в кластере БД $PG_HOST:$PG_PORT" >&2
    exit 1
  fi
  ```
- Создание директории: `mkdir -p "$BACKUP_ROOT/$IB_NAME/$TIMESTAMP"`
- **Автоочистка при ошибке**:
  ```bash
  cleanup_on_error() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]] && [[ -n "${BACKUP_DIR:-}" ]] && [[ -d "$BACKUP_DIR" ]]; then
      rm -rf "$BACKUP_DIR" 2>/dev/null || true
    fi
    exit $exit_code
  }
  trap cleanup_on_error EXIT
  ```
- Выполнение бэкапа:
  - Для `.dump`: `pg_dump -Fc | pv -f -s "$DB_SIZE" | tee backup.dump > /dev/null`
  - Для `.sql.gz`: `pg_dump | gzip | tee backup.sql.gz > /dev/null`
- Проверка целостности: `if [[ ! -f "$BACKUP_DIR/backup.dump" ]] || [[ ! -s "$BACKUP_DIR/backup.dump" ]]; then exit 1; fi`

### 4. Интеграция с ядром

- Использовать `core.engine.run_engine()` для запуска `backup.sh`
- Для прогресс-бара: `capture_output=False` + обёртка `script` при смене пользователя (реализовано в `core/engine.py`)
- Обрабатывать `BackupTimeoutError` из `core/exceptions`:
  ```python
  try:
      result = run_engine("backup/engines/backup.sh", ..., timeout=timeout)
  except BackupTimeoutError as e:
      return {"success": False, "stderr": str(e)}
  ```

## 🛡️ Обработка ошибок (обязательно!)

- **ИБ не найдена**: Проверять в `backup.sh` до создания директории, возвращать код 1
- **Недостаточно места**: Проверять в `backup.sh` после записи, удалять неполный файл
- **Таймаут**: Обрабатывать через `BackupTimeoutError` в `backup_service.py`
- **Ошибка подключения/аутентификации**: Перехватывать в `backup.sh`, возвращать понятное сообщение
- **Частичный бэкап**: Автоочистка через `trap` в `backup.sh`

## 📋 Примеры ожидаемого поведения

```bash
# Симуляция бэкапа всех ИБ (оценка места)
$ ib1c backup -f dump -A -n

📦 Начало бэкапа 14 ИБ (формат: dump) [режим --all]
======================================================================

✅ Достаточно места для бэкапа 14 ИБ:
   Требуется: 24.7 ГБ (включая запас 0.5 ГБ)
   Свободно:  82.8 ГБ

⏭️  СИМУЛЯЦИЯ: бэкап не будет создан (режим --dry-run)
======================================================================

[1/14] ⏭️  artel_2025                 → ~1.0 ГБ
[2/14] ⏭️  oksana_2025                → ~4.6 ГБ
...
[14/14] ⏭️  utsrs_2025                → ~1.8 ГБ

======================================================================
✅ Симуляция завершена: 14/14 ИБ

# Реальный бэкап с прогресс-баром
$ ib1c backup -f dump -I oksana_2025

📦 Начало бэкапа 1 ИБ (формат: dump) [--ib (1 ИБ)]
======================================================================
[2026-02-15 11:00:00] 📁 Директория: /var/backups/1c/oksana_2025/20260215_110000
[2026-02-15 11:00:00] 💾 Бэкап ИБ: oksana_2025 (формат: dump)
3,79GiB 0:06:55 [9,35MiB/s] [===================>] 100%

[2026-02-15 11:07:00] ✅ Завершён: /var/backups/1c/oksana_2025/20260215_110000/backup.dump (3,8G)

======================================================================
✅ Успешно: 1/1 ИБ

# Ошибка: ИБ не найдена
$ ib1c backup -f dump -I non_existent_db

📦 Начало бэкапа 1 ИБ (формат: dump) [--ib (1 ИБ)]
======================================================================

[1/1] ❌ non_existent_db
----------------------------------------------------------------------
❌ Ошибка: ИБ «non_existent_db» не найдена в кластере БД 10.129.0.27:5432
   → Проверьте имя: ib1c storage list-ibs
   → Или обновите список: ib1c storage update-ib-list --confirm

======================================================================
✅ Успешно: 0/1 ИБ
```

## 💡 Дополнительные требования

- **Идемпотентность**: Повторный запуск с теми же параметрами создаёт новый бэкап (новая временная метка)
- **Атомарность**: Ошибка при бэкапе одной ИБ не прерывает обработку остальных (в режиме `--all`)
- **Локализация**: Сообщения на русском с эмодзи для визуального разделения (✅, ❌, 💾, 📁)
- **Совместимость**: Поддержка дат в форматах `ДД.ММ.ГГГГ` и `ГГГГММДД` (через `core/utils.py`)
