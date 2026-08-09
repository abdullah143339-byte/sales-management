"""Formatting helpers for currency, quantities and dates.

Money is stored as integer *paisa* (smallest unit of the Pakistani Rupee,
1 Rs = 100 paisa) to avoid floating-point rounding errors.
"""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def paisa_to_decimal(paisa: int) -> Decimal:
    """Convert a paisa integer into a Decimal rupee amount."""
    return (Decimal(paisa) / 100).quantize(Decimal("0.01"))


def decimal_to_paisa(value) -> int:
    """Convert a Decimal / number into an integer paisa amount (rounded)."""
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int((d * 100).to_integral_value(rounding=ROUND_HALF_UP))


def format_currency(paisa: int, symbol: str = "Rs. ") -> str:
    """Format a paisa amount like ``Rs. 46,075`` (or ``Rs. 46,075.50``)."""
    d = paisa_to_decimal(paisa)
    if d == d.to_integral_value():
        text = format(d, ",.0f")
    else:
        text = format(d, ",.2f")
    return f"{symbol}{text}"


def parse_price_to_paisa(text: str) -> int:
    """Parse user input into paisa. Raises ValueError on invalid input."""
    if text is None:
        raise ValueError("Price cannot be empty.")
    cleaned = str(text).strip().replace(",", "").replace("Rs.", "").replace("PKR", "").strip()
    if not cleaned:
        raise ValueError("Price cannot be empty.")
    try:
        d = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError("Invalid price. Example: 9215 or 99.99") from None
    if d < 0:
        raise ValueError("Price cannot be negative.")
    if d > 999_999_999_999:
        raise ValueError("Price is too large.")
    return decimal_to_paisa(d)


def format_integer(value) -> str:
    """Format an integer with thousands separators."""
    return format(int(value), ",d")


def format_date(date_str: str) -> str:
    """Convert ``YYYY-MM-DD`` to ``DD-MM-YYYY`` for display."""
    if not date_str:
        return ""
    try:
        return datetime.date.fromisoformat(date_str).strftime("%d-%m-%Y")
    except ValueError:
        return date_str


def format_time(time_str: str) -> str:
    """Trim a stored time to HH:MM for display."""
    if not time_str:
        return ""
    return time_str[:5]
