import numpy as np
import pytest

from src.thresholds import flag, threshold_at_fpr, threshold_top_fraction


def _fpr(scores, labels, t):
    neg = labels == 0
    return flag(scores[neg], t).mean()


def test_distinct_negatives_flags_exactly_target_share():
    # 100 distinct negative scores 0..99, 10 positives far above them.
    neg = np.arange(100, dtype=float)
    pos = np.arange(1000, 1010, dtype=float)
    scores = np.r_[neg, pos]
    labels = np.r_[np.zeros(100), np.ones(10)]
    t = threshold_at_fpr(scores, labels, 0.05)
    # Exactly negatives 95..99 are flagged.
    assert flag(neg, t).sum() == 5
    assert flag(np.array([94.0]), t)[0] == False
    assert flag(np.array([95.0]), t)[0] == True
    assert flag(pos, t).all()


def test_positive_between_boundary_negatives_is_flagged():
    # The threshold sits just above the highest unflagged negative, so a
    # positive scored between negative 94 and negative 95 is flagged.
    neg = np.arange(100, dtype=float)
    scores = np.r_[neg, 94.5]
    labels = np.r_[np.zeros(100), 1]
    t = threshold_at_fpr(scores, labels, 0.05)
    assert flag(np.array([94.5]), t)[0] == True
    assert _fpr(scores, labels, t) == pytest.approx(0.05)


def test_tied_block_crossing_target_is_not_flagged():
    # 90 negatives at 0 and 10 at 1. Flagging the tied block of 10 would give
    # FPR 0.10 > 0.05, and a tie cannot be split, so nothing negative is flagged.
    neg = np.r_[np.zeros(90), np.ones(10)]
    pos = np.array([1.0, 2.0])
    scores = np.r_[neg, pos]
    labels = np.r_[np.zeros(100), np.ones(2)]
    t = threshold_at_fpr(scores, labels, 0.05)
    assert _fpr(scores, labels, t) == 0.0
    assert flag(pos, t).tolist() == [False, True]


def test_target_of_one_flags_everything():
    scores = np.array([0.1, 0.2, 0.3, 0.9])
    labels = np.array([0, 0, 1, 1])
    t = threshold_at_fpr(scores, labels, 1.0)
    assert flag(scores, t).all()


def test_realized_fpr_never_exceeds_target_and_is_maximal():
    rng = np.random.default_rng(0)
    for _ in range(50):
        n = rng.integers(50, 2000)
        # Rounded scores create many ties.
        scores = np.round(rng.random(n), rng.integers(1, 4))
        labels = (rng.random(n) < 0.1).astype(int)
        if labels.min() == labels.max():
            continue
        target = rng.uniform(0.01, 0.3)
        t = threshold_at_fpr(scores, labels, target)
        assert _fpr(scores, labels, t) <= target + 1e-12
        # Lowering the threshold to the next score below t must break the target.
        below = scores[scores < t]
        if below.size:
            assert _fpr(scores, labels, below.max()) > target


def test_integer_weights_equal_duplicated_rows():
    rng = np.random.default_rng(1)
    scores = np.round(rng.random(300), 2)
    labels = (rng.random(300) < 0.2).astype(int)
    w = rng.integers(0, 4, size=300)
    t_w = threshold_at_fpr(scores, labels, 0.05, weights=w)
    t_dup = threshold_at_fpr(np.repeat(scores, w), np.repeat(labels, w), 0.05)
    assert flag(scores, t_w).tolist() == flag(scores, t_dup).tolist()


def test_top_fraction_flags_exact_count_with_distinct_scores():
    scores = np.random.default_rng(2).permutation(200).astype(float)
    t = threshold_top_fraction(scores, 0.05)
    assert flag(scores, t).sum() == 10
    assert flag(np.array([189.0, 190.0]), t).tolist() == [False, True]


def test_top_fraction_ignores_labels_and_respects_ties():
    # 20 scores tied at the top; flagging them would exceed 5% of 100.
    scores = np.r_[np.arange(80, dtype=float), np.full(20, 99.0)]
    t = threshold_top_fraction(scores, 0.05)
    assert flag(scores, t).sum() == 0


def test_floating_point_target_boundary():
    # 0.05 * 100 is 5.000000000000001 in floating point; still exactly 5 flagged.
    scores = np.arange(100, dtype=float)
    assert flag(scores, threshold_top_fraction(scores, 0.05)).sum() == 5
    # 0.07 * 100 is 7.000000000000001.
    assert flag(scores, threshold_top_fraction(scores, 0.07)).sum() == 7
