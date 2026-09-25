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


ONE INTERPRETATION PER NOTE
---------------------------
You must produce exactly one interpretation for every operator note.

The note_index must match the position of the note in the input list.

The first note has note_index=0.
The second note has note_index=1.
And so on.

Never skip a note.
Never create extra interpretations.


MISSING INFORMATION
-------------------
Never invent a numeric value.

If a note does not provide information required for one of the supported
directives, do not guess.

For example:

"Keep a minimum battery reserve."

does not provide a numerical reserve value.

Do NOT invent:

minimum_energy_kwh = 100

Instead, if the note cannot be safely interpreted without inventing
missing information, return:

applies = false
directive_type = "no_op"
structured_adjustment = null


NO-OP
-----
If a note does not affect the energy schedule, you MUST return:

- applies = false
- directive_type = "no_op"
- structured_adjustment = null

For every applicable directive, you MUST return:

- applies = true

Never omit the applies field.


STRUCTURED ADJUSTMENT FORMAT
----------------------------

IMPORTANT:

For time-based directives, DO NOT return start_hour or end_hour.

Instead, convert the time range into an explicit list of affected hours
and return them in the "hours" field.

The "hours" field MUST contain:

- only integers
- values from 0 through 23
- no duplicate hours
- hours in ascending order


SOLAR REDUCTION
---------------
Required structured_adjustment fields:

- hours
- factor

"factor" means the fraction of solar production remaining.

Examples:

- 80% reduction -> factor = 0.2
- 50% reduction -> factor = 0.5
- 20% reduction -> factor = 0.8
- 100% reduction -> factor = 0.0
- 0% reduction -> factor = 1.0

Example:

"Solar output will be reduced by 80% from 1 PM to 3 PM."

Return:

hours = [13, 14]
factor = 0.2

Do NOT return:

start_hour = 13
end_hour = 15


MINIMUM BATTERY RESERVE
-----------------------
Required structured_adjustment fields:

- hours
- minimum_energy_kwh

The note must provide the numerical reserve value.

Example:

"Keep at least 100 kWh in the battery from 6 PM to 9 PM."

Return:

hours = [18, 19, 20]
minimum_energy_kwh = 100

Do NOT invent a reserve value if the note does not provide one.


NO CHARGE WINDOW
----------------
Required structured_adjustment field:

- hours

Convert the stated time range into the affected hourly entries.

Example:

"Do not charge the battery between 2 PM and 4 PM."

Return:

hours = [14, 15]

Do NOT return:

start_hour = 14
end_hour = 16


NO DISCHARGE WINDOW
-------------------
Required structured_adjustment field:

- hours

Example:

"Do not discharge the battery from 8 PM to 10 PM."

Return:

hours = [20, 21]


MAX GRID WINDOW
---------------
Required structured_adjustment fields:

- hours
- max_grid_kwh

The note must provide the numerical grid limit.

Example:

"Keep grid usage below 300 kWh from 4 PM to 7 PM."

Return:

hours = [16, 17, 18]
max_grid_kwh = 300

Do NOT invent max_grid_kwh if the note does not provide a numerical value.


TIME RULES
----------
Hours use 24-hour notation.

Time ranges are interpreted as:

start hour inclusive
end hour exclusive

Convert the time range into the actual affected hourly entries.

Examples:

1 PM to 3 PM -> [13, 14]

2 PM to 4 PM -> [14, 15]

8 PM to 10 PM -> [20, 21]

12 AM to 2 AM -> [0, 1]

11 PM to midnight -> [23]

The ending hour itself is NOT included.

Therefore:

"from 1 PM to 3 PM"

means:

hours = [13, 14]

NOT:

hours = [13, 14, 15]


HOURS VALIDATION
----------------
Every "hours" list MUST:

- contain integers only
- contain values from 0 through 23
- contain no duplicates
- be sorted in ascending order

Examples of valid hours:

[13, 14]
[14, 15]
[0, 1, 2]
[23]

Examples of invalid hours:

[14, 13]
[13, 13]
[24]
[-1]


OUTPUT REQUIREMENTS
-------------------
Every interpretation MUST contain all of these fields:

- note_index
- applies
- directive_type
- structured_adjustment
- explanation

Never omit any field.

For no_op:

applies = false
directive_type = "no_op"
structured_adjustment = null

For every other directive:

applies = true
structured_adjustment must contain the required fields for that directive.

Do not use default values.

Do not invent numeric values.

If the note does not provide a required numeric value, use no_op
rather than guessing.
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


