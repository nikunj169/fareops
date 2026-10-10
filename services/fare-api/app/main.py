import collections
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime

import numpy as np
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from app.inference_log import InferenceLog
from app.metrics import ABS_ERROR, LATENCY, MODEL_INFO, PREDICTION, PSI, REQUESTS, ROLLING_MAE
from app.model_store import ModelStore
from fareops_common import settings as S
from fareops_common.drift import psi
from fareops_common.features import DRIFT_FEATURES, FEATURES, row_features

logging.basicConfig(level=logging.INFO)
MODEL_VERSION = os.getenv("MODEL_VERSION", "1")
POD_NAME = os.getenv("POD_NAME", "local")
store = ModelStore(MODEL_VERSION)
ilog = InferenceLog(S.DATA_DIR, POD_NAME) if os.getenv("INFERENCE_LOG", "true") == "true" else None
window: collections.deque = collections.deque(maxlen=1000)
errors: collections.deque = collections.deque(maxlen=500)
lock = threading.Lock()
state = {"n": 0}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    MODEL_INFO.labels(MODEL_VERSION).set(1)
    store.start()
    yield


app = FastAPI(title="fare-api", lifespan=lifespan)


class Trip(BaseModel):
    pickup_datetime: datetime
    trip_distance: float = Field(gt=0, le=200)
    passenger_count: int = Field(ge=0, le=9)
    PULocationID: int = Field(ge=1, le=265)
    DOLocationID: int = Field(ge=1, le=265)
    actual_fare: float | None = None


def _update_drift(feats: list[float]) -> None:
    with lock:
        window.append(feats)
        state["n"] += 1
        if state["n"] % 50 or len(window) < 200 or store.profile is None:
            return
        arr = np.asarray(window)
        for f in DRIFT_FEATURES:
            prof = store.profile[f]
            PSI.labels(f, MODEL_VERSION).set(psi(prof["expected"], arr[:, FEATURES.index(f)], prof["edges"]))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    if not store.ready.is_set():
        raise HTTPException(503, "model not loaded")
    return {"model_version": MODEL_VERSION}


@app.get("/info")
def info():
    return {"model_version": MODEL_VERSION, "pod": POD_NAME, "ready": store.ready.is_set()}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
def predict(trip: Trip):
    start = time.perf_counter()
    if not store.ready.is_set():
        REQUESTS.labels("503", MODEL_VERSION).inc()
        raise HTTPException(503, "model not loaded")
    try:
        feats = row_features(trip.pickup_datetime, trip.trip_distance, trip.passenger_count,
                             trip.PULocationID, trip.DOLocationID)
        pred = float(store.booster.predict(np.asarray([feats], dtype="float64"))[0])
    except Exception as exc:
        REQUESTS.labels("500", MODEL_VERSION).inc()
        raise HTTPException(500, f"prediction failed: {exc}") from exc
    PREDICTION.labels(MODEL_VERSION).observe(pred)
    _update_drift(feats)
    if trip.actual_fare is not None:
        err = abs(pred - trip.actual_fare)
        ABS_ERROR.labels(MODEL_VERSION).observe(err)
        with lock:
            errors.append(err)
            ROLLING_MAE.labels(MODEL_VERSION).set(sum(errors) / len(errors))
        if ilog:
            ilog.write([f"{time.time():.3f}", trip.pickup_datetime.isoformat(), trip.trip_distance,
                        trip.passenger_count, trip.PULocationID, trip.DOLocationID, trip.actual_fare,
                        f"{pred:.4f}", MODEL_VERSION])
    REQUESTS.labels("200", MODEL_VERSION).inc()
    LATENCY.labels(MODEL_VERSION).observe(time.perf_counter() - start)
    return {"fare_prediction": round(pred, 2), "model_version": MODEL_VERSION}
