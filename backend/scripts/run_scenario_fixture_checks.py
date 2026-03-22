from __future__ import annotations

import argparse
import difflib
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Optional
from xml.etree import ElementTree as ET

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.contracts import AnalyzeRequest, NextStepResponse, SessionStateEntry
from app.services.prompt_builder import StepPlannerPromptBuilder
from app.services.step_planner import (
    MockStepPlanner,
    SettingsBluetoothScenarioPlanner,
    SettingsDisplayScenarioPlanner,
    SettingsNetworkScenarioPlanner,
    SettingsPersonalizationScenarioPlanner,
)


FIXTURE_DIR = BACKEND_DIR.parent / "fixtures" / "minimal"


@dataclass(frozen=True)
class FixtureCase:
    request_file: str
    expected_response_file: str
    incorrect_recovery_parent_action_type: Optional[str] = None


@dataclass(frozen=True)
class CaseResult:
    request_file: str
    scenario: str
    passed: bool
    expected_response_file: str
    expected: Optional[NextStepResponse] = None
    actual: Optional[NextStepResponse] = None
    mismatches: tuple[str, ...] = ()


def build_planner(session_state_reader=None):
    return SettingsPersonalizationScenarioPlanner(
        fallback_planner=SettingsDisplayScenarioPlanner(
            fallback_planner=SettingsNetworkScenarioPlanner(
                fallback_planner=SettingsBluetoothScenarioPlanner(
                    fallback_planner=MockStepPlanner(),
                    session_state_reader=session_state_reader,
                ),
                session_state_reader=session_state_reader,
            ),
            session_state_reader=session_state_reader,
        ),
        session_state_reader=session_state_reader,
    )


def load_request(filename: str) -> AnalyzeRequest:
    payload = json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))
    return AnalyzeRequest.model_validate(payload)


def load_expected_response(filename: str) -> NextStepResponse:
    payload = json.loads((FIXTURE_DIR / filename).read_text(encoding="utf-8"))
    return NextStepResponse.model_validate(payload)


def static_incorrect_state(
    request: AnalyzeRequest,
    current_action_type: str,
) -> SessionStateEntry:
    session_id = request.observation.session_id or "fixture-session"
    return SessionStateEntry(
        session_id=session_id,
        task_text=request.task_text,
        current_step_id="fixture-step",
        current_action_type=current_action_type,
        current_instruction="fixture-previous-step",
        last_feedback_type="incorrect",
        session_status="needs_review",
        planner_source="scenario",
        prompt_version="fixture",
        response_schema_version="next-step-response.v1",
        model_provider="openai",
        model_type="gpt-4.1",
        target_candidate_ui_path=None,
        target_candidate_label=None,
        last_planner_error_code=None,
        last_planner_error=None,
        completed_step_count=0,
        incorrect_feedback_count=1,
        reanalyze_feedback_count=0,
        last_foreground_window_title=request.observation.foreground_window_title,
        last_screenshot_ref="local://observation/fixture",
        last_updated_at_utc="2026-03-22T00:00:00Z",
    )


def assert_prompt_bundle(request: AnalyzeRequest) -> None:
    bundle = StepPlannerPromptBuilder().build(request)
    if bundle.prompt_version != StepPlannerPromptBuilder.PROMPT_VERSION:
        raise AssertionError(
            f"Unexpected prompt version: {bundle.prompt_version} "
            f"(expected {StepPlannerPromptBuilder.PROMPT_VERSION})"
        )
    if "Task Intent Tags:" not in bundle.user_prompt:
        raise AssertionError("Prompt is missing Task Intent Tags block")
    if "Action Constraints:" not in bundle.user_prompt:
        raise AssertionError("Prompt is missing Action Constraints block")


def collect_response_mismatches(
    *,
    expected: NextStepResponse,
    actual: NextStepResponse,
) -> list[str]:
    mismatches: list[str] = []

    if actual.session_id != expected.session_id:
        mismatches.append(f"session_id: {actual.session_id} != {expected.session_id}")
    if actual.step_id != expected.step_id:
        mismatches.append(f"step_id: {actual.step_id} != {expected.step_id}")
    if actual.action_type != expected.action_type:
        mismatches.append(f"action_type: {actual.action_type} != {expected.action_type}")
    if actual.requires_user_action != expected.requires_user_action:
        mismatches.append(
            f"requires_user_action: {actual.requires_user_action} != {expected.requires_user_action}"
        )
    if actual.instruction != expected.instruction:
        mismatches.append("instruction text mismatch")

    a_rect = actual.highlight.rect
    e_rect = expected.highlight.rect
    actual_rect = (a_rect.x, a_rect.y, a_rect.width, a_rect.height)
    expected_rect = (e_rect.x, e_rect.y, e_rect.width, e_rect.height)
    if actual_rect != expected_rect:
        mismatches.append(f"highlight.rect: {actual_rect} != {expected_rect}")

    return mismatches


def infer_scenario_name(request_file: str) -> str:
    normalized = request_file.casefold()
    if "bluetooth" in normalized:
        return "bluetooth"
    if "network" in normalized:
        return "network"
    if "display" in normalized:
        return "display"
    if "personalization" in normalized:
        return "personalization"
    return "general"


def run_case(case: FixtureCase) -> CaseResult:
    request = load_request(case.request_file)
    expected = load_expected_response(case.expected_response_file)
    assert_prompt_bundle(request)

    def reader(session_id: str) -> Optional[SessionStateEntry]:
        if case.incorrect_recovery_parent_action_type is None:
            return None
        recovery_state = static_incorrect_state(
            request=request,
            current_action_type=case.incorrect_recovery_parent_action_type,
        )
        if recovery_state.session_id == session_id:
            return recovery_state
        return None

    planner = build_planner(session_state_reader=reader)
    actual = planner.analyze(request).response
    mismatches = collect_response_mismatches(
        expected=expected,
        actual=actual,
    )
    return CaseResult(
        request_file=case.request_file,
        scenario=infer_scenario_name(case.request_file),
        passed=len(mismatches) == 0,
        expected_response_file=case.expected_response_file,
        expected=expected,
        actual=actual,
        mismatches=tuple(mismatches),
    )


def to_pretty_json(response: NextStepResponse) -> str:
    return json.dumps(response.model_dump(), ensure_ascii=False, indent=2)


def build_fixture_replace_hint(result: CaseResult) -> str:
    if result.actual is None:
        return ""
    return (
        "suggested update:\n"
        f"  replace `{result.expected_response_file}` with the following JSON:\n"
        f"{to_pretty_json(result.actual)}"
    )


def build_response_diff(result: CaseResult, max_lines: int = 40) -> list[str]:
    if result.expected is None or result.actual is None:
        return []

    expected_lines = to_pretty_json(result.expected).splitlines()
    actual_lines = to_pretty_json(result.actual).splitlines()
    diff_lines = list(
        difflib.unified_diff(
            expected_lines,
            actual_lines,
            fromfile=f"expected/{result.expected_response_file}",
            tofile=f"actual/{result.expected_response_file}",
            lineterm="",
        )
    )
    if len(diff_lines) <= max_lines:
        return diff_lines
    return diff_lines[:max_lines] + ["... (diff truncated)"]


def print_results(results: list[CaseResult]) -> None:
    by_scenario: dict[str, list[CaseResult]] = {}
    for result in results:
        by_scenario.setdefault(result.scenario, []).append(result)

    total_passed = 0
    total_failed = 0
    for scenario in sorted(by_scenario.keys()):
        scenario_results = by_scenario[scenario]
        passed_count = sum(1 for item in scenario_results if item.passed)
        failed_items = [item for item in scenario_results if not item.passed]
        failed_count = len(failed_items)
        total_passed += passed_count
        total_failed += failed_count
        print(f"[{scenario}] passed={passed_count} failed={failed_count}")
        for failed in failed_items:
            print(f"  - {failed.request_file}")
            for mismatch in failed.mismatches:
                print(f"    * {mismatch}")
            diff_lines = build_response_diff(failed)
            if diff_lines:
                print("    diff:")
                for line in diff_lines:
                    print(f"      {line}")
            hint = build_fixture_replace_hint(failed)
            if hint:
                for hint_line in hint.splitlines():
                    print(f"    {hint_line}")

    print(f"Summary: passed={total_passed} failed={total_failed}")
    if total_failed > 0:
        raise AssertionError("Scenario fixture checks failed. See mismatch details above.")


def print_results_json(results: list[CaseResult]) -> None:
    by_scenario: dict[str, list[CaseResult]] = {}
    for result in results:
        by_scenario.setdefault(result.scenario, []).append(result)

    scenario_summary: dict[str, dict[str, int]] = {}
    for scenario, scenario_results in by_scenario.items():
        scenario_summary[scenario] = {
            "passed": sum(1 for item in scenario_results if item.passed),
            "failed": sum(1 for item in scenario_results if not item.passed),
        }

    output = {
        "summary": {
            "passed": sum(1 for item in results if item.passed),
            "failed": sum(1 for item in results if not item.passed),
        },
        "scenarios": scenario_summary,
        "results": [
            {
                "request_file": item.request_file,
                "expected_response_file": item.expected_response_file,
                "scenario": item.scenario,
                "passed": item.passed,
                "mismatches": list(item.mismatches),
                "expected": item.expected.model_dump() if item.expected is not None else None,
                "actual": item.actual.model_dump() if item.actual is not None else None,
                "suggested_fixture_replacement_json": (
                    item.actual.model_dump() if (not item.passed and item.actual is not None) else None
                ),
            }
            for item in results
        ],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if output["summary"]["failed"] > 0:
        raise AssertionError("Scenario fixture checks failed. See JSON details.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scenario fixture regression checks.")
    parser.add_argument(
        "--scenario",
        choices=["bluetooth", "network", "display", "personalization", "all"],
        default="all",
        help="Run only one scenario group.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    parser.add_argument(
        "--junit-output",
        default=None,
        help="Optional path to write JUnit XML result.",
    )
    return parser.parse_args()


def write_junit_xml(results: list[CaseResult], output_path: str) -> None:
    tests = len(results)
    failures = sum(1 for item in results if not item.passed)
    suite = ET.Element(
        "testsuite",
        attrib={
            "name": "scenario_fixture_checks",
            "tests": str(tests),
            "failures": str(failures),
            "errors": "0",
        },
    )

    for item in results:
        testcase = ET.SubElement(
            suite,
            "testcase",
            attrib={
                "classname": f"scenario.{item.scenario}",
                "name": item.request_file,
            },
        )
        if not item.passed:
            failure = ET.SubElement(
                testcase,
                "failure",
                attrib={"message": "fixture mismatch"},
            )
            lines = [f"request_file={item.request_file}"] + [f"- {m}" for m in item.mismatches]
            failure.text = "\n".join(lines)

    tree = ET.ElementTree(suite)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    args = parse_args()
    cases = [
        FixtureCase(
            request_file="analyze-request-settings-bluetooth.json",
            expected_response_file="next-step-response-settings-bluetooth.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-bluetooth-page.json",
            expected_response_file="next-step-response-settings-bluetooth-page.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-network.json",
            expected_response_file="next-step-response-settings-network.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-network-page.json",
            expected_response_file="next-step-response-settings-network-page.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-display.json",
            expected_response_file="next-step-response-settings-display.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-display-page.json",
            expected_response_file="next-step-response-settings-display-page.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-personalization.json",
            expected_response_file="next-step-response-settings-personalization.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-personalization-page.json",
            expected_response_file="next-step-response-settings-personalization-page.json",
        ),
        FixtureCase(
            request_file="analyze-request-settings-network-recovery.json",
            expected_response_file="next-step-response-settings-network-recovery.json",
            incorrect_recovery_parent_action_type="open_network_settings",
        ),
        FixtureCase(
            request_file="analyze-request-settings-display-recovery.json",
            expected_response_file="next-step-response-settings-display-recovery.json",
            incorrect_recovery_parent_action_type="open_display_settings",
        ),
        FixtureCase(
            request_file="analyze-request-settings-personalization-recovery.json",
            expected_response_file="next-step-response-settings-personalization-recovery.json",
            incorrect_recovery_parent_action_type="open_personalization_settings",
        ),
    ]

    if args.scenario != "all":
        cases = [
            case
            for case in cases
            if infer_scenario_name(case.request_file) == args.scenario
        ]

    if not cases:
        raise AssertionError("No fixture cases selected.")

    results: list[CaseResult] = []
    for case in cases:
        results.append(run_case(case))

    if args.json:
        print_results_json(results)
    else:
        print_results(results)

    if args.junit_output:
        write_junit_xml(results, args.junit_output)
        print(f"JUnit report written: {args.junit_output}")

    print("Scenario fixture checks passed.")


if __name__ == "__main__":
    main()
