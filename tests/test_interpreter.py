import pytest

from app.llm.interpreter import validate_interpretation_result
from app.schemas import InterpretationResult


def test_validate_interpretation_result_accepts_matching_indexes():
    result = InterpretationResult.model_validate(
        {
            "interpretations": [
                {
                    "note_index": 0,
                    "applies": True,
                    "directive_type": "minimum_battery_reserve",
                    "structured_adjustment": {
                        "minimum_energy_kwh": 100,
                    },
                    "explanation": "Maintain the requested reserve.",
                },
                {
                    "note_index": 1,
                    "applies": False,
                    "directive_type": "no_op",
                    "structured_adjustment": None,
                    "explanation": "This note does not affect scheduling.",
                },
            ]
        }
    )

    validate_interpretation_result(
        result,
        ["Keep at least 100 kWh in the battery.", "Keep the facility clean."],
    )


def test_validate_interpretation_result_rejects_missing_note():
    result = InterpretationResult.model_validate(
        {
            "interpretations": [
                {
                    "note_index": 0,
                    "applies": False,
                    "directive_type": "no_op",
                    "structured_adjustment": None,
                    "explanation": "No scheduling constraint was found.",
                },
            ]
        }
    )

    with pytest.raises(ValueError, match="exactly one interpretation"):
        validate_interpretation_result(result, ["First note.", "Second note."])