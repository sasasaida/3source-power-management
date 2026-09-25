import pytest

from app.guardrails.validator import validate_time_window


def test_valid_time_window():
    validate_time_window(13, 15)


def test_invalid_hour():
    with pytest.raises(ValueError):
        validate_time_window(24, 25)


def test_start_hour_must_be_before_end_hour():
    with pytest.raises(ValueError):
        validate_time_window(15, 13)