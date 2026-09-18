"""Test fixtures matching the frozen interface contract exactly."""

SAMPLE_SCENARIO = {
    "scenario_id": "GRID-101",
    "operator_notes": [
        "Solar output will drop to about 20% from 1 PM to 3 PM.",
        "Do not charge the battery between 2 PM and 4 PM.",
        "The cafeteria menu changes tomorrow.",
    ],
    "hours": [
        {"hour": 0,  "demand_kwh": 180, "solar_kwh": 0,   "tariff_bdt_per_kwh": 7},
        {"hour": 1,  "demand_kwh": 175, "solar_kwh": 0,   "tariff_bdt_per_kwh": 7},
        {"hour": 2,  "demand_kwh": 170, "solar_kwh": 0,   "tariff_bdt_per_kwh": 7},
        {"hour": 3,  "demand_kwh": 165, "solar_kwh": 0,   "tariff_bdt_per_kwh": 7},
        {"hour": 4,  "demand_kwh": 175, "solar_kwh": 0,   "tariff_bdt_per_kwh": 8},
        {"hour": 5,  "demand_kwh": 190, "solar_kwh": 5,   "tariff_bdt_per_kwh": 8},
        {"hour": 6,  "demand_kwh": 230, "solar_kwh": 25,  "tariff_bdt_per_kwh": 9},
        {"hour": 7,  "demand_kwh": 260, "solar_kwh": 60,  "tariff_bdt_per_kwh": 9},
        {"hour": 8,  "demand_kwh": 280, "solar_kwh": 110, "tariff_bdt_per_kwh": 10},
        {"hour": 9,  "demand_kwh": 300, "solar_kwh": 170, "tariff_bdt_per_kwh": 11},
        {"hour": 10, "demand_kwh": 310, "solar_kwh": 220, "tariff_bdt_per_kwh": 11},
        {"hour": 11, "demand_kwh": 320, "solar_kwh": 245, "tariff_bdt_per_kwh": 12},
        {"hour": 12, "demand_kwh": 340, "solar_kwh": 250, "tariff_bdt_per_kwh": 12},
        {"hour": 13, "demand_kwh": 360, "solar_kwh": 240, "tariff_bdt_per_kwh": 13},
        {"hour": 14, "demand_kwh": 370, "solar_kwh": 200, "tariff_bdt_per_kwh": 13},
        {"hour": 15, "demand_kwh": 375, "solar_kwh": 140, "tariff_bdt_per_kwh": 14},
        {"hour": 16, "demand_kwh": 380, "solar_kwh": 80,  "tariff_bdt_per_kwh": 15},
        {"hour": 17, "demand_kwh": 390, "solar_kwh": 30,  "tariff_bdt_per_kwh": 15},
        {"hour": 18, "demand_kwh": 360, "solar_kwh": 5,   "tariff_bdt_per_kwh": 14},
        {"hour": 19, "demand_kwh": 320, "solar_kwh": 0,   "tariff_bdt_per_kwh": 12},
        {"hour": 20, "demand_kwh": 290, "solar_kwh": 0,   "tariff_bdt_per_kwh": 11},
        {"hour": 21, "demand_kwh": 260, "solar_kwh": 0,   "tariff_bdt_per_kwh": 10},
        {"hour": 22, "demand_kwh": 230, "solar_kwh": 0,   "tariff_bdt_per_kwh": 9},
        {"hour": 23, "demand_kwh": 200, "solar_kwh": 0,   "tariff_bdt_per_kwh": 9},
    ],
    "battery": {
        "capacity_kwh": 500,
        "initial_energy_kwh": 200,
        "minimum_energy_kwh": 50,
        "max_charge_kwh_per_hour": 100,
        "max_discharge_kwh_per_hour": 100,
    },
}

SAMPLE_DIRECTIVES = [
    {
        "note_index": 0,
        "applies": True,
        "directive_type": "solar_reduction",
        "structured_adjustment": {"hours": [13, 14], "factor": 0.2},
        "explanation": "Solar reduced to 20% during maintenance window.",
    },
    {
        "note_index": 1,
        "applies": True,
        "directive_type": "no_charge_window",
        "structured_adjustment": {"hours": [14, 15]},
        "explanation": "Battery charging prohibited 2 PM to 4 PM.",
    },
    {
        "note_index": 2,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": "Note does not affect energy schedule.",
    },
]