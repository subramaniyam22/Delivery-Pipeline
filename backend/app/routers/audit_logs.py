from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from uuid import UUID

from app.db import get_db
from app.deps import get_current_active_user
from app.models import AuditLog, User, Role
from app.schemas import AuditLogListResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def _require_admin_manager(current_user: User) -> None:
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Manager can view audit logs",
        )


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except Exception:
        return False


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    actor_id: Optional[UUID] = None,
    action: Optional[str] = None,
    target: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_admin_manager(current_user)

    query = db.query(AuditLog, User).join(User, User.id == AuditLog.actor_user_id)

    if actor_id:
        query = query.filter(AuditLog.actor_user_id == actor_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    if target_type and target_id:
        normalized = target_type.lower()
        if normalized == "project":
            if _is_uuid(target_id):
                query = query.filter(AuditLog.project_id == UUID(target_id))
        elif normalized == "template":
            query = query.filter(AuditLog.payload_json["template_id"].astext == target_id)
        elif normalized == "user":
            query = query.filter(AuditLog.payload_json["user_id"].astext == target_id)
    elif target:
        conditions = []
        if _is_uuid(target):
            conditions.append(AuditLog.project_id == UUID(target))
        try:
            conditions.append(AuditLog.payload_json["template_id"].astext == target)
            conditions.append(AuditLog.payload_json["user_id"].astext == target)
            conditions.append(AuditLog.payload_json["project_id"].astext == target)
        except Exception:
            pass
        if conditions:
            query = query.filter(or_(*conditions))

    total = query.count()
    offset = (page - 1) * page_size
    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = []
    for log, actor in rows:
        items.append(
            {
                "id": log.id,
                "project_id": log.project_id,
                "actor_user_id": log.actor_user_id,
                "actor": {
                    "id": actor.id,
                    "name": actor.name,
                    "email": actor.email,
                    "role": actor.role.value if hasattr(actor.role, "value") else str(actor.role),
                },
                "action": log.action,
                "payload_json": log.payload_json or {},
                "created_at": log.created_at,
            }
        )

    return {"items": items, "total": total, "page": page, "page_size": page_size}
