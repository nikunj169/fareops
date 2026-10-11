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


def test_initial_then_retrain_end_to_end(tmp_path, monkeypatch):
    """Regression: retrain downloads the champion's serving/ artifacts and then writes its own.
    Runs main() for initial then retrain against a local MLflow store; GitOps is stubbed."""
    import mlflow
    from mlflow.tracking import MlflowClient

    import trainer.train as T
    from fareops_common import settings as S

    (tmp_path / "datasets").mkdir()
    (tmp_path / "inference-logs").mkdir()
    base = _synthetic(3000)
    base.to_parquet(tmp_path / "datasets" / "baseline.parquet")
    recent = _synthetic(2500)
    recent["fare_amount"] = recent["fare_amount"] * 3  # drifted labels: the champion must lose
    recent["pickup_datetime"] = recent["pickup_datetime"].dt.strftime("%Y-%m-%dT%H:%M:%S")
    recent.insert(0, "ts", np.arange(len(recent), dtype="float64"))
    recent["prediction"], recent["model_version"] = 0.0, 1
    recent.to_csv(tmp_path / "inference-logs" / "pod-a.csv", index=False)

    commits = []

    class FakeGitOps:
        def __init__(self, *a, **k):
            pass

        def set(self, path, key, value, msg, quote=False):
            commits.append((key, value, msg))
            return True

    monkeypatch.setattr(S, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(S, "MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path}/mlflow.db")
    monkeypatch.setattr(T, "GitOpsClient", FakeGitOps)
    monkeypatch.setattr(T, "ROUNDS", 30)
    monkeypatch.setenv("MLFLOW_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    monkeypatch.chdir(tmp_path)

    for mode in ("initial", "retrain"):
        monkeypatch.setattr(sys, "argv", ["train", "--mode", mode])
        assert T.main() == 0

    mlflow.set_tracking_uri(S.MLFLOW_TRACKING_URI)
    client = MlflowClient()
    assert str(client.get_model_version_by_alias(S.MODEL_NAME, S.CHAMPION_ALIAS).version) == "1"
    v2 = client.get_model_version(S.MODEL_NAME, "2")
    assert v2.tags["mode"] == "retrain"
    files = {f.path for f in client.list_artifacts(v2.tags["run_id"], "serving")}
    assert files == {"serving/model.txt", "serving/reference_profile.json"}
    assert [(k, v) for k, v, _ in commits] == [("model-version", "1"), ("model-version", "2")]
