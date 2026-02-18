PYTHON ?= python3
VENV ?= .venv
ACTIVATE = . $(VENV)/bin/activate

.PHONY: doctor validate demo demo-autonomous demo-docker test lint typecheck

doctor:
	$(ACTIVATE) && $(PYTHON) -m terminal_demo_studio.cli doctor --mode auto

validate:
	$(ACTIVATE) && $(PYTHON) -m terminal_demo_studio.cli validate screenplays/dev_bugfix_workflow.yaml

demo:
	$(ACTIVATE) && $(PYTHON) -m terminal_demo_studio.cli run examples/mock/safety_wizard.yaml --mode scripted_vhs --local --output-dir outputs

demo-autonomous:
	$(ACTIVATE) && $(PYTHON) -m terminal_demo_studio.cli run examples/mock/agent_loop.yaml --mode autonomous_pty --output-dir outputs

demo-docker:
	$(ACTIVATE) && $(PYTHON) -m terminal_demo_studio.cli run screenplays/drift_protection.yaml --docker

test:
	$(ACTIVATE) && pytest tests -v

lint:
	$(ACTIVATE) && ruff check .

typecheck:
	$(ACTIVATE) && mypy terminal_demo_studio
