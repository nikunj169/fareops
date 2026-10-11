# FareOps demo runbook

Follow this word for word at the viva. Every timing below was measured on the project
MacBook (M1, 8 GB) on 2026-10-11; each scenario was run twice.

## 0. Before you start (about 10 minutes)

Close browsers except one Grafana tab, and close IDEs.

```bash
k3d cluster start fareops                      # only if the cluster is stopped
kubectl -n fareops get pods                    # mlflow, loop-controller, 3x fare-api all 1/1
flux get kustomizations                        # cluster, infrastructure, apps: Ready True
kubectl argo rollouts get rollout fare-api -n fareops     # Status: Healthy
```

**Ingress address.** On this Mac a local Jenkins owns `127.0.0.1:8080`, so
`localhost:8080` does not reach the cluster (see `docs/deviations.md`). Use the Mac's
LAN address instead:

```bash
export FARE_URL="http://$(ipconfig getifaddr en0):8080"
curl -s $FARE_URL/info        # {"service":"fare-api","model_version":"1",...}
```

If Jenkins is stopped for the demo, `make replay-normal` / `make replay-airport` work
as written in the guide and `FARE_URL` is `http://localhost:8080`.

Open four terminals:

| Terminal | Command |
|---|---|
| T1 | `make ui-grafana` then open http://localhost:3000 → dashboard "FareOps - self-healing model" |
| T2 | `kubectl argo rollouts get rollout fare-api -n fareops --watch` |
| T3 | replay (commands below) |
| T4 | free for `kubectl` / `git` checks |

Replay commands (T3; stop with Ctrl-C):

```bash
# normal traffic
.venv/bin/python scripts/replay.py --file $HOME/fareops-data/datasets/replay_normal.parquet  --rps 15 --url $FARE_URL
# airport traffic (drift)
.venv/bin/python scripts/replay.py --file $HOME/fareops-data/datasets/replay_airport.parquet --rps 15 --url $FARE_URL
```

**Preconditions for every run:** Rollout `Healthy`; normal replay has run for 3 or more
minutes; Grafana open; T2 watching. Healthy reference on normal traffic: request rate
15/s, live MAE about **1.8 USD**, every PSI line below 0.2.

## 1. Path A: code push to canary (about 18 minutes, mostly CI)

Keep normal replay running the whole time.

| Step | You do | System does | Measured |
|---|---|---|---|
| 1 | Merge a PR to `main` in `fareops` | CI: `test`, then 4 × `build` | test ~1 min; builds 6–12 min (trainer is slowest) |
| 2 | Nothing | `deploy` job commits `deploy: nikunj169/fareops@<sha7>` to `fareops-gitops` | ~10 s |
| 3 | Nothing | Flux applies it | ~60 s |
| 4 | Nothing | Canary 33%, 90 s pause | 1 min 30 s |
| 5 | Nothing | AnalysisRun, 3 metrics, 4 measurements each | 1 min 30 s |
| 6 | Nothing | 66%, 30 s pause, 100%, `Healthy` | ~1 min |

Deploy commit to `Healthy`: **5 min 53 s**. Evidence: `kubectl -n fareops get analysisrun`
shows `Successful`; `curl -s $FARE_URL/info` shows the change.

**Before merging, pre-pull the images** or the node overloads. A deploy changes four
image tags at once; on 8 GB the first un-prepared deploy saturated the node CPU and
caused about 5.7 minutes of failed requests. As each build finishes:

```bash
TAG=<sha7 of the merge commit>
for s in fare-api loop-controller mlflow trainer; do
  docker exec k3d-fareops-server-0 crictl pull ghcr.io/nikunj169/fareops-$s:$TAG
done
```

With pre-pull, the same deploy had 17 failed requests out of about 18,750 and no pod
restarts. For the live demo, prefer showing Path A from the recorded video.

## 2. Scenario 1: drift, retrain, canary, promotion (about 10 minutes)

| Step | You do | System does | Where to see it | Measured (run 1 / run 2) |
|---|---|---|---|---|
| 1 | T3: stop normal replay, start **airport** replay | Traffic becomes airport pickups | Grafana panel 1 | t = 0 |
| 2 | Wait about 1 minute | PSI for `is_airport_pickup` and `trip_distance` rises above 0.2; live MAE rises from ~1.8 to ~6 USD | Grafana panels 2 and 3 | alert pending at 0:26 / 0:38 |
| 3 | Wait 3 more minutes | `FareModelDrift` fires; Alertmanager posts to loop-controller | Prometheus Alerts; `kubectl -n fareops logs deploy/loop-controller` | firing at 3:29 / 3:34 |
| 4 | Nothing | Job `trainer-retrain-*` trains on baseline plus recent airport traffic; candidate beats champion by at least 5% | `kubectl -n fareops logs -l mode=retrain` shows `"passed": true` and `"registered", "version": "2"` | Job starts 3:41 / 3:47; candidate MAE 3.33 vs champion 5.56 (run 2: 3.32 vs 5.80) |
| 5 | Nothing | Trainer commits `MODEL_VERSION "2"`; Flux applies it | `git -C ~/fareops-gitops pull && git log -1` | commit at 3:55 / 4:00; applied ~35–65 s later |
| 6 | Nothing | Canary: 1 pod on v2, 90 s warm-up, analysis; MAE ratio canary/stable below 1 | T2; Grafana panel 5 shows v1 and v2 pods | ratio 0.50–0.74 / 0.49–0.55 |
| 7 | Nothing | Rollout reaches 100% and `Healthy`; watcher sets champion to v2 | MLflow UI; Grafana "Champion model version" = 2 | Healthy at 8:29 / 9:41; champion at 9:15 / 9:52 |
| 8 | Keep replay running | MAE drops to ~3.4 USD; PSI drops below 0.2 against v2's new reference profile | Grafana panels 2 and 3 | immediately after promotion |

Total: **9 min 15 s** and **9 min 52 s**, with no command after step 1.

Checks (T4):

```bash
kubectl -n fareops logs -l app=trainer,mode=retrain | grep '"event"'
git -C ~/fareops-gitops pull && git -C ~/fareops-gitops log --oneline -3
kubectl -n fareops get analysisrun
```

## 3. Scenario 2: chaos test, a bad model is rolled back (about 5 minutes)

Start once Scenario 1 is complete. Keep airport replay running.

| Step | You do | System does | Where to see it | Measured (both runs) |
|---|---|---|---|---|
| 1 | T4: `make train-bad` (prints `{"result":"started"}`) | Trainer fits on shuffled labels, registers v3 tagged `purpose=chaos`, commits `MODEL_VERSION "3"` | MLflow UI; GitOps repo log | commit at 0:25 / 0:32 |
| 2 | Nothing | Canary pod on v3; its MAE is about 10 times the stable pods' (≈39 USD vs ≈4 USD) | Grafana panel 2 | canary up at ~1:40 |
| 3 | Nothing | Metric `mae-ratio-canary-vs-stable` fails (values 9.6–10.8, limit 1.25); the Rollout aborts and traffic returns to v2 | T2 shows `Degraded` / aborted; `kubectl -n fareops describe analysisrun` | 3:45 / 3:56 |
| 4 | Nothing | Watcher tags v3 `canary=failed` and commits `revert: model v3 failed canary analysis, back to v2` | GitOps repo log; Grafana "Loop events" rollbacks = 1 | same second as the abort |
| 5 | Nothing | Flux applies the revert; the Rollout returns to `Healthy` on v2; champion stays v2 | T2; MLflow UI | 4:42 / 4:42 |

Total: **4 min 42 s** in both runs.

During step 2–3 the `FareModelDrift` alert may show *pending*: the v3 canary pod carries
the old baseline profile, so its PSI is high. It clears on rollback and does not fire.

Closing shot for the video:

```bash
git -C ~/fareops-gitops log --format='%h | %an | %s' -8      # deploy: (CI), model: (trainer), revert: (loop-controller)
```

## 4. Reset between rehearsals (start from v1 every time)

**Stop replay first.** With airport traffic running, the rollout back to v1 is itself a
canary; its MAE ratio would fail and the watcher would revert your reset.

```bash
kubectl -n fareops delete deploy mlflow && kubectl -n fareops delete pvc mlflow-data   # wipes the registry
rm -f $HOME/fareops-data/inference-logs/*
python3 scripts/set_marker.py ~/fareops-gitops/apps/fare-api/rollout.yaml model-version 1 --quote
git -C ~/fareops-gitops commit -am "chore: reset model to v1" && git -C ~/fareops-gitops push
flux reconcile kustomization apps --with-source    # recreates MLflow and its volume from Git
kubectl -n fareops rollout restart deploy/loop-controller   # clears its in-memory failed-version list
make train-initial
```

Measured: about 6 min 30 s from the first command to `Healthy` on v1 (the rollout waits
for `make train-initial` to register v1). Then restart `make ui-mlflow` (its
port-forward dies with the old pod), start normal replay and wait 3 minutes.

## 5. If something goes wrong

| Symptom | What to do |
|---|---|
| `curl localhost:8080` returns `403 No valid crumb` | You are talking to Jenkins. Use `$FARE_URL` (section 0). |
| Alert fires, no Job starts | `kubectl -n fareops logs deploy/loop-controller`; `loop_retrain_triggers_total` shows the skip reason. The cooldown is 900 s after any trainer start, including `make train-*`. |
| Trainer logs `skip: not enough recent rows` | Fewer than 2,000 labelled rows logged. Let replay run longer, then `make train-retrain`. |
| Trainer logs `gate_failed` | Confirm traffic is `replay_airport`; compare `candidate_mae` and `champion_mae` in MLflow. |
| Pods restarting, probes timing out during a deploy | Node CPU is saturated by image pulls. Wait; it recovers once MLflow is Ready. Pre-pull next time (section 1). |
| Rollout stuck `Degraded` after a failed **code** canary | The loop-controller only reverts model versions. `git revert` the `deploy:` commit in `fareops-gitops` and push. |
| MLflow UI / API stops answering on `localhost:5000` | The MLflow pod was replaced; restart `make ui-mlflow`. |
