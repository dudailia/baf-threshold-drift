PY := .venv/bin/python

.PHONY: all setup test guard audit replication shuffled train evaluate psi figures mechanism tables check sample

# Rebuilds every number and figure from data/raw/. Each step stops on a failed test or a tripwire.
all: test audit replication shuffled train evaluate psi figures mechanism tables check

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	$(PY) -m pytest -q

# train, evaluate and the checks refuse to run unless PREDICTIONS.md is committed and unchanged (src/guard.py).
guard:
	$(PY) -m src.guard

audit:
	$(PY) -m src.audit

replication: guard
	$(PY) -m src.checks replication

shuffled: guard
	$(PY) -m src.checks shuffled

train: guard
	$(PY) -m src.train

evaluate: guard
	$(PY) -m src.evaluate

psi: guard
	$(PY) -m src.checks psi tuned

figures:
	$(PY) -m src.report_figures

mechanism:
	$(PY) -m src.synthetic

tables:
	$(PY) -m src.trace render

check:
	$(PY) -m src.trace check

# Pipeline check on a 10% stratified sample of Base (Stage 5). Outputs are not interpreted anywhere.
sample: guard
	BAF_SAMPLE=0.1 BAF_VARIANTS=Base BAF_OUT=$(CURDIR)/results/sample_run $(PY) -m src.train
	BAF_SAMPLE=0.1 BAF_VARIANTS=Base BAF_OUT=$(CURDIR)/results/sample_run $(PY) -m src.evaluate
