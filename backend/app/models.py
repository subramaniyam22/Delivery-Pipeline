import enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db import Base


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CONSULTANT = "CONSULTANT"
    PC = "PC"
    BUILDER = "BUILDER"
    TESTER = "TESTER"


class Region(str, enum.Enum):
    INDIA = "INDIA"
    US = "US"
    PH = "PH"


class ProjectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Stage(str, enum.Enum):
    ONBOARDING = "ONBOARDING"
    ASSIGNMENT = "ASSIGNMENT"
    BUILD = "BUILD"
    TEST = "TEST"
    DEFECT_VALIDATION = "DEFECT_VALIDATION"
    COMPLETE = "COMPLETE"


class TaskStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class StageStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class DefectSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DefectStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALID = "VALID"
    INVALID = "INVALID"
    FIXED = "FIXED"
    RETEST = "RETEST"


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(Role), nullable=False)
    region = Column(Enum(Region), default=Region.INDIA, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    created_projects = relationship("Project", back_populates="creator", foreign_keys="Project.created_by_user_id")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_user_id")
    uploaded_artifacts = relationship("Artifact", back_populates="uploader")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    client_name = Column(String(255), nullable=False)
    priority = Column(String(50), default="MEDIUM")
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)
    current_stage = Column(Enum(Stage), default=Stage.ONBOARDING, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = relationship("User", back_populates="created_projects", foreign_keys=[created_by_user_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    stage_outputs = relationship("StageOutput", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")
    onboarding_data = relationship("OnboardingData", back_populates="project", uselist=False, cascade="all, delete-orphan")
    project_tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    client_reminders = relationship("ClientReminder", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage = Column(Enum(Stage), nullable=False)
    title = Column(String(500), nullable=False)
    assignee_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED, nullable=False)
    checklist_json = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assignee_user_id])


class StageOutput(Base):
    __tablename__ = "stage_outputs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage = Column(Enum(Stage), nullable=False)
    status = Column(Enum(StageStatus), nullable=False)
    summary = Column(Text)
    structured_output_json = Column(JSONB, default=dict)
    required_next_inputs_json = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="stage_outputs")


class Artifact(Base):
    __tablename__ = "artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage = Column(Enum(Stage), nullable=False)
    type = Column(String(100), nullable=False)  # document, image, test_report, evidence, etc.
    filename = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)  # file path or S3 URL
    notes = Column(Text)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="artifacts")
    uploader = relationship("User", back_populates="uploaded_artifacts")


class Defect(Base):
    __tablename__ = "defects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    external_id = Column(String(255), nullable=True)  # ID from external tracker
    severity = Column(Enum(DefectSeverity), nullable=False)
    status = Column(Enum(DefectStatus), default=DefectStatus.DRAFT, nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="defects")


class AdminConfig(Base):
    __tablename__ = "admin_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value_json = Column(JSONB, nullable=False)
    updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    payload_json = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="audit_logs")


class OnboardingData(Base):
    """Stores onboarding form data for a project"""
    __tablename__ = "onboarding_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, unique=True)
    
    # Client access token for external form
    client_access_token = Column(String(255), nullable=True, unique=True)
    token_expires_at = Column(DateTime, nullable=True)
    
    # Client contact information
    contacts_json = Column(JSONB, default=list)  # [{name, email, role, is_primary}]
    
    # Logo and images - support both URLs and file uploads
    logo_url = Column(String(1000), nullable=True)
    logo_file_path = Column(String(1000), nullable=True)  # For uploaded files
    images_json = Column(JSONB, default=list)  # [{url, file_path, type}]
    
    # Copy text with pricing
    copy_text = Column(Text, nullable=True)
    use_custom_copy = Column(Boolean, default=False)
    custom_copy_base_price = Column(Integer, default=500)  # Base price in dollars
    custom_copy_word_count = Column(Integer, default=1000)  # Estimated word count
    custom_copy_final_price = Column(Integer, nullable=True)  # Client agreed price
    custom_copy_notes = Column(Text, nullable=True)  # Pricing adjustment notes
    
    # WCAG
    wcag_compliance_required = Column(Boolean, default=True)
    wcag_level = Column(String(10), default="AA")  # A, AA, AAA
    
    # Privacy
    privacy_policy_url = Column(String(1000), nullable=True)
    privacy_policy_text = Column(Text, nullable=True)
    
    # Theme with templates
    theme_preference = Column(String(100), nullable=True)  # template id or 'custom'
    selected_template_id = Column(String(100), nullable=True)  # Predefined template ID
    theme_colors_json = Column(JSONB, default=dict)  # {primary, secondary, accent}
    
    # Additional custom fields
    custom_fields_json = Column(JSONB, default=list)  # [{field_name, field_value, field_type}]
    
    # Completion tracking
    completion_percentage = Column(Integer, default=0)
    last_reminder_sent = Column(DateTime, nullable=True)
    next_reminder_at = Column(DateTime, nullable=True)  # For auto-scheduling
    reminder_count = Column(Integer, default=0)
    auto_reminder_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="onboarding_data")


class ProjectTask(Base):
    """Predefined and custom tasks for project stages"""
    __tablename__ = "project_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage = Column(Enum(Stage), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    is_predefined = Column(Boolean, default=False)  # True for template tasks
    is_required = Column(Boolean, default=True)
    is_auto_completed = Column(Boolean, default=False)  # True if auto-completed based on data
    linked_field = Column(String(100), nullable=True)  # Field key for auto-completion
    status = Column(Enum(TaskStatus), default=TaskStatus.NOT_STARTED, nullable=False)
    assignee_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    order_index = Column(Integer, default=0)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="project_tasks")


class ClientReminder(Base):
    """Tracks reminders sent to clients"""
    __tablename__ = "client_reminders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)
    reminder_type = Column(String(100), nullable=False)  # onboarding_incomplete, missing_assets, etc.
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="sent")  # sent, delivered, failed
    
    # Relationships
    project = relationship("Project", back_populates="client_reminders")
