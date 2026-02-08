#!/usr/bin/env python3
"""
rm.py — CLI-интерфейс для удаления бэкапов ИБ 1С
Вызывается через ib_1c rm ... (единая точка входа)
"""

import sys
import argparse
from services.rm_service import RmService
from core.exceptions import OrchestratorError
from utils.datetime_utils import parse_older_than_arg, parse_timestamp_arg

def main(args=None):
    parser = argparse.ArgumentParser(
        description="Удалить бэкапы информационных баз 1С",
        epilog="""Примеры:
  ib_1c rm --ib artel_2025 --timestamp "07.02.2026 14:30:22" --confirm
  ib_1c rm --ib artel_2025 --older-than "01.02.2026" --dry-run
  ib_1c rm --ib artel_2025 --older-than "01.02" --confirm  # текущий год
  ib_1c rm --ib artel_2025 --dry-run  # симуляция удаления ВСЕХ бэкапов (без --confirm!)
"""
    )
    parser.add_argument("--ib", required=True, nargs="+", help="Имя ИБ (можно несколько)")
    parser.add_argument("--timestamp", help="Метка времени бэкапа (ГГГГММДД_ЧЧММСС или 'дд.мм.гггг чч:мм:сс')")
    parser.add_argument("--older-than", help="Удалить бэкапы старше даты (ГГГГММДД или 'дд.мм.гггг' или 'дд.мм')")
    parser.add_argument("--dry-run", action="store_true", help="Симуляция без удаления (не требует --confirm)")
    parser.add_argument("--confirm", action="store_true", help="Подтверждение для реального удаления")
    
    parsed = parser.parse_args(args)
    
    try:
        service = RmService()
        errors = []
        
        # Предварительная валидация аргументов дат
        timestamp_machine = None
        older_than_machine = None
        
        if parsed.timestamp:
            try:
                timestamp_machine = parse_timestamp_arg(parsed.timestamp)
            except ValueError as e:
                print(f"❌ Ошибка формата --timestamp: {e}", file=sys.stderr)
                return 1
        
        if parsed.older_than:
            older_than_machine = parse_older_than_arg(parsed.older_than)
            if len(older_than_machine) < 8:
                print(f"❌ Некорректная дата для --older-than: '{parsed.older_than}'", file=sys.stderr)
                return 1
        
        for ib_name in parsed.ib:
            print(f"\n[ИБ: {ib_name}]")
            
            # Логика выбора операции с корректной обработкой --dry-run
            if parsed.timestamp:
                result = service.remove_backup(
                    ib_name=ib_name,
                    timestamp=timestamp_machine,
                    dry_run=parsed.dry_run,
                    confirm=parsed.confirm if not parsed.dry_run else True  # Для симуляции подтверждение не нужно
                )
            elif parsed.older_than:
                result = service.remove_backup(
                    ib_name=ib_name,
                    older_than=older_than_machine,
                    dry_run=parsed.dry_run,
                    confirm=parsed.confirm if not parsed.dry_run else True
                )
            else:
                # Удаление ВСЕХ бэкапов
                if not parsed.dry_run and not parsed.confirm:
                    print(f"❌ Требуется --confirm для удаления ВСЕХ бэкапов ИБ '{ib_name}'")
                    print(f"   Используйте --dry-run для просмотра затронутых файлов.")
                    errors.append(ib_name)
                    continue
                
                result = service.remove_all_backups(
                    ib_name=ib_name,
                    confirm=(not parsed.dry_run)  # Для --dry-run всегда разрешаем
                )
            
            if result["success"]:
                if result["stdout"]:
                    print(result["stdout"].strip())
            else:
                stderr = result.get("stderr", "Неизвестная ошибка").strip()
                if "не найден" in stderr or "not found" in stderr:
                    print(f"❌ Бэкап не найден: {stderr}", file=sys.stderr)
                elif "Отказано в доступе" in stderr or "Permission denied" in stderr:
                    print(f"❌ Ошибка прав доступа: {stderr}", file=sys.stderr)
                else:
                    print(f"❌ Ошибка: {stderr}", file=sys.stderr)
                errors.append(ib_name)
        
        print(f"\n✅ Успешно: {len(parsed.ib) - len(errors)}/{len(parsed.ib)} ИБ")
        return 0 if not errors else 1
        
    except OrchestratorError as e:
        print(f"❌ {e.message}", file=sys.stderr)
        if e.details:
            print(f"   Подробности: {e.details}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Операция прервана пользователем", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ {type(e).__name__}: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
