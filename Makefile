PY := .venv/bin/python

.PHONY: all setup test guard audit train evaluate mechanism tables check

all: test audit train evaluate mechanism tables check

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	$(PY) -m pytest -q

audit:
	$(PY) -m src.audit

# train and evaluate refuse to run unless PREDICTIONS.md is committed and unchanged (src/guard.py).
guard:
	$(PY) -m src.guard

train: guard
	@echo "train: not implemented yet" && exit 1

evaluate: guard
	@echo "evaluate: not implemented yet" && exit 1

mechanism:
	$(PY) -m src.synthetic

tables:
	$(PY) -m src.trace render

check:
	$(PY) -m src.trace check
