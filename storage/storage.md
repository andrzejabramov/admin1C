## 🌳 Структура файлов

```
/opt/1cv8/scripts/
├── ib_list.conf                     # Статический список ИБ для массовых операций
├── orchestrator.py                  # Единая точка входа (CLI-маршрутизатор)
│
├── core/                            # 🧱 Инфраструктурный слой (общий для всех доменов)
│   ├── config.py                    # Глобальная конфигурация (BACKUP_ROOT, load_ib_list())
│   ├── engine.py                    # run_engine() — универсальный запуск скриптов уровня 0
│   ├── utils.py                     # Утилиты форматирования дат (machine_to_human)
│   └── exceptions.py                # Кастомные исключения (NotFoundError, PermissionError)
│
├── engines/                         # 🛠️ Общие утилиты (не относятся к доменам)
│   ├── utils.sh                     # Bash-функции (логирование, проверка кластера)
│   └── config/global.sh             # Глобальные параметры подключения к БД
│
└── storage/                         # 📦 Домен: мониторинг хранилища
    ├── config/storage.sh            # 🧩 Конфиг домена (путь к хранилищу: BACKUP_DIR)
    │
    ├── engines/                     # ⚙️ Слой 0: скрипты-движки (bash, прямой доступ к ФС)
    │   ├── disk_usage.sh            # Сбор статистики диска через `df`
    │   ├── list_backups.sh          # Поиск и метаданные файлов бэкапов (TSV-вывод)
    │   ├── count_backups.sh         # Агрегация количества/размера бэкапов по ИБ
    │   ├── validate.sh              # Валидация состояния хранилища (права, монтирование)
    │   ├── list_ibs.sh              # [Пустой] Получение списка ИБ из кластера 1С (rac)
    │   └── ssl.sh                   # Управление SSL-сертификатами (certbot)
    │
    ├── services/                    # 🧠 Слой 1: бизнес-логика (чистая, без зависимостей от интерфейсов)
    │   └── storage_service.py       # StorageMonitor — агрегация данных из движков
    │       ├── _run_engine()        # Универсальный запуск скриптов уровня 0
    │       ├── get_disk_usage()     # Парсинг вывода disk_usage.sh → dict
    │       ├── get_backups_list()   | Парсинг TSV → структурированный список
    │       ├── get_stats()          | Агрегация из count_backups.sh
    │       ├── validate_storage()   | Обработка вывода validate.sh → ошибки/предупреждения
    │       ├── calculate_growth_rate() | Расчёт темпа роста за N дней
    │       └── get_full_report()    | Сбор всех метрик в единый отчёт
    │
    └── adapters/cli/                # 🖥️ Слой 2: адаптеры интерфейсов
        └── storage_adapter.py       # CLI-адаптер (argparse → StorageMonitor → вывод таблиц)
            ├── Парсинг аргументов   | --ib, фильтрация
            ├── Вызов сервиса        | Получение отчёта через StorageMonitor
            └── Форматирование вывода| Текстовые таблицы (disk, stats, backups)
```

---

## 🔍 Детализация ключевых блоков кода

### `storage/engines/disk_usage.sh` (Слой 0)

```bash
# Блок 1: Загрузка конфигурации домена
CONFIG="$SCRIPT_DIR/config/storage.sh"
source "$CONFIG"

# Блок 2: Получение данных через df
read -r fs blocks used avail pcent mount <<< $(df "$BACKUP_DIR" | awk 'NR==2 {...}')

# Блок 3: Вывод в парсимом формате (ключ=значение)
cat <<EOF
filesystem=$fs
total_kb=$((blocks * 1024))
used_kb=$((used * 1024))
free_kb=$((avail * 1024))
used_percent=$pcent_num
EOF
```

→ **Задача:** Предоставить сырые метрики диска в формате, удобном для парсинга в Python.

---

### `storage/services/storage_service.py::StorageMonitor` (Слой 1)

```python
# Блок 1: Инициализация
def __init__(self):
    self.backup_root = BACKUP_ROOT      # Путь из core.config
    self.ib_list = load_ib_list()       # Список ИБ из ib_list.conf

# Блок 2: Универсальный запуск движков
def _run_engine(self, script_name, args=None):
    result = run_engine(script_name, args or [], user="usr1cv8")
    if result["returncode"] != 0:
        raise RuntimeError(...)
    return result["stdout"]

# Блок 3: Парсинг диска (ключ=значение → dict)
def get_disk_usage(self):
    for line in output.strip().split("\n"):
        if "=" in line:
            key, value = line.split("=", 1)
            data[key] = int(value)  # или строка при ошибке конвертации

# Блок 4: Парсинг TSV бэкапов (обработка заголовка + строк)
def get_backups_list(self):
    lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
    for line in lines[1:]:  # Пропускаем заголовок
        parts = line.split("\t")
        backups.append({
            "ib_name": parts[0].strip(),
            "timestamp": int(parts[1].strip()),  # Unix timestamp
            "size_bytes": int(parts[3].strip()),
            "path": parts[4].strip()
        })
```

→ **Задача:** Абстрагировать работу с движками, предоставить структурированные данные для адаптеров.

---

### `storage/adapters/cli/storage_adapter.py` (Слой 2)

```python
# Блок 1: Парсинг аргументов
parser = argparse.ArgumentParser(description="Мониторинг хранилища бэкапов 1С")
parser.add_argument("--ib", help="Фильтр по ИБ")

# Блок 2: Получение отчёта через сервис
monitor = StorageMonitor()
report = monitor.get_full_report(ib_name=args.ib)

# Блок 3: Форматирование таблицы диска
draw_table(
    headers=["Диск", "Всего", "Занято", "Свободно"],
    rows=[[disk["filesystem"], f"{total_gb:.1f} ГБ", ...]],
    col_widths=[14, 12, 18, 14]
)

# Блок 4: Форматирование статистики по ИБ
for stat in stats:
    ib_backups = [b for b in all_backups if b["ib_name"] == ib_orig]
    if ib_backups:
        last_backup = max(ib_backups, key=lambda x: x["timestamp"])
        last_date = format_timestamp(last_backup["timestamp"])
        last_size = format_bytes(last_backup["size_bytes"])
```

→ **Задача:** Преобразовать структурированные данные в человекочитаемый вывод (таблицы, цвета, предупреждения).

-

## 📊 Текущее состояние сервиса `storage`

| Компонент            | Статус               | Примечание                                                      |
| -------------------- | -------------------- | --------------------------------------------------------------- |
| Чтение метрик диска  | ✅ Рабочий           | `disk_usage.sh` → `get_disk_usage()`                            |
| Список бэкапов       | ✅ Рабочий           | `list_backups.sh` → `get_backups_list()`                        |
| Агрегация статистики | ✅ Рабочий           | `count_backups.sh` → `get_stats()`                              |
| Валидация хранилища  | ✅ Рабочий           | `validate.sh` → `validate_storage()`                            |
| Обновление списка ИБ | ⚠️ Требует доработки | `list_ibs.sh` пустой — нужно реализовать через `rac`            |
| SSL-мониторинг       | ⚠️ Изолирован        | `ssl.sh` работает автономно, не интегрирован в `StorageMonitor` |
