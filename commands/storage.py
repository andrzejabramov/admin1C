"""
storage.py — CLI-интерфейс для просмотра хранилища резервных копий
Использование: ib_1c storage [--ib ИМЯ_ИБ]
"""
import argparse
import sys
from datetime import datetime
from services.storage_service import StorageMonitor
from core.exceptions import NotFoundError

def format_bytes(size_bytes: int) -> str:
    """Форматирование байтов в человеко-читаемый вид"""
    if size_bytes == 0:
        return "0B"
    for unit in ["B", "K", "M", "G", "T"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}P"

def format_timestamp(ts: int) -> str:
    """Форматирование timestamp в ДД.ММ"""
    try:
        if ts <= 0:
            return "—"
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%d.%m")
    except:
        return "—"

def draw_table(headers: list, rows: list, col_widths: list):
    """Простая текстовая таблица без внешних зависимостей"""
    def row_line(cells):
        return "│ " + " │ ".join(f"{cell:<{w}}" for cell, w in zip(cells, col_widths)) + " │"
    top = "┌" + "┬".join("─" * (w + 2) for w in col_widths) + "┐"
    header_line = row_line(headers)
    sep = "├" + "┼".join("─" * (w + 2) for w in col_widths) + "┤"
    bottom = "└" + "┴".join("─" * (w + 2) for w in col_widths) + "┘"
    print(top)
    print(header_line)
    print(sep)
    for row in rows:
        print(row_line(row))
    print(bottom)

def main(args_list=None):
    try:
        parser = argparse.ArgumentParser(
            description="Просмотр хранилища резервных копий 1С",
            usage="ib_1c storage [--ib ИМЯ_ИБ]"
        )
        parser.add_argument("--ib", help="Фильтр по имени информационной базы")
        args = parser.parse_args(args_list)

        # === Валидация входных данных ===
        if args.ib is not None:
            ib_name_clean = args.ib.strip()
            if not ib_name_clean:
                print("❌ Ошибка: имя информационной базы не может быть пустым", file=sys.stderr)
                print("   Использование: ib_1c storage --ib ИМЯ_ИБ", file=sys.stderr)
                print("   Пример: ib_1c storage --ib artel_2025", file=sys.stderr)
                return 1
            args.ib = ib_name_clean

        monitor = StorageMonitor()
        report = monitor.get_full_report(ib_name=args.ib)
        disk = report["disk"]
        stats = report["stats"]
        validation = report["validation"]
        growth_rate = report["growth_rate_gb_per_day"]

        # === Валидация существования ИБ при фильтрации ===
        if args.ib and not stats:
            all_stats = monitor.get_stats()
            available_ibs = sorted([s.get("ib_name", "") for s in all_stats if s.get("ib_name")])
            raise NotFoundError(
                message=f"ИБ '{args.ib}' не найдена в хранилище",
                details=(
                    f"Доступные информационные базы ({len(available_ibs)}):\n" +
                    "\n".join([f"  • {ib}" for ib in available_ibs])
                )
            )

        # === Заголовок ===
        print(f"\n📁 Хранилище бэкапов: {report['backup_root']}\n")

        # === Таблица диска ===
        total_gb = disk.get("total_kb", 0) / (1024**3)
        used_gb = disk.get("used_kb", 0) / (1024**3)
        free_gb = disk.get("free_kb", 0) / (1024**3)
        used_pct = disk.get("used_percent", 0)
        draw_table(
            headers=["Диск", "Всего", "Занято", "Свободно"],
            rows=[[disk.get("filesystem", "—"), f"{total_gb:.1f} ГБ", f"{used_gb:.1f} ГБ ({used_pct}%)", f"{free_gb:.1f} ГБ"]],
            col_widths=[14, 12, 18, 14]
        )

        # === Фильтрация не критичных предупреждений ===
        non_critical_warnings = [
            "Нет прав чтения для usr1cv8 в /var/backups/1c"
        ]
        filtered_warnings = [
            w for w in validation.get("warnings", [])
            if w not in non_critical_warnings
        ]
        has_errors = validation.get("error_count", 0) > 0
        has_filtered_warnings = len(filtered_warnings) > 0

        if has_errors or has_filtered_warnings:
            print("\n⚠️  Диагностика хранилища:")
            if has_errors:
                for err in validation.get("errors", []):
                    print(f"   ✗ {err}")
            if has_filtered_warnings:
                for warn in filtered_warnings:
                    print(f"   • {warn}")
            hidden_count = len(validation.get("warnings", [])) - len(filtered_warnings)
            if hidden_count > 0:
                print(f"\nℹ️  Скрыто {hidden_count} не критичных предупреждений (не влияют на работу мониторинга)")

        # === Статистика по ИБ ===
        if stats:
            print("\n📊 Статистика по ИБ:")
            table_rows = []
            all_backups = report["backups"]
            for stat in stats:
                ib_orig = stat.get("ib_name", "—")
                # Обрезка ТОЛЬКО для отображения
                ib_display = ib_orig[:21] + "..." if len(ib_orig) > 24 else ib_orig
                files = stat.get("total_files", 0)
                total_size = format_bytes(stat.get("total_size_bytes", 0))
                # Фильтруем по ОРИГИНАЛЬНОМУ имени
                ib_backups = [b for b in all_backups if b.get("ib_name") == ib_orig]
                if ib_backups:
                    last_backup = max(ib_backups, key=lambda x: x.get("timestamp", 0))
                    last_date = format_timestamp(last_backup.get("timestamp", 0))
                    last_size = format_bytes(last_backup.get("size_bytes", 0))
                else:
                    last_date = "—"
                    last_size = "—"
                table_rows.append([ib_display, str(files), last_date, last_size, total_size])
            table_rows.sort(key=lambda x: x[0].lower())
            draw_table(
                headers=["ИБ", "Бэкапов", "Последний", "Последний размер", "Всего"],
                rows=table_rows,
                col_widths=[24, 11, 12, 18, 12]
            )
        else:
            print("\nℹ️  В хранилище нет резервных копий.")
            print("   Создайте первую через: ib_1c backup --ib ИМЯ_ИБ")

        # === Прогноз роста ===
        print()
        if free_gb < 0.1:
            print("⚠️  КРИТИЧЕСКИ МАЛО СВОБОДНОГО МЕСТА (< 0.1 ГБ). Требуется срочная очистка!")
        elif growth_rate > 0.1 and free_gb > 0.5:
            days_left = free_gb / growth_rate
            print(f"📈 Прогноз: при текущем темпе (~{growth_rate:.1f} ГБ/день) свободного места хватит на ~{days_left:.1f} дня")
        elif growth_rate > 0:
            print(f"ℹ️  Темп роста: ~{growth_rate:.1f} ГБ/день (недостаточно данных для точного прогноза)")
        else:
            print("ℹ️  Недостаточно данных для расчёта темпа роста (нужно минимум 2 бэкапа за последние 7 дней)")
        print()
        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Операция прервана пользователем (Ctrl+C)", file=sys.stderr)
        return 130
    except NotFoundError as e:
        print(f"❌ {e.message}", file=sys.stderr)
        if e.details:
            print(f"\n{e.details}", file=sys.stderr)
        return 127
    except Exception as e:
        print(f"❌ Критическая ошибка: {type(e).__name__}: {e}", file=sys.stderr)
        print("   Проверьте логи или выполните диагностику уровня 0:", file=sys.stderr)
        print("   /opt/1cv8/scripts/engines/disk_usage.sh", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
