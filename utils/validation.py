"""Input validation helpers used by the UI and the services."""

from __future__ import annotations

import re

from utils.formatting import parse_price_to_paisa


def validate_product_name(name: str) -> str:
    """Return the cleaned name or raise ValueError."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Product name cannot be empty.")
    if len(name) > 200:
        raise ValueError("Product name is too long (max 200 characters).")
    return name


def validate_price(text) -> int:
    """Return paisa amount or raise ValueError."""
    return parse_price_to_paisa(text)


def validate_quantity(text) -> int:
    """Return a positive integer quantity or raise ValueError."""
    if text is None:
        raise ValueError("Quantity cannot be empty.")
    cleaned = str(text).strip().replace(",", "")
    if not cleaned:
        raise ValueError("Quantity cannot be empty.")
    if not re.fullmatch(r"\d+", cleaned):
        raise ValueError("Quantity must be a whole number.")
    qty = int(cleaned)
    if qty <= 0:
        raise ValueError("Quantity must be greater than zero.")
    if qty > 1_000_000_000:
        raise ValueError("Quantity is too large.")
    return qty


def validate_stock(text) -> int:
    """Return a non-negative integer stock or raise ValueError."""
    if text is None or str(text).strip() == "":
        return 0
    cleaned = str(text).strip().replace(",", "")
    if not re.fullmatch(r"\d+", cleaned):
        raise ValueError("Stock must be a whole number (0 or more).")
    stock = int(cleaned)
    if stock < 0:
        raise ValueError("Stock cannot be negative.")
    if stock > 10_000_000_000:
        raise ValueError("Stock is too large.")
    return stock


def validate_username(username: str) -> str:
    """Return cleaned username or raise ValueError."""
    username = (username or "").strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    if len(username) > 50:
        raise ValueError("Username is too long (max 50 characters).")
    return username
