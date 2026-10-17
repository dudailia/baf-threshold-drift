"""Post hoc diagnostics, added after the shuffled-label tripwire fired. No pass/fail thresholds.

(a) shuffles: 20 label shuffles of Base's training months (main split, months 0 to 2),
    LightGBM (the check configuration) and logistic regression; pooled TPR at 5% FPR
    on test months 4 to 7 (threshold set on those months' own labels, as in the
    original check), next to the same models trained on the real labels and a
    label-free density score (Euclidean norm of the standardized features).
(b) leak_audit: per feature, AUC of the feature against the label on training months
    0 to 2 and on test months 4 to 7, for every variant. Numeric features use their
    value (sentinels as NaN, ranked lowest); categorical features use the training
    months' fraud rate per level. AUC above 0.75 or below 0.25 is flagged for review.

Run with: python -m src.diagnostics shuffles | leak_audit
"""

import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src import config
from src.data import CATEGORICAL, LABEL, MAIN_SPLIT, VARIANT_FILES, apply_sentinels
from src.guard import predictions_commit
from src.models import fit_lgbm, fit_lr, sample_configs
from src.preprocess import LGBMPrep, LRPrep
from src.thresholds import threshold_at_fpr
from src.train import CONFIG_SEED, load, log

N_SHUFFLES = 20
FLAG_HI, FLAG_LO = 0.75, 0.25


def _tpr5(s, y):
    return float((s[y == 1] >= threshold_at_fpr(s, y, 0.05)).mean())


def shuffles(commit):
    df = load("Base")
    train = df[df["month"].isin(MAIN_SPLIT["train"])]
    test = df[df["month"].isin(MAIN_SPLIT["test"])]
    y_tr, y_te = train[LABEL].to_numpy(), test[LABEL].to_numpy()
    cfg = sample_configs(config.N_TRIALS, CONFIG_SEED)[0]
    lg = LGBMPrep().fit(train)
    lr = LRPrep().fit(train)
    Xg_tr, Xg_te = lg.transform(train), lg.transform(test)
    Xl_tr, Xl_te = lr.transform(train), lr.transform(test)
    rows = []
    for k in range(N_SHUFFLES):
        ys = np.random.default_rng(k).permutation(y_tr)  # permutation 0 is the original check's shuffle
        rows.append(dict(model="lightgbm", labels="shuffled", shuffle=k,
                         tpr_at_5pct_fpr=_tpr5(fit_lgbm(Xg_tr, ys, cfg, seed=0, n_jobs=config.N_JOBS).predict_proba(Xg_te)[:, 1], y_te)))
        rows.append(dict(model="logreg", labels="shuffled", shuffle=k,
                         tpr_at_5pct_fpr=_tpr5(fit_lr(Xl_tr, ys, seed=0).predict_proba(Xl_te)[:, 1], y_te)))
        log(f"diagnostic shuffle {k + 1}/{N_SHUFFLES}: lightgbm {rows[-2]['tpr_at_5pct_fpr']:.4f}, logreg {rows[-1]['tpr_at_5pct_fpr']:.4f}")
    rows.append(dict(model="lightgbm", labels="real", shuffle=-1,
                     tpr_at_5pct_fpr=_tpr5(fit_lgbm(Xg_tr, y_tr, cfg, seed=0, n_jobs=config.N_JOBS).predict_proba(Xg_te)[:, 1], y_te)))
    rows.append(dict(model="logreg", labels="real", shuffle=-1, tpr_at_5pct_fpr=_tpr5(fit_lr(Xl_tr, y_tr, seed=0).predict_proba(Xl_te)[:, 1], y_te)))
    rows.append(dict(model="density score (no labels)", labels="none", shuffle=-1, tpr_at_5pct_fpr=_tpr5(np.linalg.norm(Xl_te, axis=1), y_te)))
    detail = pd.DataFrame(rows)
    sh = detail[detail.labels == "shuffled"].groupby("model")["tpr_at_5pct_fpr"]
    summary = pd.DataFrame({"min": sh.min(), "median": sh.median(), "max": sh.max(), "n_shuffles": sh.size()}).reset_index()
    real = detail[detail.labels == "real"].set_index("model")["tpr_at_5pct_fpr"]
    summary["real_label_tpr_at_5pct_fpr"] = summary["model"].map(real)
    summary["density_score_tpr_at_5pct_fpr"] = detail.loc[detail.labels == "none", "tpr_at_5pct_fpr"].iloc[0]
    for d in (detail, summary):
        d.insert(0, "predictions_commit", commit)
    detail.to_csv(config.RESULTS / "diag_shuffles_detail.csv", index=False)
    summary.to_csv(config.RESULTS / "diag_shuffles.csv", index=False)
    print(summary.to_string(index=False))


def _auc(y, x):
    ok = ~np.isnan(x)
    x = np.where(ok, x, np.nanmin(x) - 1 if ok.any() else 0)  # missing ranks lowest
    return float(roc_auc_score(y, x)) if len(np.unique(y)) == 2 else np.nan


def leak_audit(commit):
    rows = []
    for v in config.VARIANT_SUBSET or list(VARIANT_FILES):
        df = apply_sentinels(load(v))
        tr = df[df["month"].isin(MAIN_SPLIT["train"])]
        te = df[df["month"].isin(MAIN_SPLIT["test"])]
        feats = [c for c in df.columns if c not in (LABEL, "month")]
        for f in feats:
            if f in CATEGORICAL:
                rate = tr.groupby(f)[LABEL].mean()
                xtr, xte = tr[f].map(rate).to_numpy(float), te[f].map(rate).to_numpy(float)
            else:
                xtr, xte = tr[f].to_numpy(float), te[f].to_numpy(float)
            a_tr, a_te = _auc(tr[LABEL].to_numpy(), xtr), _auc(te[LABEL].to_numpy(), xte)
            rows.append(dict(variant=v, feature=f, auc_train_months=a_tr, auc_test_months=a_te,
                             distance_from_half=max(abs(a_tr - 0.5), abs(a_te - 0.5)),
                             flag_for_review=bool(max(a_tr, a_te) > FLAG_HI or min(a_tr, a_te) < FLAG_LO)))
    out = pd.DataFrame(rows).sort_values(["variant", "distance_from_half"], ascending=[True, False])
    out["rank"] = out.groupby("variant").cumcount() + 1
    out.insert(0, "predictions_commit", commit)
    out.to_csv(config.RESULTS / "diag_leak_audit_all.csv", index=False)
    top = out[out["rank"] <= 10]
    top.to_csv(config.RESULTS / "diag_leak_audit.csv", index=False)
    print(top[top.flag_for_review][["variant", "feature", "auc_train_months", "auc_test_months"]].to_string(index=False))


if __name__ == "__main__":
    commit = predictions_commit()
    {"shuffles": shuffles, "leak_audit": leak_audit}[sys.argv[1]](commit)
