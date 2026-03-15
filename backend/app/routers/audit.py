"""Audit log router for regulatory compliance."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import require_roles
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("government_official", "admin")),
):
    """Retrieve immutable audit logs (government / admin only)."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)
    if action:
        query = query.where(AuditLog.action == action)

    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "actor_role": log.actor_role,
            "changes": log.changes,
            "metadata": log.extra_metadata,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
