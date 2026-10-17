"""Point estimates and paired bootstrap for every threshold strategy, in one pass.

Each month's scores are sorted once. For a matrix of row weights (one row per
resample; all ones for the point estimate) the weighted counts of positives and
negatives in each age bin are accumulated over the distinct scores, from the
highest down. Every strategy then reduces to choosing how many distinct scores
to flag, so thresholds, rates and group metrics are prefix-sum lookups.

Resample weights are drawn once per (variant, month, chunk) from a fixed seed,
so every strategy, model and seed is evaluated on the same resampled rows
(paired comparisons). Threshold sources (validation month for static, month
m - k for delayed-label) are resampled too, so threshold estimation uncertainty
is included. Rules match src/thresholds.py and src/metrics.py; the unit tests
check that point estimates agree with them exactly.
"""

import hashlib

import numpy as np

_EPS = 1e-9
VALIDATION_MONTH = 3
CHUNK = 20  # resamples per chunk; fixed so that weights do not depend on memory settings
LAGS = (1, 2, 3)
STRATEGIES = ["static", "label_free_top", "label_free_val_rate", "delayed_lag1", "delayed_lag2", "delayed_lag3", "oracle",
              "groupwise_static", "groupwise_label_free"]
AGE_DEFS = {">=50": (1, 2), ">50": (2,)}  # bins counted as the older group


def AGE_BINS(age):
    """0: under 50, 1: exactly 50, 2: over 50 (ages are decade-rounded)."""
    age = np.asarray(age)
    return np.where(age < 50, 0, np.where(age == 50, 1, 2))


def resample_weights(n, n_resamples, key):
    seed = int.from_bytes(hashlib.sha256(repr(key).encode()).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    flat = (idx + np.arange(n_resamples)[:, None] * n).ravel()
    return np.bincount(flat, minlength=n_resamples * n).reshape(n_resamples, n).astype(np.float32)


class _Month:
    """Sorted scores of one month and, for a weight matrix, cumulative counts per (label, age bin)."""

    def __init__(self, scores, labels, ages):
        s = np.asarray(scores, dtype=float)
        self.order = np.argsort(-s, kind="stable")
        ss = s[self.order]
        self.starts = np.r_[0, np.flatnonzero(ss[1:] != ss[:-1]) + 1]
        self.U = ss[self.starts]  # distinct scores, descending
        cat = (np.asarray(labels)[self.order] * 3 + AGE_BINS(ages)[self.order]).astype(int)
        gid = np.repeat(np.arange(self.U.size), np.diff(np.r_[self.starts, s.size]))  # distinct-score index per sorted row
        self.cat_cols, self.cat_starts, self.cat_gids = [], [], []
        for k in range(6):
            cols = np.flatnonzero(cat == k)
            g = gid[cols]
            first = np.r_[0, np.flatnonzero(g[1:] != g[:-1]) + 1] if cols.size else np.array([], dtype=int)
            self.cat_cols.append(self.order[cols])
            self.cat_starts.append(first)
            self.cat_gids.append(g[first] if cols.size else first)
        self.n = s.size

    def cums(self, W):
        """(6, B, distinct scores + 1) cumulative weights per (label, age bin); float32 holds integer counts exactly."""
        B = W.shape[0]
        C = np.zeros((6, B, self.U.size + 1), dtype=np.float32)
        for k in range(6):
            if self.cat_cols[k].size:
                C[k][:, self.cat_gids[k] + 1] = np.add.reduceat(W[:, self.cat_cols[k]], self.cat_starts[k], axis=1)
            np.cumsum(C[k], axis=1, out=C[k])
        return C

    def count_at_or_above(self, t):
        return np.searchsorted(-self.U, -np.asarray(t), side="right")

    def threshold_from_cut(self, j):
        j = np.asarray(j)
        return np.where(j >= self.U.size, -np.inf, np.nextafter(self.U[np.minimum(j, self.U.size - 1)], np.inf))


def _total(C):
    return C[:, -1].astype(np.float64)


def _cut(cum, budget):
    """Largest number of distinct scores whose cumulative weight stays within budget (budget in float64)."""
    return (cum <= (np.asarray(budget, dtype=np.float64)[:, None] + _EPS)).sum(axis=1) - 1


def _div(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / np.where(b > 0, b, 1), np.nan)


def _neg(C, bins):
    return sum(C[a] for a in bins)


def _pos(C, bins):
    return sum(C[3 + a] for a in bins)


def _metrics(C, J, target):
    """J: (3, B) number of distinct scores flagged, per age bin."""
    flagged = [np.take_along_axis(C[k], J[k % 3][:, None], axis=1)[:, 0].astype(np.float64) for k in range(6)]
    total = [C[k][:, -1].astype(np.float64) for k in range(6)]
    tp, fp = sum(flagged[3:]), sum(flagged[:3])
    P, N = sum(total[3:]), sum(total[:3])
    W = P + N
    fpr = _div(fp, N)
    out = {}
    base = dict(realized_fpr=fpr, budget_miss=fpr - target, abs_budget_miss=np.abs(fpr - target), tpr=_div(tp, P),
                alert_rate=_div(tp + fp, W), precision=_div(tp, tp + fp))
    for age, old_bins in AGE_DEFS.items():
        young_bins = tuple(a for a in range(3) if a not in old_bins)
        g = {}
        for name, bins in (("young", young_bins), ("old", old_bins)):
            tp_g, fp_g = sum(flagged[3 + a] for a in bins), sum(flagged[a] for a in bins)
            p_g, n_g = sum(total[3 + a] for a in bins), sum(total[a] for a in bins)
            g[f"fpr_{name}"] = _div(fp_g, n_g)
            g[f"tpr_{name}"] = _div(tp_g, p_g)
            g[f"alert_share_{name}"] = _div(tp_g + fp_g, tp + fp)
            g[f"application_share_{name}"] = _div(p_g + n_g, W)
            g[f"n_pos_{name}"] = p_g
            g[f"n_neg_{name}"] = n_g
        lo, hi = np.minimum(g["fpr_young"], g["fpr_old"]), np.maximum(g["fpr_young"], g["fpr_old"])
        g["fpr_ratio"] = _div(lo, hi)
        out[age] = {**base, **g}
    return out


def _evaluate_pass(data, W, targets, primary_age, validation_month=VALIDATION_MONTH):
    """One weight matrix per month -> {(strategy, month, target): {age: {metric: array}}}, plus thresholds."""
    old_dec = AGE_DEFS[primary_age]
    groups = {"young": tuple(a for a in range(3) if a not in old_dec), "old": old_dec}
    months = sorted(data)
    oracle_t, static_rate, gw_static_t = {}, {}, {}
    results, thresholds = {}, {}
    for m in months:
        md = data[m]
        C = md.cums(W[m])
        B = C.shape[1]
        N, T = _neg(C, (0, 1, 2)), _neg(C, (0, 1, 2)) + _pos(C, (0, 1, 2))
        for f in targets:
            j_or = _cut(N, f * _total(N))
            oracle_t[(m, f)] = md.threshold_from_cut(j_or)
            if m == validation_month:
                static_rate[f] = _div(T[np.arange(B), j_or].astype(np.float64), _total(T))
                for gname, bins in groups.items():
                    Ng = _neg(C, bins)
                    gw_static_t[(f, gname)] = md.threshold_from_cut(_cut(Ng, f * _total(Ng)))
                continue
            plans = {}
            t_static = oracle_t[(validation_month, f)]
            plans["static"] = (md.count_at_or_above(t_static), t_static, validation_month)
            j = _cut(T, f * _total(T))
            plans["label_free_top"] = (j, md.threshold_from_cut(j), m)
            j = _cut(T, static_rate[f] * _total(T))
            plans["label_free_val_rate"] = (j, md.threshold_from_cut(j), m)
            for k in LAGS:
                src = m - k
                if src >= validation_month and src in data:  # source month must be among the evaluated months
                    t = oracle_t[(src, f)]
                    plans[f"delayed_lag{k}"] = (md.count_at_or_above(t), t, src)
                else:
                    plans[f"delayed_lag{k}"] = None
            plans["oracle"] = (j_or, oracle_t[(m, f)], m)
            for name in ("groupwise_static", "groupwise_label_free"):
                J = np.zeros((3, B), dtype=int)
                for gname, bins in groups.items():
                    if name == "groupwise_static":
                        jg = md.count_at_or_above(gw_static_t[(f, gname)])
                    else:
                        Tg = _neg(C, bins) + _pos(C, bins)
                        jg = _cut(Tg, f * _total(Tg))
                    for a in bins:
                        J[a] = jg
                plans[name] = (J, np.full(B, np.nan), validation_month if name == "groupwise_static" else m)
            for strategy, plan in plans.items():
                if plan is None:
                    results[(strategy, m, f)] = None
                    continue
                j, t, src = plan
                J = j if np.ndim(j) == 2 else np.tile(j, (3, 1))
                results[(strategy, m, f)] = _metrics(C, J, f)
                thresholds[(strategy, m, f)] = (t, src)
    return results, thresholds


def evaluate_months(months, targets, primary_age, n_boot, weight_seed=None, weights=None, boot_targets=None,
                    validation_month=VALIDATION_MONTH):
    """months: {month: (scores, labels, ages)} with the validation month and test months.

    Bootstrap runs on ``boot_targets`` (default: all targets). Returns (point_rows, boot) where boot maps (strategy, month, target, age_def)
    to {metric: array of n_boot values}.
    """
    data = {m: _Month(*months[m]) for m in sorted(months)}
    W = weights or {m: np.ones((1, d.n)) for m, d in data.items()}
    res, thr = _evaluate_pass(data, W, targets, primary_age, validation_month)
    metric_names = list(next(r for r in res.values() if r is not None)[primary_age])
    point = []
    for (strategy, m, f), r in sorted(res.items(), key=lambda kv: (STRATEGIES.index(kv[0][0]), kv[0][1], kv[0][2])):
        for age in AGE_DEFS:
            row = dict(strategy=strategy, month=m, fpr_target=f, age_def=age)
            if r is None:
                row.update(available=False, source_month=m - int(strategy[-1]), threshold=np.nan)
                row.update({k: np.nan for k in metric_names})
            else:
                t, src = thr[(strategy, m, f)]
                row.update(available=True, source_month=src, threshold=float(t[0]))
                row.update({k: float(v[0]) for k, v in r[age].items()})
            point.append(row)
    boot = {}
    if n_boot:
        acc = {}
        for c0 in range(0, n_boot, CHUNK):
            b = min(CHUNK, n_boot - c0)
            Wb = {m: resample_weights(d.n, CHUNK, (weight_seed, m, c0))[:b] for m, d in data.items()}
            res_b, _ = _evaluate_pass(data, Wb, boot_targets or targets, primary_age, validation_month)
            for (strategy, m, f), r in res_b.items():
                if r is None:
                    continue
                for age, metrics in r.items():
                    acc.setdefault((strategy, m, f, age), []).append(metrics)
        for key, parts in acc.items():
            boot[key] = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    return point, boot
