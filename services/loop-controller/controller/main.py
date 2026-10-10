import logging
import os
import time
from contextlib import asynccontextmanager

import mlflow
from fastapi import FastAPI, HTTPException, Response
from kubernetes import client as k8s
from kubernetes import config as k8s_config
from mlflow.tracking import MlflowClient
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

from controller.jobs import NAMESPACE, trainer_job
from controller.watcher import Watcher
from fareops_common import settings as S
from fareops_common.gitops import GitOpsClient

logging.basicConfig(level=logging.INFO)
COOLDOWN = int(os.getenv("RETRAIN_COOLDOWN_SECONDS", "900"))
TRIGGERS = Counter("loop_retrain_triggers_total", "Trainer Job requests", ["mode", "result"])
state = {"last_trigger": 0.0}
apis: dict = {}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    k8s_config.load_incluster_config()
    mlflow.set_tracking_uri(S.MLFLOW_TRACKING_URI)
    apis["batch"], apis["custom"] = k8s.BatchV1Api(), k8s.CustomObjectsApi()
    gitops = GitOpsClient(S.GITOPS_REPO, S.GITHUB_TOKEN, S.GITOPS_BRANCH)
    Watcher(apis["custom"], MlflowClient(), gitops, NAMESPACE).start()
    yield


app = FastAPI(title="loop-controller", lifespan=lifespan)


def _trainer_running() -> bool:
    jobs = apis["batch"].list_namespaced_job(NAMESPACE, label_selector="app=trainer")
    return any((j.status.active or 0) > 0 for j in jobs.items)


def _rollout_phase() -> str | None:
    ro = apis["custom"].get_namespaced_custom_object("argoproj.io", "v1alpha1", NAMESPACE, "rollouts", "fare-api")
    return ro.get("status", {}).get("phase")


def _start(mode: str) -> str:
    apis["batch"].create_namespaced_job(NAMESPACE, trainer_job(mode))
    state["last_trigger"] = time.time()
    TRIGGERS.labels(mode, "started").inc()
    return "started"


@app.post("/alert")
def alert(payload: dict):
    firing = [a for a in payload.get("alerts", [])
              if a.get("status") == "firing" and a.get("labels", {}).get("alertname") == "FareModelDrift"]
    if not firing:
        return {"result": "ignored"}
    for reason, blocked in (("trainer_running", _trainer_running),
                            ("cooldown", lambda: time.time() - state["last_trigger"] < COOLDOWN),
                            ("rollout_not_healthy", lambda: _rollout_phase() != "Healthy")):
        if blocked():
            TRIGGERS.labels("retrain", reason).inc()
            return {"result": f"skipped: {reason}"}
    return {"result": _start("retrain")}


@app.post("/train")
def train(mode: str):
    if mode not in ("initial", "retrain", "bad"):
        raise HTTPException(400, "mode must be initial, retrain or bad")
    if _trainer_running():
        raise HTTPException(409, "a trainer Job is already running")
    return {"result": _start(mode)}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/state")
def get_state():
    return {"last_trigger": state["last_trigger"], "cooldown_seconds": COOLDOWN}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
