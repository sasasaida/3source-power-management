from ollama import chat
from pydantic import ValidationError

from app.schemas import InterpretationResult


MODEL_NAME = "gemma4"


SYSTEM_PROMPT = """
You are an operator-note interpreter for an energy optimization system.

Your ONLY task is to interpret operator notes.

DO NOT:
- create an energy schedule
- optimize anything
- change demand
- change tariffs
- invent constraints
- invent values not supported by the note
- guess missing numeric values
- use 0 as a placeholder for a missing numeric value

The only supported directive types are:

1. solar_reduction
2. minimum_battery_reserve
3. no_charge_window
4. no_discharge_window
5. max_grid_window
6. no_op

You must produce exactly one interpretation for every operator note.

MISSING INFORMATION
-------------------
Never invent a numeric value.

If a note does not provide the information required for one of the
supported directives, do not guess.

For example:

"Keep a minimum battery reserve."

does not provide a numerical reserve value.

Do NOT invent:

minimum_energy_kwh = 100

Instead, determine whether the note can be interpreted as a supported
directive. If it cannot be safely interpreted without inventing missing
information, return:

applies = false
directive_type = "no_op"
structured_adjustment = null


Rules:

NO-OP
-----
If a note does not affect the energy schedule, you MUST return:

- applies = false
- directive_type = "no_op"
- structured_adjustment = null

For every applicable directive, you MUST return:

- applies = true

Never omit the applies field.

SOLAR REDUCTION
---------------
Use:
- start_hour
- end_hour
- factor

factor means the fraction of solar production remaining.

Examples:
- 80% reduction -> factor 0.2
- 50% reduction -> factor 0.5
- 20% reduction -> factor 0.8

MINIMUM BATTERY RESERVE
-----------------------
Use:
- minimum_energy_kwh

NO CHARGE WINDOW
----------------
Use:
- start_hour
- end_hour

NO DISCHARGE WINDOW
-------------------
Use:
- start_hour
- end_hour

MAX GRID WINDOW
---------------
Use:
- start_hour
- end_hour
- max_grid_kwh

TIME RULES
----------
Hours use 24-hour notation.

The start hour is inclusive.
The end hour is exclusive.

Therefore:
1 PM to 3 PM means start_hour=13 and end_hour=15.

Do not include 15 as an affected hour.

Every note must produce exactly one interpretation.

The note_index must match the position of the note in the input list.
The first note has note_index=0.
The second note has note_index=1.
And so on.

OUTPUT REQUIREMENTS
-------------------
Every interpretation MUST contain all of these fields:

- note_index
- applies
- directive_type
- structured_adjustment
- explanation

Never omit any field.

Do not use default values.

Do not invent numeric values.

If the note does not provide a required numeric value, do not guess one.
"""


def interpret_operator_notes(
    operator_notes: list[str],
) -> InterpretationResult:

    notes_text = "\n".join(
        f"Note {index}: {note}"
        for index, note in enumerate(operator_notes)
    )

    prompt = f"""
{SYSTEM_PROMPT}

Operator notes:

{notes_text}
"""

    response = chat(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        format=InterpretationResult.model_json_schema(),
    )


    try:
        result = InterpretationResult.model_validate_json(
            response.message.content
        )
    except ValidationError as exc:
        raise ValueError(
            "Ollama returned invalid directive data."
        ) from exc

    validate_interpretation_result(
        result,
        operator_notes,
    )

    return result


def validate_interpretation_result(
    result: InterpretationResult,
    operator_notes: list[str],
) -> None:

    if len(result.interpretations) != len(operator_notes):
        raise ValueError(
            "The LLM must return exactly one interpretation "
            "for every operator note."
        )

    expected_indexes = set(range(len(operator_notes)))

    actual_indexes = {
        interpretation.note_index
        for interpretation in result.interpretations
    }

    if actual_indexes != expected_indexes:
        raise ValueError(
            "The returned note_index values do not match "
            "the supplied operator notes."
        )

    for interpretation in result.interpretations:

        adjustment = interpretation.structured_adjustment

        if hasattr(adjustment, "start_hour"):
            if adjustment.start_hour >= adjustment.end_hour:
                raise ValueError(
                    "Invalid time window returned by the LLM."
                )

        if hasattr(adjustment, "factor"):
            if not 0 <= adjustment.factor <= 1:
                raise ValueError(
                    "Solar reduction factor must be between 0 and 1."
                )

        if interpretation.directive_type == "no_op":

            if interpretation.applies is not False:
                raise ValueError(
                    "no_op directive must have applies=false."
                )

            if interpretation.structured_adjustment is not None:
                raise ValueError(
                    "no_op directive must have no adjustment."
                )

        else:

            if interpretation.applies is not True:
                raise ValueError(
                    "Applicable directives must have applies=true."
                )

            if interpretation.structured_adjustment is None:
                raise ValueError(
                    "Applicable directives must have an adjustment."
                )