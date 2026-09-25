from fastapi import FastAPI, HTTPException

from app.schemas import EnergyRequest
from app.llm.interpreter import interpret_operator_notes
from app.guardrails.validator import validate_interpretations

from pipeline import full_response
from optimizer import InfeasibleError


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize-energy")
def optimize_energy(request: EnergyRequest):
    try:
        # 1. Convert the human notes into structured directives
        interpretation_result = interpret_operator_notes(
            request.operator_notes
        )

        # 2. Validate the LLM output deterministically
        validated_directives = validate_interpretations(
            interpretations=interpretation_result.interpretations,
            number_of_notes=len(request.operator_notes),
            battery_capacity_kwh=request.battery.capacity_kwh,
        )

        # 3. Convert Pydantic models into normal dictionaries
        directives = [
            directive.model_dump()
            for directive in validated_directives
        ]

        # 4. Convert the request into the dictionary format
        #    expected by the optimizer/pipeline
        scenario = request.model_dump()

        # 5. Run optimizer + final replay validator
        return full_response(scenario, directives)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except InfeasibleError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal server error.",
        ) from exc