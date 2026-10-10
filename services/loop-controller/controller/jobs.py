import os
import time

from kubernetes import client as k8s

from fareops_common import settings as S

NAMESPACE = os.getenv("NAMESPACE", "fareops")
TRAINER_IMAGE = os.getenv("TRAINER_IMAGE", "")


def trainer_job(mode: str) -> k8s.V1Job:
    labels = {"app": "trainer", "mode": mode}
    env = [
        k8s.V1EnvVar(name="MLFLOW_TRACKING_URI", value=S.MLFLOW_TRACKING_URI),
        k8s.V1EnvVar(name="DATA_DIR", value=S.DATA_DIR),
        k8s.V1EnvVar(name="GITOPS_REPO", value=S.GITOPS_REPO),
        k8s.V1EnvVar(name="GITOPS_BRANCH", value=S.GITOPS_BRANCH),
        k8s.V1EnvVar(name="GITHUB_TOKEN", value_from=k8s.V1EnvVarSource(
            secret_key_ref=k8s.V1SecretKeySelector(name="gitops-token", key="token"))),
    ]
    container = k8s.V1Container(
        name="trainer", image=TRAINER_IMAGE, args=["--mode", mode], env=env,
        resources=k8s.V1ResourceRequirements(requests={"cpu": "250m", "memory": "384Mi"},
                                             limits={"cpu": "2", "memory": "1Gi"}),
        volume_mounts=[k8s.V1VolumeMount(name="data", mount_path="/mnt/fareops-data")],
    )
    pod = k8s.V1PodSpec(
        restart_policy="Never", containers=[container],
        security_context=k8s.V1PodSecurityContext(run_as_non_root=True, run_as_user=10001),
        volumes=[k8s.V1Volume(name="data", persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
            claim_name="fareops-data"))],
    )
    return k8s.V1Job(
        metadata=k8s.V1ObjectMeta(name=f"trainer-{mode}-{int(time.time())}", labels=labels),
        spec=k8s.V1JobSpec(backoff_limit=0, ttl_seconds_after_finished=1800,
                           template=k8s.V1PodTemplateSpec(metadata=k8s.V1ObjectMeta(labels=labels), spec=pod)),
    )
