import math

from app.schemas import (
    DirectiveInterpretation,
    SolarReductionDirective,
    MinimumBatteryReserveDirective,
    NoChargeWindowDirective,
    NoDischargeWindowDirective,
    MaxGridWindowDirective,
    NoOpDirective,
)


def validate_hour(hour: int) -> None:
    """Validate that an hour is an integer from 0 through 23."""

    if not isinstance(hour, int):
        raise ValueError(
            f"Hour must be an integer, got {type(hour).__name__}."
        )

    if not 0 <= hour <= 23:
        raise ValueError(
            f"Invalid hour: {hour}. "
            "Hour must be between 0 and 23."
        )


def validate_time_window(
    start_hour: int,
    end_hour: int,
) -> None:
    """Validate a [start, end) hourly window."""

    validate_hour(start_hour)
    validate_hour(end_hour)

    if start_hour >= end_hour:
        raise ValueError(
            f"Invalid time window: {start_hour} to {end_hour}. "
            "start_hour must be less than end_hour."
        )


def validate_solar_reduction(
    directive: SolarReductionDirective,
) -> None:
    adjustment = directive.structured_adjustment

    validate_time_window(
        adjustment.start_hour,
        adjustment.end_hour,
    )

    # Contest requirement: 0 <= factor <= 1
    if not 0 <= adjustment.factor <= 1:
        raise ValueError(
            f"Invalid solar factor: {adjustment.factor}. "
            "Factor must be between 0 and 1 inclusive."
        )

    if not math.isfinite(adjustment.factor):
        raise ValueError(
            "Solar factor must be finite."
        )


def validate_minimum_battery_reserve(
    directive: MinimumBatteryReserveDirective,
    battery_capacity_kwh: float,
) -> None:
    adjustment = directive.structured_adjustment

    reserve = adjustment.minimum_energy_kwh

    if not math.isfinite(reserve):
        raise ValueError(
            "Battery reserve must be finite."
        )

    if reserve < 0:
        raise ValueError(
            "Battery reserve cannot be negative."
        )

    if reserve > battery_capacity_kwh:
        raise ValueError(
            f"Battery reserve ({reserve}) cannot exceed "
            f"battery capacity ({battery_capacity_kwh})."
        )


def validate_no_charge_window(
    directive: NoChargeWindowDirective,
) -> None:
    adjustment = directive.structured_adjustment

    validate_time_window(
        adjustment.start_hour,
        adjustment.end_hour,
    )


def validate_no_discharge_window(
    directive: NoDischargeWindowDirective,
) -> None:
    adjustment = directive.structured_adjustment

    validate_time_window(
        adjustment.start_hour,
        adjustment.end_hour,
    )


def validate_max_grid_window(
    directive: MaxGridWindowDirective,
) -> None:
    adjustment = directive.structured_adjustment

    validate_time_window(
        adjustment.start_hour,
        adjustment.end_hour,
    )

    max_grid = adjustment.max_grid_kwh

    if not math.isfinite(max_grid):
        raise ValueError(
            "max_grid_kwh must be finite."
        )

    if max_grid < 0:
        raise ValueError(
            "max_grid_kwh cannot be negative."
        )


def validate_no_op(
    directive: NoOpDirective,
) -> None:
    if directive.applies is not False:
        raise ValueError(
            "no_op must have applies=False."
        )

    if directive.structured_adjustment is not None:
        raise ValueError(
            "no_op must have structured_adjustment=None."
        )


def validate_applies_semantics(
    directive: DirectiveInterpretation,
) -> None:
    """Every directive must follow the contest applies rules."""

    if directive.directive_type == "no_op":

        if directive.applies is not False:
            raise ValueError(
                "no_op must have applies=False."
            )

        if directive.structured_adjustment is not None:
            raise ValueError(
                "no_op must have structured_adjustment=None."
            )

    else:

        if directive.applies is not True:
            raise ValueError(
                f"{directive.directive_type} must have applies=True."
            )

        if directive.structured_adjustment is None:
            raise ValueError(
                f"{directive.directive_type} requires "
                "structured_adjustment."
            )


def validate_directive(
    directive: DirectiveInterpretation,
    battery_capacity_kwh: float,
) -> DirectiveInterpretation:

    # First check the universal applies rules.
    validate_applies_semantics(directive)

    # Then validate the directive-specific data.
    if isinstance(directive, SolarReductionDirective):

        validate_solar_reduction(directive)

    elif isinstance(
        directive,
        MinimumBatteryReserveDirective,
    ):

        validate_minimum_battery_reserve(
            directive,
            battery_capacity_kwh,
        )

    elif isinstance(
        directive,
        NoChargeWindowDirective,
    ):

        validate_no_charge_window(directive)

    elif isinstance(
        directive,
        NoDischargeWindowDirective,
    ):

        validate_no_discharge_window(directive)

    elif isinstance(
        directive,
        MaxGridWindowDirective,
    ):

        validate_max_grid_window(directive)

    elif isinstance(directive, NoOpDirective):

        validate_no_op(directive)

    else:
        raise ValueError(
            f"Unsupported directive type: "
            f"{type(directive).__name__}"
        )

    return directive


def validate_interpretations(
    interpretations: list[DirectiveInterpretation],
    number_of_notes: int,
    battery_capacity_kwh: float,
) -> list[DirectiveInterpretation]:

    # ---------------------------------------------------------
    # 1. Every operator note must have exactly one interpretation
    # ---------------------------------------------------------

    if len(interpretations) != number_of_notes:
        raise ValueError(
            "Every operator note must have exactly one "
            "interpretation."
        )

    seen_note_indices: set[int] = set()

    validated: list[DirectiveInterpretation] = []

    for directive in interpretations:

        # -----------------------------------------------------
        # 2. note_index must identify an existing note
        # -----------------------------------------------------

        if not isinstance(directive.note_index, int):
            raise ValueError(
                "note_index must be an integer."
            )

        if not 0 <= directive.note_index < number_of_notes:
            raise ValueError(
                f"Invalid note_index: {directive.note_index}. "
                f"Valid range is 0 to {number_of_notes - 1}."
            )

        # -----------------------------------------------------
        # 3. Every note must appear exactly once
        # -----------------------------------------------------

        if directive.note_index in seen_note_indices:
            raise ValueError(
                f"Duplicate note_index: "
                f"{directive.note_index}"
            )

        seen_note_indices.add(directive.note_index)

        # -----------------------------------------------------
        # 4. Validate the actual directive
        # -----------------------------------------------------

        validated_directive = validate_directive(
            directive,
            battery_capacity_kwh,
        )

        validated.append(validated_directive)

    # ---------------------------------------------------------
    # 5. Make the result deterministic
    # ---------------------------------------------------------

    validated.sort(
        key=lambda directive: directive.note_index
    )

    return validated