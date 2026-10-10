SHELL := /bin/bash
.PHONY: up down venv data test replay-normal replay-airport ui-grafana ui-mlflow ui-prometheus train-initial train-bad

up:
	cd infra/ansible && ansible-playbook site.yml

down:
	cd infra/ansible && ansible-playbook teardown.yml

venv:
	python3.11 -m venv .venv && .venv/bin/pip install -r scripts/requirements-host.txt

data: venv
	.venv/bin/python scripts/prepare_data.py --out $(HOME)/fareops-data
