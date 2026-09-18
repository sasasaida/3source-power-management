"""
optimizer.py — MILP-based energy scheduler.

Public API:
    optimize(scenario: dict, directives: list[dict]) -> dict
"""
from __future__ import annotations

import pulp

ROUND_DECIMALS = 4


class InfeasibleError(Exception):
    """Raised when the constraint set has no feasible schedule."""
    pass


def optimize(scenario: dict, directives: list[dict]) -> dict:
    hours_data = scenario["hours"]
    battery = scenario["battery"]
    N = 24

    # ------------------------------------------------------------------
    # 1. Effective inputs — apply directive adjustments to base scenario
    # ------------------------------------------------------------------
    effective_solar = [float(h["solar_kwh"]) for h in hours_data]
    min_energy = [float(battery["minimum_energy_kwh"])] * N
    charge_allowed = [True] * N
    discharge_allowed = [True] * N
    grid_cap: list[float | None] = [None] * N

    for d in directives:
        if not d.get("applies") or d["directive_type"] == "no_op":
            continue
        adj = d["structured_adjustment"]
        dt = d["directive_type"]
        hrs = adj["hours"]

        if dt == "solar_reduction":
            factor = float(adj["factor"])
            for h in hrs:
                effective_solar[h] *= factor
        elif dt == "minimum_battery_reserve":
            reserve = float(adj["minimum_energy_kwh"])
            for h in hrs:
                if reserve > min_energy[h]:
                    min_energy[h] = reserve
        elif dt == "no_charge_window":
            for h in hrs:
                charge_allowed[h] = False
        elif dt == "no_discharge_window":
            for h in hrs:
                discharge_allowed[h] = False
        elif dt == "max_grid_window":
            cap = float(adj["max_grid_kwh"])
            for h in hrs:
                grid_cap[h] = cap

    # ------------------------------------------------------------------
    # 1b. Pre-flight: catch infeasibilities CBC can't report cleanly
    # ------------------------------------------------------------------
    capacity_check = float(battery["capacity_kwh"])
    base_min = float(battery["minimum_energy_kwh"])

    if base_min > capacity_check + 1e-9:
        raise InfeasibleError(
            f"Base minimum_energy_kwh ({base_min}) exceeds capacity ({capacity_check})"
        )

    for h in range(N):
        if min_energy[h] > capacity_check + 1e-9:
            raise InfeasibleError(
                f"Hour {h}: effective reserve {min_energy[h]} exceeds capacity {capacity_check}"
            )
        if effective_solar[h] < -1e-9:
            raise InfeasibleError(f"Hour {h}: effective solar is negative ({effective_solar[h]})")
        if grid_cap[h] is not None and grid_cap[h] < -1e-9:
            raise InfeasibleError(f"Hour {h}: max_grid_kwh is negative ({grid_cap[h]})")

    # Directive factor sanity (should already be 0..1, but guard anyway)
    for d in directives:
        if d.get("applies") and d["directive_type"] == "solar_reduction":
            f = float(d["structured_adjustment"]["factor"])
            if f < 0 or f > 1:
                raise InfeasibleError(f"solar_reduction factor out of [0,1]: {f}")
            
    # ------------------------------------------------------------------
    # 2. Build the MILP
    # ------------------------------------------------------------------
    prob = pulp.LpProblem("gridwise_energy", pulp.LpMinimize)

    capacity = float(battery["capacity_kwh"])
    max_charge = float(battery["max_charge_kwh_per_hour"])
    max_discharge = float(battery["max_discharge_kwh_per_hour"])
    initial_e = float(battery["initial_energy_kwh"])

    grid        = [pulp.LpVariable(f"grid_{h}", lowBound=0) for h in range(N)]
    solar_used  = [pulp.LpVariable(f"solar_{h}", lowBound=0) for h in range(N)]
    charge      = [pulp.LpVariable(f"chg_{h}", lowBound=0) for h in range(N)]
    discharge   = [pulp.LpVariable(f"dis_{h}", lowBound=0) for h in range(N)]
    E_after = [
        pulp.LpVariable(
            f"E_{h}",
            lowBound=min(float(min_energy[h]), capacity),   # clamp
            upBound=capacity,
        )
        for h in range(N)
    ]
    is_charging    = [pulp.LpVariable(f"ic_{h}", cat="Binary") for h in range(N)]
    is_discharging = [pulp.LpVariable(f"id_{h}", cat="Binary") for h in range(N)]

    # Objective
    prob += pulp.lpSum(
        grid[h] * float(hours_data[h]["tariff_bdt_per_kwh"]) for h in range(N)
    )

    for h in range(N):
        demand = float(hours_data[h]["demand_kwh"])

        # Energy balance
        prob += grid[h] + solar_used[h] + discharge[h] == demand + charge[h]

        # Solar cap
        prob += solar_used[h] <= effective_solar[h]

        # Charge / discharge caps gated by binary flags
        prob += charge[h]    <= max_charge    * is_charging[h]
        prob += discharge[h] <= max_discharge * is_discharging[h]

        # Prevent simultaneous charge + discharge
        prob += is_charging[h] + is_discharging[h] <= 1

        # Directive windows
        if not charge_allowed[h]:
            prob += charge[h] == 0
        if not discharge_allowed[h]:
            prob += discharge[h] == 0
        if grid_cap[h] is not None:
            prob += grid[h] <= grid_cap[h]

        # Battery transition and bounds
        e_before = initial_e if h == 0 else E_after[h - 1]
        prob += E_after[h] == e_before + charge[h] - discharge[h]
        prob += E_after[h] >= min_energy[h]
        prob += E_after[h] <= capacity

    # End-of-day neutrality
    prob += E_after[N - 1] == initial_e

    # ------------------------------------------------------------------
    # 3. Solve
    # ------------------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=10)
    try:
        status = pulp.LpStatus[prob.solve(solver)]
    except Exception as e:
        raise InfeasibleError(f"Error occurred while solving the MILP: {e}") from None

    if status != "Optimal":
        raise InfeasibleError(f"MILP status: {status}")

    # ------------------------------------------------------------------
    # 4. Extract plan
    # ------------------------------------------------------------------
    hourly_plan = []
    for h in range(N):
        g = max(0.0, grid[h].value() or 0.0)
        s = max(0.0, solar_used[h].value() or 0.0)
        c = max(0.0, charge[h].value() or 0.0)
        d = max(0.0, discharge[h].value() or 0.0)
        e_after = max(0.0, E_after[h].value() or 0.0)

        if c > 1e-5:
            action, bkwh = "charge", c
        elif d > 1e-5:
            action, bkwh = "discharge", d
        else:
            action, bkwh = "idle", 0.0

        hourly_plan.append({
            "hour": h,
            "grid_kwh": round(g, ROUND_DECIMALS),
            "solar_used_kwh": round(s, ROUND_DECIMALS),
            "battery_action": action,
            "battery_kwh": round(bkwh, ROUND_DECIMALS),
            "battery_energy_after_kwh": round(e_after, ROUND_DECIMALS),
        })

    total_grid = sum(e["grid_kwh"] for e in hourly_plan)
    total_cost = sum(
        e["grid_kwh"] * float(hours_data[e["hour"]]["tariff_bdt_per_kwh"])
        for e in hourly_plan
    )
    peak_grid = max((e["grid_kwh"] for e in hourly_plan), default=0.0)

    return {
        "hourly_plan": hourly_plan,
        "total_grid_kwh": round(total_grid, ROUND_DECIMALS),
        "total_cost_bdt": round(total_cost, ROUND_DECIMALS),
        "peak_grid_kwh": round(peak_grid, ROUND_DECIMALS),
    }

"""
# ----------------------------------------------------------------------
# Standalone test harness
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import json
    from fixtures import SAMPLE_SCENARIO, SAMPLE_DIRECTIVES

    print("=" * 70)
    print("Sample scenario + 3 directives")
    print("=" * 70)
    result = optimize(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES)
    print(json.dumps(result, indent=2))
    print()
    print(f"Total grid: {result['total_grid_kwh']} kWh")
    print(f"Total cost: {result['total_cost_bdt']} BDT")
    print(f"Peak grid:  {result['peak_grid_kwh']} kWh")
"""
if __name__ == "__main__":
    import json
    from fixtures import SAMPLE_SCENARIO, SAMPLE_DIRECTIVES
    from copy import deepcopy

    def run(label, scenario, directives):
        print("=" * 70)
        print(label)
        print("=" * 70)
        try:
            r = optimize(scenario, directives)
            print(f"cost={r['total_cost_bdt']:.2f}  grid={r['total_grid_kwh']:.1f}  peak={r['peak_grid_kwh']:.1f}")
            return r
        except InfeasibleError as e:
            print(f"INFEASIBLE: {e}")
            return None

    base = run("1. No directives at all", SAMPLE_SCENARIO, [])
    sample = run("2. Sample 3 directives", SAMPLE_SCENARIO, SAMPLE_DIRECTIVES)

    # Test 3: max_grid_window
    d3 = [{"note_index": 0, "applies": True, "directive_type": "max_grid_window",
           "structured_adjustment": {"hours": [16, 17, 18], "max_grid_kwh": 300.0},
           "explanation": ""}]
    run("3. max_grid_window caps hours 16-18 at 300", SAMPLE_SCENARIO, d3)

    # Test 4: minimum_battery_reserve
    d4 = [{"note_index": 0, "applies": True, "directive_type": "minimum_battery_reserve",
           "structured_adjustment": {"hours": [18, 19, 20], "minimum_energy_kwh": 400.0},
           "explanation": ""}]
    run("4. Reserve >= 400 in hours 18-20", SAMPLE_SCENARIO, d4)

    # Test 5: infeasible — reserve above capacity
    d5 = [{"note_index": 0, "applies": True, "directive_type": "minimum_battery_reserve",
           "structured_adjustment": {"hours": [5], "minimum_energy_kwh": 9999.0},
           "explanation": ""}]
    run("5. Reserve 9999 kWh (above capacity 500) — should be infeasible", SAMPLE_SCENARIO, d5)

    # Test 6: solar_reduction to 0
    d6 = [{"note_index": 0, "applies": True, "directive_type": "solar_reduction",
           "structured_adjustment": {"hours": [10, 11, 12], "factor": 0.0},
           "explanation": ""}]
    run("6. Solar zeroed hours 10-12", SAMPLE_SCENARIO, d6)