#!/usr/bin/env python3
"""
rm.py — CLI-интерфейс для удаления бэкапов
Вызывается через orchestrator.py, но может работать автономно
"""

import sys
import argparse
from services.rm_service import RmService
from core.exceptions import OrchestratorError

def main(args=None):
    parser = argparse.ArgumentParser(
        description="Удалить бэкапы информационных баз 1С",
        epilog="Пример: rm.py --ib artel_2025 --timestamp 20260204_120000 --confirm"
    )
    parser.add_argument("--ib", required=True, nargs='+', help="Имя ИБ (можно несколько)")
    parser.add_argument("--timestamp", help="Метка времени бэкапа (ГГГГММДД_ЧЧММСС)")
    parser.add_argument("--older-than", help="Удалить бэкапы старше даты (ГГГГММДД)")
    parser.add_argument("--dry-run", action="store_true", help="Симуляция без удаления")
    parser.add_argument("--confirm", action="store_true", help="Подтверждение для реального удаления")
    
    parsed = parser.parse_args(args)
    
    try:
        service = RmService()
        errors = []
        
        for ib_name in parsed.ib:
            print(f"\n[ИБ: {ib_name}]")
            
            if parsed.timestamp:
                result = service.remove_backup(
                    ib_name=ib_name,
                    timestamp=parsed.timestamp,
                    dry_run=parsed.dry_run,
                    confirm=parsed.confirm
                )
            elif parsed.older_than:
                result = service.remove_backup(
                    ib_name=ib_name,
                    older_than=parsed.older_than,
                    dry_run=parsed.dry_run,
                    confirm=parsed.confirm
                )
            else:
                if not parsed.confirm and not parsed.dry_run:
                    print(f"❌ Требуется --confirm для удаления ВСЕХ бэкапов ИБ '{ib_name}'")
                    errors.append(ib_name)
                    continue
                result = service.remove_all_backups(ib_name=ib_name, confirm=parsed.confirm)
            
            if result["success"]:
                if result["stdout"]:
                    print(result["stdout"].strip())
            else:
                print(f"❌ Ошибка: {result.get('stderr', 'Неизвестная ошибка').strip()}", file=sys.stderr)
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
