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
    """Поиск адаптеров в доменах: <домен>/adapters/cli/<команда>_adapter.py"""
    commands = {}
    for domain_dir in SCRIPTS_DIR.glob("*"):
        if not domain_dir.is_dir():
            continue
        # Исключаем системные папки
        if domain_dir.name in {"core", "docs", "engines", "commands", "__pycache__", ".git"}:
            continue
        adapter_dir = domain_dir / "adapters" / "cli"
        if not adapter_dir.exists():
            continue
        for adapter_file in adapter_dir.glob("*_adapter.py"):
            if adapter_file.name.startswith("_"):
                continue
            cmd_name = adapter_file.stem.replace("_adapter", "")
            commands[cmd_name] = f"{domain_dir.name}.adapters.cli.{adapter_file.stem}"
    return dict(sorted(commands.items()))

def main():
    available_commands = get_available_commands()
    
    # Чтение примеров из файла
    examples_file = SCRIPTS_DIR / "docs" / "help_examples.txt"
    examples_text = examples_file.read_text() if examples_file.exists() else "Примеры:\n  ib_1c backup --format dump --ib ИМЯ_ИБ"

    parser = argparse.ArgumentParser(
        prog="ib_1c",
        description="Единая команда администрирования 1С",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Доступные команды: {', '.join(available_commands.keys()) if available_commands else 'нет'}

{examples_text}
        """
    )
    
    parser.add_argument("command", choices=list(available_commands.keys()) or ["backup", "rm"], 
                       help="Операция над ИБ (динамически определяется из доменов)")
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Аргументы операции")
    
    args = parser.parse_args()
    
    # Динамическая маршрутизация через доменные адаптеры
    try:
        module_path = available_commands[args.command]
        module = importlib.import_module(module_path)
        
        if not hasattr(module, "main"):
            print(f"❌ Модуль '{args.command}' не содержит функции main()", file=sys.stderr)
            return 1
        
        return module.main(args.args)
        
    except ModuleNotFoundError as e:
        print(f"❌ Команда '{args.command}' не найдена", file=sys.stderr)
        print(f"   Доступные команды: {', '.join(available_commands.keys())}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Операция прервана пользователем", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Критическая ошибка в команде '{args.command}': {type(e).__name__}: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())