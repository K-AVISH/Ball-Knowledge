"""Softmax regression trained by gradient descent: the gesture classifier.

For each gesture k the model learns a weight vector w_k and a bias b_k. A frame's
score for gesture k is w_k . x + b_k, and softmax turns the scores into
probabilities that add up to 1.

Training minimises one cost function:

    J(W, b) = average cross-entropy  +  (l2 / 2) * (sum of squared weights)

* Cross-entropy is -log(the probability given to the true gesture). It is averaged
  so that each gesture counts equally, however many samples it has.
* The l2 term keeps the weights finite. Without it, gestures that can be told apart
  perfectly would push the weights towards infinity: the cost would keep falling
  without ever reaching a minimum, and every prediction would claim 100%.

J is convex, so it has exactly one minimum and gradient descent reaches it from any
starting point. Training starts from all-zero weights (every gesture equally likely)
and stops when the gradient is practically zero, which is what being at the minimum
means. Each step goes downhill by gradient / L, where L bounds how fast the gradient
can change, so a step never overshoots. Nesterov momentum makes the same descent take
far fewer steps; if a momentum step ever raises the cost, the momentum is reset.

Inputs are standardised (mean 0, spread 1 per feature, measured on the training data)
before training, so one step size suits every feature.
"""
from __future__ import annotations

from typing import List

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin

HISTORY_POINTS = 200          # cost values kept for the report (the curve, thinned out)


def _softmax_log(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    return z - np.log(np.exp(z).sum(axis=1, keepdims=True))


class GradientDescentClassifier(ClassifierMixin, BaseEstimator):
    """Multiclass logistic (softmax) regression, fitted by gradient descent.

    Works like a scikit-learn classifier: `fit`, `predict`, `predict_proba`, `classes_`.
    After `fit`: `cost_` (J at the end), `grad_norm_` (size of the gradient there),
    `n_iter_`, `converged_` and `cost_history_` (J at a few steps from start to end).
    """

    def __init__(self, l2: float = 0.01, max_iter: int = 20000, tol: float = 1e-6,
                 class_weight: str = "balanced") -> None:
        self.l2 = l2
        self.max_iter = max_iter
        self.tol = tol
        self.class_weight = class_weight

    # --- training -------------------------------------------------------------------
    def fit(self, X, y) -> "GradientDescentClassifier":
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y)
        if X.ndim != 2 or len(X) != len(y) or len(X) == 0:
            raise ValueError("X must be a 2-D array with one row per label in y.")
        if not np.isfinite(X).all():
            raise ValueError("X contains NaN or infinity.")
        if self.l2 <= 0:
            raise ValueError("l2 must be above 0, otherwise separable data has no minimum.")
        if self.class_weight not in ("balanced", None):
            raise ValueError("class_weight must be 'balanced' or None.")

        self.classes_, y_index = np.unique(y, return_inverse=True)
        k = len(self.classes_)
        if k < 2:
            raise ValueError("Need at least 2 classes to train.")
        n, d = X.shape
        self.n_features_in_ = d

        self.mean_ = X.mean(axis=0)
        scale = X.std(axis=0)
        scale[scale < 1e-12] = 1.0                    # a constant feature carries no information
        self.scale_ = scale
        xb = np.hstack([(X - self.mean_) / self.scale_, np.ones((n, 1))])   # last column: bias

        targets = np.eye(k)[y_index]
        if self.class_weight == "balanced":
            per_class = np.bincount(y_index, minlength=k)
            sample_w = 1.0 / (k * per_class[y_index])          # every gesture's weights sum to 1/k
        else:
            sample_w = np.full(n, 1.0 / n)
        sample_w = sample_w / sample_w.sum()

        penalised = np.ones((d + 1, 1))
        penalised[-1] = 0.0                                     # the bias is not penalised

        def cost_and_gradient(theta: np.ndarray):
            log_p = _softmax_log(xb @ theta)
            cost = -(sample_w * (targets * log_p).sum(axis=1)).sum() \
                + 0.5 * self.l2 * ((theta * penalised) ** 2).sum()
            grad = xb.T @ (sample_w[:, None] * (np.exp(log_p) - targets)) + self.l2 * theta * penalised
            return cost, grad

        # Largest curvature of J: softmax contributes at most half of the largest
        # eigenvalue of the weighted data matrix, the penalty adds l2.
        weighted = xb * np.sqrt(sample_w)[:, None]
        lipschitz = 0.5 * np.linalg.norm(weighted, 2) ** 2 + self.l2
        step = 1.0 / lipschitz

        theta = np.zeros((d + 1, k))
        cost, grad = cost_and_gradient(theta)
        history = [cost]
        look_ahead, momentum_t = theta.copy(), 1.0
        iterations, converged = 0, np.linalg.norm(grad) <= self.tol
        while not converged and iterations < self.max_iter:
            _, grad_ahead = cost_and_gradient(look_ahead)
            new_theta = look_ahead - step * grad_ahead
            new_cost, new_grad = cost_and_gradient(new_theta)
            iterations += 1
            if new_cost > cost and momentum_t > 1.0:    # momentum overshot: restart from here
                look_ahead, momentum_t = theta.copy(), 1.0
                continue
            # A plain step (no momentum) of size 1 / L cannot raise the cost; if it seems to,
            # that is rounding at the limit of float precision, and the step is kept.
            next_t = (1 + np.sqrt(1 + 4 * momentum_t ** 2)) / 2
            look_ahead = new_theta + ((momentum_t - 1) / next_t) * (new_theta - theta)
            theta, cost, grad, momentum_t = new_theta, new_cost, new_grad, next_t
            history.append(cost)
            converged = np.linalg.norm(grad) <= self.tol

        self.coef_ = theta[:-1].T / self.scale_        # weights on the original features
        self.intercept_ = theta[-1] - self.coef_ @ self.mean_
        self._theta = theta
        self.cost_ = float(cost)
        self.grad_norm_ = float(np.linalg.norm(grad))
        self.n_iter_ = iterations
        self.converged_ = bool(converged)
        self.cost_history_ = self._thin(history)
        return self

    @staticmethod
    def _thin(history: List[float]) -> List[List[float]]:
        """[[step, cost], ...] at about HISTORY_POINTS steps, always with the first and last."""
        last = len(history) - 1
        if last <= 0:
            return [[0, round(float(history[0]), 8)]]
        steps = np.unique(np.round(np.geomspace(1, last + 1, HISTORY_POINTS) - 1).astype(int))
        return [[int(s), round(float(history[s]), 8)] for s in steps]

    # --- prediction -------------------------------------------------------------------
    def predict_proba(self, X) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        if X.ndim != 2 or X.shape[1] != self.n_features_in_:
            raise ValueError(f"Expected {self.n_features_in_} features per row.")
        xb = np.hstack([(X - self.mean_) / self.scale_, np.ones((len(X), 1))])
        return np.exp(_softmax_log(xb @ self._theta))

    def predict(self, X) -> np.ndarray:
        return self.classes_[self.predict_proba(X).argmax(axis=1)]
