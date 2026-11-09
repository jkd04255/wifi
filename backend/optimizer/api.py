"""POST /optimize — 4번 독립 API. RSSI는 2번/3번이 외부에서 공급한다."""
from fastapi import FastAPI, HTTPException
from .core import CandidateSearchRequest, OptimizeRequest, generate_candidate_positions, optimize

app = FastAPI(
    title="Wi-Fi Placement Optimizer (team member 4)",
    description="Feasibility and importance-weighted optimizer; does not compute or measure RSSI.",
    version="0.2.0",
)

@app.get("/health")
def health():
    return {"status": "ok", "module": "optimizer", "signalSource": "external_required"}

@app.post("/optimize")
def optimize_endpoint(request: OptimizeRequest):
    try:
        return optimize(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/candidate-locations")
def candidates_endpoint(request: CandidateSearchRequest):
    try:
        return generate_candidate_positions(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
