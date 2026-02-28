import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from uuid import UUID

from app.db import get_db
from app.deps import get_current_active_user
from app.models import AuditLog, User, Role
from app.schemas import AuditLogListResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def _require_admin_manager(current_user: User) -> None:
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Manager can view audit logs",
        )


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value).strip())
        return True
    except (ValueError, TypeError):
        return False


def _apply_audit_log_filters(query, actor_id=None, action=None, target=None, target_type=None, target_id=None, start_date=None, end_date=None):
    """Apply filters to an AuditLog query (or joined query). Returns the query."""
    if actor_id:
        query = query.filter(AuditLog.actor_user_id == actor_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    if target_type and target_id:
        target_id = str(target_id).strip()
        normalized = str(target_type).lower()
        if normalized == "project" and _is_uuid(target_id):
            query = query.filter(AuditLog.project_id == UUID(target_id))
        elif normalized == "template":
            query = query.filter(AuditLog.payload_json["template_id"].astext == target_id)
        elif normalized == "user":
            query = query.filter(AuditLog.payload_json["user_id"].astext == target_id)
    elif target:
        target = str(target).strip()
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
    return query


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

    try:
        # Count on AuditLog only to avoid join/count issues that can cause 500
        base = db.query(AuditLog)
        base = _apply_audit_log_filters(base, actor_id, action, target, target_type, target_id, start_date, end_date)
        total = base.count()

        # Fetch page of rows with User join for actor info
        query = db.query(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_user_id)
        query = _apply_audit_log_filters(query, actor_id, action, target, target_type, target_id, start_date, end_date)
        offset = (page - 1) * page_size
        rows = (
            query.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        items = []
        for log, actor in rows:
            actor_info = None
            if actor is not None:
                try:
                    role_str = actor.role.value if hasattr(actor.role, "value") else str(actor.role)
                except Exception:
                    role_str = str(getattr(actor.role, "value", actor.role))
                actor_info = {
                    "id": actor.id,
                    "name": actor.name or "Unknown",
                    "email": actor.email or "",
                    "role": role_str,
                }
            items.append(
                {
                    "id": log.id,
                    "project_id": log.project_id,
                    "actor_user_id": log.actor_user_id,
                    "actor": actor_info,
                    "action": log.action,
                    "payload_json": log.payload_json if isinstance(log.payload_json, dict) else {},
                    "created_at": log.created_at,
                }
            )

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_audit_logs failed: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load audit logs") from e
