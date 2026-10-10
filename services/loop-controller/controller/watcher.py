import logging
import threading
import time

from prometheus_client import Counter, Gauge

from fareops_common import settings as S

log = logging.getLogger("watcher")

PROMOTIONS = Counter("loop_promotions_total", "Champion alias promotions")
ROLLBACKS = Counter("loop_rollbacks_total", "GitOps model reverts after failed canary")
CHAMPION = Gauge("loop_champion_version", "Current champion model version")


def model_version_of(rollout: dict) -> str | None:
    for c in rollout["spec"]["template"]["spec"]["containers"]:
        for e in c.get("env", []):
            if e.get("name") == "MODEL_VERSION":
                return e.get("value")
    return None


def decide(rollout: dict, champion: str | None, failed: set[str]) -> tuple:
    """Pure decision: ('promote', v) | ('rollback', bad, champion) | ('none',)."""
    status = rollout.get("status", {})
    version = model_version_of(rollout)
    if not version or version == champion:
        return ("none",)
    fully_promoted = (
        status.get("phase") == "Healthy"
        and not status.get("abort", False)
        and status.get("stableRS") is not None
        and status.get("stableRS") == status.get("currentPodHash")
        and str(status.get("observedGeneration")) == str(rollout["metadata"].get("generation"))
    )
    if fully_promoted and version not in failed:
        return ("promote", version)
    if status.get("abort", False) and champion and version not in failed:
        return ("rollback", version, champion)
    return ("none",)


class Watcher:
    def __init__(self, custom_api, mlflow_client, gitops, namespace: str, interval: int = 15):
        self.custom, self.ml, self.gitops = custom_api, mlflow_client, gitops
        self.ns, self.interval = namespace, interval
        self.failed: set[str] = set()

    def _champion(self) -> str | None:
        try:
            return str(self.ml.get_model_version_by_alias(S.MODEL_NAME, S.CHAMPION_ALIAS).version)
        except Exception:
            return None

    def tick(self) -> None:
        ro = self.custom.get_namespaced_custom_object("argoproj.io", "v1alpha1", self.ns, "rollouts", "fare-api")
        champion = self._champion()
        if champion:
            CHAMPION.set(int(champion))
        action = decide(ro, champion, self.failed)
        if action[0] == "promote":
            self.ml.set_registered_model_alias(S.MODEL_NAME, S.CHAMPION_ALIAS, action[1])
            PROMOTIONS.inc()
            log.info("promoted v%s to champion", action[1])
        elif action[0] == "rollback":
            bad, good = action[1], action[2]
            self.ml.set_model_version_tag(S.MODEL_NAME, bad, "canary", "failed")
            self.gitops.set(S.GITOPS_ROLLOUT_PATH, "model-version", good,
                            f"revert: model v{bad} failed canary analysis, back to v{good}", quote=True)
            self.failed.add(bad)
            ROLLBACKS.inc()
            log.warning("rolled back v%s -> v%s in Git", bad, good)

    def run_forever(self) -> None:
        while True:
            try:
                self.tick()
            except Exception as exc:
                log.warning("watcher tick failed: %s", exc)
            time.sleep(self.interval)

    def start(self) -> None:
        threading.Thread(target=self.run_forever, daemon=True).start()
