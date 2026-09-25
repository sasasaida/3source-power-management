import pytest

from app.guardrails.validator import validate_hours


def test_valid_hours():
    validate_hours([13, 14])


def test_single_valid_hour():
    validate_hours([23])


def test_hours_must_be_between_0_and_23():
    with pytest.raises(ValueError):
        validate_hours([24])


def test_negative_hour_is_invalid():
    with pytest.raises(ValueError):
        validate_hours([-1])


def test_hours_must_be_unique():
    with pytest.raises(ValueError):
        validate_hours([13, 13])


def test_hours_must_be_sorted():
    with pytest.raises(ValueError):
        validate_hours([14, 13])


def test_empty_hours_are_allowed():
    validate_hours([])