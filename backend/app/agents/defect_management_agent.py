"""
Defect Management Agent - Second sub-agent of the Test Phase

This agent:
1. Creates defects based on failed test cases from QA Automation Agent
2. Assigns defects to builders who worked on the project
3. Uses PMC > Location context for smart assignment
4. Handles reassignment when practitioners are unavailable
5. Validates fixed defects during Defect Validation phase
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import uuid

from app.models import (
    Defect, DefectAssignment, DefectSeverity, DefectStatus,
    TestResult, TestCase, TestScenario, TestResultStatus,
    User, Role, UserAvailability, BuilderWorkHistory,
    Project, Stage
)
from app.agents.prompts import get_llm
from app.utils.llm import invoke_llm


class DefectManagementAgent:
    """
    Defect Management Agent responsible for:
    - Creating defects from failed test cases
    - Smart assignment based on builder history and PMC/Location
    - Handling reassignment for unavailable practitioners
    - Validating fixed defects
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm(task="analysis")
        self.agent_name = "DEFECT_MANAGEMENT_AGENT"
    
    def create_defects_from_failed_tests(
        self,
        project_id: str,
        failed_results: List[TestResult] = None
    ) -> List[Defect]:
        """
        Create defects from failed test results
        """
        if failed_results is None:
            # Get all failed results without defects
            failed_results = self.db.query(TestResult).join(
                TestCase, TestResult.test_case_id == TestCase.id
            ).join(
                TestScenario, TestCase.scenario_id == TestScenario.id
            ).filter(
                TestScenario.project_id == project_id,
                TestResult.status == TestResultStatus.FAILED,
                TestResult.defect_id == None
            ).all()
        
        created_defects = []
        
        for result in failed_results:
            # Get test case and scenario for context
            test_case = self.db.query(TestCase).filter(
                TestCase.id == result.test_case_id
            ).first()
            
            if not test_case:
                continue
            
            scenario = self.db.query(TestScenario).filter(
                TestScenario.id == test_case.scenario_id
            ).first()
            
            # Determine severity based on test priority
            severity_map = {
                1: DefectSeverity.CRITICAL,
                2: DefectSeverity.HIGH,
                3: DefectSeverity.MEDIUM,
                4: DefectSeverity.LOW
            }
            severity = severity_map.get(test_case.priority, DefectSeverity.MEDIUM)
            
            # Create defect
            defect = Defect(
                id=uuid.uuid4(),
                project_id=project_id,
                title=f"Failed: {test_case.title}",
                severity=severity,
                status=DefectStatus.DRAFT,
                description=self._generate_defect_description(test_case, result),
                pmc_name=scenario.pmc_name if scenario else None,
                location_name=scenario.location_name if scenario else None,
                source_test_case_id=test_case.id,
                created_by_agent=self.agent_name,
                evidence_json={
                    'test_result_id': str(result.id),
                    'error_message': result.error_message,
                    'actual_result': result.actual_result,
                    'screenshot_url': result.screenshot_url,
                    'ai_notes': result.ai_notes
                },
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            self.db.add(defect)
            self.db.flush()  # Get the defect ID
            
            # Link test result to defect
            result.defect_id = defect.id
            
            # Auto-assign to appropriate builder
            assigned_user = self._find_best_builder_for_assignment(
                project_id=project_id,
                pmc_name=scenario.pmc_name if scenario else None,
                location_name=scenario.location_name if scenario else None
            )
            
            if assigned_user:
                defect.assigned_to_user_id = assigned_user.id
                defect.assigned_by_agent = True
                
                # Create assignment record
                assignment = DefectAssignment(
                    id=uuid.uuid4(),
                    defect_id=defect.id,
                    assigned_to_user_id=assigned_user.id,
                    assigned_by_agent=self.agent_name,
                    pmc_name=scenario.pmc_name if scenario else None,
                    location_name=scenario.location_name if scenario else None,
                    assignment_reason=f"Auto-assigned based on work history for {scenario.pmc_name or 'project'} > {scenario.location_name or 'all locations'}",
                    assigned_at=datetime.utcnow()
                )
                self.db.add(assignment)
            
            created_defects.append(defect)
        
        self.db.commit()
        
        # Refresh all defects to get updated relationships
        for defect in created_defects:
            self.db.refresh(defect)
        
        return created_defects
    
    def _generate_defect_description(
        self,
        test_case: TestCase,
        result: TestResult
    ) -> str:
        """Generate a comprehensive defect description"""
        description = f"""
## Defect from Failed Test

### Test Case
**Title:** {test_case.title}
**Description:** {test_case.description or 'N/A'}

### Preconditions
{test_case.preconditions or 'N/A'}

### Test Steps
"""
        if test_case.steps_json:
            for step in test_case.steps_json:
                description += f"\n{step.get('step_number', '?')}. {step.get('action', 'N/A')}"
                description += f"\n   Expected: {step.get('expected_result', 'N/A')}"
        
        description += f"""

### Expected Outcome
{test_case.expected_outcome or 'N/A'}

### Actual Result
{result.actual_result or 'N/A'}

### Error Details
{result.error_message or 'N/A'}

### AI Analysis
{result.ai_notes or 'N/A'}

---
*This defect was auto-generated by the QA Automation Agent based on failed test execution.*
"""
        return description.strip()
    
    def _find_best_builder_for_assignment(
        self,
        project_id: str,
        pmc_name: str = None,
        location_name: str = None
    ) -> Optional[User]:
        """
        Find the best builder to assign the defect to based on:
        1. Builder who worked on the specific PMC > Location
        2. Builder who worked on the PMC (any location)
        3. Builder who worked on the project
        4. Any available builder
        """
        today = datetime.utcnow()
        
        # Build query for builders with work history
        base_query = self.db.query(User).filter(
            User.role == Role.BUILDER,
            User.is_active == True,
            User.is_archived == False
        )
        
        # Get unavailable user IDs
        unavailable_users = self.db.query(UserAvailability.user_id).filter(
            UserAvailability.start_date <= today,
            UserAvailability.end_date >= today,
            UserAvailability.is_available == False
        ).subquery()
        
        base_query = base_query.filter(~User.id.in_(unavailable_users))
        
        # Try to find builder by PMC + Location
        if pmc_name and location_name:
            builder = self.db.query(User).join(
                BuilderWorkHistory, BuilderWorkHistory.user_id == User.id
            ).filter(
                User.role == Role.BUILDER,
                User.is_active == True,
                User.is_archived == False,
                ~User.id.in_(unavailable_users),
                BuilderWorkHistory.project_id == project_id,
                BuilderWorkHistory.pmc_name == pmc_name,
                BuilderWorkHistory.location_name == location_name
            ).order_by(BuilderWorkHistory.last_worked_at.desc()).first()
            
            if builder:
                return builder
        
        # Try to find builder by PMC only
        if pmc_name:
            builder = self.db.query(User).join(
                BuilderWorkHistory, BuilderWorkHistory.user_id == User.id
            ).filter(
                User.role == Role.BUILDER,
                User.is_active == True,
                User.is_archived == False,
                ~User.id.in_(unavailable_users),
                BuilderWorkHistory.project_id == project_id,
                BuilderWorkHistory.pmc_name == pmc_name
            ).order_by(BuilderWorkHistory.last_worked_at.desc()).first()
            
            if builder:
                return builder
        
        # Try to find any builder who worked on the project
        builder = self.db.query(User).join(
            BuilderWorkHistory, BuilderWorkHistory.user_id == User.id
        ).filter(
            User.role == Role.BUILDER,
            User.is_active == True,
            User.is_archived == False,
            ~User.id.in_(unavailable_users),
            BuilderWorkHistory.project_id == project_id
        ).order_by(BuilderWorkHistory.last_worked_at.desc()).first()
        
        if builder:
            return builder
        
        # Fall back to any available builder
        return base_query.first()
    
    def reassign_defect(
        self,
        defect_id: str,
        new_assignee_id: str,
        assigned_by_user_id: str,
        reason: str = None
    ) -> Defect:
        """
        Reassign a defect to a different builder
        This is typically done by PC when the original builder is unavailable
        """
        defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise ValueError(f"Defect {defect_id} not found")
        
        # Deactivate current assignment
        current_assignment = self.db.query(DefectAssignment).filter(
            DefectAssignment.defect_id == defect_id,
            DefectAssignment.is_active == True
        ).first()
        
        if current_assignment:
            current_assignment.is_active = False
            current_assignment.reassigned_reason = reason
        
        # Create new assignment
        new_assignment = DefectAssignment(
            id=uuid.uuid4(),
            defect_id=defect_id,
            assigned_to_user_id=new_assignee_id,
            assigned_by_user_id=assigned_by_user_id,
            pmc_name=defect.pmc_name,
            location_name=defect.location_name,
            assignment_reason=reason or "Manual reassignment by PC",
            assigned_at=datetime.utcnow()
        )
        self.db.add(new_assignment)
        
        # Update defect
        defect.assigned_to_user_id = new_assignee_id
        defect.assigned_by_agent = False
        defect.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(defect)
        
        return defect
    
    def validate_fixed_defect(self, defect_id: str) -> Dict[str, Any]:
        """
        Validate a fixed defect
        Called during Defect Validation phase
        """
        defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            return {'success': False, 'error': 'Defect not found'}
        
        if defect.status != DefectStatus.FIXED:
            return {'success': False, 'error': 'Defect is not in FIXED status'}
        
        # Get the original test case if available
        test_result = self.db.query(TestResult).filter(
            TestResult.defect_id == defect_id
        ).first()
        
        validation_notes = []
        is_valid = True
        
        # AI-based validation
        if defect.fix_description:
            prompt = f"""
            Analyze this defect fix and determine if it adequately addresses the issue:
            
            Original Issue:
            {defect.description}
            
            Fix Description:
            {defect.fix_description}
            
            Respond in JSON format:
            {{
                "is_adequate": true/false,
                "confidence": 0.0-1.0,
                "concerns": ["list of any concerns"],
                "recommendation": "VALID" or "NEEDS_RETEST" or "REOPEN"
            }}
            """
            
            try:
                response = invoke_llm(self.llm, prompt)
                if isinstance(response, str):
                    import re
                    json_match = re.search(r'\{[\s\S]*\}', response)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        is_valid = analysis.get('is_adequate', True)
                        validation_notes.append(f"AI Confidence: {analysis.get('confidence', 'N/A')}")
                        validation_notes.append(f"Recommendation: {analysis.get('recommendation', 'VALID')}")
                        if analysis.get('concerns'):
                            validation_notes.append(f"Concerns: {', '.join(analysis['concerns'])}")
            except Exception as e:
                validation_notes.append(f"AI validation error: {str(e)}")
        else:
            validation_notes.append("No fix description provided - manual validation required")
            is_valid = False
        
        # Update defect
        if is_valid:
            defect.status = DefectStatus.VALID
            defect.validated_by_agent = True
            defect.validation_notes = "\n".join(validation_notes)
        else:
            defect.status = DefectStatus.RETEST
            defect.validation_notes = "\n".join(validation_notes)
        
        defect.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(defect)
        
        return {
            'success': True,
            'is_valid': is_valid,
            'status': defect.status.value,
            'validation_notes': validation_notes
        }
    
    def validate_all_fixed_defects(self, project_id: str) -> Dict[str, Any]:
        """
        Validate all fixed defects for a project
        Returns summary of validation results
        """
        fixed_defects = self.db.query(Defect).filter(
            Defect.project_id == project_id,
            Defect.status == DefectStatus.FIXED
        ).all()
        
        results = {
            'total': len(fixed_defects),
            'validated': 0,
            'needs_retest': 0,
            'details': []
        }
        
        for defect in fixed_defects:
            validation = self.validate_fixed_defect(str(defect.id))
            results['details'].append({
                'defect_id': str(defect.id),
                'title': defect.title,
                **validation
            })
            
            if validation.get('is_valid'):
                results['validated'] += 1
            else:
                results['needs_retest'] += 1
        
        return results
    
    def get_available_builders(self, project_id: str = None) -> List[User]:
        """Get list of available builders for reassignment"""
        today = datetime.utcnow()
        
        # Get unavailable user IDs
        unavailable_users = self.db.query(UserAvailability.user_id).filter(
            UserAvailability.start_date <= today,
            UserAvailability.end_date >= today,
            UserAvailability.is_available == False
        ).subquery()
        
        query = self.db.query(User).filter(
            User.role == Role.BUILDER,
            User.is_active == True,
            User.is_archived == False,
            ~User.id.in_(unavailable_users)
        )
        
        return query.all()
    
    def get_defects_by_status(
        self,
        project_id: str,
        status: DefectStatus = None
    ) -> List[Defect]:
        """Get defects for a project, optionally filtered by status"""
        query = self.db.query(Defect).filter(Defect.project_id == project_id)
        if status:
            query = query.filter(Defect.status == status)
        return query.order_by(Defect.created_at.desc()).all()
    
    def get_defect_summary(self, project_id: str) -> Dict[str, Any]:
        """Get summary of defects for a project"""
        defects = self.db.query(Defect).filter(
            Defect.project_id == project_id
        ).all()
        
        summary = {
            'total': len(defects),
            'by_status': {},
            'by_severity': {},
            'unassigned': 0,
            'auto_assigned': 0
        }
        
        for defect in defects:
            # Count by status
            status_key = defect.status.value
            summary['by_status'][status_key] = summary['by_status'].get(status_key, 0) + 1
            
            # Count by severity
            severity_key = defect.severity.value
            summary['by_severity'][severity_key] = summary['by_severity'].get(severity_key, 0) + 1
            
            # Count assignments
            if not defect.assigned_to_user_id:
                summary['unassigned'] += 1
            elif defect.assigned_by_agent:
                summary['auto_assigned'] += 1
        
        return summary
    
    def mark_defect_fixed(
        self,
        defect_id: str,
        fixed_by_user_id: str,
        fix_description: str
    ) -> Defect:
        """Mark a defect as fixed by a builder"""
        defect = self.db.query(Defect).filter(Defect.id == defect_id).first()
        if not defect:
            raise ValueError(f"Defect {defect_id} not found")
        
        defect.status = DefectStatus.FIXED
        defect.fixed_by_user_id = fixed_by_user_id
        defect.fixed_at = datetime.utcnow()
        defect.fix_description = fix_description
        defect.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(defect)
        
        return defect
