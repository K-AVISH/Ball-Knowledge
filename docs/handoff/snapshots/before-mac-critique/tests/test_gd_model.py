"""Tests for gd_model.py: the softmax regression trained by gradient descent.

Synthetic data only. These tests check that gradient descent reaches the minimum of
its cost function, not how well any real gesture is recognised.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gd_model import GradientDescentClassifier  # noqa: E402


def blobs(sizes=(50, 80, 30), spread=1.0, gap=0.7, d=20, seed=0):
    rng = np.random.default_rng(seed)
    X = np.vstack([rng.normal(i * gap, spread, size=(n, d)) for i, n in enumerate(sizes)])
    y = np.repeat(np.array(["a", "b", "c"][:len(sizes)]), sizes)
    return X, y


@pytest.mark.parametrize("l2", [0.1, 0.01])
def test_reaches_the_same_minimum_as_scikit_learn(l2):
    """Same convex cost, so both solvers must land on the same single minimum.
    scikit-learn minimises C * sum(w_i * loss_i) + |W|^2 / 2; with balanced weights that is
    our cost times C * n, so C = 1 / (l2 * n)."""
    from sklearn.linear_model import LogisticRegression

    X, y = blobs()
    gd = GradientDescentClassifier(l2=l2, tol=1e-8).fit(X, y)
    Xs = (X - gd.mean_) / gd.scale_
    sk = LogisticRegression(C=1 / (l2 * len(X)), class_weight="balanced", tol=1e-12,
                            max_iter=100000).fit(Xs, y)
    assert gd.converged_
    assert np.abs(gd.predict_proba(X) - sk.predict_proba(Xs)).max() < 1e-5


def test_cost_starts_at_log_k_and_never_rises():
    X, y = blobs()
    gd = GradientDescentClassifier(l2=0.05).fit(X, y)
    costs = [c for _, c in gd.cost_history_]
    assert gd.cost_history_[0] == [0, round(float(np.log(3)), 8)]   # all-zero weights: 1/3 each
    assert all(b <= a + 1e-12 for a, b in zip(costs, costs[1:]))
    assert costs[-1] == pytest.approx(gd.cost_, abs=1e-8)              # the curve ends at the result
    assert gd.converged_ and gd.grad_norm_ <= gd.tol


def test_gradient_is_zero_at_the_result():
    """Check the stopping rule independently: a numerical gradient of the cost at the
    fitted weights must be close to zero."""
    X, y = blobs(sizes=(30, 40), d=5)
    gd = GradientDescentClassifier(l2=0.1, tol=1e-8).fit(X, y)
    theta = gd._theta.copy()
    xb = np.hstack([(X - gd.mean_) / gd.scale_, np.ones((len(X), 1))])
    yi = np.unique(y, return_inverse=True)[1]
    w = 1.0 / (2 * np.bincount(yi)[yi]); w /= w.sum()

    def cost(t):
        z = xb @ t
        z = z - z.max(axis=1, keepdims=True)
        logp = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
        return -(w * logp[np.arange(len(yi)), yi]).sum() + 0.05 * (t[:-1] ** 2).sum()

    eps, grad = 1e-6, np.zeros_like(theta)
    for idx in np.ndindex(theta.shape):
        up, down = theta.copy(), theta.copy()
        up[idx] += eps
        down[idx] -= eps
        grad[idx] = (cost(up) - cost(down)) / (2 * eps)
    assert np.abs(grad).max() < 1e-6
    assert cost(theta) == pytest.approx(gd.cost_, abs=1e-9)


def test_separable_data_keeps_finite_weights_and_sub_100_percent_confidence():
    X, y = blobs(sizes=(40, 40), spread=0.1, gap=5.0, d=4)          # trivially separable
    strong = GradientDescentClassifier(l2=1.0).fit(X, y)
    weak = GradientDescentClassifier(l2=0.001).fit(X, y)
    assert strong.converged_ and weak.converged_
    assert np.isfinite(weak.coef_).all()
    assert strong.predict_proba(X).max() < weak.predict_proba(X).max() < 1.0


def test_each_gesture_counts_equally_however_many_samples():
    X, y = blobs(sizes=(200, 20), spread=1.0, gap=0.5, d=3)
    balanced = GradientDescentClassifier(l2=0.1).fit(X, y)
    plain = GradientDescentClassifier(l2=0.1, class_weight=None).fit(X, y)
    small = y == "b"
    assert (balanced.predict(X[small]) == "b").mean() > (plain.predict(X[small]) == "b").mean()


def test_training_is_deterministic():
    X, y = blobs()
    a = GradientDescentClassifier().fit(X, y)
    b = GradientDescentClassifier().fit(X, y)
    assert np.array_equal(a.predict_proba(X), b.predict_proba(X)) and a.n_iter_ == b.n_iter_


def test_constant_features_are_harmless():
    X, y = blobs(sizes=(20, 20), d=4)
    X = np.hstack([X, np.zeros((40, 3)), np.full((40, 1), 7.0)])
    gd = GradientDescentClassifier().fit(X, y)
    assert gd.converged_ and np.isfinite(gd.predict_proba(X)).all()


def test_stopping_early_is_reported():
    X, y = blobs()
    gd = GradientDescentClassifier(l2=0.001, max_iter=5).fit(X, y)
    assert not gd.converged_ and gd.n_iter_ == 5 and gd.grad_norm_ > gd.tol


def test_survives_a_save_and_load(tmp_path):
    import joblib

    X, y = blobs()
    gd = GradientDescentClassifier().fit(X, y)
    joblib.dump(gd, tmp_path / "m.joblib")
    loaded = joblib.load(tmp_path / "m.joblib")
    assert np.array_equal(loaded.predict_proba(X), gd.predict_proba(X))
    assert list(loaded.classes_) == ["a", "b", "c"] and loaded.n_features_in_ == 20
    assert loaded.get_params() == {"l2": 0.01, "max_iter": 20000, "tol": 1e-6, "class_weight": "balanced"}


@pytest.mark.parametrize("kwargs,X,y,message", [
    ({"l2": 0}, [[0.0], [1.0]], ["a", "b"], "l2"),
    ({}, [[0.0], [1.0]], ["a", "a"], "2 classes"),
    ({}, [[np.nan], [1.0]], ["a", "b"], "NaN"),
    ({}, [[0.0], [1.0]], ["a"], "one row per label"),
    ({"class_weight": "odd"}, [[0.0], [1.0]], ["a", "b"], "class_weight"),
])
def test_bad_input_is_rejected(kwargs, X, y, message):
    with pytest.raises(ValueError, match=message):
        GradientDescentClassifier(**kwargs).fit(np.array(X), np.array(y))


def test_wrong_feature_count_at_prediction_is_rejected():
    X, y = blobs()
    gd = GradientDescentClassifier().fit(X, y)
    with pytest.raises(ValueError, match="20 features"):
        gd.predict_proba(X[:, :5])
