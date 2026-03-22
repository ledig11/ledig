.PHONY: qa-fixtures qa-fixtures-json qa-golden qa-all py-compile

qa-fixtures:
	python3 backend/scripts/run_scenario_fixture_checks.py

qa-fixtures-json:
	python3 backend/scripts/run_scenario_fixture_checks.py --json

qa-golden:
	python3 backend/scripts/run_golden_path_check.py

py-compile:
	python3 -m py_compile \
		backend/app/contracts.py \
		backend/app/api/analyze.py \
		backend/app/api/debug.py \
		backend/app/api/ws.py \
		backend/app/storage/log_store.py \
		backend/app/storage/log_store_port.py \
		backend/app/services/prompt_builder.py \
		backend/app/services/realtime_hub.py \
		backend/app/services/step_planner.py \
		backend/scripts/run_scenario_fixture_checks.py \
		backend/scripts/run_golden_path_check.py

qa-all: py-compile qa-fixtures qa-golden
	@echo "QA all passed."
