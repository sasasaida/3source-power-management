from ollama import chat
from pydantic import ValidationError

from app.schemas import InterpretationResult


MODEL_NAME = "gemma4"


SYSTEM_PROMPT = """
You are an energy-management instruction interpreter.

Your ONLY job is to convert each operator note into exactly one structured directive.
Do NOT optimize schedules, make energy decisions, or invent values.

Supported directive types:

1. solar_reduction
   {"hours": [...], "factor": 0..1}
   Example: "reduce solar by 80%" -> factor = 0.2

2. minimum_battery_reserve
   {"hours": [...], "minimum_energy_kwh": number}

3. no_charge_window
   {"hours": [...]}

4. no_discharge_window
   {"hours": [...]}

5. max_grid_window
   {"hours": [...], "max_grid_kwh": number}

6. no_op
   applies=false
   structured_adjustment=null
   Use when the note does not affect energy scheduling.

RULES:

- Return exactly one interpretation for every operator note.
- note_index must match the note's zero-based index.
- For every applicable directive, applies=true.
- For no_op, applies=false and structured_adjustment=null.
- Never invent numeric values.
- Never change demand, tariff, battery capacity, or other scenario parameters.
- Use only information explicitly stated or directly implied by the note.
- hours must contain unique integers from 0 to 23 in ascending order.
- Time ranges use start-inclusive, end-exclusive semantics:
  1 PM-3 PM -> [13,14]
  2 PM-4 PM -> [14,15]
  11 PM-midnight -> [23]
  12 AM-2 AM -> [0,1]
- "at all times" means [0,1,2,...,23].
- For percentages, convert the remaining percentage to factor:
  80% reduction -> 0.2
  50% reduction -> 0.5
- Do not add fields that are not required by the directive type.
- Keep explanations short and factual.

Return JSON matching the required schema.
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

    return result


