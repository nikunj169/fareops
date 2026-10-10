# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm
RUN useradd --uid 10001 --create-home app
COPY mlflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
USER 10001
EXPOSE 5000
ENTRYPOINT ["mlflow", "server"]
