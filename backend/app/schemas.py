from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, date
from uuid import UUID
from app.models import Role, Region, ProjectStatus, Stage, TaskStatus, StageStatus, DefectSeverity, DefectStatus, OnboardingReviewStatus, JobRunStatus


# ============= User Schemas =============
class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="User's full name")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 characters)")
    role: Role
    region: Optional[Region] = Region.INDIA
    date_of_joining: Optional[date] = None
    
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace')
        return v.strip()
    
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


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
    title: str = Field(..., min_length=3, max_length=500, description="Project title")
    description: Optional[str] = None
    client_name: str = Field(..., min_length=2, max_length=255, description="Client name")
    priority: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    pmc_name: Optional[str] = Field(None, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    location_names: Optional[List[str]] = None
    client_email_ids: Optional[str] = Field(None, max_length=1000)
    project_type: Optional[str] = Field(None, max_length=50)
    estimated_revenue_usd: Optional[float] = Field(None, ge=0, description="Estimated revenue in USD for dashboard")
    status: Optional[ProjectStatus] = ProjectStatus.DRAFT
    
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip()
    
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Client name cannot be empty or whitespace')
        return v.strip()


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[ProjectStatus] = None
    current_stage: Optional[Stage] = None
    project_type: Optional[str] = None
    minimum_requirements_override: Optional[List[str]] = None
    allow_requirements_exceptions: Optional[bool] = None
    require_manual_review: Optional[bool] = None
    pmc_name: Optional[str] = None
    location: Optional[str] = None
    location_names: Optional[List[str]] = None
    client_email_ids: Optional[str] = None
    estimated_revenue_usd: Optional[float] = None
    manager_user_id: Optional[UUID] = None


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
    description: Optional[str] = None
    client_name: str
    priority: str
    status: ProjectStatus
    project_type: Optional[str] = None
    current_stage: Stage
    estimated_revenue_usd: Optional[float] = None
    region: Optional[Region] = None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    onboarding_updated_at: Optional[datetime] = None
    has_new_updates: Optional[bool] = False
    completion_percentage: Optional[int] = 0
    # Team Assignments
    pc_user_id: Optional[UUID] = None
    consultant_user_id: Optional[UUID] = None
    builder_user_id: Optional[UUID] = None
    tester_user_id: Optional[UUID] = None
    minimum_requirements_override: Optional[List[str]] = None
    allow_requirements_exceptions: Optional[bool] = None
    # Agent handling (when project created or advanced by an agent)
    created_by_agent_type: Optional[str] = None
    last_handled_by_agent_type: Optional[str] = None
    # Nested user info for display
    creator: Optional[UserBrief] = None
    consultant: Optional[UserBrief] = None
    pc: Optional[UserBrief] = None
    builder: Optional[UserBrief] = None
    tester: Optional[UserBrief] = None
    
    # Sales Fields
    pmc_name: Optional[str] = None
    location: Optional[str] = None
    location_names: Optional[List[str]] = None
    client_email_ids: Optional[str] = None
    sales_user_id: Optional[UUID] = None
    manager_user_id: Optional[UUID] = None
    stage_history: Optional[List[Dict[str, Any]]] = None
    hitl_enabled: Optional[bool] = False
    pending_approvals_count: Optional[int] = 0
    pending_approvals: Optional[List[Dict[str, Any]]] = None
    
    sales_rep: Optional[UserBrief] = None
    manager_chk: Optional[UserBrief] = None

    # Autonomous pipeline: hold/review/blockers/defect loop
    hold_reason: Optional[str] = None
    needs_review_reason: Optional[str] = None
    blockers_json: Optional[List[str]] = None
    defect_cycle_count: Optional[int] = 0


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
    artifact_type: Optional[str] = None
    notes: Optional[str] = None


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    project_id: UUID
    stage: Stage
    type: str
    artifact_type: Optional[str]
    filename: str
    url: str
    storage_key: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    notes: Optional[str]
    metadata_json: Optional[Dict[str, Any]] = None
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
    job_run_id: Optional[UUID]
    stage: Stage
    status: StageStatus
    gate_decision: Optional[str]
    score: Optional[float]
    report_json: Optional[Dict[str, Any]] = None
    evidence_links_json: Optional[List[Any]] = None
    summary: Optional[str]
    structured_output_json: Dict[str, Any]
    required_next_inputs_json: List[Any]
    created_at: datetime


# ============= JobRun Schemas =============
class JobEnqueueRequest(BaseModel):
    payload_json: Optional[Dict[str, Any]] = None


class JobRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    stage: Stage
    status: JobRunStatus
    attempts: int
    max_attempts: int
    payload_json: Dict[str, Any]
    error_json: Dict[str, Any]
    request_id: Optional[str]
    actor_user_id: Optional[UUID]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    next_run_at: datetime
    locked_by: Optional[str]
    locked_at: Optional[datetime]


# ============= ProjectConfig Schemas =============
class ProjectConfigUpdate(BaseModel):
    stage_gates_json: Optional[Dict[str, Any]] = None
    thresholds_json: Optional[Dict[str, Any]] = None
    hitl_enabled: Optional[bool] = None


class ProjectConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    stage_gates_json: Optional[Dict[str, Any]]
    thresholds_json: Optional[Dict[str, Any]]
    hitl_enabled: bool
    updated_at: datetime


# ============= Template Registry Schemas =============
class TemplateCreate(BaseModel):
    name: str
    repo_url: Optional[str] = None
    default_branch: Optional[str] = "main"
    meta_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    features_json: Optional[List[str]] = None
    preview_url: Optional[str] = None
    source_type: Optional[str] = "ai"
    intent: Optional[str] = None
    preview_status: Optional[str] = None
    preview_last_generated_at: Optional[datetime] = None
    preview_error: Optional[str] = None
    preview_thumbnail_url: Optional[str] = None
    is_active: Optional[bool] = True
    is_published: Optional[bool] = True
    category: Optional[str] = None
    style: Optional[str] = None
    feature_tags_json: Optional[List[str]] = None
    status: Optional[str] = "draft"
    is_default: Optional[bool] = False
    is_recommended: Optional[bool] = False
    repo_path: Optional[str] = None
    pages_json: Optional[List[Any]] = None
    required_inputs_json: Optional[List[Any]] = None
    optional_inputs_json: Optional[List[Any]] = None
    default_config_json: Optional[Dict[str, Any]] = None
    rules_json: Optional[List[Any]] = None
    validation_results_json: Optional[Dict[str, Any]] = None
    version: Optional[int] = 1
    changelog: Optional[str] = None
    parent_template_id: Optional[UUID] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    repo_url: Optional[str] = None
    default_branch: Optional[str] = None
    meta_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    features_json: Optional[List[str]] = None
    preview_url: Optional[str] = None
    source_type: Optional[str] = None
    intent: Optional[str] = None
    preview_status: Optional[str] = None
    preview_last_generated_at: Optional[datetime] = None
    preview_error: Optional[str] = None
    preview_thumbnail_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None
    category: Optional[str] = None
    style: Optional[str] = None
    feature_tags_json: Optional[List[str]] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None
    is_recommended: Optional[bool] = None
    repo_path: Optional[str] = None
    pages_json: Optional[List[Any]] = None
    required_inputs_json: Optional[List[Any]] = None
    optional_inputs_json: Optional[List[Any]] = None
    default_config_json: Optional[Dict[str, Any]] = None
    rules_json: Optional[List[Any]] = None
    validation_results_json: Optional[Dict[str, Any]] = None
    version: Optional[int] = None
    changelog: Optional[str] = None
    parent_template_id: Optional[UUID] = None


class SetRecommendedBody(BaseModel):
    value: bool


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    repo_url: Optional[str] = None
    default_branch: Optional[str] = None
    meta_json: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    features_json: Optional[List[str]] = None
    preview_url: Optional[str] = None
    source_type: str
    intent: Optional[str] = None
    preview_status: str
    preview_last_generated_at: Optional[datetime] = None
    preview_error: Optional[str] = None
    preview_thumbnail_url: Optional[str] = None
    created_at: datetime
    is_active: bool
    is_published: bool
    category: Optional[str] = None
    style: Optional[str] = None
    feature_tags_json: Optional[List[str]] = None
    status: Optional[str] = "draft"
    is_default: Optional[bool] = False
    is_recommended: Optional[bool] = False
    repo_path: Optional[str] = None
    pages_json: Optional[List[Any]] = None
    required_inputs_json: Optional[List[Any]] = None
    optional_inputs_json: Optional[List[Any]] = None
    default_config_json: Optional[Dict[str, Any]] = None
    rules_json: Optional[List[Any]] = None
    validation_results_json: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    validation_last_run_at: Optional[datetime] = None
    validation_hash: Optional[str] = None
    version: Optional[int] = 1
    changelog: Optional[str] = None
    parent_template_id: Optional[UUID] = None
    blueprint_json: Optional[Dict[str, Any]] = None
    blueprint_schema_version: Optional[int] = 1
    blueprint_quality_json: Optional[Dict[str, Any]] = None
    prompt_log_json: Optional[List[Any]] = None
    blueprint_hash: Optional[str] = None
    performance_metrics_json: Optional[Dict[str, Any]] = None
    is_deprecated: Optional[bool] = False
    build_source_type: Optional[str] = None  # blueprint | s3_zip | git
    build_source_ref: Optional[str] = None  # S3 key or git ref


# ============= ConfirmationRequest Schemas =============
class ConfirmationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    type: str
    title: str
    description: Optional[str] = None
    status: str
    requested_at: datetime
    decided_at: Optional[datetime] = None
    decided_by: Optional[UUID] = None
    decision_comment: Optional[str] = None
    reminder_count: int = 0
    last_reminded_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None


class ConfirmationDecideRequest(BaseModel):
    approve: bool  # True = approved, False = rejected
    comment: str = Field(..., min_length=1, description="Required when approving or rejecting")


# ============= PolicyConfig Schemas =============
class PolicyConfigValue(BaseModel):
    reminder_cadence_hours: Optional[int] = 24
    max_reminders: Optional[int] = 10
    idle_minutes: Optional[int] = 30
    build_retry_cap: Optional[int] = 3
    defect_validation_cycle_cap: Optional[int] = 5
    pass_threshold_percent: Optional[int] = 98
    lighthouse_thresholds_json: Optional[Dict[str, Any]] = None  # perf, a11y, bp, seo (min 90)
    axe_policy_json: Optional[Dict[str, Any]] = None  # block serious/critical; medium/minor <5 callouts
    proof_pack_soft_mb: Optional[int] = 50
    proof_pack_hard_mb: Optional[int] = 200


class PolicyConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    key: str
    value_json: Dict[str, Any]
    updated_at: datetime


# ============= Sentiment Schemas =============
class SentimentCreate(BaseModel):
    rating: int
    comment: Optional[str] = None


class SentimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    rating: int
    comment: Optional[str]
    submitted_at: datetime
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    stage_at_delivery: Optional[str] = None
    created_by_user_id: Optional[UUID] = None
    created_by_type: Optional[str] = None
    project_title: Optional[str] = None
    client_name: Optional[str] = None


# ============= Delivery Outcome Schemas (Prompt 9) =============
class DeliveryOutcomeCreate(BaseModel):
    template_registry_id: Optional[UUID] = None
    cycle_time_days: Optional[int] = None
    defect_count: int = 0
    reopened_defects_count: int = 0
    on_time_delivery: Optional[bool] = None
    final_quality_score: Optional[float] = None


class DeliveryOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    template_registry_id: Optional[UUID] = None
    cycle_time_days: Optional[int] = None
    defect_count: int
    reopened_defects_count: int
    on_time_delivery: Optional[bool] = None
    final_quality_score: Optional[float] = None
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
class PreviewStrategy(str, Enum):
    zip_only = "zip_only"
    serve_static_preview = "serve_static_preview"


class AdminConfigUpdate(BaseModel):
    value_json: Any
    version: Optional[int] = None


class AdminConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    key: str
    value_json: Any
    config_version: int
    updated_by_user_id: Optional[UUID]
    updated_at: datetime


# ============= Audit Log Schemas =============
class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: Optional[UUID]
    actor_user_id: UUID
    actor: Optional[UserBrief] = None
    action: str
    payload_json: Dict[str, Any]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


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
    wcag_confirmed: bool = False
    privacy_policy_url: Optional[str] = None
    privacy_policy_text: Optional[str] = None
    theme_preference: Optional[str] = None
    theme_colors: Optional[Dict[str, str]] = None
    custom_fields: List[Dict[str, Any]] = []
    requirements: Optional[Dict[str, Any]] = None


class OnboardingReviewAction(BaseModel):
    action: str  # APPROVE, REJECT, REQUEST_CHANGES
    notes: Optional[str] = None


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
    wcag_confirmed: Optional[bool] = None
    privacy_policy_url: Optional[str] = None
    privacy_policy_text: Optional[str] = None
    theme_preference: Optional[str] = None
    selected_template_id: Optional[str] = None
    theme_colors: Optional[Dict[str, str]] = None
    custom_fields: Optional[List[Dict[str, Any]]] = None
    auto_reminder_enabled: Optional[bool] = None
    requirements: Optional[Dict[str, Any]] = None
    # Per-field sentinels: NOT_APPLICABLE | NOT_NEEDED (counts as provided)
    field_sentinels: Optional[Dict[str, str]] = None


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
    wcag_confirmed: Optional[bool] = None
    privacy_policy_url: Optional[str]
    privacy_policy_text: Optional[str]
    theme_preference: Optional[str]
    selected_template_id: Optional[str]
    theme_colors_json: Dict[str, Any]
    custom_fields_json: List[Dict[str, Any]]
    requirements_json: Dict[str, Any]
    completion_percentage: int
    field_sentinels_json: Dict[str, str] = {}
    field_tooltip: Optional[str] = "Each required field must have a value or be marked Not Applicable / Not Needed."
    last_reminder_sent: Optional[datetime]
    next_reminder_at: Optional[datetime]
    reminder_count: int
    auto_reminder_enabled: Optional[bool] = True
    reminder_interval_hours: Optional[int] = 24
    submitted_at: Optional[datetime] = None
    missing_fields_eta_json: Optional[Dict[str, str]] = None
    last_content_update_at: Optional[datetime] = None
    
    review_status: OnboardingReviewStatus = OnboardingReviewStatus.PENDING
    ai_review_notes: Optional[str] = None
    consultant_review_notes: Optional[str] = None
    
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
    reminder_type: str = "onboarding"
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
