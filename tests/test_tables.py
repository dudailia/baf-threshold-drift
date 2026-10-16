import pytest

from src.tables import TABLES
from src.trace import load_pool, load_results, render
from tests.fake_results import write_fake_results


@pytest.fixture
def results(tmp_path):
    write_fake_results(tmp_path)
    return tmp_path


def _rows(md):
    return [line for line in md.splitlines()[2:] if line.startswith("| ")]


def test_headline_has_tpr_next_to_realized_fpr_and_labels_oracle(results):
    md = TABLES["headline"](load_results(results), "Base")
    header = md.splitlines()[0].split(" | ")
    i_fpr = next(i for i, h in enumerate(header) if h.startswith("Realized FPR"))
    i_tpr = next(i for i, h in enumerate(header) if h.startswith("TPR"))
    assert abs(i_tpr - i_fpr) <= 2
    assert "Oracle (upper bound, not deployable)" in md
    # 5 primary strategies x 4 months.
    assert len(_rows(md)) == 20


def test_delay_sweep_marks_in_sample_cells_not_available(results):
    md = TABLES["delay_sweep"](load_results(results), "Base")
    # Lag 2 at month 4 and lag 3 at months 4 and 5 would use training months.
    assert md.count("not available") == 3
    # Lag 1 at month 4, lag 2 at month 5, lag 3 at month 6 use month 3: equal to static.
    assert md.count("equals static") == 3


def test_small_cells_table_lists_only_flagged_groups_with_intervals(results):
    md = TABLES["small_cells"](load_results(results), None)
    rows = _rows(md)
    assert rows and all("Variant IV" in r for r in rows)
    assert all("[" in r and "]" in r for r in rows)


def test_paired_table_has_verdicts(results):
    md = TABLES["paired"](load_results(results), "Variant IV")
    assert "differs" in md or "inconclusive" in md
    assert "static" not in [r.split(" | ")[0].strip("| ") for r in _rows(md)]


@pytest.mark.parametrize("name,arg", [("headline", "Base"), ("fairness", "Base"), ("alert_shares", "Variant IV"),
                                      ("delay_sweep", "Variant IV"), ("paired", "Base"), ("small_cells", None),
                                      ("model_comparison", None), ("age_sensitivity", None)])
def test_every_table_renders_and_traces(results, tmp_path, name, arg):
    tmpl = tmp_path / "t.template.md"
    tmpl.write_text("{{table:" + name + ("|" + arg if arg else "") + "}}\n")
    out = tmp_path / "out.md"
    render(tmpl, out, results, TABLES)  # raises if any number does not trace
    assert out.read_text().count("\n") > 2
    assert load_pool(results).contains("95")


def test_exploratory_targets_says_so_when_absent(results):
    assert TABLES["exploratory_targets"](load_results(results), None) == "No exploratory targets in the results."


def test_exploratory_targets_lists_non_primary_targets(results):
    import pandas as pd

    r = load_results(results)
    for name in ("summary", "metrics"):
        extra = r[name].copy()
        extra["fpr_target"] = 0.01
        r[name] = pd.concat([r[name], extra])
    md = TABLES["exploratory_targets"](r, "Base")
    assert "| Base | 1 |" in md


def test_csv_table_shows_small_file(results):
    import pandas as pd

    r = {"checks": pd.DataFrame({"check": ["shuffled labels"], "tpr_at_5pct_fpr": [0.0512]})}
    assert TABLES["csv"](r, "checks").splitlines()[2] == "| shuffled labels | 0.0512 |"
