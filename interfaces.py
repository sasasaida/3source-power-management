"""
interfaces.py — SHARED CONTRACT between LLM-interpreter half and optimizer half.
Do NOT modify without syncing both sides.
"""

# The exact set of directive types (must match Problem Statement Section 04)
DIRECTIVE_TYPES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}

# Required structured_adjustment keys per directive type
REQUIRED_ADJUSTMENT_KEYS = {
    "solar_reduction":         {"hours", "factor"},
    "minimum_battery_reserve": {"hours", "minimum_energy_kwh"},
    "no_charge_window":        {"hours"},
    "no_discharge_window":     {"hours"},
    "max_grid_window":         {"hours", "max_grid_kwh"},
    "no_op":                   set(),
}

# ---- Boundary 1: what optimizer.optimize() receives ----
# scenario: dict with keys scenario_id, operator_notes, hours, battery
# directives: list[DirectiveDict]

# ---- Boundary 2: what optimizer.optimize() returns ----
# OptimizeResult: dict with keys hourly_plan, total_grid_kwh,
#                 total_cost_bdt, peak_grid_kwh

# ---- Boundary 3: what main.build_response() returns to the client ----
# FullResponse: dict with keys scenario_id, directive_interpretation,
#               hourly_plan, total_grid_kwh, total_cost_bdt,
#               peak_grid_kwh, plan_summary