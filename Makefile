.PHONY: qa-fixtures qa-fixtures-json qa-golden qa-sessions qa-session-golden qa-session-matrix qa-rc qa-all py-compile

qa-fixtures:
	python3 backend/scripts/run_scenario_fixture_checks.py

qa-fixtures-json:
	python3 backend/scripts/run_scenario_fixture_checks.py --json

qa-golden:
	python3 backend/scripts/run_golden_path_check.py

qa-sessions:
	python3 -m unittest backend.tests.test_session_manager -v
	python3 -m unittest backend.tests.test_sessions_api -v
	python3 -m unittest backend.tests.test_legacy_api_session_sync -v

qa-session-golden:
	python3 backend/scripts/run_session_golden_check.py

qa-session-matrix:
	python3 backend/scripts/run_session_fixture_matrix_check.py

qa-rc:
	python3 backend/scripts/run_rc_stability_check.py

py-compile:
	python3 -m py_compile \
		backend/app/contracts.py \
		backend/app/api/analyze.py \
		backend/app/api/sessions.py \
		backend/app/api/debug.py \
		backend/app/api/ws.py \
		backend/app/models/session.py \
		backend/app/models/next_step.py \
		backend/app/models/feedback.py \
		backend/app/orchestrator/session_manager.py \
		backend/app/orchestrator/session_provider.py \
		backend/app/orchestrator/session_store_port.py \
		backend/app/storage/log_store.py \
		backend/app/storage/log_store_port.py \
		backend/app/services/prompt_builder.py \
		backend/app/services/realtime_hub.py \
		backend/app/services/step_planner.py \
		backend/app/services/next_step_service.py \
		backend/scripts/run_scenario_fixture_checks.py \
		backend/scripts/run_golden_path_check.py \
		backend/scripts/run_session_golden_check.py \
		backend/scripts/run_session_fixture_matrix_check.py \
		backend/scripts/run_rc_stability_check.py

qa-all: py-compile qa-fixtures qa-sessions qa-session-golden qa-session-matrix qa-golden qa-rc
	@echo "QA all passed."
