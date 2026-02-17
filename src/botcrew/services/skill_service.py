"""Skill CRUD service layer.

Provides create, list, get (by ID and name), update, and soft-delete
operations for skills with cursor-based pagination.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from botcrew.models.skill import Skill
from botcrew.schemas.pagination import PaginationMeta, decode_cursor

logger = logging.getLogger(__name__)


class SkillService:
    """Service for skill CRUD operations with pagination.

    Args:
        db: Async SQLAlchemy session for database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_skill(
        self,
        name: str,
        description: str,
        body: str,
    ) -> Skill:
        """Create a new skill with a normalised (lowercase) name.

        Args:
            name: Skill name (will be stripped and lowercased).
            description: Short description (max 250 chars).
            body: Full skill body in markdown.

        Returns:
            The created Skill record.

        Raises:
            ValueError: If a skill with the same name already exists.
        """
        skill = Skill(
            name=name.strip().lower(),
            description=description,
            body=body,
        )
        self.db.add(skill)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError(
                f"Skill with name '{name.strip().lower()}' already exists"
            ) from exc
        await self.db.refresh(skill)
        return skill

    async def list_skills(
        self,
        page_size: int = 20,
        after: str | None = None,
    ) -> tuple[list[Skill], PaginationMeta]:
        """List active skills with cursor-based pagination.

        Args:
            page_size: Maximum number of skills to return.
            after: Opaque cursor for pagination.

        Returns:
            Tuple of (skills list, pagination metadata).
        """
        query = select(Skill).where(Skill.is_active.is_(True))

        if after:
            cursor_created_at, cursor_id = decode_cursor(after)
            query = query.where(
                (Skill.created_at > cursor_created_at)
                | (
                    (Skill.created_at == cursor_created_at)
                    & (Skill.id > cursor_id)
                )
            )

        query = query.order_by(Skill.created_at.asc(), Skill.id.asc())
        query = query.limit(page_size + 1)

        result = await self.db.execute(query)
        skills = list(result.scalars().all())

        has_next = len(skills) > page_size
        if has_next:
            skills = skills[:page_size]

        has_prev = after is not None

        return skills, PaginationMeta(has_next=has_next, has_prev=has_prev)

    async def get_skill(self, skill_id: str) -> Skill | None:
        """Get an active skill by UUID.

        Args:
            skill_id: UUID of the skill.

        Returns:
            The Skill record, or None if not found or inactive.
        """
        result = await self.db.execute(
            select(Skill).where(Skill.id == skill_id, Skill.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def get_skill_by_name(self, name: str) -> Skill | None:
        """Get an active skill by name (lowercase match).

        Args:
            name: Skill name (will be lowercased for lookup).

        Returns:
            The Skill record, or None if not found or inactive.
        """
        result = await self.db.execute(
            select(Skill).where(
                Skill.name == name.lower(), Skill.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def update_skill(self, skill_id: str, **kwargs: object) -> Skill:
        """Partial update of a skill's fields.

        Args:
            skill_id: UUID of the skill to update.
            **kwargs: Fields to update (name, description, body).

        Returns:
            The updated Skill record.

        Raises:
            ValueError: If the skill is not found or inactive.
        """
        skill = await self.get_skill(skill_id)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_id}")

        for field, value in kwargs.items():
            if value is not None:
                if field == "name":
                    value = str(value).strip().lower()
                setattr(skill, field, value)

        await self.db.commit()
        await self.db.refresh(skill)
        return skill

    async def delete_skill(self, skill_id: str) -> None:
        """Soft-delete a skill by setting is_active to False.

        Args:
            skill_id: UUID of the skill to deactivate.

        Raises:
            ValueError: If the skill is not found or already inactive.
        """
        skill = await self.get_skill(skill_id)
        if skill is None:
            raise ValueError(f"Skill not found: {skill_id}")

        skill.is_active = False
        await self.db.commit()
