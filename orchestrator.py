#!/usr/bin/env python3
"""
orchestrator.py — единая точка входа для администрирования 1С

Поддерживает синтаксис из cmd.md:
  orchestrator.py rm --ib artel_2025 oksana_2025 --timestamp 20260204_120000 --confirm
"""

import sys
import argparse
import traceback
from typing import List
from services.rm_service import RmService
from core.exceptions import (
    OrchestratorError,
    RmError,
    NotFoundError,
    PermissionError
)

def format_error(e: Exception, debug: bool = False) -> str:
    """Форматирование ошибки для человекочитаемого вывода"""
    if isinstance(e, OrchestratorError):
        msg = f"❌ {e.message}"
        if e.details:
            msg += f"\n   Подробности: {e.details}"
        return msg
    
    # Стандартные исключения
    if isinstance(e, KeyboardInterrupt):
        return "⚠️  Операция прервана пользователем"
    
    if debug:
        return f"❌ Критическая ошибка: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    
    return f"❌ {type(e).__name__}: {str(e)}"

def handle_rm_command(args: argparse.Namespace, debug: bool = False) -> int:
    """Обработка команды 'rm' с централизованной обработкой ошибок"""
    service = RmService()
    errors: List[str] = []
    
    for ib_name in args.ib:
        print(f"\n[ИБ: {ib_name}]")
        
        try:
            # Валидация ИБ на уровне сервиса (будет брошено NotFoundError при отсутствии)
            if args.timestamp:
                result = service.remove_backup(
                    ib_name=ib_name,
                    timestamp=args.timestamp,
                    dry_run=args.dry_run,
                    confirm=args.confirm
                )
            elif args.older_than:
                result = service.remove_backup(
                    ib_name=ib_name,
                    older_than=args.older_than,
                    dry_run=args.dry_run,
                    confirm=args.confirm
                )
            else:
                if not args.confirm and not args.dry_run:
                    raise RmError(
                        message="Требуется --confirm для удаления ВСЕХ бэкапов ИБ",
                        details=f"ИБ: {ib_name}. Используйте --dry-run для просмотра или --confirm для подтверждения."
                    )
                result = service.remove_all_backups(ib_name=ib_name, confirm=args.confirm)
            
            # Анализ результата выполнения скрипта
            if not result["success"]:
                stderr = result.get("stderr", "").strip()
                if "Отказано в доступе" in stderr or "Permission denied" in stderr:
                    raise PermissionError(
                        message="Ошибка прав доступа при удалении бэкапа",
                        details=stderr
                    )
                elif "не найден" in stderr or "not found" in stderr:
                    raise NotFoundError(
                        message="Бэкап не найден",
                        details=stderr
                    )
                else:
                    raise RmError(
                        message="Ошибка при выполнении операции удаления",
                        details=stderr
                    )
            
            # Успешное выполнение
            stdout = result.get("stdout", "").strip()
            if stdout:
                print(stdout)
                
        except OrchestratorError as e:
            print(format_error(e, debug), file=sys.stderr)
            errors.append(ib_name)
        except Exception as e:
            print(format_error(e, debug), file=sys.stderr)
            errors.append(ib_name)
    
    # Итоговый отчёт
    total = len(args.ib)
    success = total - len(errors)
    print(f"\n✅ Успешно: {success}/{total} ИБ")
    
    return 0 if not errors else 1

def main():
    # Проверка режима отладки (--debug в любом месте аргументов)
    debug = "--debug" in sys.argv
    
    try:
        parser = argparse.ArgumentParser(
            description="Оркестратор администрирования 1С",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Примеры:
  %(prog)s rm --ib artel_2025 --dry-run
  %(prog)s rm --ib artel_2025 oksana_2025 --timestamp 20260204_120000 --confirm
  %(prog)s rm --ib artel_2025 --debug  # Вывод полного стека при ошибке
            """
        )
        
        # Глобальный флаг --debug (удаляем из sys.argv чтобы не мешал парсеру)
        if debug:
            sys.argv.remove("--debug")
        
        subparsers = parser.add_subparsers(dest="command", required=True, help="Команда")
        
        # Команда 'rm'
        rm_parser = subparsers.add_parser("rm", help="Удалить бэкапы ИБ")
        rm_parser.add_argument("--ib", required=True, nargs='+',
                              help="Имя ИБ (можно несколько: --ib ИБ1 ИБ2 ИБ3)")
        rm_parser.add_argument("--timestamp", help="Метка времени бэкапа (ГГГГММДД_ЧЧММСС)")
        rm_parser.add_argument("--older-than", help="Удалить бэкапы старше даты (ГГГГММДД)")
        rm_parser.add_argument("--dry-run", action="store_true", help="Симуляция")
        rm_parser.add_argument("--confirm", action="store_true", help="Подтверждение для реального удаления")
        
        args = parser.parse_args()
        
        if args.command == "rm":
            sys.exit(handle_rm_command(args, debug))
        else:
            parser.print_help()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n" + format_error(KeyboardInterrupt(), debug), file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print("\n" + format_error(e, debug), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
