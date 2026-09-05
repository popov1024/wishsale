"""Вспомогательные функции: нормализация чисел и т.п."""
from __future__ import annotations

import re
from typing import Optional


def to_float(value) -> Optional[float]:
    """Приводит значение к числу. '37' → 37.0, '37-38' → 37.0, '37,5' → 37.5.

    None, '' и строки без цифр → None.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".").replace("\u00a0", "").replace(" ", "")
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None
