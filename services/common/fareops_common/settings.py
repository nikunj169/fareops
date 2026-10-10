import os

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.fareops.svc.cluster.local:5000")
MLFLOW_EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "fare-prediction")
MODEL_NAME = os.getenv("MODEL_NAME", "fare-model")
CHAMPION_ALIAS = "champion"
DATA_DIR = os.getenv("DATA_DIR", "/mnt/fareops-data")
GITOPS_REPO = os.getenv("GITOPS_REPO", "")  # "<GH_USER>/fareops-gitops"
GITOPS_BRANCH = os.getenv("GITOPS_BRANCH", "main")
GITOPS_ROLLOUT_PATH = "apps/fare-api/rollout.yaml"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
MIN_IMPROVEMENT = float(os.getenv("MIN_IMPROVEMENT", "0.05"))  # candidate must beat champion MAE by 5%
RECENT_ROWS = int(os.getenv("RECENT_ROWS", "6000"))
MIN_RECENT_ROWS = int(os.getenv("MIN_RECENT_ROWS", "2000"))
PROFILE_ROWS = int(os.getenv("PROFILE_ROWS", "2000"))
