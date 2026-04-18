"""Unit test example — pure functions, no I/O, no network."""

from __future__ import annotations

import pytest


def add(a: int, b: int) -> int:
    """Example: production code would live in src/ — this is inline for demo."""
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("division by zero")
    return a / b


# ---------- Basic assertions ----------


def test_add_positives() -> None:
    assert add(2, 3) == 5


def test_add_negatives() -> None:
    assert add(-1, -1) == -2


# ---------- Parametrized ----------


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (6, 2, 3),
        (9, 3, 3),
        (1, 2, 0.5),
    ],
)
def test_divide(a: float, b: float, expected: float) -> None:
    assert divide(a, b) == expected


def test_divide_by_zero_raises() -> None:
    with pytest.raises(ValueError, match="division by zero"):
        divide(1, 0)


# ---------- Fixture usage ----------


def test_user_factory(make_user) -> None:  # type: ignore[no-untyped-def]
    user = make_user(name="Bob")
    assert user["name"] == "Bob"
    assert user["active"] is True
