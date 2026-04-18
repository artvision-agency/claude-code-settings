"""Каждая scrape-запись валидируется против JSONSchema.

Если парсер вернул мусор (`price: "8 500 р"` вместо int) — тест падает
сразу и говорит конкретное поле. Лучше чем silent-save в БД.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


@pytest.fixture(scope="module")
def validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


@pytest.mark.schema
def test_valid_record_passes(validator: Draft202012Validator):
    record = {
        "name": "Стул венге",
        "price": 12500,
        "url": "https://example.com/p/1",
        "telephone": "+7 (812) 555-01-23",
    }
    errors = list(validator.iter_errors(record))
    assert not errors, [(e.path, e.message) for e in errors]


@pytest.mark.schema
@pytest.mark.parametrize("broken", [
    {"name": "", "price": 100, "url": "https://x.com/"},               # empty name
    {"name": "X", "price": -5, "url": "https://x.com/"},               # negative price
    {"name": "X", "price": "100", "url": "https://x.com/"},            # price as str
    {"name": "X", "price": 100, "url": "not-a-url"},                   # bad url
    {"name": "X", "price": 100, "url": "https://x.com/", "telephone": "abc"},
])
def test_invalid_records_fail(validator: Draft202012Validator, broken: dict):
    errors = list(validator.iter_errors(broken))
    assert errors, f"Expected schema errors for {broken}"
