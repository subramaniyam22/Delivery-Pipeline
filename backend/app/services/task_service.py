from sqlalchemy.orm import Session
from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskUpdate
from typing import Optional, List
from uuid import UUID


def create_task(db: Session, project_id: UUID, data: TaskCreate, user) -> Task:
    """Create a new task"""
    task = Task(
        project_id=project_id,
        stage=data.stage,
        title=data.title,
        assignee_user_id=data.assignee_user_id,
        status=TaskStatus.NOT_STARTED,
        checklist_json=data.checklist_json or {}
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_tasks_by_project(db: Session, project_id: UUID) -> List[Task]:
    """Get all tasks for a project"""
    return db.query(Task).filter(Task.project_id == project_id).all()


def update_task(db: Session, task_id: UUID, data: TaskUpdate, user) -> Optional[Task]:
    """Update a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: UUID) -> bool:
    """Delete a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False
    
    db.delete(task)
    db.commit()
    return True
