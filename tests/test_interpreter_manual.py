from app.llm.interpreter import interpret_operator_notes
from app.guardrails.validator import validate_interpretations


def main() -> None:
    notes = [
        "Do not charge the battery between 2 PM and 4 PM.",
        "Solar output will drop to about 20% from 1 PM to 3 PM." ,
        "Keep at least 120 kWh in reserve from 6 PM until 9 PM." ,
        "Please keep the facility clean.",
    ]

    result = interpret_operator_notes(notes)
    validated = validate_interpretations(
        result.interpretations,
        len(notes),
        battery_capacity_kwh=500,
    )

    print("\nSUCCESS")
    print("=" * 50)

    for interpretation in validated:
        print()
        print("Note:", interpretation.note_index)
        print("Applies:", interpretation.applies)
        print("Directive:", interpretation.directive_type)
        print("Adjustment:", interpretation.structured_adjustment)
        print("Explanation:", interpretation.explanation)


if __name__ == "__main__":
    main()