# /opt/1cv8/scripts/commands/backup.py
"""
CLI-адаптер для бэкапов — только парсинг аргументов и вывод.
Бизнес-логика вынесена в services.backup_service.
"""

import sys
import argparse
from services.backup_service import backup_multiple
from core.config import load_ib_list  # ← добавляем импорт


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Создать бэкап информационных баз 1С",
        epilog="Примеры:\n"
               "  backup --format dump --ib artel_2025 oksana_2025\n"
               "  backup --format dump --all"
    )
    parser.add_argument("--format", choices=["dump", "sql"], required=True, help="Формат бэкапа")
    
    # Взаимоисключающие аргументы: --ib ИЛИ --all
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ib", nargs='+', metavar="ИМЯ", help="Имя ИБ (можно несколько)")
    group.add_argument("--all", action="store_true", help="Бэкап всех ИБ из ib_list.conf")
    
    parser.add_argument("--dry-run", action="store_true", help="Симуляция без реального бэкапа")
    
    parsed = parser.parse_args(args)
    
    # Получаем список ИБ в зависимости от режима
    if parsed.all:
        ib_list = load_ib_list()
        # Фильтруем служебные/некорректные ИБ (пустые, с размером 0, служебные имена)
        ib_list = [ib for ib in ib_list if ib and not ib.startswith('_') and ib not in ('all', 'test_ib', 'tst_db', 'apral_2025')]
        if not ib_list:
            print("❌ Нет ИБ для бэкапа в ib_list.conf (или все отфильтрованы как служебные)", file=sys.stderr)
            return 1
        print(f"\n📦 Начало бэкапа {len(ib_list)} ИБ (формат: {parsed.format}) [режим --all]")
    else:
        ib_list = parsed.ib
        print(f"\n📦 Начало бэкапа {len(ib_list)} ИБ (формат: {parsed.format})")
    
    print("=" * 70)
    
    if parsed.dry_run:
        print(f"\n⏭️  СИМУЛЯЦИЯ: бэкап {len(ib_list)} ИБ (формат: {parsed.format})")
        print("=" * 70)
        for idx, ib_name in enumerate(ib_list, 1):
            print(f"\n[{idx}/{len(ib_list)}] ⏭️  {ib_name}")
            print("-" * 70)
            print("Симуляция: бэкап не будет создан (режим --dry-run)")
        print("\n" + "=" * 70)
        print(f"✅ Симуляция завершена: {len(ib_list)}/{len(ib_list)} ИБ")
        return 0
    
    # Вызов сервиса с потоковым выводом (прогресс отобразится напрямую)
    results = backup_multiple(ib_list, parsed.format, dry_run=False)
    
    errors = []
    for idx, result in enumerate(results, 1):
        ib_name = result["ib_name"]
        if not result["success"]:
            print(f"\n[{idx}/{len(results)}] ❌ {ib_name}")
            print("-" * 70)
            print(f"❌ Ошибка: {result['stderr'] or 'Неизвестная ошибка'}", file=sys.stderr)
            errors.append(ib_name)
        else:
            print(f"\n[{idx}/{len(results)}] ✅ {ib_name}")
    
    print("\n" + "=" * 70)
    print(f"✅ Успешно: {len(results) - len(errors)}/{len(results)} ИБ")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())