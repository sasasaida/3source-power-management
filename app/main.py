from fastapi import FastAPI

from app.schemas import EnergyRequest

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize-energy")
def optimize_energy(request: EnergyRequest):
    return {
        "scenario_id": request.scenario_id,
        "message": "Request received successfully"
    }