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
    V1ObjectMeta,
    V1Pod,
    V1PodSpec,
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

    # Main agent container
    agent_container = V1Container(
        name="agent",
        image="botcrew-agent:latest",
        command=["python", "-m", "http.server", "8080"],
        ports=[V1ContainerPort(container_port=8080)],
        env=env_vars,
    )

    # Browser sidecar as init container with restartPolicy=Always
    # (K8s 1.28+ native sidecar pattern: starts before main, runs alongside)
    browser_sidecar = V1Container(
        name="browser",
        image="mcr.microsoft.com/playwright/python:v1.50.0-noble",
        command=["python", "-m", "http.server", "8001"],
        ports=[V1ContainerPort(container_port=8001)],
        restart_policy="Always",
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
        ),
    )
