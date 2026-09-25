"""
validator.py — deterministic replay of the returned plan.

Mirrors the judge's checks (Problem Statement §9, §11.3). Runs on every
response before it leaves the server. Raise ValidationError on any failure.
"""
from __future__ import annotations

TOL = 1e-3  # tighter than judge's 1e-2


class ValidationError(Exception):
    """Raised when the plan violates the spec."""
    pass


def _effective_inputs(scenario: dict, directives: list[dict]):
    """Recompute effective_solar and per-hour min_energy from directives."""
    hours = scenario["hours"]
    battery = scenario["battery"]
    N = 24

    effective_solar = [float(h["solar_kwh"]) for h in hours]
    min_energy = [float(battery["minimum_energy_kwh"])] * N

    for d in directives:
        if not d.get("applies") or d["directive_type"] == "no_op":
            continue
        adj = d["structured_adjustment"]
        dt = d["directive_type"]
        hrs = adj["hours"]

        if dt == "solar_reduction":
            f = float(adj["factor"])
            for h in hrs:
                effective_solar[h] *= f
        elif dt == "minimum_battery_reserve":
            r = float(adj["minimum_energy_kwh"])
            for h in hrs:
                if r > min_energy[h]:
                    min_energy[h] = r

    return effective_solar, min_energy


def validate_plan(scenario: dict, directives: list[dict], result: dict) -> None:
    """
    Replays the plan against the spec. Raises ValidationError on any failure.
    Returns None on success.
    """
    hours_data = scenario["hours"]
    battery = scenario["battery"]
    N = 24

    plan = result.get("hourly_plan")
    if not isinstance(plan, list) or len(plan) != N:
        raise ValidationError(f"hourly_plan must have exactly {N} entries, got {len(plan) if isinstance(plan, list) else type(plan)}")

    if [e.get("hour") for e in plan] != list(range(N)):
        raise ValidationError("hourly_plan hours must be 0..23 in ascending order, no duplicates")

    effective_solar, min_energy = _effective_inputs(scenario, directives)

    capacity = float(battery["capacity_kwh"])
    initial_e = float(battery["initial_energy_kwh"])
    max_charge = float(battery["max_charge_kwh_per_hour"])
    max_discharge = float(battery["max_discharge_kwh_per_hour"])

    prev_E = initial_e

    for e in plan:
        h = e["hour"]
        g = float(e["grid_kwh"])
        s = float(e["solar_used_kwh"])
        bk = float(e["battery_kwh"])
        action = e["battery_action"]
        E_reported = float(e["battery_energy_after_kwh"])

        # 1. Non-negative finite
        for name, v in [("grid_kwh", g), ("solar_used_kwh", s),
                        ("battery_kwh", bk), ("battery_energy_after_kwh", E_reported)]:
            if v != v or v == float("inf") or v == float("-inf"):
                raise ValidationError(f"h{h}: {name} is not finite ({v})")
            if v < -TOL:
                raise ValidationError(f"h{h}: {name} is negative ({v})")

        # 2. Action consistency
        if action not in ("charge", "discharge", "idle"):
            raise ValidationError(f"h{h}: invalid battery_action '{action}'")
        if action == "idle" and bk > TOL:
            raise ValidationError(f"h{h}: idle action but battery_kwh={bk}")
        if action != "idle" and bk < -TOL:
            raise ValidationError(f"h{h}: battery_kwh negative on {action}")

        c = bk if action == "charge" else 0.0
        d = bk if action == "discharge" else 0.0

        # 3. Rate limits
        if c > max_charge + TOL:
            raise ValidationError(f"h{h}: charge {c} exceeds max {max_charge}")
        if d > max_discharge + TOL:
            raise ValidationError(f"h{h}: discharge {d} exceeds max {max_discharge}")

        # 4. Solar cap vs effective
        if s > effective_solar[h] + 1e-2:
            raise ValidationError(
                f"h{h}: solar_used {s} exceeds effective solar {effective_solar[h]}"
            )

        # 5. Energy balance
        demand = float(hours_data[h]["demand_kwh"])
        lhs = g + s + d
        rhs = demand + c
        if abs(lhs - rhs) > 1e-2:
            raise ValidationError(
                f"h{h}: energy balance broken: {lhs:.4f} != {rhs:.4f} "
                f"(grid={g}, solar={s}, discharge={d}, demand={demand}, charge={c})"
            )

        # 6. Battery transition
        E_expected = prev_E + c - d
        if abs(E_expected - E_reported) > 1e-2:
            raise ValidationError(
                f"h{h}: battery state mismatch: reported {E_reported}, "
                f"expected {E_expected:.4f} (prev {prev_E}, charge {c}, discharge {d})"
            )

        # 7. Battery bounds
        if E_reported < min_energy[h] - 1e-2:
            raise ValidationError(
                f"h{h}: battery {E_reported} below reserve {min_energy[h]}"
            )
        if E_reported > capacity + 1e-2:
            raise ValidationError(
                f"h{h}: battery {E_reported} exceeds capacity {capacity}"
            )

        prev_E = E_reported

    # 8. End-of-day neutrality
    if abs(prev_E - initial_e) > 1e-2:
        raise ValidationError(
            f"end-of-day battery {prev_E} != initial {initial_e}"
        )

    # 9. Directive-specific checks
    for dd in directives:
        if not dd.get("applies") or dd["directive_type"] == "no_op":
            continue
        adj = dd["structured_adjustment"]
        dt = dd["directive_type"]

        if dt == "no_charge_window":
            for h in adj["hours"]:
                if plan[h]["battery_action"] == "charge":
                    raise ValidationError(f"h{h}: charged inside no_charge_window")
        elif dt == "no_discharge_window":
            for h in adj["hours"]:
                if plan[h]["battery_action"] == "discharge":
                    raise ValidationError(f"h{h}: discharged inside no_discharge_window")
        elif dt == "max_grid_window":
            cap = float(adj["max_grid_kwh"])
            for h in adj["hours"]:
                if plan[h]["grid_kwh"] > cap + 1e-2:
                    raise ValidationError(
                        f"h{h}: grid {plan[h]['grid_kwh']} exceeds cap {cap}"
                    )

    # 10. Totals must match recomputation
    recalc_grid = sum(float(e["grid_kwh"]) for e in plan)
    recalc_cost = sum(
        float(e["grid_kwh"]) * float(hours_data[e["hour"]]["tariff_bdt_per_kwh"])
        for e in plan
    )
    recalc_peak = max((float(e["grid_kwh"]) for e in plan), default=0.0)

    if abs(recalc_grid - float(result["total_grid_kwh"])) > 1e-2:
        raise ValidationError(
            f"total_grid_kwh mismatch: reported {result['total_grid_kwh']}, "
            f"recomputed {recalc_grid:.4f}"
        )
    if abs(recalc_cost - float(result["total_cost_bdt"])) > 1e-2:
        raise ValidationError(
            f"total_cost_bdt mismatch: reported {result['total_cost_bdt']}, "
            f"recomputed {recalc_cost:.4f}"
        )
    if abs(recalc_peak - float(result["peak_grid_kwh"])) > 1e-2:
        raise ValidationError(
            f"peak_grid_kwh mismatch: reported {result['peak_grid_kwh']}, "
            f"recomputed {recalc_peak:.4f}"
        )


# ----------------------------------------------------------------------
# Standalone test harness
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from fixtures import SAMPLE_SCENARIO, SAMPLE_DIRECTIVES
    from optimizer import optimize, InfeasibleError
    import copy

    def run_case(label, scenario, directives):
        print("=" * 70)
        print(label)
        print("=" * 70)
        try:
            result = optimize(scenario, directives)
        except InfeasibleError as e:
            print(f"  optimizer: INFEASIBLE ({e})")
            return
        try:
            validate_plan(scenario, directives, result)
            print(f"  VALID  cost={result['total_cost_bdt']:.2f}  grid={result['total_grid_kwh']:.1f}")
        except ValidationError as e:
            print(f"  INVALID: {e}")

    # --- Happy paths ---
    run_case("1. No directives", SAMPLE_SCENARIO, [])
    run_case("2. Sample 3 directives", SAMPLE_SCENARIO, SAMPLE_DIRECTIVES)

    # --- Tampered plans: validator MUST catch these ---
    print()
    print("#" * 70)
    print("# TAMPERED PLANS — validator must reject each")
    print("#" * 70)

    base = optimize(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES)

    # Tamper 1: bump grid by 10 kWh in hour 0 (breaks balance + totals)
    t1 = copy.deepcopy(base)
    t1["hourly_plan"][0]["grid_kwh"] += 10
    try:
        validate_plan(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES, t1)
        print("T1: FAIL — validator missed balance break")
    except ValidationError as e:
        print(f"T1: caught ({e})")

    # Tamper 2: violate end-of-day neutrality (leave battery lower)
    t2 = copy.deepcopy(base)
    t2["hourly_plan"][-1]["battery_energy_after_kwh"] = 100  # not 200
    try:
        validate_plan(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES, t2)
        print("T2: FAIL — validator missed end-of-day")
    except ValidationError as e:
        print(f"T2: caught ({e})")

    # Tamper 3: charge during no_charge_window (hours 14, 15)
    t3 = copy.deepcopy(base)
    h = 14
    t3["hourly_plan"][h]["battery_action"] = "charge"
    t3["hourly_plan"][h]["battery_kwh"] = 50
    try:
        validate_plan(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES, t3)
        print("T3: FAIL — validator missed no_charge_window")
    except ValidationError as e:
        print(f"T3: caught ({e})")

    # Tamper 4: exceed effective solar (hour 13 has effective 48)
    t4 = copy.deepcopy(base)
    t4["hourly_plan"][13]["solar_used_kwh"] = 200
    try:
        validate_plan(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES, t4)
        print("T4: FAIL — validator missed solar cap")
    except ValidationError as e:
        print(f"T4: caught ({e})")

    # Tamper 5: wrong total_cost
    t5 = copy.deepcopy(base)
    t5["total_cost_bdt"] += 1
    try:
        validate_plan(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES, t5)
        print("T5: FAIL — validator missed cost mismatch")
    except ValidationError as e:
        print(f"T5: caught ({e})")

    # Tamper 6: wrong number of hours
    t6 = copy.deepcopy(base)
    t6["hourly_plan"] = t6["hourly_plan"][:23]
    try:
        validate_plan(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES, t6)
        print("T6: FAIL — validator missed truncated plan")
    except ValidationError as e:
        print(f"T6: caught ({e})")