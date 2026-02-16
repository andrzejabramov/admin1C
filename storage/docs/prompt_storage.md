# Промпт для воспроизведения сервиса `storage`

```
You are an expert Python/Unix systems engineer. Design a read-only monitoring service for a 1C backup storage system with strict vertical domain architecture.

DOMAIN: storage/
PURPOSE: Aggregate and display backup storage metrics (disk usage, backup counts/sizes, validation status). NO write operations. NO modification of filesystem.

ARCHITECTURE (strict layer separation):
• Layer 0 (engines/): Bash scripts with set -euo pipefail. Output machine-parsable formats only:
  - disk_usage.sh → key=value (filesystem, total_kb, used_kb, free_kb, used_percent)
  - list_backups.sh → TSV with header (ib_name\ttimestamp\tfile_type\tsize_bytes\tpath)
  - count_backups.sh → TSV (ib_name\ttotal_files\ttotal_size_bytes)
  - validate.sh → key=value + error=.../warning=... lines
  All scripts source config/storage.sh (BACKUP_DIR="/var/backups/1c")
  MUST run as usr1cv8 (no hardcoded sudo inside scripts)

• Layer 1 (services/storage_service.py): Pure Python business logic. Class StorageMonitor:
  - __init__() → loads ib_list.conf via core.config.load_ib_list()
  - _run_engine(script, args) → calls core.engine.run_engine("storage/engines/"+script, ..., user="usr1cv8")
  - get_disk_usage() → parses key=value → dict with GB conversions
  - get_backups_list() → parses TSV → list[dict] with Unix timestamps (int)
  - get_stats() → parses TSV → list[dict] per IB (total_files, total_size_bytes)
  - validate_storage() → extracts errors/warnings from validate.sh output
  - calculate_growth_rate(backups, days=7) → float GB/day (0.0 if <2 backups)
  - get_full_report(ib_name=None) → aggregates all metrics + growth rate
  NO direct filesystem access. NO CLI dependencies. NO print() statements.

• Layer 2 (adapters/cli/storage_adapter.py): CLI presentation only:
  - argparse interface (--ib for filtering)
  - Instantiates StorageMonitor()
  - Calls get_full_report(ib_name)
  - Formats output as ASCII tables (disk stats, per-IB backup summary)
  - Human-friendly formatting (machine_to_human timestamps, format_bytes sizes)
  NO business logic. NO direct engine calls.

INTEGRATIONS:
• core/config.py: BACKUP_ROOT = Path("/var/backups/1c"), load_ib_list() → reads ib_list.conf
• core/engine.py: run_engine(script_path, args, user="usr1cv8", capture_output=True)
• core/utils.py: machine_to_human(), format_bytes()
• orchestrator.py: Discovers adapters via */adapters/cli/*_adapter.py pattern

CONSTRAINTS:
• StorageMonitor NEVER creates directories or files
• All engine calls MUST specify user="usr1cv8" (avoid permission errors on stat/find)
• TSV parsers MUST skip header lines and malformed rows gracefully (continue on ValueError)
• Validation warnings about "lost+found" or missing usr1cv8 read rights MUST be filtered from CLI output
• Growth rate calculation requires ≥2 backups within 7 days; otherwise return 0.0
• Empty IB directories (no backup files) MUST be excluded from statistics
• Blacklist system directories: lost+found, .snapshot, ., ..

ERROR HANDLING:
• Script not found → RuntimeError with path
• Script execution failure (returncode != 0) → RuntimeError with stderr/stdout
• Partial TSV parse failure → skip malformed row, continue processing
• IB not found in storage → clear error message with available IB list
• Disk stats unavailable → show error block but continue with backup stats if available

OUTPUT EXAMPLE (ib_1c storage --ib artel_2025):
📁 Хранилище бэкапов: /var/backups/1c
┌────────────────┬──────────────┬────────────────────┬────────────────┐
│ Диск           │ Всего        │ Занято             │ Свободно       │
├────────────────┼──────────────┼────────────────────┼────────────────┤
│ /dev/vdb       │ 97.9 ГБ      │ 31.5 ГБ (34%)      │ 61.4 ГБ        │
└────────────────┴──────────────┴────────────────────┴────────────────┘
📊 Статистика по ИБ:
┌──────────────────────────┬─────────────┬──────────────┬────────────────────┬──────────────┐
│ ИБ                       │ Бэкапов     │ Последний    │ Последний размер   │ Всего        │
├──────────────────────────┼─────────────┼──────────────┼────────────────────┼──────────────┤
│ artel_2025               │ 6           │ 07.02        │ 991.0M             │ 5.8G         │
└──────────────────────────┴─────────────┴──────────────┴────────────────────┴──────────────┘
ℹ️  Темп роста: ~0.0 ГБ/день (недостаточно данных для точного прогноза)
```
