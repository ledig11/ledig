from fastapi import APIRouter, Depends

from app.contracts import AnalyzeRequest, NextStepResponse
from app.services.step_planner import MockStepPlanner, StepPlanner

router = APIRouter()


def get_step_planner() -> StepPlanner:
    return MockStepPlanner()


@router.post("/analyze", response_model=NextStepResponse)
def analyze(
    request: AnalyzeRequest,
    step_planner: StepPlanner = Depends(get_step_planner),
) -> NextStepResponse:
    return step_planner.analyze(request)
