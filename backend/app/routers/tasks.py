from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Task
from app.schemas import TaskCreate, TaskResponse, TaskUpdate
from app.deps import get_current_active_user
from app.services import task_service
from app.rbac import check_full_access
from typing import List
from uuid import UUID

router = APIRouter(prefix="/projects", tags=["tasks"])


@router.post("/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: UUID,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create task (PC/Admin/Manager)"""
    allowed_roles = [Role.PC, Role.ADMIN, Role.MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only PC, Admin, and Manager can create tasks"
        )
    
    task = task_service.create_task(db, project_id, data, current_user)
    return task


@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
def list_tasks(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all tasks for a project (all authenticated users)"""
    tasks = task_service.get_tasks_by_project(db, project_id)
    return tasks


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update task
    - PC/Admin/Manager can update any field
    - Assignee can update status only
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check permissions
    allowed_roles = [Role.PC, Role.ADMIN, Role.MANAGER]
    is_assignee = task.assignee_user_id == current_user.id
    
    if current_user.role not in allowed_roles and not is_assignee:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this task"
        )
    
    # If assignee but not PC/Admin/Manager, can only update status
    if is_assignee and current_user.role not in allowed_roles:
        if data.title is not None or data.assignee_user_id is not None or data.checklist_json is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assignees can only update task status"
            )
    
    updated_task = task_service.update_task(db, task_id, data, current_user)
    return updated_task


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete task (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can delete tasks"
        )
    
    success = task_service.delete_task(db, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    return None
