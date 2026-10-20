"""Stage F checks: replication of the paper's setup on Base, shuffled-label run, PSI drift table.

Replication (PROTOCOL.md, Sanity checks): train months 0 to 5, test months 6 and 7,
raw sentinels, threshold from the notebook's ROC rule on the pooled test labels,
older group customer_age >= 50 as in notebook cell 10; once with `month` as a
feature and once without. The comparison statistic is the mean TPR of the 5 best
configurations by test TPR, which is how Figure 1 highlights its top 5 models.

Run with: python -m src.checks replication | shuffled | psi
"""

import json
import sys
import time

import numpy as np
import pandas as pd

from src import config
from src.data import CATEGORICAL, LABEL, MAIN_SPLIT, PAPER_SPLIT, VARIANT_FILES, apply_sentinels
from src.guard import predictions_commit
from src.metrics import confusion, notebook_operating_point, psi, rates
from src.models import fit_lgbm, sample_configs
from src.preprocess import LGBMPrep
from src.thresholds import threshold_at_fpr
from src.train import CONFIG_SEED, load, log, pred_path

FIGURE1_BASE_TOP5_TPR = 0.55  # read by eye from Figure 1 (PROTOCOL.md, claim 7)
LOOSE_BOUND = 0.05
SHUFFLED_TOLERANCE = 0.02  # pooled oracle TPR at 5% FPR must lie in 0.05 +- 0.02


def _append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def _read(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def replication(commit):
    df = load("Base")
    train = df[df["month"].isin(PAPER_SPLIT["train"])]
    test = df[df["month"].isin(PAPER_SPLIT["test"])]
    y = test[LABEL].to_numpy()
    older = (test["customer_age"] >= 50).to_numpy()
    ckpt = config.CHECKPOINTS / "replication.jsonl"
    done = {(r["with_month"], r["trial"]) for r in _read(ckpt)}
    configs = sample_configs(config.N_TRIALS, CONFIG_SEED)
    for with_month in (True, False):
        prep = LGBMPrep(include_month=with_month, raw_sentinels=True).fit(train)
        assert ("month" in prep.columns) == with_month
        Xtr, Xte = prep.transform(train), prep.transform(test)
        for i, cfg in enumerate(configs):
            if (with_month, i) in done:
                continue
            t0 = time.time()
            s = fit_lgbm(Xtr, train[LABEL].to_numpy(), cfg, seed=0, n_jobs=config.N_JOBS).predict_proba(Xte)[:, 1]
            t, tpr_roc = notebook_operating_point(s, y)
            pred = (s > t).astype(float)  # notebook binarizes with ">"
            fy = rates(confusion(pred[~older], y[~older], 0.5))["fpr"]
            fo = rates(confusion(pred[older], y[older], 0.5))["fpr"]
            r = rates(confusion(pred, y, 0.5))
            rec = dict(with_month=with_month, trial=i, tpr=tpr_roc, realized_fpr=r["fpr"], fpr_young=fy, fpr_old=fo,
                       fpr_ratio=min(fy, fo) / max(fy, fo), fit_seconds=time.time() - t0, predictions_commit=commit)
            _append(ckpt, rec)
            log(f"replication month={with_month} trial {i + 1}/{len(configs)} TPR {tpr_roc:.4f} FPR ratio {rec['fpr_ratio']:.3f} ({rec['fit_seconds']:.0f}s)")
    rows = pd.DataFrame(_read(ckpt))
    rows = rows[rows["trial"] < len(configs)]
    summary = []
    for with_month, g in rows.groupby("with_month"):
        top = g.nlargest(5, "tpr")
        summary.append(dict(check="replication", with_month=bool(with_month), n_configs=len(g), best_tpr=g["tpr"].max(),
                            top5_mean_tpr=top["tpr"].mean(), top5_mean_fpr_ratio=top["fpr_ratio"].mean(),
                            median_tpr=g["tpr"].median(), figure1_top5_tpr_by_eye=FIGURE1_BASE_TOP5_TPR,
                            bound_lo=FIGURE1_BASE_TOP5_TPR - LOOSE_BOUND, bound_hi=FIGURE1_BASE_TOP5_TPR + LOOSE_BOUND,
                            within_bound=bool(abs(top["tpr"].mean() - FIGURE1_BASE_TOP5_TPR) <= LOOSE_BOUND)))
    out = pd.DataFrame(summary)
    rows["predictions_commit"] = commit
    out.insert(0, "predictions_commit", commit)
    rows.to_csv(config.RESULTS / "replication_trials.csv", index=False)
    out.to_csv(config.RESULTS / "replication.csv", index=False)
    fired = [f"replication TPR outside loose Figure 1 bound: top-5 mean {r.top5_mean_tpr:.4f}"
             for r in out.itertuples() if r.with_month and not r.within_bound]
    return out, fired


def _check_model(df, labels, cfg):
    train = df[df["month"].isin(MAIN_SPLIT["train"])]
    prep = LGBMPrep().fit(train)
    model = fit_lgbm(prep.transform(train), labels, cfg, seed=0, n_jobs=config.N_JOBS)
    return prep, model


def shuffled(commit):
    df = load("Base")
    train = df[df["month"].isin(MAIN_SPLIT["train"])]
    rng = np.random.default_rng(0)
    y_shuf = rng.permutation(train[LABEL].to_numpy())  # permuted within training months only
    cfg = sample_configs(config.N_TRIALS, CONFIG_SEED)[0]
    prep, model = _check_model(df, y_shuf, cfg)
    ev = df[df["month"].isin(MAIN_SPLIT["validation"] + MAIN_SPLIT["test"])]
    s = model.predict_proba(prep.transform(ev))[:, 1]
    y, m = ev[LABEL].to_numpy(), ev["month"].to_numpy()
    val = MAIN_SPLIT["validation"][0]
    t_static = threshold_at_fpr(s[m == val], y[m == val], 0.05)
    rows = []
    test = np.isin(m, MAIN_SPLIT["test"])
    for label, mask in [(str(k), m == k) for k in MAIN_SPLIT["test"]] + [("4-7 pooled", test)]:
        t_or = threshold_at_fpr(s[mask], y[mask], 0.05)
        rows.append(dict(check="shuffled labels", months=label, positives=int(y[mask].sum()),
                         oracle_tpr_at_5pct_fpr=float((s[mask & (y == 1)] >= t_or).mean()),
                         static_realized_fpr=float((s[mask & (y == 0)] >= t_static).mean()),
                         static_tpr=float((s[mask & (y == 1)] >= t_static).mean())))
    out = pd.DataFrame(rows)
    out.insert(0, "predictions_commit", commit)
    out.to_csv(config.RESULTS / "shuffled.csv", index=False)
    pooled = out.loc[out.months == "4-7 pooled", "oracle_tpr_at_5pct_fpr"].iloc[0]
    fired = [] if abs(pooled - 0.05) <= SHUFFLED_TOLERANCE else [f"shuffled-label pooled TPR at 5% FPR {pooled:.4f} not within 0.05 +- {SHUFFLED_TOLERANCE}"]
    log(f"shuffled labels: pooled oracle TPR at 5% FPR {pooled:.4f}")
    return out, fired


def psi_table(commit, variants, importance_source):
    """Top 10 features by LightGBM gain; reference is the pooled training months 0 to 2."""
    rows = []
    for v in variants:
        df = load(v)
        if importance_source == "tuned":
            gain = json.loads(pred_path(v, "lightgbm", config.SEEDS[0]).with_suffix(".json").read_text())["gain_importance"]
        else:
            prep, model = _check_model(df, df.loc[df["month"].isin(MAIN_SPLIT["train"]), LABEL].to_numpy(),
                                       sample_configs(config.N_TRIALS, CONFIG_SEED)[0])
            gain = dict(zip(prep.columns, model.booster_.feature_importance("gain").tolist()))
        top = sorted(gain, key=gain.get, reverse=True)[:10]
        X = apply_sentinels(df)
        ref = X[X["month"].isin(MAIN_SPLIT["train"])]
        for rank, feat in enumerate(top, 1):
            row = dict(variant=v, importance_source=importance_source, rank=rank, feature=feat)
            for month in range(8):
                row[f"psi_month_{month}"] = psi(ref[feat].to_numpy(), X.loc[X["month"] == month, feat].to_numpy(),
                                                categorical=feat in CATEGORICAL)
            rows.append(row)
    out = pd.DataFrame(rows)
    out.insert(0, "predictions_commit", commit)
    out.to_csv(config.RESULTS / "psi.csv", index=False)
    return out


def main(argv):
    commit = predictions_commit()
    config.RESULTS.mkdir(parents=True, exist_ok=True)
    cmd = argv[1]
    fired = []
    if cmd == "replication":
        _, fired = replication(commit)
    elif cmd == "shuffled":
        _, fired = shuffled(commit)
    elif cmd == "psi":
        src = argv[2] if len(argv) > 2 else "tuned"
        psi_table(commit, config.VARIANT_SUBSET or (["Base"] if src == "check" else list(VARIANT_FILES)), src)
    path = config.RESULTS / "tripwires.json"
    tw = json.loads(path.read_text()) if path.exists() else {}
    tw.update(predictions_commit=commit)
    tw[cmd] = fired
    path.write_text(json.dumps(tw, indent=1))
    for f in fired:
        log(f"TRIPWIRE {f}")
    return 1 if fired and config.TRIPWIRES_FATAL else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
