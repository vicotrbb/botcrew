"""Async Kubernetes pod lifecycle manager.

Wraps kubernetes-asyncio CoreV1Api for agent pod CRUD operations.
Handles in-cluster and local kubeconfig loading with fallback pattern.
"""

from __future__ import annotations

import logging
from typing import Any

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client import ApiException, CoreV1Api

from botcrew.k8s.pod_spec import build_agent_pod_spec

logger = logging.getLogger(__name__)


async def _load_k8s_config() -> None:
    """Load K8s config: in-cluster if available, local kubeconfig otherwise.

    In production (running inside a K8s pod), load_incluster_config() uses
    the service account token mounted by Kubernetes. In local development,
    fall back to the user's kubeconfig (~/.kube/config).
    """
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except config.ConfigException:
        await config.load_kube_config()
        logger.info("Loaded local kubeconfig")


class PodManager:
    """Manages Kubernetes pod lifecycle for agents.

    Call initialize() once at application startup to load K8s config
    and create the API client. Call close() at shutdown to clean up.

    Args:
        namespace: Kubernetes namespace where agent pods are created.
    """

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self._api: CoreV1Api | None = None

    async def initialize(self) -> None:
        """Load K8s config and create the CoreV1Api client."""
        await _load_k8s_config()
        self._api = client.CoreV1Api()
        logger.info("PodManager initialized for namespace '%s'", self.namespace)

    async def close(self) -> None:
        """Close the K8s API client connection."""
        if self._api is not None:
            await self._api.api_client.close()
            logger.info("PodManager closed")

    async def create_agent_pod(self, agent: Any) -> str:
        """Create a bare K8s pod for an agent.

        Builds the pod spec from the agent's attributes and submits it
        to the Kubernetes API.

        Args:
            agent: Object with id, name, model_provider, model_name attributes.

        Returns:
            The pod name (format: agent-{uuid}).
        """
        assert self._api is not None, "PodManager not initialized"
        pod = build_agent_pod_spec(agent, self.namespace)
        await self._api.create_namespaced_pod(
            namespace=self.namespace,
            body=pod,
        )
        pod_name = f"agent-{agent.id}"
        logger.info("Created pod '%s' in namespace '%s'", pod_name, self.namespace)
        return pod_name

    async def delete_agent_pod(
        self,
        pod_name: str,
        grace_period: int = 30,
    ) -> None:
        """Delete an agent pod with graceful shutdown.

        Handles 404 (pod already gone) silently for idempotent deletes.

        Args:
            pod_name: Name of the pod to delete.
            grace_period: Seconds to wait for graceful termination.
        """
        assert self._api is not None, "PodManager not initialized"
        try:
            await self._api.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
                grace_period_seconds=grace_period,
            )
            logger.info("Deleted pod '%s'", pod_name)
        except ApiException as e:
            if e.status == 404:
                logger.debug("Pod '%s' already deleted (404)", pod_name)
            else:
                raise

    async def get_pod_status(self, pod_name: str) -> str | None:
        """Get the current phase of a pod.

        Args:
            pod_name: Name of the pod to query.

        Returns:
            Pod phase string (Pending, Running, Succeeded, Failed, Unknown),
            or None if the pod does not exist.
        """
        assert self._api is not None, "PodManager not initialized"
        try:
            pod = await self._api.read_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
            )
            return pod.status.phase
        except ApiException as e:
            if e.status == 404:
                return None
            raise

    async def list_agent_pods(self) -> list[Any]:
        """List all agent pods in the namespace.

        Filters by the app=botcrew-agent label selector.

        Returns:
            List of V1Pod objects.
        """
        assert self._api is not None, "PodManager not initialized"
        pods = await self._api.list_namespaced_pod(
            namespace=self.namespace,
            label_selector="app=botcrew-agent",
        )
        return pods.items
