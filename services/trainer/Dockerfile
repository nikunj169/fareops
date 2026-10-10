# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY trainer/requirements.txt requirements.txt
RUN pip wheel --wheel-dir /wheels -r requirements.txt
COPY common ./common
RUN pip wheel --no-deps --wheel-dir /wheels ./common

FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/* && useradd --uid 10001 --create-home app
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
 && rm -rf /wheels
WORKDIR /app
COPY trainer/trainer ./trainer
USER 10001
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "trainer.train"]
