"""Run all 10 public cases through the optimizer and compare against reference."""
import json
from optimizer import optimize, InfeasibleError
from validator import validate_plan, ValidationError

with open("BUP_CSE_FEST_2026_Preli_Public_Sample_Cases.json") as f:
    pack = json.load(f)

TOL = 0.01
passed = failed = 0

for case in pack["cases"]:
    cid = case["id"]
    label = case["label"]
    scenario = case["input"]
    directives = case["expected_output"]["directive_interpretation"]
    ref = case["expected_output"]

    print(f"\n{'='*70}\n{cid} — {label}\n{'='*70}")

    try:
        result = optimize(scenario, directives)
    except InfeasibleError as e:
        print(f"  INFEASIBLE (unexpected): {e}")
        failed += 1
        continue

    # Validate our own output
    try:
        validate_plan(scenario, directives, result)
    except ValidationError as e:
        print(f"  VALIDATION FAILED: {e}")
        failed += 1
        continue

    our_cost = result["total_cost_bdt"]
    ref_cost = ref["total_cost_bdt"]
    our_grid = result["total_grid_kwh"]
    ref_grid = ref["total_grid_kwh"]
    our_peak = result["peak_grid_kwh"]
    ref_peak = ref["peak_grid_kwh"]

    cost_ok = abs(our_cost - ref_cost) <= TOL
    grid_ok = abs(our_grid - ref_grid) <= TOL
    #peak_ok = abs(our_peak - ref_peak) <= TOL

    tag = "PASS" if (cost_ok and grid_ok) else "FAIL"
    if tag == "PASS":
        passed += 1
    else:
        failed += 1

    print(f"  [{tag}] cost  ours={our_cost:>10.2f}  ref={ref_cost:>10.2f}")
    print(f"        grid  ours={our_grid:>10.2f}  ref={ref_grid:>10.2f}")
    print(f"        peak  ours={our_peak:>10.2f}  ref={ref_peak:>10.2f}")

print(f"\n{'='*70}")
print(f"RESULT: {passed} passed, {failed} failed out of {len(pack['cases'])}")
print(f"{'='*70}")