from abc import ABC, abstractmethod

from app.contracts import AnalyzeRequest, HighlightDto, NextStepResponse, RectDto


class StepPlanner(ABC):
    @abstractmethod
    def analyze(self, request: AnalyzeRequest) -> NextStepResponse:
        raise NotImplementedError


class MockStepPlanner(StepPlanner):
    def analyze(self, request: AnalyzeRequest) -> NextStepResponse:
        normalized_task = request.task_text.strip()
        instruction = (
            f"请先确认当前窗口与任务“{normalized_task}”相关，然后点击继续。"
        )

        return NextStepResponse(
            session_id="mock-session-001",
            step_id="step-001",
            instruction=instruction,
            action_type="confirm",
            requires_user_action=True,
            highlight=HighlightDto(
                rect=RectDto(
                    x=640,
                    y=320,
                    width=280,
                    height=120,
                )
            ),
        )
