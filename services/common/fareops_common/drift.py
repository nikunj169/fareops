import numpy as np

EPS = 1e-4


def _bin_counts(values: np.ndarray, edges: list[float]) -> np.ndarray:
    return np.bincount(np.searchsorted(edges, values, side="right"), minlength=len(edges) + 1)


def build_profile(X: np.ndarray, feature_names: list[str], drift_features: list[str], bins: int = 10) -> dict:
    profile = {}
    for f in drift_features:
        col = X[:, feature_names.index(f)]
        if len(np.unique(col)) <= 2:
            edges = [0.5]  # binary feature
        else:
            qs = np.quantile(col, np.linspace(0, 1, bins + 1)[1:-1])
            edges = sorted({float(q) for q in qs})
        counts = _bin_counts(col, edges)
        profile[f] = {"edges": edges, "expected": (counts / counts.sum()).tolist()}
    return profile


def psi(expected: list[float], values: np.ndarray, edges: list[float]) -> float:
    counts = _bin_counts(np.asarray(values, dtype="float64"), edges)
    actual = counts / max(counts.sum(), 1)
    e = np.clip(np.asarray(expected, dtype="float64"), EPS, None)
    a = np.clip(actual, EPS, None)
    return float(np.sum((a - e) * np.log(a / e)))
