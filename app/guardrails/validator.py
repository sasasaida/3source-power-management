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


def validate_hours(hours: list[int]) -> None:
    """Validate that hours are unique integers from 0 to 23 in ascending order."""

    if not isinstance(hours, list):
        raise ValueError("hours must be a list")

    if any(not isinstance(hour, int) for hour in hours):
        raise ValueError("hours must contain only integers")

    if any(hour < 0 or hour > 23 for hour in hours):
        raise ValueError("hours must be between 0 and 23")

    if len(hours) != len(set(hours)):
        raise ValueError("hours must be unique")

    if hours != sorted(hours):
        raise ValueError("hours must be in ascending order")


def validate_solar_reduction(
    directive: SolarReductionDirective,
) -> SolarReductionDirective:

    adjustment = directive.structured_adjustment

    validate_hours(adjustment.hours)

    if not math.isfinite(adjustment.factor):
        raise ValueError("solar reduction factor must be finite")

    if not 0 <= adjustment.factor <= 1:
        raise ValueError("solar reduction factor must be between 0 and 1")

    return directive


def validate_minimum_battery_reserve(
    directive: MinimumBatteryReserveDirective,
    battery_capacity_kwh: float,
) -> MinimumBatteryReserveDirective:

    adjustment = directive.structured_adjustment

    validate_hours(adjustment.hours)

    reserve = adjustment.minimum_energy_kwh

    if not math.isfinite(reserve):
        raise ValueError("minimum battery reserve must be finite")

    if reserve < 0:
        raise ValueError("minimum battery reserve cannot be negative")

    if reserve > battery_capacity_kwh:
        raise ValueError(
            "minimum battery reserve cannot exceed battery capacity"
        )

    return directive


def validate_no_charge_window(
    directive: NoChargeWindowDirective,
) -> NoChargeWindowDirective:

    validate_hours(directive.structured_adjustment.hours)

    return directive


def validate_no_discharge_window(
    directive: NoDischargeWindowDirective,
) -> NoDischargeWindowDirective:

    validate_hours(directive.structured_adjustment.hours)

    return directive


def validate_max_grid_window(
    directive: MaxGridWindowDirective,
) -> MaxGridWindowDirective:

    adjustment = directive.structured_adjustment

    validate_hours(adjustment.hours)

    max_grid = adjustment.max_grid_kwh

    if not math.isfinite(max_grid):
        raise ValueError("maximum grid value must be finite")

    if max_grid < 0:
        raise ValueError("maximum grid value cannot be negative")

    return directive


def validate_no_op(directive: NoOpDirective) -> NoOpDirective:

    if directive.applies is not False:
        raise ValueError("no_op directive must have applies=false")

    if directive.structured_adjustment is not None:
        raise ValueError(
            "no_op directive must have structured_adjustment=null"
        )

    return directive


def validate_applies_semantics(
    directive: DirectiveInterpretation,
) -> None:

    if directive.directive_type == "no_op":

        if directive.applies is not False:
            raise ValueError(
                "no_op directive must have applies=false"
            )

        if directive.structured_adjustment is not None:
            raise ValueError(
                "no_op directive must have structured_adjustment=null"
            )

    else:

        if directive.applies is not True:
            raise ValueError(
                "non-no_op directive must have applies=true"
            )

        if directive.structured_adjustment is None:
            raise ValueError(
                "non-no_op directive must have structured_adjustment"
            )


def validate_directive(
    directive: DirectiveInterpretation,
    battery_capacity_kwh: float,
) -> DirectiveInterpretation:

    validate_applies_semantics(directive)

    if isinstance(directive, SolarReductionDirective):
        return validate_solar_reduction(directive)

    if isinstance(directive, MinimumBatteryReserveDirective):
        return validate_minimum_battery_reserve(
            directive,
            battery_capacity_kwh,
        )

    if isinstance(directive, NoChargeWindowDirective):
        return validate_no_charge_window(directive)

    if isinstance(directive, NoDischargeWindowDirective):
        return validate_no_discharge_window(directive)

    if isinstance(directive, MaxGridWindowDirective):
        return validate_max_grid_window(directive)

    if isinstance(directive, NoOpDirective):
        return validate_no_op(directive)

    raise ValueError(
        f"Unsupported directive type: {directive.directive_type}"
    )


def validate_interpretations(
    interpretations: list[DirectiveInterpretation],
    number_of_notes: int,
    battery_capacity_kwh: float,
) -> list[DirectiveInterpretation]:

    # Every operator note must have exactly one interpretation.
    if len(interpretations) != number_of_notes:
        raise ValueError(
            f"Expected {number_of_notes} interpretations, "
            f"got {len(interpretations)}"
        )

    seen_note_indices = set()
    validated = []

    for directive in interpretations:

        note_index = directive.note_index

        if not isinstance(note_index, int):
            raise ValueError("note_index must be an integer")

        if not 0 <= note_index < number_of_notes:
            raise ValueError(
                f"note_index {note_index} does not refer to an existing note"
            )

        if note_index in seen_note_indices:
            raise ValueError(
                f"Duplicate note_index: {note_index}"
            )

        seen_note_indices.add(note_index)

        validated_directive = validate_directive(
            directive,
            battery_capacity_kwh,
        )

        validated.append(validated_directive)

    # Return interpretations in the same order as the operator notes.
    validated.sort(key=lambda directive: directive.note_index)

    return validated