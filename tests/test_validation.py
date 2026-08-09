"""Tests for validation and formatting helpers."""

import pytest

from utils import validation
from utils.formatting import decimal_to_paisa, format_currency, parse_price_to_paisa


def test_parse_price():
    assert parse_price_to_paisa("9215") == 921500
    assert parse_price_to_paisa("9,215") == 921500
    assert parse_price_to_paisa("Rs. 9,215") == 921500
    assert parse_price_to_paisa("99.99") == 9999
    assert parse_price_to_paisa(" 1000 ") == 100000
    assert parse_price_to_paisa("0") == 0


def test_parse_price_invalid():
    for bad in ("", "abc", "-5", "1.2.3", None):
        with pytest.raises(ValueError):
            parse_price_to_paisa(bad)


def test_format_currency():
    assert format_currency(560000) == "Rs. 5,600"
    assert format_currency(4607500) == "Rs. 46,075"
    assert format_currency(9999) == "Rs. 99.99"
    assert format_currency(0) == "Rs. 0"


def test_decimal_to_paisa_rounding():
    assert decimal_to_paisa("99.999") == 10000  # rounds to 100.00
    assert decimal_to_paisa(100) == 10000


def test_validate_product_name():
    assert validation.validate_product_name("  Galaxy  ") == "Galaxy"
    with pytest.raises(ValueError):
        validation.validate_product_name("")
    with pytest.raises(ValueError):
        validation.validate_product_name("   ")


def test_validate_quantity():
    assert validation.validate_quantity("5") == 5
    assert validation.validate_quantity("1,000") == 1000
    for bad in ("", "0", "-1", "1.5", "abc", None):
        with pytest.raises(ValueError):
            validation.validate_quantity(bad)


def test_validate_stock():
    assert validation.validate_stock("") == 0
    assert validation.validate_stock("10") == 10
    with pytest.raises(ValueError):
        validation.validate_stock("-1")
    with pytest.raises(ValueError):
        validation.validate_stock("abc")
