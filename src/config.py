"""Paths and run sizes. Environment variables let tests and the synthetic fixture
run the full pipeline into a scratch folder without touching the real outputs.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = Path(os.environ.get("BAF_RAW_DIR", ROOT / "data" / "raw"))
OUT = Path(os.environ.get("BAF_OUT", ROOT))
RESULTS = OUT / "results"
REPORTS = OUT / "reports"
FIGURES = OUT / "figures"
DOCS = Path(os.environ.get("BAF_DOCS", ROOT / "docs"))
PREDICTIONS_DIR = RESULTS / "predictions"
CHECKPOINTS = RESULTS / "checkpoints"
LOGS = RESULTS / "logs"

N_TRIALS = int(os.environ.get("BAF_N_TRIALS", 20))
SEEDS = list(range(int(os.environ.get("BAF_N_SEEDS", 5))))
N_BOOT = int(os.environ.get("BAF_N_BOOT", 1000))
SAMPLE_FRACTION = float(os.environ.get("BAF_SAMPLE", 1.0))
N_JOBS = int(os.environ.get("BAF_N_JOBS", 8))
# Tripwires stop the pipeline (non-zero exit) unless BAF_TRIPWIRES_FATAL=0, which only the synthetic fixture uses.
TRIPWIRES_FATAL = os.environ.get("BAF_TRIPWIRES_FATAL", "1") == "1"
_variants = os.environ.get("BAF_VARIANTS")
VARIANT_SUBSET = [v.strip() for v in _variants.split(",")] if _variants else None
