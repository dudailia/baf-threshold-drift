"""Traceability: render RESULTS.md and the one-pager from results files, and check them.

Templates live in docs/*.template.md. Inline numbers are written as
``{{value:key|fmt}}`` (key in results/values.json) and tables as
``{{table:name}}`` (built by src/tables.py from the results CSVs). A digit typed
in a template outside a placeholder must be a declared text constant in
results/manifest.json, or rendering fails.

The checker extracts every number from the rendered files and fails if one does
not match a value in the results CSVs, values.json or the manifest at the
precision shown, or if a rendered file differs from a fresh render.

Run with: python -m src.trace render | check
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import DOCS as DOCS_DIR
from src.config import OUT, RESULTS, ROOT

DOCS = {
    DOCS_DIR / "RESULTS.template.md": OUT / "RESULTS.md",
    DOCS_DIR / "README.template.md": OUT / "README.md",
    DOCS_DIR / "one_pager.template.md": OUT / "reports" / "one_pager.md",
}


class CheckError(Exception):
    pass


_STRIP = [
    re.compile(r"```.*?```", re.S),
    re.compile(r"<!--.*?-->", re.S),
    re.compile(r"`[^`]*`"),
    re.compile(r"\]\([^)]*\)"),
    re.compile(r"https?://\S+"),
]
_NUMBER = re.compile(r"(?<![\w.,])[-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w])")
_PLACEHOLDER = re.compile(r"\{\{\s*(value|table):([^}|]+?)(?:\|([^}]+?))?\s*\}\}")


def extract_numbers(text):
    for pattern in _STRIP:
        text = pattern.sub(" ", text)
    return _NUMBER.findall(text)


def _parse(token):
    token = token.replace("−", "-").replace(",", "")
    decimals = len(token.split(".")[1]) if "." in token else 0
    return float(token), decimals


def _numbers_in(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _numbers_in(v)


class Pool:
    """Every number a document may cite, also as a percent and in absolute value."""

    def __init__(self, values):
        v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
        self.sorted = np.unique(np.concatenate([v, 100 * v, np.abs(v), np.abs(100 * v)]))

    def contains(self, token):
        x, d = _parse(token)
        tol = 0.5 * 10.0**-d + 1e-9
        i = np.searchsorted(self.sorted, x - tol)
        return i < self.sorted.size and self.sorted[i] <= x + tol


def _manifest(results_dir):
    path = Path(results_dir) / "manifest.json"
    return json.loads(path.read_text()) if path.exists() else {}


def load_results(results_dir=RESULTS):
    return {p.stem: pd.read_csv(p) for p in sorted(Path(results_dir).glob("*.csv"))}


def load_pool(results_dir=RESULTS):
    nums = []
    for df in load_results(results_dir).values():
        num = df.select_dtypes("number").to_numpy(dtype=float).ravel()
        nums.append(num)
        # Numbers inside generated text columns (for example predictions_scored.csv details).
        for col in df.select_dtypes(exclude="number").columns:
            if col == "predictions_commit":
                continue
            found = [_parse(t)[0] for cell in df[col].dropna().astype(str).unique() for t in _NUMBER.findall(cell)]
            nums.append(np.asarray(found, dtype=float))
    extra = list(_numbers_in(_manifest(results_dir)))
    values_path = Path(results_dir) / "values.json"
    if values_path.exists():
        extra += list(_numbers_in(json.loads(values_path.read_text())))
    return Pool(np.concatenate(nums + [np.asarray(extra, dtype=float)]))


def check_document(path, pool):
    missing = [tok for tok in extract_numbers(Path(path).read_text()) if not pool.contains(tok)]
    if missing:
        raise CheckError(f"{path}: numbers not found in results or manifest: {sorted(set(missing))}")


FORMATS = {
    "pct1": lambda v: f"{100 * v:.1f}",
    "pct2": lambda v: f"{100 * v:.2f}",
    "pt2": lambda v: f"{100 * v:+.2f}",
    "apt2": lambda v: f"{abs(100 * v):.2f}",
    "pct0": lambda v: f"{100 * v:.0f}",
    "f2": lambda v: f"{v:.2f}",
    "f3": lambda v: f"{v:.3f}",
    "int": lambda v: f"{int(round(v)):,}",
    "str": str,
}


def render_text(template_text, results_dir, tables):
    constants = {float(c) for c in _numbers_in(_manifest(results_dir).get("text_constants", []))}
    typed = [t for t in extract_numbers(_PLACEHOLDER.sub(" ", template_text)) if _parse(t)[0] not in constants]
    if typed:
        raise CheckError(f"numbers typed in template that are not declared text constants: {sorted(set(typed))}")
    values_path = Path(results_dir) / "values.json"
    values = json.loads(values_path.read_text()) if values_path.exists() else {}
    results = load_results(results_dir)

    def sub(m):
        kind, name, fmt = m.group(1), m.group(2).strip(), (m.group(3) or "str").strip()
        if kind == "table":
            return tables[name](results, m.group(3).strip() if m.group(3) else None)
        if name not in values:
            raise CheckError(f"value {name!r} not in values.json")
        return FORMATS[fmt](values[name])

    return _PLACEHOLDER.sub(sub, template_text)


def render(template, out, results_dir=RESULTS, tables=None):
    text = render_text(Path(template).read_text(), results_dir, tables or {})
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(text)
    check_document(out, load_pool(results_dir))


def fmt_seed_spread(values, pct=False, decimals=2):
    v = 100 * np.asarray(values, dtype=float) if pct else np.asarray(values, dtype=float)
    f = f"{{:.{decimals}f}}"
    sd = v.std(ddof=1) if v.size > 1 else 0.0
    return f"{f.format(v.mean())} ({f.format(sd)}; {f.format(v.min())} to {f.format(v.max())})"


def verdict(paired_ci, ci_a, ci_b, heavy=0.5):
    """PROTOCOL.md: inconclusive if the paired interval contains 0 or the marginal intervals overlap heavily."""
    lo, hi = paired_ci
    if lo <= 0 <= hi:
        return "inconclusive"
    overlap = max(0.0, min(ci_a[1], ci_b[1]) - max(ci_a[0], ci_b[0]))
    shorter = min(ci_a[1] - ci_a[0], ci_b[1] - ci_b[0])
    if shorter > 0 and overlap >= heavy * shorter:
        return "inconclusive"
    return "differs"


def main(argv):
    from src.tables import TABLES

    cmd = argv[1] if len(argv) > 1 else "check"
    pool = load_pool(RESULTS)
    for template, out in DOCS.items():
        if not template.exists():
            raise CheckError(f"missing template {template}")
        fresh = render_text(template.read_text(), RESULTS, TABLES)
        if cmd == "render":
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(fresh)
        elif not out.exists() or out.read_text() != fresh:
            raise CheckError(f"{out} differs from a fresh render of {template}; edit the template, not the output")
        check_document(out, pool)
        print(f"{cmd}: {out} ok")


if __name__ == "__main__":
    main(sys.argv)
