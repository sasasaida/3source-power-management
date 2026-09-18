from ollama import chat

from app.schemas import InterpretationResult


MODEL_NAME = "gemma4"


def interpret_operator_notes(
    operator_notes: list[str],
) -> InterpretationResult:

    prompt = f"""
You are an operator-note interpreter for an energy optimization system.

Your ONLY job is to interpret the operator notes.

Do NOT create an energy schedule.
Do NOT optimize anything.
Do NOT change demand.
Do NOT change tariffs.
Do NOT invent information.

The only supported directive types are:

1. solar_reduction
2. minimum_battery_reserve
3. no_charge_window
4. no_discharge_window
5. max_grid_window
6. no_op

You must produce exactly one interpretation for every operator note.

For a note that does not affect the energy schedule:
- applies = false
- directive_type = "no_op"
- structured_adjustment = null

For an applicable note:
- applies = true
- use exactly one of the supported directive types
- provide the relevant structured_adjustment

Time rules:
- Hours use 24-hour notation from 0 to 23.
- The start hour is inclusive.
- The end hour is exclusive.
- Therefore, 1 PM to 3 PM means hours [13, 14].

Solar reduction rule:
- structured_adjustment.factor means the fraction of solar production remaining.
- An 80 percent reduction means factor = 0.2.
- A 50 percent reduction means factor = 0.5.

Interpret each note according to its meaning.
Do not invent constraints that are not present in the note.

Operator notes:

{operator_notes}
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

    return InterpretationResult.model_validate_json(
        response.message.content
    )