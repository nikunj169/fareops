# Pinned versions (resolved 2026-10-10)

Every value below was resolved with the commands in the guide's "Tech stack" section
(`gh api repos/<repo>/releases/latest` and `pip index versions`). No value is guessed.
Resolved on: 2026-10-10.

| Component | Version |
|---|---|
| colima | pending — filled after Phase 1 (`colima version`) |
| k3d / default k3s image | pending — filled after Phase 1 (`k3d version`) |
| flux | pending — filled after Phase 1 (`flux version --client`) |
| argo-rollouts | v1.10.0 |
| prometheus | v3.15.0 |
| alertmanager | v0.34.1 |
| grafana | v13.2.3 |
| mlflow / mlflow-skinny | 3.17.0 |
| lightgbm | 4.7.0 |
| pandas / pyarrow / numpy | 3.0.6 / 26.0.0 / 2.4.6 |
| fastapi / uvicorn / prometheus-client | 0.143.0 / 0.54.0 / 0.26.0 |
| kubernetes (python) / requests / httpx | 37.0.1 / 2.34.2 / 0.28.1 |
| pytest / ruff | 9.1.1 / 0.17.0 |
| GitHub Actions (tag + SHA each) | see table below |

## GitHub Actions (pinned to full commit SHA)

| Action | Tag | Commit SHA |
|---|---|---|
| actions/checkout | v7.0.1 | 3d3c42e5aac5ba805825da76410c181273ba90b1 |
| actions/setup-python | v7.0.0 | 5fda3b95a4ea91299a34e894583c3862153e4b97 |
| docker/setup-qemu-action | v4.4.0 | 99012661954931238ded8c8b007157a8430204e1 |
| docker/setup-buildx-action | v4.4.1 | f87e5991a6d7451dcb8d9637bfbc97413f497069 |
| docker/login-action | v4.6.0 | dbcb813823bdd20940b903addbd779551569679f |
| docker/build-push-action | v7.4.0 | c3c9e263c25d99ce0380d002d59b67737d91b0dc |
| aquasecurity/trivy-action | v0.36.0 | ed142fd0673e97e23eac54620cfb913e5ce36c25 |

## Image tag formats (per the guide)

- Prometheus and Alertmanager keep the `v`: `prom/prometheus:v3.15.0`,
  `prom/alertmanager:v0.34.1`
- Grafana drops it: release tag `v13.2.3` → image `grafana/grafana:13.2.3`
- Argo Rollouts manifests are vendored from
  `https://github.com/argoproj/argo-rollouts/releases/download/v1.10.0/install.yaml`

## Rules (from the guide)

- `mlflow` (server, trainer) and `mlflow-skinny` (fare-api, loop-controller) must stay
  at the same version: both 3.17.0.
- If the pinned set fails `pip install` together, numpy steps down to the newest version
  LightGBM and MLflow both accept, and the reason is recorded in `docs/deviations.md`.
