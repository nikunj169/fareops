import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # services/loop-controller -> `controller` package

from controller.jobs import trainer_job  # noqa: E402
from controller.watcher import decide, model_version_of  # noqa: E402


def rollout(**status):
    """Guide 5.5 fixture: generation 4, MODEL_VERSION='3', Healthy status."""
    base_status = {"phase": "Healthy", "abort": False, "stableRS": "abc",
                   "currentPodHash": "abc", "observedGeneration": "4"}
    base_status.update(status)
    return {
        "metadata": {"generation": 4},
        "spec": {"template": {"spec": {"containers": [
            {"name": "fare-api", "env": [{"name": "MODEL_VERSION", "value": "3"}]},
        ]}}},
        "status": base_status,
    }


def test_model_version_of_reads_container_env():
    assert model_version_of(rollout()) == "3"


def test_promote_when_fully_promoted_and_not_champion():
    assert decide(rollout(), "2", set()) == ("promote", "3")


def test_none_when_already_champion():
    assert decide(rollout(), "3", set()) == ("none",)


def test_none_while_canary_in_progress():
    assert decide(rollout(currentPodHash="def"), "2", set()) == ("none",)


def test_rollback_when_aborted_and_has_champion():
    assert decide(rollout(abort=True, phase="Degraded"), "2", set()) == ("rollback", "3", "2")


def test_none_when_version_already_failed():
    assert decide(rollout(), "2", {"3"}) == ("none",)


def test_trainer_job_spec():
    job = trainer_job("retrain")
    pod_spec = job.spec.template.spec
    assert pod_spec.containers[0].args == ["--mode", "retrain"]
    assert job.spec.backoff_limit == 0
    token = next(e for e in pod_spec.containers[0].env if e.name == "GITHUB_TOKEN")
    assert token.value_from.secret_key_ref.name == "gitops-token"
    assert pod_spec.volumes[0].persistent_volume_claim.claim_name == "fareops-data"
