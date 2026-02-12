#!/usr/bin/env python3
"""
rm_adapter.py — CLI-адаптер для удаления бэкапов ИБ 1С
Вызывается через ib1c rm ... (единая точка входа)
"""

import sys
import argparse
from rm.services.rm_service import RmService
from core.exceptions import OrchestratorError
from core.utils import parse_older_than_arg, parse_timestamp_arg

def main(args=None):
    parser = argparse.ArgumentParser(
        prog="ib1c rm",
        description="Удалить бэкапы информационных баз 1С",
        epilog="""Примеры:
  ib1c rm -I test_db -n                          # Симуляция удаления ВСЕХ бэкапов ИБ
  ib1c rm -I test_db --dry                       # То же самое (длинный флаг)
  ib1c rm -I test_db -t 20260208_183432 -c       # Удалить конкретный бэкап по метке
  ib1c rm -I test_db --at 20260208_183432 -c     # То же самое (--at вместо --timestamp)
  ib1c rm -I test_db -b 20260206 -c              # Удалить бэкапы старше 6 февраля
  ib1c rm -I test_db -a 20260207 -c              # Удалить бэкапы новее 7 февраля
  ib1c rm -I test_db -a 20260206 -b 20260208 -c  # Удалить бэкапы между 6 и 8 февраля
  ib1c rm -I test_db -B 20260206..20260208 -n   # То же самое через --between
  ib1c rm -I test_db db_test -b 20260206 -n     # Несколько ИБ сразу
  ib1c rm -A -n                                  # Симуляция удаления ВСЕХ бэкапов всех ИБ
  ib1c rm -A -c                                  # Реальное удаление ВСЕХ бэкапов всех ИБ
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )
    parser.add_argument("-I", "--ib", nargs="+", metavar="ИБ",
                        help="Имя ИБ (можно несколько)")
    parser.add_argument("-A", "--all", action="store_true",
                        help="Удалить ВСЕ бэкапы всех ИБ (глобальная операция)")
    parser.add_argument("-t", "--at", "--timestamp", dest="timestamp", metavar="МЕТКА",
                        help="Метка времени бэкапа (ГГГГММДД_ЧЧММСС или 'дд.мм.гггг чч:мм:сс')")
    parser.add_argument("-b", "--before", metavar="ДАТА",
                        help="Удалить бэкапы старше даты (ГГГГММДД или 'дд.мм.гггг' или 'дд.мм')")
    parser.add_argument("-a", "--after", metavar="ДАТА",
                        help="Удалить бэкапы новее даты (ГГГГММДД или 'дд.мм.гггг' или 'дд.мм')")
    parser.add_argument("-B", "--between", metavar="ДИАПАЗОН",
                        help="Диапазон дат (формат: НАЧАЛО..КОНЕЦ, например 20260206..20260208)")
    parser.add_argument("-n", "--dry", "--dry-run", dest="dry_run", action="store_true",
                        help="Симуляция без удаления")
    parser.add_argument("-c", "--confirm", action="store_true",
                        help="Подтверждение для реального удаления")
    parser.add_argument("-h", "--help", action="help",
                        help="Показать эту справку и выйти")
    
    parsed = parser.parse_args(args)
    
    # Валидация: --all и --ib взаимоисключающие
    if parsed.all and parsed.ib:
        print("❌ Флаги --all (-A) и --ib (-I) взаимоисключающие", file=sys.stderr)
        return 1
    
    # Валидация: требуется хотя бы один из флагов --all или --ib
    if not parsed.all and not parsed.ib:
        print("❌ Требуется указать --ib (-I) или --all (-A)", file=sys.stderr)
        return 1
    
    # Валидация конфликтов флагов фильтрации
    if parsed.timestamp and (parsed.before or parsed.after or parsed.between):
        print("❌ --at (-t) несовместим с --before (-b), --after (-a) или --between (-B)", file=sys.stderr)
        return 1
    
    if parsed.between and (parsed.before or parsed.after):
        print("❌ --between (-B) несовместим с --before (-b) или --after (-a)", file=sys.stderr)
        return 1
    
    # Парсинг --between → after + before
    after_value = None
    before_value = None
    
    if parsed.between:
        if ".." not in parsed.between:
            print(f"❌ Неверный формат --between: ожидается НАЧАЛО..КОНЕЦ (например 20260206..20260208)", file=sys.stderr)
            return 1
        parts = parsed.between.split("..", 1)
        after_value = parts[0].strip()
        before_value = parts[1].strip()
    
    if parsed.after:
        after_value = parsed.after
    
    if parsed.before:
        before_value = parsed.before
    
    # Предварительная валидация аргументов дат
    timestamp_machine = None
    if parsed.timestamp:
        try:
            timestamp_machine = parse_timestamp_arg(parsed.timestamp)
        except ValueError as e:
            print(f"❌ Ошибка формата --at: {e}", file=sys.stderr)
            return 1
    
    if after_value:
        after_value = parse_older_than_arg(after_value)
        if len(after_value) < 8:
            print(f"❌ Некорректная дата для --after: '{parsed.after}'", file=sys.stderr)
            return 1
    
    if before_value:
        before_value = parse_older_than_arg(before_value)
        if len(before_value) < 8:
            print(f"❌ Некорректная дата для --before: '{parsed.before}'", file=sys.stderr)
            return 1
    
    try:
        service = RmService()
        errors = []
        
        if parsed.all:
            # Глобальное удаление всех ИБ
            print("\n[⚠️  ГЛОБАЛЬНАЯ ОПЕРАЦИЯ: ВСЕ ИБ]")
            result = service.remove_all_ibs(
                dry_run=parsed.dry_run,
                confirm=(parsed.confirm or parsed.dry_run)
            )
            if result["success"]:
                output = result["stdout"].strip() or result["stderr"].strip()
                if output:
                    print(output)
            else:
                stderr = result.get("stderr", "Неизвестная ошибка").strip()
                print(f"❌ Ошибка: {stderr}", file=sys.stderr)
                errors.append("all_ibs")
        else:
            # Удаление для указанных ИБ
            for ib_name in parsed.ib:
                print(f"\n[ИБ: {ib_name}]")
                
                if timestamp_machine:
                    result = service.remove_backup(
                        ib_name=ib_name,
                        timestamp=timestamp_machine,
                        dry_run=parsed.dry_run,
                        confirm=(parsed.confirm or parsed.dry_run)
                    )
                elif after_value or before_value:
                    result = service.remove_backup(
                        ib_name=ib_name,
                        after=after_value,
                        before=before_value,
                        dry_run=parsed.dry_run,
                        confirm=(parsed.confirm or parsed.dry_run)
                    )
                else:
                    # Удаление ВСЕХ бэкапов указанной ИБ
                    result = service.remove_all_backups(
                        ib_name=ib_name,
                        dry_run=parsed.dry_run,
                        confirm=(parsed.confirm or parsed.dry_run)
                    )
                
                if result["success"]:
                    output = result["stdout"].strip() or result["stderr"].strip()
                    if output:
                        print(output)
                else:
                    stderr = result.get("stderr", "Неизвестная ошибка").strip()
                    if "не найден" in stderr or "not found" in stderr:
                        print(f"❌ Бэкап не найден: {stderr}", file=sys.stderr)
                    elif "Отказано в доступе" in stderr or "Permission denied" in stderr:
                        print(f"❌ Ошибка прав доступа: {stderr}", file=sys.stderr)
                    else:
                        print(f"❌ Ошибка: {stderr}", file=sys.stderr)
                    errors.append(ib_name)
        
        print(f"\n✅ Успешно: {1 if parsed.all else len(parsed.ib) - len(errors)}/{1 if parsed.all else len(parsed.ib)} ИБ")
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
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
