import json

import numpy as np
import pandas as pd
import pytest

from src.figures import plot_roc_operating_points
from src.trace import (
    CheckError,
    check_document,
    extract_numbers,
    fmt_seed_spread,
    load_pool,
    render,
    verdict,
)


@pytest.fixture
def results_dir(tmp_path):
    rows = []
    for seed in range(3):
        for strategy in ["static", "oracle"]:
            rows.append(
                dict(variant="Base", model="lightgbm", seed=seed, strategy=strategy, month=4,
                     realized_fpr=0.0512 + 0.001 * seed, tpr=0.4321 + 0.01 * seed)
            )
    pd.DataFrame(rows).to_csv(tmp_path / "metrics.csv", index=False)
    (tmp_path / "manifest.json").write_text(
        json.dumps({"n_seeds": 3, "text_constants": [5, 95, 1000], "predictions_commit": "abc123"})
    )
    (tmp_path / "values.json").write_text(json.dumps({"static_fpr_m4": 0.0512}))
    return tmp_path


def test_extract_numbers_skips_code_links_and_identifiers():
    text = "FPR 4.97% over 1,000 resamples, lag1 and x2, `seed 7`, [link](http://a/12.html) -0.58 pt"
    assert extract_numbers(text) == ["4.97", "1,000", "-0.58"]


def test_extract_numbers_skips_fenced_code_and_html_comments():
    text = "a 3.5\n```\nb 9.9\n```\n<!-- 8.8 -->\nc 2"
    assert extract_numbers(text) == ["3.5", "2"]


def test_pool_matches_fraction_shown_as_percent_and_rounded(results_dir):
    pool = load_pool(results_dir)
    assert pool.contains("5.12")  # 0.0512 as a percent
    assert pool.contains("0.0512")
    assert pool.contains("43.2")  # 0.4321 as a percent, 1 decimal
    assert pool.contains("1,000")  # manifest text constant
    assert not pool.contains("7.77")


def test_check_document_fails_on_number_absent_from_results(results_dir, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("Static FPR was 5.12% in month 4, and 6.66% later.")
    with pytest.raises(CheckError, match="6.66"):
        check_document(doc, load_pool(results_dir))


def test_check_document_passes_when_every_number_traces(results_dir, tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("Static FPR was 5.12% in month 4 over 3 seeds, 95% interval, 1,000 resamples.")
    check_document(doc, load_pool(results_dir))


def test_render_fills_values_and_tables(results_dir, tmp_path):
    tmpl = tmp_path / "t.template.md"
    tmpl.write_text("FPR {{value:static_fpr_m4|pct2}}%.\n\n{{table:demo}}\n")
    out = tmp_path / "out.md"
    tables = {"demo": lambda r, arg: "| a |\n|---|\n| 1 |"}
    render(tmpl, out, results_dir, tables)
    text = out.read_text()
    assert "FPR 5.12%." in text
    assert "| 1 |" in text


def test_render_rejects_typed_number_in_template(results_dir, tmp_path):
    tmpl = tmp_path / "t.template.md"
    tmpl.write_text("Static FPR was 5.12% by hand.")
    with pytest.raises(CheckError, match="5.12"):
        render(tmpl, tmp_path / "out.md", results_dir, {})


def test_render_allows_declared_text_constants(results_dir, tmp_path):
    tmpl = tmp_path / "t.template.md"
    tmpl.write_text("Target 5% FPR, 95% intervals from 1,000 resamples.")
    render(tmpl, tmp_path / "out.md", results_dir, {})


def test_seed_spread_format():
    assert fmt_seed_spread(np.array([0.050, 0.052, 0.054]), pct=True, decimals=2) == "5.20 (0.20; 5.00 to 5.40)"


def test_verdict_rules():
    # Paired interval excludes 0 and marginal intervals barely overlap.
    assert verdict((0.01, 0.03), (0.040, 0.050), (0.049, 0.070)) == "differs"
    # Paired interval contains 0.
    assert verdict((-0.01, 0.03), (0.040, 0.050), (0.060, 0.070)) == "inconclusive"
    # Paired excludes 0 but marginal intervals overlap by more than half the shorter width.
    assert verdict((0.001, 0.003), (0.040, 0.050), (0.042, 0.052)) == "inconclusive"


def test_roc_operating_points_lie_on_the_curve(tmp_path):
    from sklearn.metrics import roc_curve

    rng = np.random.default_rng(0)
    y = (rng.random(5000) < 0.05).astype(int)
    s = rng.normal(2.0 * y, 1.0)
    curves = {("Base", 4): (s, y)}
    points = {("Base", 4, "static"): 1.5, ("Base", 4, "oracle"): 1.8}
    out = tmp_path / "roc.png"
    coords = plot_roc_operating_points(curves, points, out)
    fpr, tpr, _ = roc_curve(y, s, drop_intermediate=False)
    for (fx, ty) in coords.values():
        assert np.min(np.abs(fpr - fx) + np.abs(tpr - ty)) < 1e-12
    assert out.exists() and out.stat().st_size > 0
