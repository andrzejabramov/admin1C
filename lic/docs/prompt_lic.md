### 🤖 prompt_lic.md — Промпт для разработки сервиса

```
You are an expert Python/Unix systems engineer. Design a read-only monitoring service for 1C software licenses with strict layer separation and zero-risk operations.

DOMAIN: lic/
PURPOSE: Monitor license blocks (files in /var/1C/licenses/*.lic) — extract registration numbers, user counts, license types. NO activation/deactivation operations.

ARCHITECTURE (strict layers):
• Layer 0 (lic/engines/): Bash scripts with minimal dependencies. Output machine-parsable formats only:
  - license_list.sh → TSV (regnum\tfilename\ttype\tusers\tstatus)
  - license_detail.sh → key=value (Регистрационный номер=..., Тип лицензии=...)
  - monitor.sh → key=value (TOTAL_USERS=27, TOTAL_SERVERS=1, ACTIVE_SESSIONS=2)
  - backup.sh → key=value (BACKUP_PATH=..., BACKUP_COUNT=8)
  All scripts MUST:
  • Read files as text (cp1251 encoding) with binary prefix tolerance
  • Use grep/awk/tail only (no Python/Java dependencies)
  • Run as usr1cv8 via core.engine.run_engine(..., user="usr1cv8")

• Layer 1 (lic/services/lic_service.py): Pure Python business logic. Class LicenseMonitor:
  - _run_engine(script, args) → delegates to core.engine.run_engine("lic/engines/" + script, ...)
  - get_license_list() → parses TSV → list[dict] with regnum (without G0 suffix)
  - get_license_info(regnum) → calls license_detail.sh → parses key=value → dict
  - get_monitoring() → parses monitor.sh output → dict with totals
  - create_backup() → calls backup.sh → returns backup metadata
  NO direct filesystem access. NO CLI dependencies.

• Layer 2 (lic/adapters/cli/lic_adapter.py): CLI presentation only:
  - argparse interface with short flags: -A (all), -l (block), -m (monitor), -b (backup)
  - Calls LicenseMonitor methods
  - Formats output as ASCII tables with word-wrap for long values (e.g., product names)
  NO business logic. NO direct engine calls.

INTEGRATIONS:
• core/engine.py: run_engine(script_path, args, user="usr1cv8", capture_output=True)
• core/utils.py: machine_to_human() for timestamp formatting
• orchestrator.py: Discovers adapters via */adapters/cli/*_adapter.py pattern

CONSTRAINTS:
• ZERO write operations on license files (read-only only)
• NO dependency on ring/rac/java (files contain binary prefixes — use grep/tail)
• Graceful error handling: missing files → user-friendly messages, not stack traces
• Registration numbers always end with G0 suffix in UI, but stored without in TSV
• All engine outputs MUST be machine-parsable (no decorative text)

OUTPUT EXAMPLE (ib1c lic -A):

┌────────────────────────┬──────────────┬────────────────┬────────────────┬────────────┐
│ Регистрационный номер  │ Тип          │ Продукт        │ Пользователей  │ Статус     │
├────────────────────────┼──────────────┼────────────────┼────────────────┼────────────┤
│ 8101827471G0           │ клиент       │ 20210223203512 │ 1              │ активна    │
│ 8100223833G0           │ клиент       │ 20210607113754 │ 5              │ активна    │
│ ...                    │ ...          │ ...            │ ...            │ ...        │
│ 8101355471G0           │ сервер 64    │ 20250626080710 │ 1              │ активна    │
└────────────────────────┴──────────────┴────────────────┴────────────────┴────────────┘

ℹ️  Итого: 8 блоков лицензий | 27 клиентских | 1 серверная
```
