from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class DirectiveType(str, Enum):
    SOLAR_REDUCTION = "solar_reduction"
    MINIMUM_BATTERY_RESERVE = "minimum_battery_reserve"
    NO_CHARGE_WINDOW = "no_charge_window"
    NO_DISCHARGE_WINDOW = "no_discharge_window"
    MAX_GRID_WINDOW = "max_grid_window"
    NO_OP = "no_op"


class TimeWindow(BaseModel):
    start_hour: int = Field(ge=0, le=23)
    end_hour: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def validate_window(self):
        if self.start_hour >= self.end_hour:
            raise ValueError(
                "start_hour must be less than end_hour"
            )

        return self


class SolarReductionAdjustment(TimeWindow):
    factor: float = Field(ge=0.0, le=1.0)


class MinimumBatteryReserveAdjustment(BaseModel):
    minimum_energy_kwh: float = Field(gt=0)


class NoChargeWindowAdjustment(TimeWindow):
    pass


class NoDischargeWindowAdjustment(TimeWindow):
    pass


class MaxGridWindowAdjustment(TimeWindow):
    max_grid_kwh: float = Field(ge=0)


class NoOpAdjustment(BaseModel):
    pass


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