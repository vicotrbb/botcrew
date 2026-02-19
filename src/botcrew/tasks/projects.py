"""Celery tasks for project workspace operations.

Handles GitHub clone/pull and workspace cleanup.
All tasks are sync (Celery workers are sync processes).
"""

import logging
import os
import shutil
import subprocess

from botcrew.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=120,
)
def clone_github_repo(self, project_id: str, repo_url: str) -> dict:
    """Clone a GitHub repository into the project workspace.

    Creates the project directory structure and clones the repo into it.
    Uses GIT_TERMINAL_PROMPT=0 to prevent hanging on auth prompts.

    Args:
        project_id: UUID string of the project.
        repo_url: HTTPS URL of the GitHub repository.

    Returns:
        Dict with status and project_id.
    """
    workspace_path = f"/workspace/projects/{project_id}"
    botcrew_dir = os.path.join(workspace_path, ".botcrew")

    os.makedirs(workspace_path, exist_ok=True)
    os.makedirs(botcrew_dir, exist_ok=True)

    try:
        result = subprocess.run(
            ["git", "clone", repo_url, "."],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr}")
        return {"status": "cloned", "project_id": project_id}
    except Exception as exc:
        logger.warning(
            "Clone failed for project %s (attempt %d/%d): %s",
            project_id,
            self.request.retries + 1,
            self.max_retries + 1,
            str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1)
def pull_github_repo(self, project_id: str) -> dict:
    """Pull latest changes from remote into project workspace.

    Uses fast-forward only to avoid merge conflicts. If a conflict occurs,
    returns an error status instead of retrying (user must handle).

    Args:
        project_id: UUID string of the project.

    Returns:
        Dict with status (pulled/conflict) and project_id.
    """
    workspace_path = f"/workspace/projects/{project_id}"

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        if result.returncode != 0:
            return {"status": "conflict", "error": result.stderr}
        return {"status": "pulled", "project_id": project_id}
    except Exception as exc:
        logger.warning(
            "Pull failed for project %s: %s",
            project_id,
            str(exc),
        )
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=1)
def cleanup_project_workspace(self, project_id: str) -> dict:
    """Remove project directory from workspace PVC.

    Args:
        project_id: UUID string of the project.

    Returns:
        Dict with status and project_id.
    """
    workspace_path = f"/workspace/projects/{project_id}"

    try:
        if os.path.exists(workspace_path):
            shutil.rmtree(workspace_path)
        return {"status": "cleaned", "project_id": project_id}
    except Exception as exc:
        logger.warning(
            "Cleanup failed for project %s: %s",
            project_id,
            str(exc),
        )
        raise self.retry(exc=exc)


