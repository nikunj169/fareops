"""FareOps trainer. Modes: initial | retrain | bad. Exit 0 = success or no-op, 1 = error."""
import argparse
import json
import os
import sys
import tempfile
import time

import lightgbm as lgb
import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

from fareops_common import settings as S
from fareops_common.drift import build_profile
from fareops_common.features import DRIFT_FEATURES, FEATURES, frame_features
from fareops_common.gitops import GitOpsClient
from trainer.data import load_baseline, load_recent

PARAMS = {"objective": "regression", "learning_rate": 0.05, "num_leaves": 63, "min_data_in_leaf": 20,
          "feature_fraction": 0.9, "bagging_fraction": 0.8, "bagging_freq": 1, "seed": 42,
          "verbosity": -1, "num_threads": 2}
ROUNDS = 300


def log(**kv):
    print(json.dumps(kv), flush=True)


def fit(X: np.ndarray, y: np.ndarray) -> lgb.Booster:
    return lgb.train(PARAMS, lgb.Dataset(X, label=y, feature_name=FEATURES), num_boost_round=ROUNDS)


def mae(model: lgb.Booster, X: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean(np.abs(model.predict(X) - y)))


def time_split(df: pd.DataFrame, frac: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    cut = int(len(df) * frac)
    return df.iloc[:cut], df.iloc[cut:]


def load_serving(client: MlflowClient, version: str, dst: str) -> lgb.Booster:
    run_id = client.get_model_version(S.MODEL_NAME, version).tags["run_id"]
    path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="serving", dst_path=dst)
    return lgb.Booster(model_file=os.path.join(path, "model.txt"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["initial", "retrain", "bad"], required=True)
    mode = ap.parse_args().mode
    mlflow.set_tracking_uri(S.MLFLOW_TRACKING_URI)
    mlflow.set_experiment(S.MLFLOW_EXPERIMENT)
    client = MlflowClient()
    baseline = load_baseline(S.DATA_DIR)
    champion_mae = None

    if mode == "initial":
        train_df, hold_df = time_split(baseline, 0.9)
        profile_df = train_df
    elif mode == "bad":
        train_df, hold_df = time_split(baseline, 0.9)
        profile_df = train_df
    else:  # retrain
        recent = load_recent(S.DATA_DIR, S.RECENT_ROWS)
        if len(recent) < S.MIN_RECENT_ROWS:
            log(event="skip", reason="not enough recent rows", rows=len(recent))
            return 0
        recent_train, hold_df = time_split(recent, 0.8)
        train_df = pd.concat([baseline, recent_train[baseline.columns]], ignore_index=True)
        profile_df = recent.tail(S.PROFILE_ROWS)

    X_train, y_train = frame_features(train_df), train_df["fare_amount"].to_numpy(dtype="float64")
    if mode == "bad":
        y_train = np.random.default_rng(0).permutation(y_train)  # deliberately broken model
    X_hold, y_hold = frame_features(hold_df), hold_df["fare_amount"].to_numpy(dtype="float64")
    model = fit(X_train, y_train)
    candidate_mae = mae(model, X_hold, y_hold)

    with tempfile.TemporaryDirectory() as tmp:
        if mode == "retrain":
            champ = client.get_model_version_by_alias(S.MODEL_NAME, S.CHAMPION_ALIAS)
            # Own directory: download_artifacts() creates <dst>/serving, which must not collide
            # with the candidate's <tmp>/serving created below.
            champion_dir = os.path.join(tmp, "champion")
            os.makedirs(champion_dir)
            champion_mae = mae(load_serving(client, champ.version, champion_dir), X_hold, y_hold)
        passed = mode != "retrain" or candidate_mae <= champion_mae * (1 - S.MIN_IMPROVEMENT)
        log(event="evaluated", mode=mode, candidate_mae=candidate_mae, champion_mae=champion_mae, passed=passed)

        with mlflow.start_run(run_name=f"{mode}-{int(time.time())}") as run:
            mlflow.log_params({"mode": mode, "rows_train": len(train_df), "rows_holdout": len(hold_df), **PARAMS})
            mlflow.log_metric("candidate_mae", candidate_mae)
            if champion_mae is not None:
                mlflow.log_metric("champion_mae", champion_mae)
            serving = os.path.join(tmp, "serving")
            os.makedirs(serving)
            model.save_model(os.path.join(serving, "model.txt"))
            with open(os.path.join(serving, "reference_profile.json"), "w") as fh:
                json.dump(build_profile(frame_features(profile_df), FEATURES, DRIFT_FEATURES), fh)
            mlflow.log_artifacts(serving, artifact_path="serving")
            info = mlflow.lightgbm.log_model(model, artifact_path="model")
            mlflow.set_tag("gate", "passed" if passed else "failed")
            run_id = run.info.run_id

        if not passed:
            log(event="gate_failed", run_id=run_id)
            return 0

    version = mlflow.register_model(info.model_uri, S.MODEL_NAME).version
    client.set_model_version_tag(S.MODEL_NAME, version, "run_id", run_id)
    client.set_model_version_tag(S.MODEL_NAME, version, "mode", mode)
    if mode == "bad":
        client.set_model_version_tag(S.MODEL_NAME, version, "purpose", "chaos")
    if mode == "initial":
        client.set_registered_model_alias(S.MODEL_NAME, S.CHAMPION_ALIAS, version)
    log(event="registered", version=version)

    msg = f"model: deploy {S.MODEL_NAME} v{version} ({mode}, mae={candidate_mae:.3f})"
    committed = GitOpsClient(S.GITOPS_REPO, S.GITHUB_TOKEN, S.GITOPS_BRANCH).set(
        S.GITOPS_ROLLOUT_PATH, "model-version", str(version), msg, quote=True)
    log(event="gitops", committed=committed, version=version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
