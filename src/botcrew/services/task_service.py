"""Task CRUD service layer.

Provides create, list, get, update, hard-delete, agent/secret/skill
assignment, and append-only notes operations for tasks with cursor-based
pagination.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.task import Task, TaskAgent, TaskSecret, TaskSkill
from botcrew.schemas.pagination import PaginationMeta, decode_cursor
from botcrew.services.channel_service import ChannelService

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task CRUD, assignment, and delete operations.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_task(
        self,
        name: str,
        description: str | None = None,
        directive: str = "",
    ) -> Task:
        """Create a new task with an auto-created channel.

        Creates the DB record and auto-creates a ``#task-<slug>`` shared
        channel via :class:`ChannelService`.

        Args:
            name: Task name (required, max 100 chars).
            description: Optional short description.
            directive: Task directive body (markdown).

        Returns:
            The created Task record.
        """
        task = Task(
            name=name,
            description=description,
            directive=directive,
        )
        self.db.add(task)
        await self.db.flush()

        # Auto-create task channel
        channel_service = ChannelService(self.db)
        channel_name = f"#task-{name.lower().replace(' ', '-')}"
        channel = await channel_service.create_channel(
            name=channel_name,
            description=f"Task channel for {name}",
            channel_type="task",
        )
        task.channel_id = channel.id

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def list_tasks(
        self,
        page_size: int = 20,
        after: str | None = None,
    ) -> tuple[list[Task], PaginationMeta]:
        """List all tasks with cursor-based pagination.

        Args:
            page_size: Maximum number of tasks to return.
            after: Opaque cursor for pagination.

        Returns:
            Tuple of (tasks list, pagination metadata).
        """
        query = select(Task)

        if after:
            cursor_created_at, cursor_id = decode_cursor(after)
            query = query.where(
                (Task.created_at > cursor_created_at)
                | (
                    (Task.created_at == cursor_created_at)
                    & (Task.id > cursor_id)
                )
            )

        query = query.order_by(Task.created_at.asc(), Task.id.asc())
        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        tasks = list(result.scalars().all())

        has_next = len(tasks) > page_size
        if has_next:
            tasks = tasks[:page_size]

        has_prev = after is not None

        return tasks, PaginationMeta(has_next=has_next, has_prev=has_prev)

    async def get_task(self, task_id: str) -> Task | None:
        """Get a task by UUID.

        Args:
            task_id: UUID of the task.

        Returns:
            The Task record, or None if not found.
        """
        result = await self.db.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def update_task(self, task_id: str, **kwargs: object) -> Task:
        """Partial update of a task's fields.

        Updates name, description, directive, and/or status.

        Args:
            task_id: UUID of the task to update.
            **kwargs: Fields to update.

        Returns:
            The updated Task record.

        Raises:
            ValueError: If the task is not found.
        """
        task = await self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        for field, value in kwargs.items():
            if value is not None:
                setattr(task, field, value)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete_task(self, task_id: str) -> None:
        """Hard-delete a task with full cascade.

        Deletion order respects FK constraints:
        1. TaskAgent records
        2. TaskSecret records
        3. TaskSkill records
        4. Channel cleanup (read_cursors, members, messages, channel)
        5. Task record

        Args:
            task_id: UUID of the task to delete.

        Raises:
            ValueError: If the task is not found.
        """
        task = await self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        # 1. Delete TaskAgent records
        await self.db.execute(
            delete(TaskAgent).where(TaskAgent.task_id == task_id)
        )

        # 2. Delete TaskSecret records
        await self.db.execute(
            delete(TaskSecret).where(TaskSecret.task_id == task_id)
        )

        # 3. Delete TaskSkill records
        await self.db.execute(
            delete(TaskSkill).where(TaskSkill.task_id == task_id)
        )

        # 4. Channel cleanup -- clear FK on task first, then delete channel
        if task.channel_id:
            from botcrew.models.channel import Channel, ChannelMember
            from botcrew.models.message import Message
            from botcrew.models.read_cursor import ReadCursor

            channel_id = task.channel_id

            # Clear channel reference on task before deleting channel (FK constraint)
            task.channel_id = None
            await self.db.flush()

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
            await self.db.execute(
                delete(Channel).where(Channel.id == channel_id)
            )

        # 5. Delete task record
        await self.db.delete(task)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Agent assignment
    # ------------------------------------------------------------------

    async def assign_agent(self, task_id: str, agent_id: str) -> TaskAgent:
        """Assign an agent to a task.

        Creates a TaskAgent record and adds the agent to the task
        channel. Catches IntegrityError for duplicate assignments.

        Args:
            task_id: UUID of the task.
            agent_id: UUID of the agent.

        Returns:
            The created TaskAgent record.

        Raises:
            ValueError: If agent is already assigned to this task.
        """
        assignment = TaskAgent(task_id=task_id, agent_id=agent_id)
        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Agent already assigned to this task") from exc

        # Add agent to task channel
        task = await self.get_task(task_id)
        if task and task.channel_id:
            channel_service = ChannelService(self.db)
            try:
                await channel_service.add_member(
                    task.channel_id, agent_id=agent_id
                )
            except ValueError:
                # Already a member -- ignore
                pass

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def list_task_agents(self, task_id: str) -> list[TaskAgent]:
        """List all agent assignments for a task.

        Args:
            task_id: UUID of the task.

        Returns:
            List of TaskAgent records ordered by created_at.
        """
        result = await self.db.execute(
            select(TaskAgent)
            .where(TaskAgent.task_id == task_id)
            .order_by(TaskAgent.created_at.asc())
        )
        return list(result.scalars().all())

    async def remove_agent(self, task_id: str, agent_id: str) -> None:
        """Remove an agent from a task.

        Deletes the TaskAgent record and removes the agent from the
        task channel.

        Args:
            task_id: UUID of the task.
            agent_id: UUID of the agent.

        Raises:
            ValueError: If the assignment does not exist.
        """
        result = await self.db.execute(
            select(TaskAgent).where(
                TaskAgent.task_id == task_id,
                TaskAgent.agent_id == agent_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise ValueError("Agent is not assigned to this task")

        # Delete assignment
        await self.db.delete(assignment)

        # Remove from task channel
        task = await self.get_task(task_id)
        if task and task.channel_id:
            from botcrew.models.channel import ChannelMember

            await self.db.execute(
                delete(ChannelMember).where(
                    ChannelMember.channel_id == task.channel_id,
                    ChannelMember.agent_id == agent_id,
                )
            )

        await self.db.commit()

    # ------------------------------------------------------------------
    # Secret assignment
    # ------------------------------------------------------------------

    async def assign_secret(self, task_id: str, secret_id: str) -> TaskSecret:
        """Assign a secret to a task.

        Creates a TaskSecret record. Catches IntegrityError for
        duplicate assignments.

        Args:
            task_id: UUID of the task.
            secret_id: UUID of the secret.

        Returns:
            The created TaskSecret record.

        Raises:
            ValueError: If secret is already assigned to this task.
        """
        assignment = TaskSecret(task_id=task_id, secret_id=secret_id)
        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Secret already assigned to this task") from exc

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def list_task_secrets(self, task_id: str) -> list[TaskSecret]:
        """List all secret assignments for a task.

        Args:
            task_id: UUID of the task.

        Returns:
            List of TaskSecret records ordered by created_at.
        """
        result = await self.db.execute(
            select(TaskSecret)
            .where(TaskSecret.task_id == task_id)
            .order_by(TaskSecret.created_at.asc())
        )
        return list(result.scalars().all())

    async def remove_secret(self, task_id: str, secret_id: str) -> None:
        """Remove a secret from a task.

        Args:
            task_id: UUID of the task.
            secret_id: UUID of the secret.

        Raises:
            ValueError: If the assignment does not exist.
        """
        result = await self.db.execute(
            select(TaskSecret).where(
                TaskSecret.task_id == task_id,
                TaskSecret.secret_id == secret_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise ValueError("Secret is not assigned to this task")

        await self.db.delete(assignment)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Skill assignment
    # ------------------------------------------------------------------

    async def assign_skill(self, task_id: str, skill_id: str) -> TaskSkill:
        """Assign a skill to a task.

        Creates a TaskSkill record. Catches IntegrityError for
        duplicate assignments.

        Args:
            task_id: UUID of the task.
            skill_id: UUID of the skill.

        Returns:
            The created TaskSkill record.

        Raises:
            ValueError: If skill is already assigned to this task.
        """
        assignment = TaskSkill(task_id=task_id, skill_id=skill_id)
        self.db.add(assignment)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Skill already assigned to this task") from exc

        await self.db.commit()
        await self.db.refresh(assignment)
        return assignment

    async def list_task_skills(self, task_id: str) -> list[TaskSkill]:
        """List all skill assignments for a task.

        Args:
            task_id: UUID of the task.

        Returns:
            List of TaskSkill records ordered by created_at.
        """
        result = await self.db.execute(
            select(TaskSkill)
            .where(TaskSkill.task_id == task_id)
            .order_by(TaskSkill.created_at.asc())
        )
        return list(result.scalars().all())

    async def remove_skill(self, task_id: str, skill_id: str) -> None:
        """Remove a skill from a task.

        Args:
            task_id: UUID of the task.
            skill_id: UUID of the skill.

        Raises:
            ValueError: If the assignment does not exist.
        """
        result = await self.db.execute(
            select(TaskSkill).where(
                TaskSkill.task_id == task_id,
                TaskSkill.skill_id == skill_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise ValueError("Skill is not assigned to this task")

        await self.db.delete(assignment)
        await self.db.commit()

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    async def append_note(
        self, task_id: str, agent_name: str, content: str
    ) -> Task:
        """Append a timestamped note to a task.

        Notes are append-only with a separator between entries.

        Args:
            task_id: UUID of the task.
            agent_name: Display name of the agent adding the note.
            content: Note content text.

        Returns:
            The updated Task record.

        Raises:
            ValueError: If the task is not found.
        """
        task = await self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")

        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {agent_name}:\n{content}"

        if task.notes:
            task.notes = f"{task.notes}\n\n---\n{entry}"
        else:
            task.notes = entry

        await self.db.commit()
        await self.db.refresh(task)
        return task
