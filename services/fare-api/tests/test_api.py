import importlib
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/fare-api -> the `app` package

from fareops_common.drift import build_profile  # noqa: E402
from fareops_common.features import FEATURES  # noqa: E402

main = None

TRIP = {"pickup_datetime": "2024-02-03T08:15:00", "trip_distance": 2.4,
        "passenger_count": 1, "PULocationID": 161, "DOLocationID": 237, "actual_fare": 13.5}


@pytest.fixture()
def app_main(tmp_path, monkeypatch):
    """Guide 4.6.1: DATA_DIR -> tmp_path BEFORE importing app.main; reload on later tests."""
    global main
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INFERENCE_LOG", "true")
    import fareops_common.settings
    importlib.reload(fareops_common.settings)  # S.DATA_DIR must follow this test's tmp_path
    if main is None:
        main = importlib.import_module("app.main")
    else:
        main = importlib.reload(main)
    return main


def test_not_ready_503(app_main):
    """Guide 4.6.2: no TestClient context manager here, so the loader thread never starts."""
    from fastapi.testclient import TestClient
    client = TestClient(app_main.app)
    assert client.get("/ready").status_code == 503
    assert client.post("/predict", json=TRIP).status_code == 503


def _tiny_model():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, len(FEATURES)))
    y = 3 + 2.5 * X[:, 2] + rng.normal(0, 0.1, 500)
    params = {"objective": "regression", "verbosity": -1, "min_data_in_leaf": 5, "seed": 42}
    return lgb.train(params, lgb.Dataset(X, label=y, feature_name=FEATURES), num_boost_round=30), X


def test_predict_metrics_and_log(app_main, tmp_path):
    """Guide 4.6.3-4: inject booster+profile, post 250 labelled trips, check metrics + CSV."""
    from fastapi.testclient import TestClient
    model, X = _tiny_model()
    app_main.store.booster = model
    app_main.store.profile = build_profile(X, FEATURES, ["trip_distance", "pickup_hour", "is_airport_pickup"])
    app_main.store.ready.set()
    client = TestClient(app_main.app)
    with client:
        for i in range(250):
            r = client.post("/predict", json={**TRIP, "trip_distance": 1.0 + (i % 20) * 0.5})
            assert r.status_code == 200
            assert isinstance(r.json()["fare_prediction"], (int, float))
        text = client.get("/metrics").text
        assert "fare_api_feature_psi" in text
        assert "fare_api_abs_error_usd_count" in text
    csv = tmp_path / "inference-logs" / "local.csv"
    assert len(csv.read_text().splitlines()) == 251  # header + 250


def test_invalid_trip_422(app_main):
    """Guide 4.6.5: trip_distance -1 fails Field(gt=0)."""
    from fastapi.testclient import TestClient
    client = TestClient(app_main.app)
    r = client.post("/predict", json={**TRIP, "trip_distance": -1})
    assert r.status_code == 422


def test_info_reports_service(app_main):
    """Guide 9.7: /info names the service (the visible Path A change)."""
    from fastapi.testclient import TestClient
    client = TestClient(app_main.app)
    body = client.get("/info").json()
    assert body["service"] == "fare-api"
    assert body["ready"] is False
