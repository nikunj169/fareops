# Resource usage (guide 9.8)

Measured on the project MacBook (Apple Silicon M1, 8 GB RAM; Colima VM 5 GiB) with
`kubectl top pods -A` and `kubectl top node` on 2026-10-11 16:06 IST, while
`replay.py` sent `replay_normal.parquet` at 15 requests/s (steady state, model v1,
Rollout Healthy, 3 fare-api pods).

## Memory budget: guide estimate vs measured

| Component | Request | Limit | Measured memory | Measured CPU |
|---|---|---|---|---|
| K3s server + Traefik + CoreDNS + metrics-server | n/a | ~600 MiB (estimate) | see note 1 | see note 1 |
| Flux kustomize-controller | 64 MiB | 256 MiB | 27 MiB | 8m |
| Flux source-controller | 64 MiB | 256 MiB | 19 MiB | 13m |
| Argo Rollouts controller | 64 MiB | 256 MiB | 22 MiB | 23m |
| Prometheus | 256 MiB | 512 MiB | 39 MiB | 17m |
| Alertmanager | 32 MiB | 64 MiB | 10 MiB | 5m |
| Grafana | 96 MiB | 256 MiB | 220 MiB | 37m |
| MLflow server | 192 MiB | 512 MiB | 364 MiB | 13m |
| fare-api (3 pods) | 160 MiB each | 384 MiB each | 94 / 94 / 95 MiB | 48m / 45m / 50m |
| loop-controller | 96 MiB | 256 MiB | 98 MiB | 12m |
| trainer Job (short-lived) | 384 MiB | 1 GiB | not yet measured | not yet measured |

Whole node (`kubectl top node`): **846m CPU (21%)**, **1957 MiB memory (39%)** of the
5 GiB VM.

Note 1 — the K3s server process itself is not a pod, so `kubectl top pods` cannot
show it. Its pod-visible parts measured: Traefik 27 MiB, CoreDNS 14 MiB,
metrics-server 20 MiB, local-path-provisioner 8 MiB, svclb-traefik 1 MiB (70 MiB
total). All pods together sum to 1152 MiB; the remaining ~805 MiB of the node's
1957 MiB is the K3s server, containerd and the kernel — above the guide's ~600 MiB
estimate for that row.

Observations:
- MLflow (364 MiB) and Grafana (220 MiB) are the two components closest to their
  limits (71% and 86%). MLflow fits only because its background job system is
  disabled (see `docs/deviations.md`, Phase 8).
- Prometheus uses far less than budgeted (39 MiB) shortly after a restart with a
  small series count; expect it to grow with retention.
- fare-api idles well under its 160 MiB request at 15 rps (~5 rps per pod).

## Raw output

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

## Minimum specs

Apple Silicon, 8 GB RAM, macOS 13+, 25 GB disk (guide 11.4 item 7).
