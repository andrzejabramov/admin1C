# backup/adapters/cli/backup_adapter.py
"""
CLI-адаптер для бэкапов — только парсинг аргументов и вывод.
Бизнес-логика вынесена в доменный сервис backup.services.backup_service.
"""

import sys
import argparse
from backup.services.backup_service import (
    backup_multiple,
    estimate_total_backup_size,
    get_free_space,
    check_disk_space
)
from core.config import load_ib_list


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Создать бэкап информационных баз 1С",
        epilog="Примеры:\n"
               "  ib_1c backup --format dump --ib artel_2025 oksana_2025\n"
               "  ib_1c backup --format dump --all\n"
               "  ib_1c backup --format dump --all --dry-run"
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
        # Фильтруем служебные/некорректные ИБ
        ib_list = [ib for ib in ib_list if ib and not ib.startswith('_') and ib not in ('all', 'test_ib', 'tst_db', 'apral_2025', 'test_sb')]
        if not ib_list:
            print("❌ Нет ИБ для бэкапа в ib_list.conf (или все отфильтрованы как служебные)", file=sys.stderr)
            return 1
        mode_label = "режим --all"
    else:
        ib_list = parsed.ib
        mode_label = f"--ib ({len(ib_list)} ИБ)"
    
    print(f"\n📦 Начало бэкапа {len(ib_list)} ИБ (формат: {parsed.format}) [{mode_label}]")
    print("=" * 70)
    
    # === Проверка дискового пространства для массовых операций ===
    if parsed.all or parsed.dry_run:
        check_result = check_disk_space(ib_list, parsed.format)
        print(f"\n{check_result['message']}")
        
        # В режиме --dry-run — только показываем оценку и завершаем
        if parsed.dry_run:
            print("\n⏭️  СИМУЛЯЦИЯ: бэкап не будет создан (режим --dry-run)")
            print("=" * 70)
            for idx, ib_name in enumerate(ib_list, 1):
                size_gb = estimate_total_backup_size([ib_name], parsed.format)
                print(f"\n[{idx}/{len(ib_list)}] ⏭️  {ib_name:<30} → ~{size_gb:.1f} ГБ")
            print("\n" + "=" * 70)
            print(f"✅ Симуляция завершена: {len(ib_list)}/{len(ib_list)} ИБ")
            return 0
        
        # В реальном режиме --all — прерываем при нехватке места
        if not check_result["sufficient"]:
            print("\n⚠️  Бэкап прерван из-за нехватки дискового пространства", file=sys.stderr)
            print("   Совет: очистите старые бэкапы перед повторной попыткой:", file=sys.stderr)
            print("     ib_1c rm --ib ИМЯ --keep N", file=sys.stderr)
            return 1
    
    # === Выполнение бэкапа ===
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