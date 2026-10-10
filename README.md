# FareOps: Self-Healing MLOps Platform

FareOps serves a NYC taxi fare prediction model on a local Kubernetes cluster. It
detects data drift, retrains itself, promotes the new model through GitOps,
canary-releases it, and rolls back automatically if the new model performs worse live.
Everything is visible in Grafana. Pushing a code change to `main` runs lint and tests,
builds four multi-arch images, scans them with Trivy, and canary-deploys through Flux
and Argo Rollouts; separately, a Prometheus drift alert triggers the loop-controller,
which starts the trainer Job, and the trainer commits the new model version back to the
GitOps repo where Flux and Argo Rollouts take over.
