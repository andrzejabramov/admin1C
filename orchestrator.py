#!/usr/bin/env python3
"""
orchestrator.py — ВНУТРЕННЯЯ точка маршрутизации
Вызывается через симлинк ib_1c как единая команда администрирования 1С.
"""

import sys
import argparse
import importlib
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

def get_available_commands():
    """Динамически получить список доступных команд из interfaces/cli/"""
    cli_dir = SCRIPTS_DIR / "commands"
    commands = []
    if cli_dir.exists():
        for f in cli_dir.glob("*.py"):
            if f.name != "__init__.py" and not f.name.startswith("_"):
                commands.append(f.stem)
    return sorted(commands)

def main():
    available_commands = get_available_commands()
    
    parser = argparse.ArgumentParser(
        prog="ib_1c",
        description="Единая команда администрирования 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Доступные команды: {', '.join(available_commands) if available_commands else 'нет'}

Примеры:
  ib_1c backup --format dump --ib artel_2025 oksana_2025
  ib_1c rm --ib artel_2025 --timestamp 20260204_120000 --confirm
        """
    )
    
    parser.add_argument("command", choices=available_commands or ["backup", "rm"], 
                       help="Операция над ИБ (динамически определяется из interfaces/cli/)")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Аргументы операции")
    
    args = parser.parse_args()
    
    # Динамическая маршрутизация через импорт
    try:
        module_path = f"commands.{args.command}"
        module = importlib.import_module(module_path)
        
        if not hasattr(module, "main"):
            print(f"❌ Модуль '{args.command}' не содержит функции main()", file=sys.stderr)
            return 1
        
        return module.main(args.args)
        
    except ModuleNotFoundError as e:
        cli_dir = SCRIPTS_DIR / "commands"
        print(f"❌ Команда '{args.command}' не найдена", file=sys.stderr)
        print(f"   Доступные команды: {', '.join(available_commands)}", file=sys.stderr)
        print(f"   Для добавления новой команды создайте: {cli_dir}/{args.command}.py", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Операция прервана пользователем", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Критическая ошибка в команде '{args.command}': {type(e).__name__}: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
