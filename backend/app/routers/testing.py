"""
Testing Router - API endpoints for Test Phase Sub-Agents

Provides endpoints for:
- Test scenario management
- Test case management
- Test execution
- Defect management and assignment
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.deps import get_db, get_current_active_user
from app.models import (
    User, Role, Project, TestScenario, TestCase, TestExecution, TestResult,
    Defect, DefectAssignment, UserAvailability, BuilderWorkHistory,
    TestExecutionStatus, TestResultStatus, DefectStatus, DefectSeverity
)
from app.agents.qa_automation_agent import QAAutomationAgent
from app.agents.defect_management_agent import DefectManagementAgent
from app.rbac import check_full_access, check_can_manage_projects

router = APIRouter(prefix="/testing", tags=["testing"])


# ============== Pydantic Schemas ==============

class TestStepSchema(BaseModel):
    step_number: int
    action: str
    expected_result: str


class TestScenarioCreate(BaseModel):
    name: str
    description: Optional[str] = None
    source_file: Optional[str] = None
    pmc_name: Optional[str] = None
    location_name: Optional[str] = None
    priority: int = 2


class TestScenarioResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: Optional[str]
    source_file: Optional[str]
    pmc_name: Optional[str]
    location_name: Optional[str]
    is_auto_generated: bool
    priority: int
    created_at: datetime
    test_cases_count: int = 0
    
    class Config:
        from_attributes = True


class TestCaseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    steps: List[TestStepSchema] = []
    expected_outcome: Optional[str] = None
    is_automated: bool = False
    automation_script: Optional[str] = None
    priority: int = 2


class TestCaseResponse(BaseModel):
    id: UUID
    scenario_id: UUID
    title: str
    description: Optional[str]
    preconditions: Optional[str]
    steps_json: List[dict]
    expected_outcome: Optional[str]
    is_automated: bool
    priority: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TestExecutionResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    status: str
    executed_by: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_tests: int
    passed_count: int
    failed_count: int
    skipped_count: int
    blocked_count: int
    ai_analysis: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TestResultResponse(BaseModel):
    id: UUID
    execution_id: UUID
    test_case_id: UUID
    status: str
    actual_result: Optional[str]
    error_message: Optional[str]
    execution_time_ms: Optional[int]
    ai_notes: Optional[str]
    defect_id: Optional[UUID]
    executed_at: datetime
    
    class Config:
        from_attributes = True


class DefectResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: Optional[str]
    severity: str
    status: str
    description: str
    pmc_name: Optional[str]
    location_name: Optional[str]
    assigned_to_user_id: Optional[UUID]
    assigned_by_agent: bool
    created_by_agent: Optional[str]
    fixed_by_user_id: Optional[UUID]
    fixed_at: Optional[datetime]
    validated_by_agent: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DefectReassignRequest(BaseModel):
    new_assignee_id: UUID
    reason: Optional[str] = None


class DefectFixRequest(BaseModel):
    fix_description: str


class UserAvailabilityCreate(BaseModel):
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    is_available: bool = False


class AvailableBuilderResponse(BaseModel):
    id: UUID
    name: str
    email: str
    region: Optional[str]
    
    class Config:
        from_attributes = True


# ============== Test Scenario Endpoints ==============

@router.get("/projects/{project_id}/scenarios", response_model=List[TestScenarioResponse])
def get_test_scenarios(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all test scenarios for a project"""
    qa_agent = QAAutomationAgent(db)
    scenarios = qa_agent.get_test_scenarios(str(project_id))
    
    # Add test case count
    result = []
    for scenario in scenarios:
        scenario_dict = {
            'id': scenario.id,
            'project_id': scenario.project_id,
            'name': scenario.name,
            'description': scenario.description,
            'source_file': scenario.source_file,
            'pmc_name': scenario.pmc_name,
            'location_name': scenario.location_name,
            'is_auto_generated': scenario.is_auto_generated,
            'priority': scenario.priority,
            'created_at': scenario.created_at,
            'test_cases_count': len(scenario.test_cases) if scenario.test_cases else 0
        }
        result.append(TestScenarioResponse(**scenario_dict))
    
    return result


@router.post("/projects/{project_id}/scenarios", response_model=TestScenarioResponse)
def create_test_scenario(
    project_id: UUID,
    scenario_data: TestScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new test scenario"""
    if not check_can_manage_projects(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create test scenarios"
        )
    
    qa_agent = QAAutomationAgent(db)
    scenario = qa_agent.create_test_scenario(
        project_id=str(project_id),
        name=scenario_data.name,
        description=scenario_data.description,
        source_file=scenario_data.source_file,
        pmc_name=scenario_data.pmc_name,
        location_name=scenario_data.location_name,
        created_by_user_id=str(current_user.id)
    )
    
    return TestScenarioResponse(
        id=scenario.id,
        project_id=scenario.project_id,
        name=scenario.name,
        description=scenario.description,
        source_file=scenario.source_file,
        pmc_name=scenario.pmc_name,
        location_name=scenario.location_name,
        is_auto_generated=scenario.is_auto_generated,
        priority=scenario.priority,
        created_at=scenario.created_at,
        test_cases_count=0
    )


@router.post("/projects/{project_id}/scenarios/generate", response_model=TestScenarioResponse)
def generate_test_scenario(
    project_id: UUID,
    scenario_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate test scenario with AI-generated test cases"""
    if not check_can_manage_projects(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to generate test scenarios"
        )
    
    # Get project info
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    qa_agent = QAAutomationAgent(db)
    
    # Create scenario
    scenario = qa_agent.create_test_scenario(
        project_id=str(project_id),
        name=scenario_name,
        description=f"AI-generated test scenario for {project.title}",
        is_auto_generated=True,
        created_by_user_id=str(current_user.id)
    )
    
    # Generate test cases
    context = {
        'project_title': project.title,
        'client_name': project.client_name,
        'priority': project.priority
    }
    
    generated_cases = qa_agent.generate_test_cases_from_context(
        project_id=str(project_id),
        scenario_name=scenario_name,
        context=context
    )
    
    # Create test cases
    for case_data in generated_cases:
        qa_agent.create_test_case(
            scenario_id=str(scenario.id),
            title=case_data.get('title', 'Untitled Test'),
            description=case_data.get('description'),
            preconditions=case_data.get('preconditions'),
            steps=[{
                'step_number': s.get('step_number', i+1),
                'action': s.get('action', ''),
                'expected_result': s.get('expected_result', '')
            } for i, s in enumerate(case_data.get('steps', []))],
            expected_outcome=case_data.get('expected_outcome'),
            is_automated=case_data.get('is_automated', False),
            priority=case_data.get('priority', 2)
        )
    
    db.refresh(scenario)
    
    return TestScenarioResponse(
        id=scenario.id,
        project_id=scenario.project_id,
        name=scenario.name,
        description=scenario.description,
        source_file=scenario.source_file,
        pmc_name=scenario.pmc_name,
        location_name=scenario.location_name,
        is_auto_generated=scenario.is_auto_generated,
        priority=scenario.priority,
        created_at=scenario.created_at,
        test_cases_count=len(generated_cases)
    )


# ============== Test Case Endpoints ==============

@router.get("/scenarios/{scenario_id}/cases", response_model=List[TestCaseResponse])
def get_test_cases(
    scenario_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all test cases for a scenario"""
    cases = db.query(TestCase).filter(
        TestCase.scenario_id == scenario_id
    ).order_by(TestCase.order_index).all()
    
    return [TestCaseResponse(
        id=tc.id,
        scenario_id=tc.scenario_id,
        title=tc.title,
        description=tc.description,
        preconditions=tc.preconditions,
        steps_json=tc.steps_json or [],
        expected_outcome=tc.expected_outcome,
        is_automated=tc.is_automated,
        priority=tc.priority,
        created_at=tc.created_at
    ) for tc in cases]


@router.post("/scenarios/{scenario_id}/cases", response_model=TestCaseResponse)
def create_test_case(
    scenario_id: UUID,
    case_data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new test case"""
    if not check_can_manage_projects(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create test cases"
        )
    
    qa_agent = QAAutomationAgent(db)
    test_case = qa_agent.create_test_case(
        scenario_id=str(scenario_id),
        title=case_data.title,
        description=case_data.description,
        preconditions=case_data.preconditions,
        steps=[s.dict() for s in case_data.steps],
        expected_outcome=case_data.expected_outcome,
        is_automated=case_data.is_automated,
        automation_script=case_data.automation_script,
        priority=case_data.priority
    )
    
    return TestCaseResponse(
        id=test_case.id,
        scenario_id=test_case.scenario_id,
        title=test_case.title,
        description=test_case.description,
        preconditions=test_case.preconditions,
        steps_json=test_case.steps_json or [],
        expected_outcome=test_case.expected_outcome,
        is_automated=test_case.is_automated,
        priority=test_case.priority,
        created_at=test_case.created_at
    )


# ============== Test Execution Endpoints ==============

@router.get("/projects/{project_id}/executions", response_model=List[TestExecutionResponse])
def get_test_executions(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all test executions for a project"""
    qa_agent = QAAutomationAgent(db)
    executions = qa_agent.get_test_executions(str(project_id))
    
    return [TestExecutionResponse(
        id=ex.id,
        project_id=ex.project_id,
        name=ex.name,
        status=ex.status.value if ex.status else 'PENDING',
        executed_by=ex.executed_by or 'Unknown',
        started_at=ex.started_at,
        completed_at=ex.completed_at,
        total_tests=ex.total_tests or 0,
        passed_count=ex.passed_count or 0,
        failed_count=ex.failed_count or 0,
        skipped_count=ex.skipped_count or 0,
        blocked_count=ex.blocked_count or 0,
        ai_analysis=ex.ai_analysis,
        created_at=ex.created_at
    ) for ex in executions]


@router.post("/projects/{project_id}/executions", response_model=TestExecutionResponse)
def run_test_execution(
    project_id: UUID,
    execution_name: str = "Test Execution",
    scenario_ids: List[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Run test execution for a project"""
    if not check_can_manage_projects(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to run test executions"
        )
    
    qa_agent = QAAutomationAgent(db)
    
    execution = qa_agent.execute_tests(
        project_id=str(project_id),
        execution_name=execution_name,
        scenario_ids=[str(sid) for sid in scenario_ids] if scenario_ids else None
    )
    
    # If there are failed tests, create defects
    if execution.failed_count > 0:
        defect_agent = DefectManagementAgent(db)
        failed_results = qa_agent.get_failed_test_results(str(project_id))
        defect_agent.create_defects_from_failed_tests(
            project_id=str(project_id),
            failed_results=failed_results
        )
    
    return TestExecutionResponse(
        id=execution.id,
        project_id=execution.project_id,
        name=execution.name,
        status=execution.status.value if execution.status else 'PENDING',
        executed_by=execution.executed_by or 'Unknown',
        started_at=execution.started_at,
        completed_at=execution.completed_at,
        total_tests=execution.total_tests or 0,
        passed_count=execution.passed_count or 0,
        failed_count=execution.failed_count or 0,
        skipped_count=execution.skipped_count or 0,
        blocked_count=execution.blocked_count or 0,
        ai_analysis=execution.ai_analysis,
        created_at=execution.created_at
    )


@router.get("/executions/{execution_id}/results", response_model=List[TestResultResponse])
def get_test_results(
    execution_id: UUID,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get test results for an execution"""
    query = db.query(TestResult).filter(TestResult.execution_id == execution_id)
    
    if status_filter:
        try:
            status_enum = TestResultStatus(status_filter)
            query = query.filter(TestResult.status == status_enum)
        except ValueError:
            pass
    
    results = query.all()
    
    return [TestResultResponse(
        id=r.id,
        execution_id=r.execution_id,
        test_case_id=r.test_case_id,
        status=r.status.value if r.status else 'UNKNOWN',
        actual_result=r.actual_result,
        error_message=r.error_message,
        execution_time_ms=r.execution_time_ms,
        ai_notes=r.ai_notes,
        defect_id=r.defect_id,
        executed_at=r.executed_at
    ) for r in results]


# ============== Defect Management Endpoints ==============

@router.get("/projects/{project_id}/defects", response_model=List[DefectResponse])
def get_project_defects(
    project_id: UUID,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all defects for a project"""
    defect_agent = DefectManagementAgent(db)
    
    status_enum = None
    if status_filter:
        try:
            status_enum = DefectStatus(status_filter)
        except ValueError:
            pass
    
    defects = defect_agent.get_defects_by_status(str(project_id), status_enum)
    
    return [DefectResponse(
        id=d.id,
        project_id=d.project_id,
        title=d.title,
        severity=d.severity.value if d.severity else 'MEDIUM',
        status=d.status.value if d.status else 'DRAFT',
        description=d.description,
        pmc_name=d.pmc_name,
        location_name=d.location_name,
        assigned_to_user_id=d.assigned_to_user_id,
        assigned_by_agent=d.assigned_by_agent or False,
        created_by_agent=d.created_by_agent,
        fixed_by_user_id=d.fixed_by_user_id,
        fixed_at=d.fixed_at,
        validated_by_agent=d.validated_by_agent or False,
        created_at=d.created_at
    ) for d in defects]


@router.get("/projects/{project_id}/defects/summary")
def get_defect_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get defect summary for a project"""
    defect_agent = DefectManagementAgent(db)
    return defect_agent.get_defect_summary(str(project_id))


@router.post("/defects/{defect_id}/reassign", response_model=DefectResponse)
def reassign_defect(
    defect_id: UUID,
    reassign_data: DefectReassignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Reassign a defect to a different builder (PC only)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER, Role.PC]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, or PC can reassign defects"
        )
    
    defect_agent = DefectManagementAgent(db)
    
    try:
        defect = defect_agent.reassign_defect(
            defect_id=str(defect_id),
            new_assignee_id=str(reassign_data.new_assignee_id),
            assigned_by_user_id=str(current_user.id),
            reason=reassign_data.reason
        )
        
        return DefectResponse(
            id=defect.id,
            project_id=defect.project_id,
            title=defect.title,
            severity=defect.severity.value if defect.severity else 'MEDIUM',
            status=defect.status.value if defect.status else 'DRAFT',
            description=defect.description,
            pmc_name=defect.pmc_name,
            location_name=defect.location_name,
            assigned_to_user_id=defect.assigned_to_user_id,
            assigned_by_agent=defect.assigned_by_agent or False,
            created_by_agent=defect.created_by_agent,
            fixed_by_user_id=defect.fixed_by_user_id,
            fixed_at=defect.fixed_at,
            validated_by_agent=defect.validated_by_agent or False,
            created_at=defect.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/defects/{defect_id}/fix", response_model=DefectResponse)
def mark_defect_fixed(
    defect_id: UUID,
    fix_data: DefectFixRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Mark a defect as fixed (Builder only)"""
    if current_user.role not in [Role.ADMIN, Role.MANAGER, Role.BUILDER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, Manager, or Builder can mark defects as fixed"
        )
    
    defect_agent = DefectManagementAgent(db)
    
    try:
        defect = defect_agent.mark_defect_fixed(
            defect_id=str(defect_id),
            fixed_by_user_id=str(current_user.id),
            fix_description=fix_data.fix_description
        )
        
        return DefectResponse(
            id=defect.id,
            project_id=defect.project_id,
            title=defect.title,
            severity=defect.severity.value if defect.severity else 'MEDIUM',
            status=defect.status.value if defect.status else 'DRAFT',
            description=defect.description,
            pmc_name=defect.pmc_name,
            location_name=defect.location_name,
            assigned_to_user_id=defect.assigned_to_user_id,
            assigned_by_agent=defect.assigned_by_agent or False,
            created_by_agent=defect.created_by_agent,
            fixed_by_user_id=defect.fixed_by_user_id,
            fixed_at=defect.fixed_at,
            validated_by_agent=defect.validated_by_agent or False,
            created_at=defect.created_at
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/defects/{defect_id}/validate")
def validate_defect(
    defect_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate a fixed defect using AI agent"""
    if not check_can_manage_projects(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to validate defects"
        )
    
    defect_agent = DefectManagementAgent(db)
    result = defect_agent.validate_fixed_defect(str(defect_id))
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result.get('error', 'Validation failed'))
    
    return result


@router.post("/projects/{project_id}/defects/validate-all")
def validate_all_defects(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Validate all fixed defects for a project"""
    if not check_can_manage_projects(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to validate defects"
        )
    
    defect_agent = DefectManagementAgent(db)
    return defect_agent.validate_all_fixed_defects(str(project_id))


# ============== Builder Availability Endpoints ==============

@router.get("/available-builders", response_model=List[AvailableBuilderResponse])
def get_available_builders(
    project_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get list of available builders for defect assignment"""
    defect_agent = DefectManagementAgent(db)
    builders = defect_agent.get_available_builders(str(project_id) if project_id else None)
    
    return [AvailableBuilderResponse(
        id=b.id,
        name=b.name,
        email=b.email,
        region=b.region.value if b.region else None
    ) for b in builders]


@router.post("/users/{user_id}/availability", status_code=status.HTTP_201_CREATED)
def set_user_availability(
    user_id: UUID,
    availability_data: UserAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set user availability (for leave management)"""
    if not check_full_access(current_user.role) and str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to set availability for other users"
        )
    
    availability = UserAvailability(
        user_id=user_id,
        start_date=availability_data.start_date,
        end_date=availability_data.end_date,
        reason=availability_data.reason,
        is_available=availability_data.is_available,
        created_at=datetime.utcnow()
    )
    
    db.add(availability)
    db.commit()
    
    return {"message": "Availability set successfully"}


@router.get("/users/{user_id}/availability")
def get_user_availability(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user availability records"""
    availabilities = db.query(UserAvailability).filter(
        UserAvailability.user_id == user_id
    ).order_by(UserAvailability.start_date.desc()).all()
    
    return [{
        'id': str(a.id),
        'start_date': a.start_date,
        'end_date': a.end_date,
        'reason': a.reason,
        'is_available': a.is_available
    } for a in availabilities]
