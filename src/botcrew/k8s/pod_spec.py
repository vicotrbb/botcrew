"""K8s V1Pod builder for agent pods.

Constructs a bare Kubernetes pod spec for each agent, including the main
agent container and a browser sidecar using the K8s 1.28+ native sidecar
pattern (init container with restartPolicy=Always).

The agent parameter is duck-typed (expects id, name, model_provider,
model_name attributes) to avoid circular imports with the ORM models.
"""

from __future__ import annotations

from typing import Any, Protocol

from kubernetes_asyncio.client import (
    V1Container,
    V1ContainerPort,
    V1EnvVar,
    V1HTTPGetAction,
    V1ObjectMeta,
    V1PersistentVolumeClaimVolumeSource,
    V1Pod,
    V1PodSpec,
    V1Probe,
    V1ResourceRequirements,
    V1Volume,
    V1VolumeMount,
)


class AgentLike(Protocol):
    """Duck type for objects with agent attributes."""

    id: str
    name: str
    model_provider: str
    model_name: str


def build_agent_pod_spec(agent: Any, namespace: str) -> V1Pod:
    """Build a V1Pod specification for an agent.

    Uses the full agent UUID as pod name (no truncation) to guarantee
    uniqueness. Sets hostname and subdomain for headless service DNS
    resolution (e.g. agent-<uuid>.botcrew-agents.botcrew.svc.cluster.local).

    Args:
        agent: Object with id, name, model_provider, model_name attributes.
        namespace: Kubernetes namespace for the pod.

    Returns:
        A fully constructed V1Pod ready for creation via CoreV1Api.
    """
    pod_name = f"agent-{agent.id}"

    # Environment variables injected into the agent container
    env_vars = [
        V1EnvVar(name="AGENT_ID", value=str(agent.id)),
        V1EnvVar(name="AGENT_NAME", value=agent.name),
        V1EnvVar(name="MODEL_PROVIDER", value=agent.model_provider),
        V1EnvVar(name="MODEL_NAME", value=agent.model_name),
        V1EnvVar(
            name="ORCHESTRATOR_URL",
            value="http://botcrew-orchestrator:8000",
        ),
    ]

    # Workspace volume mount -- full PVC mount with directory convention
    workspace_mount = V1VolumeMount(
        name="agent-workspace",
        mount_path="/workspace",
        # Full PVC mount -- agent personal dir at /workspace/agents/{agent.id}/
        # Project dirs at /workspace/projects/{project_id}/
    )

    # Main agent container -- Dockerfile CMD runs uvicorn
    agent_container = V1Container(
        name="agent",
        image="botcrew-agent:latest",
        ports=[V1ContainerPort(container_port=8080)],
        env=env_vars,
        volume_mounts=[workspace_mount],
        startup_probe=V1Probe(
            http_get=V1HTTPGetAction(path="/health", port=8080),
            initial_delay_seconds=10,
            period_seconds=5,
            failure_threshold=12,  # 60s total startup window
        ),
        liveness_probe=V1Probe(
            http_get=V1HTTPGetAction(path="/health", port=8080),
            period_seconds=30,
            failure_threshold=3,
        ),
        resources=V1ResourceRequirements(
            requests={"memory": "256Mi", "cpu": "200m"},
            limits={"memory": "1Gi", "cpu": "1000m"},
        ),
    )

    # Browser sidecar as init container with restartPolicy=Always
    # (K8s 1.28+ native sidecar pattern: starts before main, runs alongside)
    # Dockerfile CMD runs the browser sidecar FastAPI app
    browser_sidecar = V1Container(
        name="browser",
        image="botcrew-browser-sidecar:latest",
        ports=[V1ContainerPort(container_port=8001)],
        restart_policy="Always",
        startup_probe=V1Probe(
            http_get=V1HTTPGetAction(path="/api/v1/health", port=8001),
            initial_delay_seconds=5,
            period_seconds=2,
            failure_threshold=15,  # 30s total startup window
        ),
        liveness_probe=V1Probe(
            http_get=V1HTTPGetAction(path="/api/v1/health", port=8001),
            period_seconds=30,
            failure_threshold=3,
        ),
        resources=V1ResourceRequirements(
            requests={"memory": "128Mi", "cpu": "100m"},
            limits={"memory": "512Mi", "cpu": "500m"},
        ),
    )

    # Workspace volume -- shared PVC with directory convention
    workspace_volume = V1Volume(
        name="agent-workspace",
        persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
            claim_name="botcrew-agent-workspaces",
        ),
    )

    return V1Pod(
        metadata=V1ObjectMeta(
            name=pod_name,
            namespace=namespace,
            labels={
                "app": "botcrew-agent",
                "botcrew.io/agent-id": str(agent.id),
            },
            annotations={
                "botcrew.io/agent-name": agent.name,
            },
        ),
        spec=V1PodSpec(
            service_account_name="botcrew-agent",
            hostname=pod_name,
            subdomain="botcrew-agents",
            restart_policy="Never",
            containers=[agent_container],
            init_containers=[browser_sidecar],
            volumes=[workspace_volume],
        ),
    )
