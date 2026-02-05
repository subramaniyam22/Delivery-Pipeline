from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User, Role, Region
from app.schemas import UserCreate, UserResponse, UserUpdate
from app.deps import get_current_active_user
from app.auth import hash_password
from app.rbac import check_full_access
from typing import List
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user's information"""
    return current_user


@router.post("/seed", response_model=UserResponse)
def seed_admin_user(db: Session = Depends(get_db)):
    """
    Seed initial admin user
    Only works if no users exist in the database
    """
    # Check if any users exist
    existing_users = db.query(User).count()
    if existing_users > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users already exist. Cannot seed admin user."
        )
    
    # Create admin user
    admin = User(
        name="Admin User",
        email="admin@delivery.com",
        password_hash=hash_password("admin123"),
        role=Role.ADMIN,
        region=Region.US,
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return admin


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new user (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can create users"
        )
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        region=data.region or Region.INDIA,
        date_of_joining=data.date_of_joining,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all active (non-archived) users (Admin/Manager/Sales only for view)"""
    if not check_full_access(current_user.role) and current_user.role != Role.SALES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, and Sales can list users"
        )
    
    users = db.query(User).filter(User.is_archived == False).all()
    return users


@router.get("/archived", response_model=List[UserResponse])
def list_archived_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all archived users (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can list archived users"
        )
    
    users = db.query(User).filter(User.is_archived == True).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user by ID (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can view user details"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can update users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Archive user (Admin only) - moves user to archived section"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can archive users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot archive yourself"
        )
    
    user.is_archived = True
    user.is_active = False
    user.archived_at = datetime.utcnow()
    db.commit()
    
    return None


@router.post("/{user_id}/reactivate", response_model=UserResponse)
def reactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reactivate an archived user (Admin only)"""
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can reactivate users"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not archived"
        )
    
    user.is_archived = False
    user.is_active = True
    user.archived_at = None
    db.commit()
    db.refresh(user)
    
    return user


# ============== Manager Assignment Endpoints ==============

@router.get("/by-role/{role}")
def get_users_by_role(
    role: Role,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all active users by role"""
    users = db.query(User).filter(
        User.role == role,
        User.is_active == True,
        User.is_archived == False
    ).all()
    
    return [
        {
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "region": u.region.value if u.region else None
        }
        for u in users
    ]


@router.get("/managers/list")
def list_managers(
    region: Region = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all managers, optionally filtered by region"""
    query = db.query(User).filter(
        User.role == Role.MANAGER,
        User.is_active == True,
        User.is_archived == False
    )
    
    if region:
        query = query.filter(User.region == region)
    
    managers = query.all()
    
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "email": m.email,
            "region": m.region.value if m.region else None,
            "team_count": len([u for u in m.team_members if u.is_active])
        }
        for m in managers
    ]


@router.post("/{user_id}/assign-manager")
def assign_manager(
    user_id: UUID,
    manager_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Assign a manager to a user (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can assign managers"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Only certain roles can have managers
    if user.role not in [Role.CONSULTANT, Role.PC, Role.BUILDER, Role.TESTER]:
        raise HTTPException(
            status_code=400, 
            detail="Only Consultant, PC, Builder, and Tester can be assigned to a manager"
        )
    
    manager = db.query(User).filter(User.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    if manager.role != Role.MANAGER:
        raise HTTPException(status_code=400, detail="Selected user is not a manager")
    
    user.manager_id = manager_id
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"{user.name} assigned to manager {manager.name}",
        "user_id": str(user.id),
        "manager_id": str(manager.id)
    }


@router.delete("/{user_id}/remove-manager")
def remove_manager(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove manager assignment from a user (Admin/Manager only)"""
    if not check_full_access(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin and Manager can remove manager assignments"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.manager_id = None
    db.commit()
    
    return {"message": f"Manager removed from {user.name}"}


@router.get("/managers/{manager_id}/team")
def get_manager_team(
    manager_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get team members for a manager (Admin/Manager only, or the manager themselves)"""
    manager = db.query(User).filter(User.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # Check access
    if current_user.role not in [Role.ADMIN, Role.MANAGER]:
        if current_user.id != manager_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    team_members = db.query(User).filter(
        User.manager_id == manager_id,
        User.is_active == True,
        User.is_archived == False
    ).all()
    
    return [
        {
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "region": u.region.value if u.region else None
        }
        for u in team_members
    ]


@router.get("/my-team")
def get_my_team(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get my team members (for managers)"""
    if current_user.role != Role.MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can view their team"
        )
    
    team_members = db.query(User).filter(
        User.manager_id == current_user.id,
        User.is_active == True,
        User.is_archived == False
    ).all()
    
    return [
        {
            "id": str(u.id),
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "region": u.region.value if u.region else None,
            "date_of_joining": u.date_of_joining.isoformat() if u.date_of_joining else None
        }
        for u in team_members
    ]
