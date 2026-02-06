# commands/backup.py
"""
CLI-адаптер для бэкапов — только парсинг аргументов и вывод.
Бизнес-логика вынесена в services.backup_service.
"""

import sys
import argparse
from services.backup_service import backup_multiple


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Создать бэкап информационных баз 1С",
        epilog="Пример: backup.py --format dump --ib artel_2025 oksana_2025"
    )
    parser.add_argument("--format", choices=["dump", "sql"], required=True, help="Формат бэкапа")
    parser.add_argument("--ib", required=True, nargs='+', help="Имя ИБ (можно несколько)")
    parser.add_argument("--dry-run", action="store_true", help="Симуляция без реального бэкапа")
    
    parsed = parser.parse_args(args)
    
    if parsed.dry_run:
        print(f"\n⏭️  СИМУЛЯЦИЯ: бэкап {len(parsed.ib)} ИБ (формат: {parsed.format})")
        print("=" * 70)
        for idx, ib_name in enumerate(parsed.ib, 1):
            print(f"\n[{idx}/{len(parsed.ib)}] ⏭️  {ib_name}")
            print("-" * 70)
            print("Симуляция: бэкап не будет создан (режим --dry-run)")
        print("\n" + "=" * 70)
        print(f"✅ Симуляция завершена: {len(parsed.ib)}/{len(parsed.ib)} ИБ")
        return 0
    
    print(f"\n📦 Начало бэкапа {len(parsed.ib)} ИБ (формат: {parsed.format})")
    print("=" * 70)
    
    # Вызов сервиса с потоковым выводом (прогресс отобразится напрямую)
    results = backup_multiple(parsed.ib, parsed.format, dry_run=False)
    
    errors = []
    for idx, result in enumerate(results, 1):
        ib_name = result["ib_name"]
        if not result["success"]:
            # Ошибки всё равно нужно показать (они не прошли через потоковый вывод)
            print(f"\n[{idx}/{len(results)}] ❌ {ib_name}")
            print("-" * 70)
            print(f"❌ Ошибка: {result['stderr'] or 'Неизвестная ошибка'}", file=sys.stderr)
            errors.append(ib_name)
    
    print("\n" + "=" * 70)
    print(f"✅ Успешно: {len(results) - len(errors)}/{len(results)} ИБ")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())