#!/usr/bin/env python3
"""
backup.py — CLI-интерфейс для создания бэкапов ИБ 1С
Вызывается через ib_1c backup ... (единая точка входа)
"""

import sys
import argparse
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent
ENGINES_DIR = SCRIPTS_DIR / "engines"

def main(args=None):
    parser = argparse.ArgumentParser(
        description="Создать бэкап информационных баз 1С",
        epilog="Пример: backup.py --format dump --ib artel_2025 oksana_2025"
    )
    parser.add_argument("--format", choices=["dump", "sql"], required=True, help="Формат бэкапа")
    parser.add_argument("--ib", required=True, nargs='+', help="Имя ИБ (можно несколько)")
    
    parsed = parser.parse_args(args)
    
    errors = []
    
    print(f"\n📦 Начало бэкапа {len(parsed.ib)} ИБ (формат: {parsed.format})")
    print("=" * 70)
    
    for idx, ib_name in enumerate(parsed.ib, 1):
        print(f"\n[{idx}/{len(parsed.ib)}] 🔄 {ib_name}")
        print("-" * 70)
        
        cmd = ["sudo", "-u", "usr1cv8", str(ENGINES_DIR / "backup.sh"), 
               "--ib", ib_name, "--format", parsed.format]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(result.stdout)
            else:
                print(f"❌ Ошибка: {result.stderr}", file=sys.stderr)
                errors.append(ib_name)
                
        except KeyboardInterrupt:
            print("\n⚠️  Прервано пользователем", file=sys.stderr)
            return 130
        except Exception as e:
            print(f"❌ Критическая ошибка: {e}", file=sys.stderr)
            errors.append(ib_name)
    
    print("\n" + "=" * 70)
    print(f"✅ Успешно: {len(parsed.ib) - len(errors)}/{len(parsed.ib)} ИБ")
    
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
