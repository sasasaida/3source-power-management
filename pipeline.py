"""
pipeline.py — single entry point for the optimizer half.

The pipeline is orchestration only:
  1. Run the optimizer with the validated directives.
  2. Run the final replay validator on the result.
  3. Return the validated result.

It does NOT silently fall back to a directive-free plan. A schedule that
violates an operator directive is not a valid schedule, so we never
produce one.
"""
from __future__ import annotations

from optimizer import optimize, InfeasibleError
from validator import validate_plan, ValidationError


def run_pipeline(scenario: dict, directives: list[dict]) -> dict:
    """
    Orchestrate optimization + final validation.

    Raises:
        InfeasibleError  — directives cannot be jointly satisfied
        ValidationError  — optimizer produced a plan that violates the spec
    """
    result = optimize(scenario, directives)
    validate_plan(scenario, directives, result)
    return result


def generate_summary(scenario: dict, directives: list[dict], result: dict) -> str:
    applied = [d for d in directives if d.get("applies")]
    types = sorted({d["directive_type"] for d in applied if d["directive_type"] != "no_op"})
    directives_part = (
        f"Applied directives: {', '.join(types)}." if types
        else "No operator directives applied."
    )
    return (
        f"{directives_part} "
        f"Total grid {result['total_grid_kwh']:.1f} kWh, "
        f"cost {result['total_cost_bdt']:.2f} BDT, "
        f"peak {result['peak_grid_kwh']:.1f} kWh."
    )


def build_response(scenario: dict, directives: list[dict], result: dict) -> dict:
    return {
        "scenario_id": scenario["scenario_id"],
        "directive_interpretation": directives,
        "hourly_plan": result["hourly_plan"],
        "total_grid_kwh": result["total_grid_kwh"],
        "total_cost_bdt": result["total_cost_bdt"],
        "peak_grid_kwh": result["peak_grid_kwh"],
        "plan_summary": generate_summary(scenario, directives, result),
    }


def full_response(scenario: dict, directives: list[dict]) -> dict:
    """Convenience: run pipeline + assemble response. May raise."""
    result = run_pipeline(scenario, directives)
    return build_response(scenario, directives, result)


# ----------------------------------------------------------------------
# Standalone test harness
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from fixtures import SAMPLE_SCENARIO, SAMPLE_DIRECTIVES

    print("=" * 70)
    print("Happy path")
    print("=" * 70)
    response = full_response(SAMPLE_SCENARIO, SAMPLE_DIRECTIVES)
    for k in ("scenario_id", "total_cost_bdt", "peak_grid_kwh", "plan_summary"):
        print(f"  {k}: {response[k]}")

    print()
    print("=" * 70)
    print("Infeasible directive — must raise, must NOT fall back")
    print("=" * 70)
    bad = [{
        "note_index": 0, "applies": True,
        "directive_type": "minimum_battery_reserve",
        "structured_adjustment": {"hours": [5], "minimum_energy_kwh": 9999},
        "explanation": "",
    }]
    try:
        full_response(SAMPLE_SCENARIO, bad)
        print("  BUG: infeasible directive did not raise")
    except InfeasibleError as e:
        print(f"  Correctly raised InfeasibleError: {e}")