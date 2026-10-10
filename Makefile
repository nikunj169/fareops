SHELL := /bin/bash
.PHONY: up down venv data test replay-normal replay-airport ui-grafana ui-mlflow ui-prometheus

up:
	cd infra/ansible && ansible-playbook site.yml

down:
	cd infra/ansible && ansible-playbook teardown.yml

venv:
	python3.11 -m venv .venv && .venv/bin/pip install -r scripts/requirements-host.txt

data: venv
	.venv/bin/python scripts/prepare_data.py --out $(HOME)/fareops-data

ui-grafana:
	kubectl -n monitoring port-forward svc/grafana 3000:3000
ui-mlflow:
	kubectl -n fareops port-forward svc/mlflow 5000:5000
ui-prometheus:
	kubectl -n monitoring port-forward svc/prometheus 9090:9090
replay-normal:
	.venv/bin/python scripts/replay.py --file $(HOME)/fareops-data/datasets/replay_normal.parquet --rps 15
replay-airport:
	.venv/bin/python scripts/replay.py --file $(HOME)/fareops-data/datasets/replay_airport.parquet --rps 15
train-%:
	@kubectl -n fareops port-forward svc/loop-controller 18000:8000 >/dev/null 2>&1 & PF=$$!; sleep 3; \
	  curl -fsS -X POST "localhost:18000/train?mode=$$*"; echo; kill $$PF
