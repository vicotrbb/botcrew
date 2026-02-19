"""Project CRUD service layer.

Provides create, list, get, update, hard-delete, agent assignment,
GitHub sync dispatch, and project-file retrieval operations for
projects with cursor-based pagination.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.project import Project, ProjectAgent, ProjectFile
from botcrew.schemas.pagination import PaginationMeta, decode_cursor
from botcrew.services.channel_service import ChannelService

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path("/workspace/projects")


class ProjectService:
    """Service for project CRUD, assignment, sync, and delete operations.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        goals: str | None = None,
        github_repo_url: str | None = None,
    ) -> Project:
        """Create a new project with an auto-created channel.

        Creates the DB record, auto-creates a ``#project-<slug>`` shared
        channel via :class:`ChannelService`, attempts to create the workspace
        directory on disk, and optionally queues a GitHub clone task.

        Args:
            name: Project name (required, max 100 chars).
            description: Optional project description.
            goals: Optional goals markdown.
            github_repo_url: Optional HTTPS URL to clone.

        Returns:
            The created Project record.
        """
        project = Project(
            name=name,
            description=description,
            goals=goals,
            github_repo_url=github_repo_url,
        )
        self.db.add(project)
        await self.db.flush()

        # Auto-create project channel
        channel_service = ChannelService(self.db)
        channel_name = f"#project-{name.lower().replace(' ', '-')}"
        channel = await channel_service.create_channel(
            name=channel_name,
            description=f"Project channel for {name}",
            channel_type="shared",
        )
        project.channel_id = channel.id

        await self.db.commit()
        await self.db.refresh(project)

        # Create workspace directory (orchestrator may not have PVC access)
        try:
            workspace_dir = WORKSPACE_ROOT / str(project.id) / ".botcrew"
            workspace_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.debug(
                "Could not create workspace dir for project %s "
                "(orchestrator may not have PVC access)",
                project.id,
            )

        # Queue GitHub clone if URL provided
        if github_repo_url:
            from botcrew.tasks.projects import clone_github_repo

            clone_github_repo.delay(str(project.id), github_repo_url)

        return project

    async def list_projects(
        self,
        page_size: int = 20,
        after: str | None = None,
    ) -> tuple[list[Project], PaginationMeta]:
        """List active projects with cursor-based pagination.

        Args:
            page_size: Maximum number of projects to return.
            after: Opaque cursor for pagination.

        Returns:
            Tuple of (projects list, pagination metadata).
        """
        query = select(Project).where(Project.status == "active")

        if after:
            cursor_created_at, cursor_id = decode_cursor(after)
            query = query.where(
                (Project.created_at > cursor_created_at)
                | (
                    (Project.created_at == cursor_created_at)
                    & (Project.id > cursor_id)
                )
            )

        query = query.order_by(Project.created_at.asc(), Project.id.asc())
        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        projects = list(result.scalars().all())

        has_next = len(projects) > page_size
        if has_next:
            projects = projects[:page_size]

        has_prev = after is not None

        return projects, PaginationMeta(has_next=has_next, has_prev=has_prev)

    async def get_project(self, project_id: str) -> Project | None:
        """Get an active project by UUID.

        Args:
            project_id: UUID of the project.

        Returns:
            The Project record, or None if not found or inactive.
        """
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def update_project(self, project_id: str, **kwargs: object) -> Project:
        """Partial update of a project's fields.

        Updates name, description, goals, specs, and/or github_repo_url.
        If goals or specs changed, writes them to workspace ``.botcrew/``
        directory files (guarded -- orchestrator may not have PVC access).

        Args:
            project_id: UUID of the project to update.
            **kwargs: Fields to update.

        Returns:
            The updated Project record.

        Raises:
            ValueError: If the project is not found or inactive.
        """
        project = await self.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        for field, value in kwargs.items():
            if value is not None:
                setattr(project, field, value)

        await self.db.commit()
        await self.db.refresh(project)

        # Write goals/specs to workspace .botcrew/ files
        workspace_botcrew = WORKSPACE_ROOT / str(project.id) / ".botcrew"
        if "goals" in kwargs and kwargs["goals"] is not None:
            try:
                workspace_botcrew.mkdir(parents=True, exist_ok=True)
                (workspace_botcrew / "goals.md").write_text(str(kwargs["goals"]))
            except OSError:
                logger.debug(
                    "Could not write goals.md for project %s", project_id
                )
        if "specs" in kwargs and kwargs["specs"] is not None:
            try:
                workspace_botcrew.mkdir(parents=True, exist_ok=True)
                (workspace_botcrew / "specs.md").write_text(str(kwargs["specs"]))
            except OSError:
                logger.debug(
                    "Could not write specs.md for project %s", project_id
                )

        return project

    async def delete_project(self, project_id: str) -> None:
        """Hard-delete a project with full cascade.

        Deletion order respects FK constraints:
        1. ProjectFile records
        2. ProjectAgent records
        3. Channel cleanup (read_cursors, members, messages, channel)
        4. Queue workspace cleanup Celery task
        5. Project record

        Args:
            project_id: UUID of the project to delete.

        Raises:
            ValueError: If the project is not found.
        """
        project = await self.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")

        # 1. Delete ProjectFile records
        await self.db.execute(
            delete(ProjectFile).where(ProjectFile.project_id == project_id)
        )

        # 2. Delete ProjectAgent records
        await self.db.execute(
            delete(ProjectAgent).where(ProjectAgent.project_id == project_id)
        )

        # 3. Channel cleanup
        if project.channel_id:
            from botcrew.models.channel import ChannelMember
            from botcrew.models.message import Message
            from botcrew.models.read_cursor import ReadCursor

            channel_id = project.channel_id

            await self.db.execute(
                delete(ReadCursor).where(ReadCursor.channel_id == channel_id)
            )
            await self.db.execute(
                delete(ChannelMember).where(
                    ChannelMember.channel_id == channel_id
                )
            )
            await self.db.execute(
                delete(Message).where(Message.channel_id == channel_id)
            )

            from botcrew.models.channel import Channel

            await self.db.execute(
                delete(Channel).where(Channel.id == channel_id)
            )

        # 4. Queue workspace cleanup
        from botcrew.tasks.projects import cleanup_project_workspace

        cleanup_project_workspace.delay(str(project.id))

        # 5. Delete project record
        await self.db.delete(project)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Agent assignment
    # ------------------------------------------------------------------

    async def assign_agent(
        self,
        project_id: str,
        agent_id: str,
        role_prompt: str | None = None,
    ) -> ProjectAgent:
        """Assign an agent to a project.

        Creates a ProjectAgent record and adds the agent to the project
        channel. Catches IntegrityError for duplicate assignments.

        Args:
            project_id: UUID of the project.
            agent_id: UUID of the agent.
            role_prompt: Optional per-project role prompt.

        Returns:
            The created ProjectAgent record.

        Raises:
            ValueError: If agent is already assigned to this project.
        """
        assignment = ProjectAgent(
            project_id=project_id,
            agent_id=agent_id,
            role_prompt=role_prompt,
        )
        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Agent already assigned to this project") from exc

        # Add agent to project channel
        project = await self.get_project(project_id)
        if project and project.channel_id:
            channel_service = ChannelService(self.db)
            try:
                await channel_service.add_member(
                    project.channel_id, agent_id=agent_id
                )
            except ValueError:
                # Already a member -- ignore
                pass

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def list_project_agents(
        self, project_id: str
    ) -> list[ProjectAgent]:
        """List all agent assignments for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of ProjectAgent records ordered by created_at.
        """
        result = await self.db.execute(
            select(ProjectAgent)
            .where(ProjectAgent.project_id == project_id)
            .order_by(ProjectAgent.created_at.asc())
        )
        return list(result.scalars().all())

    async def remove_agent(
        self, project_id: str, agent_id: str
    ) -> None:
        """Remove an agent from a project immediately.

        Deletes the ProjectAgent record and removes the agent from the
        project channel synchronously for immediate UI feedback.

        Args:
            project_id: UUID of the project.
            agent_id: UUID of the agent.

        Raises:
            ValueError: If the assignment does not exist.
        """
        result = await self.db.execute(
            select(ProjectAgent).where(
                ProjectAgent.project_id == project_id,
                ProjectAgent.agent_id == agent_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise ValueError("Agent is not assigned to this project")

        # Delete assignment immediately
        await self.db.delete(assignment)

        # Remove from project channel
        project = await self.get_project(project_id)
        if project and project.channel_id:
            from botcrew.models.channel import ChannelMember

            await self.db.execute(
                delete(ChannelMember).where(
                    ChannelMember.channel_id == project.channel_id,
                    ChannelMember.agent_id == agent_id,
                )
            )

        await self.db.commit()

    # ------------------------------------------------------------------
    # GitHub sync
    # ------------------------------------------------------------------

    async def trigger_sync(self, project_id: str) -> dict:
        """Queue a GitHub pull sync for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            Dict with ``{"status": "sync_queued"}``.

        Raises:
            ValueError: If project not found or has no github_repo_url.
        """
        project = await self.get_project(project_id)
        if project is None:
            raise ValueError(f"Project not found: {project_id}")
        if not project.github_repo_url:
            raise ValueError("Project has no github_repo_url configured")

        from botcrew.tasks.projects import pull_github_repo

        pull_github_repo.delay(str(project.id))
        return {"status": "sync_queued"}

    # ------------------------------------------------------------------
    # Project files
    # ------------------------------------------------------------------

    async def list_project_files(
        self, project_id: str
    ) -> list[ProjectFile]:
        """List all backed-up spec files for a project.

        Args:
            project_id: UUID of the project.

        Returns:
            List of ProjectFile records ordered by path.
        """
        result = await self.db.execute(
            select(ProjectFile)
            .where(ProjectFile.project_id == project_id)
            .order_by(ProjectFile.path.asc())
        )
        return list(result.scalars().all())

    async def get_project_file(
        self, project_id: str, file_id: str
    ) -> ProjectFile | None:
        """Get a single project file by ID, verifying project ownership.

        Args:
            project_id: UUID of the project.
            file_id: UUID of the project file.

        Returns:
            The ProjectFile record, or None if not found or wrong project.
        """
        result = await self.db.execute(
            select(ProjectFile).where(
                ProjectFile.id == file_id,
                ProjectFile.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()
