"""
Утилиты для работы с форматами дат/времени
Поддержка преобразования между человекочитаемым и машиночитаемым форматами
"""

from datetime import datetime
from typing import Optional, Tuple

# Форматы
MACHINE_FORMAT = "%Y%m%d_%H%M%S"      # 20260207_143022
MACHINE_DATE_ONLY = "%Y%m%d"          # 20260207
HUMAN_FORMAT = "%d.%m.%Y %H:%M:%S"    # 07.02.2026 14:30:22
HUMAN_DATE_ONLY = "%d.%m.%Y"          # 07.02.2026

def machine_to_human(machine_str: str) -> str:
    """Преобразовать машиночитаемую метку в человекочитаемую
    
    Примеры:
        "20260207_143022" → "07.02.2026 14:30:22"
        "20260207"        → "07.02.2026"
    """
    try:
        if "_" in machine_str:
            dt = datetime.strptime(machine_str, MACHINE_FORMAT)
            return dt.strftime(HUMAN_FORMAT)
        else:
            dt = datetime.strptime(machine_str, MACHINE_DATE_ONLY)
            return dt.strftime(HUMAN_DATE_ONLY)
    except (ValueError, TypeError):
        return machine_str  # Возврат исходной строки при ошибке

def human_to_machine(human_str: str) -> Tuple[Optional[str], Optional[str]]:
    """Преобразовать человекочитаемую дату в машиночитаемую
    
    Возвращает: (машиночитаемая_строка, тип: 'timestamp' или 'date')
    
    Примеры:
        "07.02.2026 14:30:22" → ("20260207_143022", "timestamp")
        "07.02.2026"          → ("20260207", "date")
        "07.02"               → (None, "неполная_дата")
    """
    formats = [
        (HUMAN_FORMAT, "timestamp", MACHINE_FORMAT),
        (HUMAN_DATE_ONLY, "date", MACHINE_DATE_ONLY),
    ]
    
    for fmt, fmt_type, target_fmt in formats:
        try:
            dt = datetime.strptime(human_str.strip(), fmt)
            return (dt.strftime(target_fmt), fmt_type)
        except ValueError:
            continue
    
    # Обработка неполной даты "07.02" — предполагаем текущий год
    cleaned = human_str.strip().replace(".", "")
    if len(cleaned) == 4 and cleaned.isdigit():  # "07.02"
        try:
            dt = datetime.strptime(f"{human_str.strip()}.{datetime.now().year}", HUMAN_DATE_ONLY)
            return (dt.strftime(MACHINE_DATE_ONLY), "date")
        except ValueError:
            pass
    
    return (None, "неподдерживаемый_формат")

def parse_older_than_arg(arg_value: str) -> str:
    """Универсальный парсер для --older-than
    
    Принимает:
        - "20260201" (машиночитаемый)
        - "01.02.2026" (человекочитаемый)
        - "01.02" (неполный — текущий год)
    
    Возвращает машиночитаемую дату для передачи в скрипты
    """
    machine, _ = human_to_machine(arg_value)
    if machine:
        return machine
    
    # Если не распознано — предполагаем машиночитаемый формат как есть
    return arg_value.strip()

def parse_timestamp_arg(arg_value: str) -> str:
    """Парсер для --timestamp (полная метка времени)
    
    Принимает:
        - "20260207_143022" (машиночитаемый)
        - "07.02.2026 14:30:22" (человекочитаемый)
    
    Возвращает машиночитаемую метку
    """
    machine, fmt_type = human_to_machine(arg_value)
    if machine and fmt_type == "timestamp":
        return machine
    
    # Проверить, может быть уже в правильном формате
    if "_" in arg_value and len(arg_value.replace("_", "")) == 14:
        return arg_value.strip()
    
    raise ValueError(f"Неверный формат метки времени: '{arg_value}'. Ожидается 'ГГГГММДД_ЧЧММСС' или 'дд.мм.гггг чч:мм:сс'")

# Экспорт для импорта
__all__ = ["machine_to_human", "human_to_machine", "parse_older_than_arg", "parse_timestamp_arg"]
