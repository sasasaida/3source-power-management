from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator


# ----------------------------------------------------------------------
# Shared validation
# ----------------------------------------------------------------------

def validate_hours(hours: list[int]) -> list[int]:
    """Validate that hours are unique integers from 0-23 in ascending order."""

    if any(not isinstance(hour, int) for hour in hours):
        raise ValueError("hours must contain only integers")

    if any(hour < 0 or hour > 23 for hour in hours):
        raise ValueError("hours must be between 0 and 23")

    if len(hours) != len(set(hours)):
        raise ValueError("hours must be unique")

    if hours != sorted(hours):
        raise ValueError("hours must be in ascending order")

    return hours


# ----------------------------------------------------------------------
# Structured adjustments
# ----------------------------------------------------------------------

class TimeWindow(BaseModel):
    hours: list[int]

    _validate_hours = field_validator("hours")(validate_hours)


class SolarReductionAdjustment(TimeWindow):
    factor: float = Field(ge=0.0, le=1.0)


class MinimumBatteryReserveAdjustment(TimeWindow):
    minimum_energy_kwh: float = Field(ge=0)


class NoChargeWindowAdjustment(TimeWindow):
    pass


class NoDischargeWindowAdjustment(TimeWindow):
    pass


class MaxGridWindowAdjustment(TimeWindow):
    max_grid_kwh: float = Field(ge=0)


# ----------------------------------------------------------------------
# Directive models
# ----------------------------------------------------------------------

class SolarReductionDirective(BaseModel):
    note_index: int = Field(ge=0)
    applies: Literal[True]
    directive_type: Literal["solar_reduction"]
    structured_adjustment: SolarReductionAdjustment
    explanation: str = Field(min_length=1)


class MinimumBatteryReserveDirective(BaseModel):
    note_index: int = Field(ge=0)
    applies: Literal[True]
    directive_type: Literal["minimum_battery_reserve"]
    structured_adjustment: MinimumBatteryReserveAdjustment
    explanation: str = Field(min_length=1)


class NoChargeWindowDirective(BaseModel):
    note_index: int = Field(ge=0)
    applies: Literal[True]
    directive_type: Literal["no_charge_window"]
    structured_adjustment: NoChargeWindowAdjustment
    explanation: str = Field(min_length=1)


class NoDischargeWindowDirective(BaseModel):
    note_index: int = Field(ge=0)
    applies: Literal[True]
    directive_type: Literal["no_discharge_window"]
    structured_adjustment: NoDischargeWindowAdjustment
    explanation: str = Field(min_length=1)


class MaxGridWindowDirective(BaseModel):
    note_index: int = Field(ge=0)
    applies: Literal[True]
    directive_type: Literal["max_grid_window"]
    structured_adjustment: MaxGridWindowAdjustment
    explanation: str = Field(min_length=1)


class NoOpDirective(BaseModel):
    note_index: int = Field(ge=0)
    applies: Literal[False]
    directive_type: Literal["no_op"]
    structured_adjustment: None = None
    explanation: str = Field(min_length=1)


# ----------------------------------------------------------------------
# Discriminated union
# ----------------------------------------------------------------------

DirectiveInterpretation = Annotated[
    Union[
        SolarReductionDirective,
        MinimumBatteryReserveDirective,
        NoChargeWindowDirective,
        NoDischargeWindowDirective,
        MaxGridWindowDirective,
        NoOpDirective,
    ],
    Field(discriminator="directive_type"),
]


class InterpretationResult(BaseModel):
    interpretations: list[DirectiveInterpretation]