import json
import logging
import os
import tempfile
import threading
import time

import lightgbm as lgb
import mlflow
from mlflow.tracking import MlflowClient

from fareops_common import settings as S

log = logging.getLogger("model_store")


class ModelStore:
    """Loads booster + reference profile for one model version, retrying until it succeeds."""

    def __init__(self, version: str):
        self.version = version
        self.booster: lgb.Booster | None = None
        self.profile: dict | None = None
        self.ready = threading.Event()

    def _load_once(self) -> None:
        client = MlflowClient()
        run_id = client.get_model_version(S.MODEL_NAME, self.version).tags["run_id"]
        path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="serving",
                                                   dst_path=tempfile.mkdtemp())
        self.booster = lgb.Booster(model_file=os.path.join(path, "model.txt"))
        with open(os.path.join(path, "reference_profile.json")) as fh:
            self.profile = json.load(fh)

    def _loop(self) -> None:
        mlflow.set_tracking_uri(S.MLFLOW_TRACKING_URI)
        while not self.ready.is_set():
            try:
                self._load_once()
                self.ready.set()
                log.info("loaded model version %s", self.version)
            except Exception as exc:  # MLflow down, version not registered yet, tag not set yet
                log.warning("model %s not loadable yet: %s", self.version, exc)
                time.sleep(10)

    def start(self) -> None:
        threading.Thread(target=self._loop, daemon=True).start()
