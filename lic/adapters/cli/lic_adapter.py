#!/usr/bin/env python3
"""
lic.py — мониторинг и управление лицензиями 1С
Работает только с read-only операциями через прямой парсинг файлов .lic
"""

import sys
import argparse
from pathlib import Path
from core.utils import machine_to_human
from lic.services.lic_service import LicenseMonitor

def format_size(bytes_size: int) -> str:
    """Форматирование размера в человекочитаемый вид"""
    if bytes_size == 0:
        return "0B"
    for unit in ["B", "K", "M", "G", "T"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f}P"

def wrap_text(text: str, width: int) -> list:
    """Разбивает текст на строки заданной ширины (без разрыва слов)"""
    if not text:
        return [""]
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if len(current_line) + len(word) + (1 if current_line else 0) <= width:
            current_line += (" " if current_line else "") + word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines or [""]

def draw_table(headers: list, rows: list, col_widths: list = None) -> None:
    """Рисует ASCII-таблицу с заголовками и строками"""
    if col_widths is None:
        col_widths = [max(len(str(cell)) for cell in col) + 2 for col in zip(*([headers] + rows))]
    
    print("┌" + "┬".join("─" * w for w in col_widths) + "┐")
    
    header_cells = []
    for i, header in enumerate(headers):
        header_cells.append(f" {header:{col_widths[i]-2}} ")
    print("│" + "│".join(header_cells) + "│")
    
    print("├" + "┼".join("─" * w for w in col_widths) + "┤")
    
    for row in rows:
        line_counts = [1]
        wrapped_cells = []
        for i, cell in enumerate(row):
            if i == len(col_widths) - 1:
                wrapped = wrap_text(str(cell), col_widths[i] - 4)
                wrapped_cells.append(wrapped)
                line_counts.append(len(wrapped))
            else:
                wrapped_cells.append([str(cell)])
                line_counts.append(1)
        
        max_lines = max(line_counts)
        
        for line_idx in range(max_lines):
            cells = []
            for i in range(len(col_widths)):
                content = ""
                if i < len(wrapped_cells):
                    lines = wrapped_cells[i]
                    if line_idx < len(lines):
                        content = lines[line_idx]
                if i == len(col_widths) - 1:
                    cells.append(f" {content:{col_widths[i]-2}} ")
                else:
                    cells.append(f" {content:{col_widths[i]-2}} ")
            print("│" + "│".join(cells) + "│")
    
    print("└" + "┴".join("─" * w for w in col_widths) + "┘")

def print_license_table(licenses: list):
    """Вывести таблицу лицензий"""
    headers = ["Регистрационный номер", "Тип", "Продукт", "Пользователей", "Статус"]
    rows = []
    
    total_users = 0
    total_servers = 0
    
    for lic in licenses:
        regnum = lic["regnum"] + "G0"
        type_ = lic["type"]
        users = int(lic["users"])
        
        if "сервер" in type_.lower():
            total_servers += 1
        else:
            total_users += users
        
        product_name = lic["filename"].replace(".lic", "")
        if "_" in product_name:
            product_name = product_name.split("_")[0] + "..."
        
        rows.append([regnum, type_, product_name, str(users), lic["status"]])
    
    if rows:
        print()
        draw_table(headers=headers, rows=rows, col_widths=[24, 14, 16, 16, 12])
        print(f"\nℹ️  Итого: {len(licenses)} блоков лицензий | {total_users} клиентских | {total_servers} серверная\n")

def print_license_detail(regnum: str):
    """Вывести детали конкретной лицензии с переносом длинных значений"""
    monitor = LicenseMonitor()
    info = monitor.get_license_info(regnum)
    
    if not info:
        print(f"❌ Лицензия с номером {regnum} не найдена\n", file=sys.stderr)
        return 1
    
    regnum_full = info.get("Регистрационный номер", regnum.strip())
    
    headers = ["Параметр", "Значение"]
    rows = [
        ["Регистрационный номер", regnum_full],
        ["Тип лицензии", info.get("Тип лицензии", "неизвестно")],
        ["Продукт", info.get("Наименование продукта", "неизвестно")],
        ["Пользователей", info.get("Количество пользователей", "0")],
        ["Срок действия", info.get("Срок действия", "неограничен")]
    ]
    
    print()
    draw_table(headers=headers, rows=rows, col_widths=[24, 50])
    return 0

def print_monitoring():
    """Вывести статистику использования лицензий"""
    monitor = LicenseMonitor()
    stats = monitor.get_full_report()
    
    headers = ["Показатель", "Значение"]
    rows = [
        ["Клиентских лицензий", str(stats["total_users"])],
        ["Серверных лицензий", str(stats["total_servers"])],
        ["Активных сессий", str(stats["active_sessions"])],
        ["Общее количество блоков", str(stats["total_licenses"])]
    ]
    
    print()
    draw_table(headers=headers, rows=rows, col_widths=[25, 15])

def print_backup_info(backup: dict):
    """Вывести информацию о резервной копии"""
    print(f"\n✅ Резервная копия создана: {backup['backup_path']}")
    print(f"   Блоков лицензий: {backup['backup_count']}")
    print(f"   Временная метка: {machine_to_human(backup['timestamp'])}\n")

def main(args=None):
    parser = argparse.ArgumentParser(description="Мониторинг лицензий 1С")
    parser.add_argument("-A", "--all", action="store_true", help="Сводка по всем лицензиям")
    parser.add_argument("-l", "--block", metavar="НОМЕР", help="Детализация блока по рег. номеру (с/без суффикса G0)")
    parser.add_argument("-m", "--monitor", action="store_true", help="Мониторинг использования лицензий")
    parser.add_argument("-b", "--backup", action="store_true", help="Создать резервную копию лицензий")
    
    parsed = parser.parse_args(args)
    
    if parsed.all:
        monitor = LicenseMonitor()
        licenses = monitor.get_license_list()
        print_license_table(licenses)
        return 0
    
    if parsed.block:
        return print_license_detail(parsed.block)
    
    if parsed.monitor:
        print_monitoring()
        return 0
    
    if parsed.backup:
        monitor = LicenseMonitor()
        backup = monitor.create_backup()
        print_backup_info(backup)
        return 0
    
    parser.print_help()
    return 1

if __name__ == "__main__":
    sys.exit(main())
