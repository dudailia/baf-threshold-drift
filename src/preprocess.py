"""Preprocessing fit on training months only (PROTOCOL.md, Features and preprocessing)."""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data import CATEGORICAL, LABEL, apply_sentinels


def _features(df, include_month):
    drop = [LABEL] + ([] if include_month else ["month"])
    return [c for c in df.columns if c not in drop]


class LGBMPrep:
    """Sentinels to NaN; categoricals as pandas categories with the training months' levels."""

    def __init__(self, include_month=False, raw_sentinels=False):
        self.include_month = include_month
        self.raw_sentinels = raw_sentinels

    def fit(self, train):
        self.columns = _features(train, self.include_month)
        self.categories = {c: sorted(train[c].astype(str).unique()) for c in CATEGORICAL if c in self.columns}
        return self

    def transform(self, df):
        X = df if self.raw_sentinels else apply_sentinels(df)
        X = X[self.columns].copy()
        for c, cats in self.categories.items():
            v = X[c].astype(str)
            X[c] = pd.Categorical(v.where(v.isin(cats)), categories=cats)
        return X


class LRPrep:
    """Missing indicators, training-median imputation and scaling for numerics; one-hot for categoricals."""

    def fit(self, train):
        cols = _features(train, include_month=False)
        num = [c for c in cols if c not in CATEGORICAL]
        cat = [c for c in cols if c in CATEGORICAL]
        self.columns = cols
        self.ct = ColumnTransformer(
            [
                ("num", Pipeline([("impute", SimpleImputer(strategy="median", add_indicator=True)), ("scale", StandardScaler())]), num),
                ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
            ]
        )
        self.ct.fit(apply_sentinels(train)[cols])
        self.feature_names = list(self.ct.get_feature_names_out())
        return self

    def transform(self, df):
        return np.asarray(self.ct.transform(apply_sentinels(df)[self.columns]), dtype=float)
