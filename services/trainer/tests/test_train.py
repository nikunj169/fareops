import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo-local import of the trainer package

from trainer.train import fit, mae, time_split  # noqa: E402


def _synthetic(n: int = 2000) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    dist = rng.uniform(1.0, 10.0, n)
    fare = 3 + 2.5 * dist + rng.normal(0, 0.5, n)
    return pd.DataFrame({
        "pickup_datetime": pd.date_range("2024-01-01", periods=n, freq="h"),
        "trip_distance": dist,
        "passenger_count": np.ones(n, dtype="int64"),
        "PULocationID": np.full(n, 43, dtype="int64"),
        "DOLocationID": np.full(n, 230, dtype="int64"),
        "fare_amount": fare,
    })


def test_time_split_sizes():
    df = _synthetic(2000)
    train, hold = time_split(df, 0.8)
    assert len(train) == 1600
    assert len(hold) == 400


def test_model_beats_mean_baseline():
    from fareops_common.features import frame_features
    df = _synthetic(2000)
    train, hold = time_split(df, 0.8)
    X_train, y_train = frame_features(train), train["fare_amount"].to_numpy(dtype="float64")
    X_hold, y_hold = frame_features(hold), hold["fare_amount"].to_numpy(dtype="float64")
    model = fit(X_train, y_train)
    model_mae = mae(model, X_hold, y_hold)
    mean_baseline_mae = float(np.mean(np.abs(np.full_like(y_hold, y_train.mean()) - y_hold)))
    assert model_mae < mean_baseline_mae
