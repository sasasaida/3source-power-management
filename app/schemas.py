from pydantic import BaseModel, Field
from typing import Any


class HourData(BaseModel):
    hour: int
    demand_kwh: float
    solar_kwh: float
    tariff_bdt_per_kwh: float


class Battery(BaseModel):
    capacity_kwh: float
    initial_energy_kwh: float
    minimum_energy_kwh: float
    max_charge_kwh_per_hour: float
    max_discharge_kwh_per_hour: float


class EnergyRequest(BaseModel):
    scenario_id: str
    operator_notes: list[str]
    hours: list[HourData] = Field(min_length=24, max_length=24)
    battery: Battery



class DirectiveInterpretation(BaseModel):
    note_index: int
    applies: bool
    directive_type: str
    structured_adjustment: dict[str, Any] | None
    explanation: str

class InterpretationResult(BaseModel):
    interpretations: list[DirectiveInterpretation]