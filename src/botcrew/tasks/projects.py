"""Celery tasks for project workspace operations.

Handles GitHub clone/pull, workspace cleanup, and delayed agent removal
finalization. All tasks are sync (Celery workers are sync processes).
"""

import logging
import os
import shutil
import subprocess

import sqlalchemy
from botcrew.tasks.celery_app import celery_app
from sqlalchemy.orm import Session

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


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def finalize_agent_removal(self, project_id: str, agent_id: str) -> dict:
    """Finalize agent removal from a project after grace period.

    Called with countdown=60 by ProjectService to give the agent time to
    wrap up. Creates its own sync DB session (Celery workers are sync).

    Removes:
    - ProjectAgent record linking agent to project
    - ChannelMember record for the agent in the project channel

    Args:
        project_id: UUID string of the project.
        agent_id: UUID string of the agent.

    Returns:
        Dict with status, project_id, and agent_id.
    """
    try:
        from botcrew.config import get_settings

        settings = get_settings()

        # Build sync DB URL from async URL
        sync_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
        engine = sqlalchemy.create_engine(sync_url)

        with Session(engine) as session:
            # Delete ProjectAgent record
            session.execute(
                sqlalchemy.text(
                    "DELETE FROM project_agents "
                    "WHERE project_id = :project_id AND agent_id = :agent_id"
                ),
                {"project_id": project_id, "agent_id": agent_id},
            )

            # Find project channel_id and remove agent from channel membership
            row = session.execute(
                sqlalchemy.text(
                    "SELECT channel_id FROM projects WHERE id = :project_id"
                ),
                {"project_id": project_id},
            ).fetchone()

            if row and row[0]:
                channel_id = row[0]
                session.execute(
                    sqlalchemy.text(
                        "DELETE FROM channel_members "
                        "WHERE channel_id = :channel_id AND agent_id = :agent_id"
                    ),
                    {"channel_id": channel_id, "agent_id": agent_id},
                )

            session.commit()

        engine.dispose()

        logger.info(
            "Finalized removal of agent %s from project %s",
            agent_id,
            project_id,
        )
        return {"status": "removed", "project_id": project_id, "agent_id": agent_id}

    except Exception as exc:
        logger.warning(
            "Finalize removal failed for agent %s project %s (attempt %d/%d): %s",
            agent_id,
            project_id,
            self.request.retries + 1,
            self.max_retries + 1,
            str(exc),
        )
        raise self.retry(exc=exc)
