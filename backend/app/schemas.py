from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
from app.models import Role, Region, ProjectStatus, Stage, TaskStatus, StageStatus, DefectSeverity, DefectStatus


# ============= User Schemas =============
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Role
    region: Optional[Region] = Region.INDIA
    date_of_joining: Optional[date] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[Role] = None
    region: Optional[Region] = None
    date_of_joining: Optional[date] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    email: EmailStr
    role: Role
    region: Optional[Region] = None
    date_of_joining: Optional[date] = None
    manager_id: Optional[UUID] = None
    is_active: bool
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ============= Auth Schemas =============
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ============= Project Schemas =============
class ProjectCreate(BaseModel):
    title: str
    client_name: str
    priority: str = "MEDIUM"


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[ProjectStatus] = None


class TeamAssignmentRequest(BaseModel):
    pc_user_id: Optional[UUID] = None
    consultant_user_id: Optional[UUID] = None
    builder_user_id: Optional[UUID] = None
    tester_user_id: Optional[UUID] = None


class UserBrief(BaseModel):
    """Brief user info for display in lists"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    email: str
    role: str


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    title: str
    client_name: str
    priority: str
    status: ProjectStatus
    current_stage: Stage
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    # Team Assignments
    pc_user_id: Optional[UUID] = None
    consultant_user_id: Optional[UUID] = None
    builder_user_id: Optional[UUID] = None
    tester_user_id: Optional[UUID] = None
    # Nested user info for display
    creator: Optional[UserBrief] = None
    consultant: Optional[UserBrief] = None
    pc: Optional[UserBrief] = None
    builder: Optional[UserBrief] = None
    tester: Optional[UserBrief] = None


class OnboardingUpdateRequest(BaseModel):
    data: Dict[str, Any]


# ============= Task Schemas =============
class TaskCreate(BaseModel):
    stage: Stage
    title: str
    assignee_user_id: Optional[UUID] = None
    checklist_json: Optional[Dict[str, Any]] = {}


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    assignee_user_id: Optional[UUID] = None
    status: Optional[TaskStatus] = None
    checklist_json: Optional[Dict[str, Any]] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    stage: Stage
    title: str
    assignee_user_id: Optional[UUID]
    status: TaskStatus
    checklist_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ============= Artifact Schemas =============
class ArtifactCreate(BaseModel):
    stage: Stage
    type: str
    notes: Optional[str] = None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    stage: Stage
    type: str
    filename: str
    url: str
    notes: Optional[str]
    uploaded_by_user_id: UUID
    created_at: datetime


# ============= Defect Schemas =============
class DefectCreate(BaseModel):
    severity: DefectSeverity
    description: str
    evidence_json: Optional[Dict[str, Any]] = {}
    external_id: Optional[str] = None


class DefectUpdate(BaseModel):
    severity: Optional[DefectSeverity] = None
    description: Optional[str] = None
    status: Optional[DefectStatus] = None
    evidence_json: Optional[Dict[str, Any]] = None


class DefectValidateRequest(BaseModel):
    validation_result: str  # VALID_DEFECT, INVALID_DEFECT, NEED_RETEST
    notes: Optional[str] = None


class DefectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    external_id: Optional[str]
    severity: DefectSeverity
    status: DefectStatus
    description: str
    evidence_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ============= StageOutput Schemas =============
class StageOutputResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    stage: Stage
    status: StageStatus
    summary: Optional[str]
    structured_output_json: Dict[str, Any]
    required_next_inputs_json: List[Any]
    created_at: datetime


# ============= Workflow Schemas =============
class WorkflowAdvanceRequest(BaseModel):
    notes: Optional[str] = None


class ApprovalRequest(BaseModel):
    notes: Optional[str] = None


class SendBackRequest(BaseModel):
    target_stage: Stage
    reason: str


class StageStatusUpdateRequest(BaseModel):
    status: TaskStatus  # NOT_STARTED, IN_PROGRESS, DONE
    notes: Optional[str] = None


# ============= AdminConfig Schemas =============
class AdminConfigUpdate(BaseModel):
    value_json: Dict[str, Any]


class AdminConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    key: str
    value_json: Dict[str, Any]
    updated_by_user_id: Optional[UUID]
    updated_at: datetime


# ============= Assignment Schemas =============
class AssignmentPublishRequest(BaseModel):
    tasks: List[TaskCreate]
    notes: Optional[str] = None


# ============= Onboarding Data Schemas =============
class ContactInfo(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    is_primary: bool = False


class OnboardingDataCreate(BaseModel):
    contacts: List[ContactInfo] = []
    logo_url: Optional[str] = None
    images: List[str] = []
    copy_text: Optional[str] = None
    use_custom_copy: bool = False
    wcag_compliance_required: bool = True
    wcag_level: str = "AA"
    privacy_policy_url: Optional[str] = None
    privacy_policy_text: Optional[str] = None
    theme_preference: Optional[str] = None
    theme_colors: Optional[Dict[str, str]] = None
    custom_fields: List[Dict[str, Any]] = []


class OnboardingDataUpdate(BaseModel):
    contacts: Optional[List[ContactInfo]] = None
    logo_url: Optional[str] = None
    logo_file_path: Optional[str] = None
    images: Optional[List[Any]] = None  # Can be URLs or file info objects
    copy_text: Optional[str] = None
    use_custom_copy: Optional[bool] = None
    custom_copy_base_price: Optional[int] = None
    custom_copy_word_count: Optional[int] = None
    custom_copy_final_price: Optional[int] = None
    custom_copy_notes: Optional[str] = None
    wcag_compliance_required: Optional[bool] = None
    wcag_level: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    privacy_policy_text: Optional[str] = None
    theme_preference: Optional[str] = None
    selected_template_id: Optional[str] = None
    theme_colors: Optional[Dict[str, str]] = None
    custom_fields: Optional[List[Dict[str, Any]]] = None
    auto_reminder_enabled: Optional[bool] = None


class OnboardingDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    client_access_token: Optional[str] = None
    contacts_json: List[Dict[str, Any]]
    logo_url: Optional[str]
    logo_file_path: Optional[str]
    images_json: List[Any]
    copy_text: Optional[str]
    use_custom_copy: bool
    custom_copy_base_price: Optional[int] = 500
    custom_copy_word_count: Optional[int] = 1000
    custom_copy_final_price: Optional[int]
    custom_copy_notes: Optional[str]
    wcag_compliance_required: bool
    wcag_level: str
    privacy_policy_url: Optional[str]
    privacy_policy_text: Optional[str]
    theme_preference: Optional[str]
    selected_template_id: Optional[str]
    theme_colors_json: Dict[str, Any]
    custom_fields_json: List[Dict[str, Any]]
    completion_percentage: int
    last_reminder_sent: Optional[datetime]
    next_reminder_at: Optional[datetime]
    reminder_count: int
    auto_reminder_enabled: Optional[bool] = True
    created_at: datetime
    updated_at: datetime


# ============= Project Task Schemas =============
class ProjectTaskCreate(BaseModel):
    stage: Stage
    title: str
    description: Optional[str] = None
    is_required: bool = True
    assignee_user_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    order_index: int = 0


class ProjectTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_required: Optional[bool] = None
    status: Optional[TaskStatus] = None
    assignee_user_id: Optional[UUID] = None
    due_date: Optional[datetime] = None
    order_index: Optional[int] = None


class ProjectTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    stage: Stage
    title: str
    description: Optional[str]
    is_predefined: bool
    is_required: bool
    is_auto_completed: Optional[bool] = False
    linked_field: Optional[str] = None
    status: TaskStatus
    assignee_user_id: Optional[UUID]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    order_index: int
    created_by_user_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============= Client Reminder Schemas =============
class ClientReminderCreate(BaseModel):
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    reminder_type: str
    message: str


class ClientReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    recipient_email: str
    recipient_name: Optional[str]
    reminder_type: str
    message: str
    sent_at: datetime
    status: str
