PY := .venv/bin/python

.PHONY: all clean setup test guard audit replication shuffled diagnostics train evaluate psi figures predictions values mechanism tables check sample

# Rebuilds every number and figure from data/raw/. Each step stops on a failed test or a tripwire.
all: test audit replication shuffled diagnostics train evaluate psi figures predictions values mechanism tables check

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

# The shuffled-label check FAILED its declared tolerance; the user accepted it as a caveat
# (PROTOCOL.md, decision log), so its non-zero exit is recorded in results/tripwires.json and make continues.
shuffled: guard
	-$(PY) -m src.checks shuffled

# Post hoc diagnostics added after the shuffled-label tripwire fired (no pass/fail thresholds).
diagnostics: guard
	$(PY) -m src.diagnostics leak_audit
	$(PY) -m src.diagnostics shuffles

train: guard
	$(PY) -m src.train

evaluate: guard
	$(PY) -m src.evaluate

psi: guard
	$(PY) -m src.checks psi tuned

figures:
	$(PY) -m src.report_figures

predictions:
	$(PY) -m src.predictions_eval

values:
	$(PY) -m src.values

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

# Removes everything `make all` regenerates. Keeps data/, results/independent_check.csv (an external audit
# record that make all does not produce) and results_posthoc/ (post hoc analyses, not part of make all).
clean:
	find results -mindepth 1 -maxdepth 1 ! -name independent_check.csv -exec rm -rf {} +
	rm -f figures/*.png reports/data_audit.md reports/mechanism.md
	rm -f RESULTS.md README.md reports/one_pager.md RESULTS_POSTHOC.md prep/call_questions.md
