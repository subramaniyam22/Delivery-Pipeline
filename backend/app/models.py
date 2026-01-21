import enum
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, Integer, Float, Date, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, date
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
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"
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
    date_of_joining = Column(Date, nullable=True)  # For leave calculations
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Manager Assignment - For team hierarchy
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    manager = relationship("User", remote_side=[id], backref="team_members", foreign_keys=[manager_id])
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
    features_json = Column(JSONB, default=dict)
    
    # Client Contact Information
    client_emails = Column(JSONB, default=list)  # List of client email addresses
    client_primary_contact = Column(String(255), nullable=True)
    client_company = Column(String(255), nullable=True)
    
    # Phase Tracking & SLA
    phase_deadlines = Column(JSONB, default=dict)  # {"ONBOARDING": "2026-01-20", "BUILD": "2026-02-01"}
    phase_start_dates = Column(JSONB, default=dict)  # {"ONBOARDING": "2026-01-12"}
    is_delayed = Column(Boolean, default=False)
    delay_reason = Column(Text, nullable=True)
    
    # Archive/Pause Tracking
    paused_at = Column(DateTime, nullable=True)
    paused_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    pause_reason = Column(Text, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    archived_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    archive_reason = Column(Text, nullable=True)

    # Minimum requirements overrides (Admin-configurable)
    minimum_requirements_override = Column(JSONB, nullable=True)  # List of required onboarding fields
    allow_requirements_exceptions = Column(Boolean, default=False)
    
    # Team Assignments
    pc_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    consultant_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    builder_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    tester_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    creator = relationship("User", back_populates="created_projects", foreign_keys=[created_by_user_id])
    pc = relationship("User", foreign_keys=[pc_user_id])
    consultant = relationship("User", foreign_keys=[consultant_user_id])
    builder = relationship("User", foreign_keys=[builder_user_id])
    tester = relationship("User", foreign_keys=[tester_user_id])
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    stage_outputs = relationship("StageOutput", back_populates="project", cascade="all, delete-orphan")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    defects = relationship("Defect", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project", cascade="all, delete-orphan")
    onboarding_data = relationship("OnboardingData", back_populates="project", uselist=False, cascade="all, delete-orphan")
    project_tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    client_reminders = relationship("ClientReminder", back_populates="project", cascade="all, delete-orphan")
    test_scenarios = relationship("TestScenario", back_populates="project", cascade="all, delete-orphan")
    test_executions = relationship("TestExecution", back_populates="project", cascade="all, delete-orphan")


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
    title = Column(String(500), nullable=True)  # Short title for the defect
    severity = Column(Enum(DefectSeverity), nullable=False)
    status = Column(Enum(DefectStatus), default=DefectStatus.DRAFT, nullable=False)
    description = Column(Text, nullable=False)
    evidence_json = Column(JSONB, default=dict)
    
    # PMC/Location context for assignment
    pmc_name = Column(String(255), nullable=True)
    location_name = Column(String(255), nullable=True)
    
    # Assignment tracking
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    assigned_by_agent = Column(Boolean, default=False)  # True if auto-assigned by Defect Management Agent
    
    # Source tracking
    source_test_case_id = Column(UUID(as_uuid=True), nullable=True)  # Link to failed test case
    created_by_agent = Column(String(100), nullable=True)  # "DEFECT_MANAGEMENT_AGENT" if auto-created
    
    # Fix tracking
    fixed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    fixed_at = Column(DateTime, nullable=True)
    fix_description = Column(Text, nullable=True)
    
    # Validation tracking
    validated_by_agent = Column(Boolean, default=False)  # True if validated by agent
    validation_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="defects")
    test_results = relationship("TestResult", back_populates="defect")
    assignments = relationship("DefectAssignment", back_populates="defect", cascade="all, delete-orphan")


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
    wcag_confirmed = Column(Boolean, default=False)  # User explicitly confirmed WCAG settings
    
    # Privacy
    privacy_policy_url = Column(String(1000), nullable=True)
    privacy_policy_text = Column(Text, nullable=True)
    
    # Theme with templates
    theme_preference = Column(String(100), nullable=True)  # template id or 'custom'
    selected_template_id = Column(String(100), nullable=True)  # Predefined template ID
    theme_colors_json = Column(JSONB, default=dict)  # {primary, secondary, accent}
    
    # Additional custom fields
    custom_fields_json = Column(JSONB, default=list)  # [{field_name, field_value, field_type}]
    requirements_json = Column(JSONB, default=dict)  # Structured project requirements
    
    # Completion tracking
    completion_percentage = Column(Integer, default=0)
    last_reminder_sent = Column(DateTime, nullable=True)
    next_reminder_at = Column(DateTime, nullable=True)  # For auto-scheduling
    reminder_count = Column(Integer, default=0)
    auto_reminder_enabled = Column(Boolean, default=True)
    reminder_interval_hours = Column(Integer, default=24)  # 6, 12, or 24 hours

    # Client submission tracking
    submitted_at = Column(DateTime, nullable=True)
    missing_fields_eta_json = Column(JSONB, nullable=True)  # { field_key: "2026-01-18" }
    
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


# ============== Test Phase Sub-Agents Models ==============

class TestExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TestResultStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class TestScenario(Base):
    """Test scenarios uploaded for a project"""
    __tablename__ = "test_scenarios"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    source_file = Column(String(500), nullable=True)  # Original file name if uploaded
    source_url = Column(String(1000), nullable=True)  # URL if external
    pmc_name = Column(String(255), nullable=True)  # PMC context
    location_name = Column(String(255), nullable=True)  # Location context
    is_auto_generated = Column(Boolean, default=False)  # True if AI generated from project context
    priority = Column(Integer, default=2)  # 1-Critical, 2-High, 3-Medium, 4-Low
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="test_scenarios")
    test_cases = relationship("TestCase", back_populates="scenario", cascade="all, delete-orphan")


class TestCase(Base):
    """Individual test cases within a scenario"""
    __tablename__ = "test_cases"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("test_scenarios.id"), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    preconditions = Column(Text, nullable=True)
    steps_json = Column(JSONB, default=list)  # [{step_number, action, expected_result}]
    expected_outcome = Column(Text, nullable=True)
    test_data_json = Column(JSONB, default=dict)  # Test input data
    is_automated = Column(Boolean, default=False)  # Can be run by QA Automation Agent
    automation_script = Column(Text, nullable=True)  # Script or selector info for automation
    priority = Column(Integer, default=2)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    scenario = relationship("TestScenario", back_populates="test_cases")
    test_results = relationship("TestResult", back_populates="test_case", cascade="all, delete-orphan")


class TestExecution(Base):
    """Represents a test execution run (batch of tests)"""
    __tablename__ = "test_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Sprint 1 Regression", "Smoke Test"
    status = Column(Enum(TestExecutionStatus), default=TestExecutionStatus.PENDING)
    executed_by = Column(String(100), default="QA_AUTOMATION_AGENT")  # Agent or user identifier
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_tests = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    blocked_count = Column(Integer, default=0)
    execution_log = Column(Text, nullable=True)  # Agent's execution notes
    ai_analysis = Column(Text, nullable=True)  # AI analysis of test results
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="test_executions")
    test_results = relationship("TestResult", back_populates="execution", cascade="all, delete-orphan")


class TestResult(Base):
    """Individual test case results within an execution"""
    __tablename__ = "test_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("test_executions.id"), nullable=False)
    test_case_id = Column(UUID(as_uuid=True), ForeignKey("test_cases.id"), nullable=False)
    status = Column(Enum(TestResultStatus), nullable=False)
    actual_result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    screenshot_url = Column(String(1000), nullable=True)
    execution_time_ms = Column(Integer, nullable=True)  # Time taken in milliseconds
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ai_notes = Column(Text, nullable=True)  # AI agent's observations
    
    # Link to defect if test failed
    defect_id = Column(UUID(as_uuid=True), ForeignKey("defects.id"), nullable=True)
    
    # Relationships
    execution = relationship("TestExecution", back_populates="test_results")
    test_case = relationship("TestCase", back_populates="test_results")
    defect = relationship("Defect", back_populates="test_results")


# Enhanced Defect model fields for Defect Management Agent
class DefectAssignment(Base):
    """Tracks defect assignments with PMC/Location context"""
    __tablename__ = "defect_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    defect_id = Column(UUID(as_uuid=True), ForeignKey("defects.id"), nullable=False)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # PC or Agent
    assigned_by_agent = Column(String(100), nullable=True)  # "DEFECT_MANAGEMENT_AGENT" if auto-assigned
    pmc_name = Column(String(255), nullable=True)  # PMC context for assignment
    location_name = Column(String(255), nullable=True)  # Location context
    assignment_reason = Column(Text, nullable=True)  # Why this user was assigned
    is_active = Column(Boolean, default=True)  # False if reassigned
    reassigned_reason = Column(Text, nullable=True)  # Reason for reassignment (e.g., "User on leave")
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    defect = relationship("Defect", back_populates="assignments")


class UserAvailability(Base):
    """Tracks user availability (on leave, etc.)"""
    __tablename__ = "user_availability"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)  # Leave, Training, etc.
    is_available = Column(Boolean, default=False)  # False = not available
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class BuilderWorkHistory(Base):
    """Tracks which builders worked on which PMC/Location combinations"""
    __tablename__ = "builder_work_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    pmc_name = Column(String(255), nullable=True)
    location_name = Column(String(255), nullable=True)
    worked_on_stage = Column(Enum(Stage), default=Stage.BUILD)
    task_count = Column(Integer, default=0)  # Number of tasks completed
    last_worked_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# ============== Capacity Management Models ==============

class CapacityConfig(Base):
    """Default capacity configuration by role and region"""
    __tablename__ = "capacity_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(Enum(Role), nullable=False)
    region = Column(Enum(Region), nullable=True)  # NULL means applies to all regions
    daily_hours = Column(Float, default=6.8, nullable=False)  # Default 6.8 hours/day
    weekly_hours = Column(Float, default=34.0, nullable=False)  # Default 34 hours/week (5 days * 6.8)
    buffer_percentage = Column(Float, default=10.0)  # Reserve 10% for meetings/admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        # Unique constraint: one config per role-region combination
        Index('ix_capacity_config_role_region', 'role', 'region', unique=True),
    )


class UserDailyCapacity(Base):
    """Tracks daily capacity for each user - actual vs available"""
    __tablename__ = "user_daily_capacity"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    total_hours = Column(Float, default=6.8, nullable=False)  # Total available hours
    allocated_hours = Column(Float, default=0.0, nullable=False)  # Hours allocated to projects
    actual_hours = Column(Float, nullable=True)  # Actual hours worked (for learning)
    is_available = Column(Boolean, default=True)  # False if on leave/holiday
    unavailability_reason = Column(String(255), nullable=True)  # Reason: leave type or holiday name
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="daily_capacities")
    
    __table_args__ = (
        Index('ix_user_daily_capacity_user_date', 'user_id', 'date', unique=True),
    )
    
    @property
    def remaining_hours(self):
        return max(0, self.total_hours - self.allocated_hours)
    
    @property
    def utilization_percentage(self):
        if self.total_hours == 0:
            return 0
        return round((self.allocated_hours / self.total_hours) * 100, 1)


class ProjectWorkload(Base):
    """Estimated workload for projects by stage"""
    __tablename__ = "project_workloads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage = Column(Enum(Stage), nullable=False)
    role = Column(Enum(Role), nullable=False)  # Which role is responsible
    estimated_hours = Column(Float, nullable=False)  # Estimated hours to complete
    actual_hours = Column(Float, nullable=True)  # Actual hours (filled after completion)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    priority_score = Column(Float, default=1.0)  # Higher = more urgent
    complexity_factor = Column(Float, default=1.0)  # 1.0 = normal, >1 = complex
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", backref="workloads")
    assigned_user = relationship("User", backref="assigned_workloads")


class CapacityAllocation(Base):
    """Tracks capacity allocations to projects"""
    __tablename__ = "capacity_allocations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    workload_id = Column(UUID(as_uuid=True), ForeignKey("project_workloads.id"), nullable=True)
    date = Column(Date, nullable=False)
    allocated_hours = Column(Float, nullable=False)
    actual_hours = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="capacity_allocations")
    project = relationship("Project", backref="capacity_allocations")


class CapacitySuggestion(Base):
    """AI-generated capacity suggestions with feedback for learning"""
    __tablename__ = "capacity_suggestions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    role = Column(Enum(Role), nullable=False)
    suggested_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    suggestion_type = Column(String(50), nullable=False)  # 'assignment', 'reallocation', 'capacity_crunch'
    suggestion_text = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.5)  # 0-1 confidence
    factors_json = Column(JSONB, default=dict)  # Factors considered for suggestion
    was_accepted = Column(Boolean, nullable=True)  # User feedback
    feedback_notes = Column(Text, nullable=True)
    actual_outcome = Column(String(100), nullable=True)  # What actually happened
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    feedback_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", backref="capacity_suggestions")
    suggested_user = relationship("User", backref="capacity_suggestions")


class CapacityHistory(Base):
    """Historical capacity data for learning and predictions"""
    __tablename__ = "capacity_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    week_start = Column(Date, nullable=False)  # Week starting date
    role = Column(Enum(Role), nullable=False)
    region = Column(Enum(Region), nullable=True)
    planned_hours = Column(Float, default=0.0)
    actual_hours = Column(Float, default=0.0)
    projects_count = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    efficiency_score = Column(Float, nullable=True)  # actual_hours / planned_hours ratio
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="capacity_history")


class CapacityManualInput(Base):
    """Manual input for capacity vs project load learning"""
    __tablename__ = "capacity_manual_inputs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_type = Column(String(50), nullable=False)  # 'actual_hours', 'complexity', 'efficiency'
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    role = Column(Enum(Role), nullable=True)
    region = Column(Enum(Region), nullable=True)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    context_json = Column(JSONB, default=dict)  # Additional context
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Default workload estimates by stage and role (in hours)
DEFAULT_STAGE_WORKLOAD = {
    Stage.ONBOARDING: {Role.CONSULTANT: 4.0, Role.PC: 2.0},
    Stage.ASSIGNMENT: {Role.PC: 3.0, Role.CONSULTANT: 1.0},
    Stage.BUILD: {Role.BUILDER: 20.0, Role.PC: 4.0},
    Stage.TEST: {Role.TESTER: 12.0, Role.PC: 2.0},
    Stage.DEFECT_VALIDATION: {Role.TESTER: 6.0, Role.BUILDER: 8.0, Role.PC: 2.0},
    Stage.COMPLETE: {Role.PC: 1.0},
}


# ============== Leave & Holiday Management Models ==============

class LeaveType(str, enum.Enum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    PERSONAL = "PERSONAL"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    BEREAVEMENT = "BEREAVEMENT"
    UNPAID = "UNPAID"
    WORK_FROM_HOME = "WORK_FROM_HOME"  # Partial availability
    TRAINING = "TRAINING"


class LeaveStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class UserLeave(Base):
    """Tracks user leave/time-off requests"""
    __tablename__ = "user_leaves"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    leave_type = Column(Enum(LeaveType), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    reason = Column(Text, nullable=True)
    partial_day = Column(Boolean, default=False)  # True if only part of day
    hours_off = Column(Float, nullable=True)  # Hours off if partial_day
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="leaves")
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])


class RegionHoliday(Base):
    """Region-specific public holidays"""
    __tablename__ = "region_holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region = Column(Enum(Region), nullable=False)
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    is_optional = Column(Boolean, default=False)  # Optional holiday
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('ix_region_holiday_date', 'region', 'date', unique=True),
    )


class CompanyHoliday(Base):
    """Company-wide holidays that apply to all regions"""
    __tablename__ = "company_holidays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    year = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True)  # Mandatory vs optional holiday
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('ix_company_holiday_date', 'date', unique=True),
    )


# ============== Leave Entitlements & Balance Management ==============

class LeaveEntitlementType(str, enum.Enum):
    """Types of leave entitlements"""
    CASUAL = "CASUAL"
    SICK = "SICK"
    EARNED = "EARNED"
    MATERNITY = "MATERNITY"
    PATERNITY = "PATERNITY"
    BEREAVEMENT = "BEREAVEMENT"
    UNPAID = "UNPAID"
    COMPENSATORY = "COMPENSATORY"
    WORK_FROM_HOME = "WORK_FROM_HOME"


class LeaveEntitlementPolicy(Base):
    """Company-wide leave entitlement policy by role/region"""
    __tablename__ = "leave_entitlement_policies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    leave_type = Column(Enum(LeaveEntitlementType), nullable=False)
    role = Column(Enum(Role), nullable=True)  # Null means applies to all roles
    region = Column(Enum(Region), nullable=True)  # Null means applies to all regions
    annual_days = Column(Float, nullable=False)  # Annual entitlement in days
    can_carry_forward = Column(Boolean, default=False)
    max_carry_forward_days = Column(Float, default=0)
    requires_approval = Column(Boolean, default=True)
    min_notice_days = Column(Integer, default=0)  # Minimum notice required
    max_consecutive_days = Column(Integer, nullable=True)  # Max days at once
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('ix_leave_policy_type_role_region', 'leave_type', 'role', 'region', unique=True),
    )


class UserLeaveBalance(Base):
    """Individual user leave balances for each year"""
    __tablename__ = "user_leave_balances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    leave_type = Column(Enum(LeaveEntitlementType), nullable=False)
    year = Column(Integer, nullable=False)
    entitled_days = Column(Float, nullable=False)  # Total entitled for year
    used_days = Column(Float, default=0)  # Days used
    pending_days = Column(Float, default=0)  # Days in pending requests
    carried_forward = Column(Float, default=0)  # Carried from previous year
    adjusted_days = Column(Float, default=0)  # Manual adjustments (+/-)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="leave_balances")
    
    @property
    def available_days(self):
        """Calculate available balance"""
        return self.entitled_days + self.carried_forward + self.adjusted_days - self.used_days - self.pending_days
    
    __table_args__ = (
        Index('ix_user_leave_balance', 'user_id', 'leave_type', 'year', unique=True),
    )


# ============== Calendar & Meeting Sync ==============

class CalendarProvider(str, enum.Enum):
    """Supported calendar providers"""
    GOOGLE = "GOOGLE"
    OUTLOOK = "OUTLOOK"
    APPLE = "APPLE"
    MANUAL = "MANUAL"


class CalendarConnection(Base):
    """User calendar connections for syncing"""
    __tablename__ = "calendar_connections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(Enum(CalendarProvider), nullable=False)
    access_token = Column(Text, nullable=True)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    token_expires_at = Column(DateTime, nullable=True)
    calendar_id = Column(String(255), nullable=True)  # Selected calendar
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime, nullable=True)
    sync_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="calendar_connections")
    
    __table_args__ = (
        Index('ix_calendar_connection_user', 'user_id', 'provider', unique=True),
    )


class MeetingBlock(Base):
    """Synced meetings that block capacity"""
    __tablename__ = "meeting_blocks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("calendar_connections.id"), nullable=True)
    external_id = Column(String(255), nullable=True)  # External calendar event ID
    title = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_all_day = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    is_busy = Column(Boolean, default=True)  # Whether to count as blocking
    category = Column(String(100), nullable=True)  # e.g., "internal", "client", "personal"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", backref="meeting_blocks")
    connection = relationship("CalendarConnection", backref="meetings")
    
    @property
    def duration_hours(self):
        """Calculate meeting duration in hours"""
        if self.is_all_day:
            return 8.0  # Assume full day
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600
    
    __table_args__ = (
        Index('ix_meeting_user_date', 'user_id', 'start_time'),
    )


# ============== Time Tracking for Learning ==============

class TimeEntry(Base):
    """Actual time spent on work for learning and predictions"""
    __tablename__ = "time_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    date = Column(Date, nullable=False)
    hours = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)  # "development", "meetings", "admin", etc.
    description = Column(Text, nullable=True)
    is_billable = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="time_entries")
    project = relationship("Project", backref="time_entries")
    
    __table_args__ = (
        Index('ix_time_entry_user_date', 'user_id', 'date'),
    )


# ============== Capacity Adjustments ==============

class CapacityAdjustment(Base):
    """Manual capacity adjustments for special circumstances"""
    __tablename__ = "capacity_adjustments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    adjustment_type = Column(String(50), nullable=False)  # "reduced_hours", "overtime", "training"
    daily_hours_adjustment = Column(Float, nullable=False)  # Positive or negative
    reason = Column(Text, nullable=True)
    approved_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="capacity_adjustments")
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])


# ============== SLA Configuration ==============

class SLAConfiguration(Base):
    """SLA configuration for project phases"""
    __tablename__ = "sla_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage = Column(String(50), unique=True, nullable=False)
    default_days = Column(Integer, nullable=False, default=7)
    warning_threshold_days = Column(Integer, nullable=False, default=2)  # Days before deadline to warn
    critical_threshold_days = Column(Integer, nullable=False, default=1)  # Days before deadline for critical
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ClientReminderLog(Base):
    """Log of reminders sent to clients"""
    __tablename__ = "client_reminder_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    reminder_type = Column(String(100), nullable=False)  # "requirements_pending", "document_needed", etc.
    sent_to = Column(JSONB, nullable=False)  # List of email addresses
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    sent_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), default="SENT")  # SENT, FAILED, BOUNCED
    
    # Relationships
    project = relationship("Project", backref="reminder_logs")
    sent_by = relationship("User", backref="sent_reminders")


class ThemeTemplate(Base):
    __tablename__ = "theme_templates"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    preview_url = Column(String(1000), nullable=True)
    actual_web_url = Column(String(1000), nullable=True)
    colors_json = Column(JSONB, default=dict)
    actual_web_url = Column(String(1000), nullable=True)
    colors_json = Column(JSONB, default=dict)
    features_json = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True) # Used for soft delete
    is_published = Column(Boolean, default=False) # Used for visibility to clients


class ChatLog(Base):
    """Logs of chat between Client and AI/Consultant"""
    __tablename__ = "chat_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    sender = Column(String(50), nullable=False)  # 'user', 'bot', 'consultant'
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", backref="chat_logs")


