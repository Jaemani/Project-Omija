.PHONY: dev build test check

# Live dev server: rebuild pages on source change + browser auto-reload.
dev:
	uv run python scripts/serve.py

# Regenerate every demo page once.
build:
	uv run python scripts/omija_console_home.py
	uv run python scripts/omija_demo.py
	uv run python scripts/data_coverage_map.py
	uv run python scripts/program_threat_view.py

test:
	uv run pytest -q

# Pipeline + ranking + readiness verification battery.
check:
	uv run pytest -q
	uv run python scripts/p3_rank.py
	uv run python scripts/early_warning_readiness.py
