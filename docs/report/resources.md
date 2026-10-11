# Resource usage (guide 9.8)

Measured on the project MacBook (Apple Silicon M1, 8 GB RAM; Colima VM 5 GiB) with
`kubectl top pods -A` and `kubectl top node` on 2026-10-11, while `replay.py` sent
traffic at 15 requests/s.

## Memory budget: guide estimate vs measured

Two samples: **A** = steady state on model v1, `replay_normal` at 15 requests/s
(16:06 IST); **B** = end of Scenario 2 after two rollouts, `replay_airport` at
15 requests/s on model v2 (18:30 IST).

| Component | Request | Limit | Measured memory A / B | Measured CPU A / B |
|---|---|---|---|---|
| K3s server + Traefik + CoreDNS + metrics-server | n/a | ~600 MiB (estimate) | see note 1 | see note 1 |
| Flux kustomize-controller | 64 MiB | 256 MiB | 27 / 72 MiB | 8m / 35m |
| Flux source-controller | 64 MiB | 256 MiB | 19 / 44 MiB | 13m / 9m |
| Argo Rollouts controller | 64 MiB | 256 MiB | 22 / 36 MiB | 23m / 28m |
| Prometheus | 256 MiB | 512 MiB | 39 / 57 MiB | 17m / 19m |
| Alertmanager | 32 MiB | 64 MiB | 10 / 17 MiB | 5m / 4m |
| Grafana | 96 MiB | 256 MiB | 220 / 227 MiB | 37m / 27m |
| MLflow server | 192 MiB | 512 MiB | 364 / 371 MiB | 13m / 14m |
| fare-api (3 pods, 4 during canary) | 160 MiB each | 384 MiB each | 94–95 / 94 MiB each | 45–50m / 38–59m each |
| loop-controller | 96 MiB | 256 MiB | 98 / 100 MiB | 12m / 15m |
| trainer Job (short-lived) | 384 MiB | 1 GiB | 296 MiB (note 2) | 999m (note 2) |

Whole node (`kubectl top node`), 5 GiB VM, 4 CPUs:

| Sample | CPU | Memory |
|---|---|---|
| A — steady state, v1 | 846m (21%) | 1957 MiB (39%) |
| During Scenario 1 (canary running) | 925m (23%) | 2624 MiB (53%) |
| B — end of Scenario 2 | 1397m (34%) | 2691 MiB (54%) |

Note 1 — the K3s server process itself is not a pod, so `kubectl top pods` cannot
show it. Its pod-visible parts in sample A: Traefik 27 MiB, CoreDNS 14 MiB,
metrics-server 20 MiB, local-path-provisioner 8 MiB, svclb-traefik 1 MiB (70 MiB
total). All pods together sum to 1152 MiB; the remaining ~805 MiB of the node's
1957 MiB is the K3s server, containerd and the kernel — above the guide's ~600 MiB
estimate for that row.

Note 2 — one `kubectl top` sample taken mid-training of a `retrain` Job. Training
takes about 20 seconds, shorter than the metrics-server scrape interval, so this is a
single reading, not a verified peak.

Observations:
- MLflow (364–371 MiB) and Grafana (220–227 MiB) are the two components closest to
  their limits (about 72% and 89%). MLflow fits only because its background job system
  is disabled (see `docs/deviations.md`, Phase 8).
- Node memory grew by about 730 MiB between samples A and B. Most of it is not in the
  pod numbers (those grew by about 175 MiB): it is image layers and page cache from
  three image generations and several rollouts.
- Prometheus uses far less than budgeted (39–57 MiB) with a small series count and a
  few hours of data; expect it to grow with retention.
- fare-api idles well under its 160 MiB request at 15 requests/s (~5 per pod).
- **Deploy spike.** A deploy that changes all four image tags drove the node to 357%
  CPU (`docker stats`) while pulling images; see `docs/demo-runbook.md` section 1 for
  the pre-pull step that avoids it.
- Mac side during sample B: `memory_pressure` reported 30% of 8 GB free. The
  acceptance check "at least 2 GB free in Activity Monitor during Scenario 1" still
  has to be read off Activity Monitor by a person.

## Raw output

Sample A:

```
$ kubectl top pods -A
NAMESPACE       NAME                                      CPU(cores)   MEMORY(bytes)
argo-rollouts   argo-rollouts-d7b9fcd65-wm7pt             23m          22Mi
fareops         fare-api-5d8f545cb9-d2g46                 48m          94Mi
fareops         fare-api-5d8f545cb9-m56lw                 45m          94Mi
fareops         fare-api-5d8f545cb9-wl6hf                 50m          95Mi
fareops         loop-controller-75684c5b48-sr228          12m          98Mi
fareops         mlflow-6fd49d7ddd-vr27d                   13m          364Mi
flux-system     kustomize-controller-5cbd55fc45-4f8jf     8m           27Mi
flux-system     source-controller-96584dff-bm9kt          13m          19Mi
kube-system     coredns-8db54c48d-wv69p                   20m          14Mi
kube-system     local-path-provisioner-5d9d9885bc-kvqp5   2m           8Mi
kube-system     metrics-server-786d997795-nwsmz           22m          20Mi
kube-system     svclb-traefik-4846e5e1-q6xkq              0m           1Mi
kube-system     traefik-9bcdbbd9-86n9m                    30m          27Mi
monitoring      alertmanager-7cc6cb6958-s5cjm             5m           10Mi
monitoring      grafana-bb9867c97-nxm6d                   37m          220Mi
monitoring      prometheus-77994f5cd4-tqp64               17m          39Mi

$ kubectl top node
NAME                   CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
k3d-fareops-server-0   846m         21%      1957Mi          39%
```

Sample B:

```
$ kubectl top pods -A
NAMESPACE       NAME                                      CPU(cores)   MEMORY(bytes)
argo-rollouts   argo-rollouts-d7b9fcd65-wm7pt             28m          36Mi
fareops         fare-api-69b54888d8-7v7kt                 38m          94Mi
fareops         fare-api-69b54888d8-ckvbg                 59m          94Mi
fareops         fare-api-69b54888d8-kf2rx                 49m          94Mi
fareops         loop-controller-5bd96578b8-lhzww          15m          100Mi
fareops         mlflow-6797c4f466-dnmx6                   14m          371Mi
flux-system     kustomize-controller-5cbd55fc45-4f8jf     35m          72Mi
flux-system     source-controller-96584dff-bm9kt          9m           44Mi
kube-system     coredns-8db54c48d-wv69p                   15m          16Mi
kube-system     local-path-provisioner-5d9d9885bc-kvqp5   2m           24Mi
kube-system     metrics-server-786d997795-nwsmz           15m          24Mi
kube-system     svclb-traefik-4846e5e1-q6xkq              0m           0Mi
kube-system     traefik-9bcdbbd9-86n9m                    35m          56Mi
monitoring      alertmanager-7cc6cb6958-s5cjm             4m           17Mi
monitoring      grafana-bb9867c97-nxm6d                   27m          227Mi
monitoring      prometheus-77994f5cd4-tqp64               19m          57Mi

$ kubectl top node
NAME                   CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
k3d-fareops-server-0   1397m        34%      2691Mi          54%
```

Trainer sample (mid-training):

```
$ kubectl top pods -n fareops
trainer-retrain-1791719507-mpjdw   999m         296Mi
```

## Minimum specs

Apple Silicon, 8 GB RAM, macOS 13+, 25 GB disk (guide 11.4 item 7).
