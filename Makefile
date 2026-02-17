# Haytham Development Makefile
# Quick iteration commands for development workflow

.PHONY: help run burr stage resume reset test test-unit test-e2e lint format clean jaeger-up jaeger-down test-agents test-agents-quick test-agents-verbose record-fixtures clear-from clear-from-preview stages-list view-stage stages

# Default target
help:
	@echo "Haytham Development Commands"
	@echo ""
	@echo "Application:"
	@echo "  make run              - Start the Streamlit application"
	@echo "  make burr             - Start Burr tracking UI"
	@echo ""
	@echo "Observability:"
	@echo "  make jaeger-up        - Start Jaeger for trace visualization"
	@echo "  make jaeger-down      - Stop Jaeger"
	@echo "  make jaeger-ui        - Open Jaeger UI in browser"
	@echo ""
	@echo "Workflow Execution:"
	@echo "  make stage STAGE=...  - Run a single stage (e.g., STAGE=idea-analysis)"
	@echo "  make resume           - Resume workflow from last checkpoint"
	@echo "  make reset            - Clear session and start fresh"
	@echo "  make clear-from STAGE=... - Clear outputs from stage onward (for re-run)"
	@echo "  make stages-list      - List all stages in order"
	@echo ""
	@echo "Testing:"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-e2e         - Run end-to-end tests"
	@echo ""
	@echo "Agent Quality (LLM-as-Judge):"
	@echo "  make test-agents          - Evaluate all pilot agents (4 agents x 2 ideas)"
	@echo "  make test-agents-quick    - Quick: concept_expansion x T1 only"
	@echo "  make test-agents-verbose  - Full evaluation with judge reasoning"
	@echo "  make record-fixtures IDEA_ID=T1 - Record session outputs as test fixtures"
	@echo ""
	@echo "Development:"
	@echo "  make lint             - Run linter (ruff check)"
	@echo "  make format           - Format code (ruff format)"
	@echo "  make clean            - Clean temporary files"
	@echo ""
	@echo "Examples:"
	@echo "  make stage STAGE=idea-analysis"
	@echo "  make clear-from STAGE=market-context"

# =============================================================================
# Application
# =============================================================================

run:
	uv run streamlit run frontend_streamlit/Haytham.py

burr:
	uv run burr

# =============================================================================
# Observability
# =============================================================================

# Start Jaeger for trace visualization
jaeger-up:
	@echo "Starting Jaeger..."
	docker compose up -d
	@echo ""
	@echo "Jaeger is running!"
	@echo "  - UI: http://localhost:16686"
	@echo "  - OTLP endpoint: http://localhost:4317"
	@echo ""
	@echo "To enable tracing, set in .env:"
	@echo "  OTEL_SDK_DISABLED=false"

# Stop Jaeger
jaeger-down:
	@echo "Stopping Jaeger..."
	docker compose down
	@echo "Jaeger stopped."

# Open Jaeger UI
jaeger-ui:
	@echo "Opening Jaeger UI..."
	open http://localhost:16686 2>/dev/null || xdg-open http://localhost:16686 2>/dev/null || echo "Visit: http://localhost:16686"

# =============================================================================
# Workflow Execution
# =============================================================================

# Run a single stage
# Usage: make stage STAGE=idea-analysis
stage:
ifndef STAGE
	$(error STAGE is required. Usage: make stage STAGE=idea-analysis)
endif
	@echo "Running stage: $(STAGE)"
	uv run python -c "from haytham.workflow.stage_executor import execute_stage; \
		from burr.core import State; \
		from haytham.session.session_manager import SessionManager; \
		sm = SessionManager(); \
		state = State({'system_goal': sm.get_system_goal() or '', 'session_manager': sm}); \
		execute_stage('$(STAGE)', state)"

# Resume from last checkpoint
resume:
	@echo "Resuming workflow from last checkpoint..."
	uv run python -c "from haytham.session.session_manager import SessionManager; \
		sm = SessionManager(); \
		session = sm.load_session(); \
		if session: \
			print(f'Session status: {session.get(\"status\")}'); \
			print(f'Completed stages: {session.get(\"completed_stages\", [])}'); \
			print(f'Current stage: {session.get(\"current_stage\", \"none\")}'); \
		else: \
			print('No active session found. Use make run to start.')"

# Clear session and start fresh
reset:
	@echo "Clearing session..."
	rm -rf session/*
	@echo "Session cleared. Ready to start fresh."

# Clear stages from a given stage onward (for re-running)
# Usage: make clear-from STAGE=market-context
clear-from:
ifndef STAGE
	$(error STAGE is required. Usage: make clear-from STAGE=market-context)
endif
	uv run python -c "import shutil; \
		from pathlib import Path; \
		from haytham.workflow.stage_registry import get_stage_registry; \
		registry = get_stage_registry(); \
		all_slugs = [m.slug for m in registry.all_stages()]; \
		start = '$(STAGE)'; \
		assert start in all_slugs, f'{start} not found. Use: make stages-list'; \
		idx = all_slugs.index(start); \
		to_clear = all_slugs[idx:]; \
		session = Path('session'); \
		cleared = []; \
		[cleared.append(s) or shutil.rmtree(session / s) for s in to_clear if (session / s).exists()]; \
		print(f'Cleared {len(cleared)} stage(s): {cleared}' if cleared else 'Nothing to clear.')"

# Preview what would be cleared (dry run)
# Usage: make clear-from-preview STAGE=market-context
clear-from-preview:
ifndef STAGE
	$(error STAGE is required. Usage: make clear-from-preview STAGE=market-context)
endif
	uv run python -c "from pathlib import Path; \
		from haytham.workflow.stage_registry import get_stage_registry; \
		registry = get_stage_registry(); \
		all_slugs = [m.slug for m in registry.all_stages()]; \
		start = '$(STAGE)'; \
		assert start in all_slugs, f'{start} not found. Use: make stages-list'; \
		idx = all_slugs.index(start); \
		to_clear = all_slugs[idx:]; \
		session = Path('session'); \
		existing = [s for s in to_clear if (session / s).exists()]; \
		print('Would clear:'); \
		[print(f'  - {s}') for s in existing] if existing else print('  (nothing to clear)')"

# List all stages in order
stages-list:
	@uv run python -c "from haytham.workflow.stage_registry import get_stage_registry; \
		registry = get_stage_registry(); \
		print('All stages in execution order:'); \
		print(); \
		[print(f'  {m.display_index:>3}  {m.slug:<30} {m.display_name}') for m in registry.all_stages()]"

# =============================================================================
# Testing
# =============================================================================

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/ -v -m "not integration"

test-e2e:
	uv run pytest tests/ -v -m integration

# =============================================================================
# Agent Quality (LLM-as-Judge, ADR-018)
# =============================================================================

test-agents:
	uv run python -m haytham.testing.runner

test-agents-quick:
	uv run python -m haytham.testing.runner --agents concept_expansion --ideas T1

test-agents-verbose:
	uv run python -m haytham.testing.runner -v

record-fixtures:
ifndef IDEA_ID
	$(error IDEA_ID is required. Usage: make record-fixtures IDEA_ID=T1)
endif
	uv run python -m haytham.testing.runner --record --ideas $(IDEA_ID)

# =============================================================================
# Development
# =============================================================================

lint:
	uv run ruff check haytham/ --fix

format:
	uv run ruff format haytham/

clean:
	rm -rf __pycache__ .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned temporary files."

# =============================================================================
# View Stage Outputs (Developer Experience)
# =============================================================================

# View output from a specific stage
# Usage: make view-stage STAGE=idea-analysis
view-stage:
ifndef STAGE
	$(error STAGE is required. Usage: make view-stage STAGE=idea-analysis)
endif
	@echo "=== Output for stage: $(STAGE) ==="
	@cat session/$(STAGE)/*.md 2>/dev/null || echo "No output found for $(STAGE)"

# List all completed stages
stages:
	@echo "=== Completed Stages ==="
	@for dir in session/*/; do \
		if [ -f "$${dir}checkpoint.md" ]; then \
			stage=$$(basename $$dir); \
			echo "  ✓ $$stage"; \
		fi; \
	done 2>/dev/null || echo "No stages completed yet."
