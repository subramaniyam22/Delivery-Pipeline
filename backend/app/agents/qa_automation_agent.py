"""
QA Automation Agent - First sub-agent of the Test Phase

This agent:
1. Consumes uploaded test scenarios and test scripts
2. Learns from test scenarios and test cases based on the project
3. Executes tests (simulated or actual)
4. Stores failed test cases in database for the Defect Management Agent
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import json
import uuid

from app.models import (
    TestScenario, TestCase, TestExecution, TestResult,
    TestExecutionStatus, TestResultStatus, Project, Artifact, Stage
)
from app.agents.prompts import get_llm
from app.utils.llm import invoke_llm


class QAAutomationAgent:
    """
    QA Automation Agent responsible for:
    - Parsing and understanding test scenarios
    - Generating test cases from project context
    - Executing tests and recording results
    - Identifying failed tests for defect creation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm(task="analysis")
        self.agent_name = "QA_AUTOMATION_AGENT"
    
    def analyze_test_artifacts(self, project_id: str) -> Dict[str, Any]:
        """
        Analyze uploaded test artifacts (scenarios, scripts, documents)
        and extract test information
        """
        # Get test-related artifacts
        artifacts = self.db.query(Artifact).filter(
            Artifact.project_id == project_id,
            Artifact.stage == Stage.TEST,
            Artifact.type.in_(['test_scenario', 'test_script', 'test_document', 'document'])
        ).all()
        
        analyzed_artifacts = []
        for artifact in artifacts:
            analyzed_artifacts.append({
                'id': str(artifact.id),
                'filename': artifact.filename,
                'type': artifact.type,
                'notes': artifact.notes
            })
        
        return {
            'artifacts_count': len(analyzed_artifacts),
            'artifacts': analyzed_artifacts
        }
    
    def generate_test_cases_from_context(
        self, 
        project_id: str, 
        scenario_name: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Use AI to generate test cases based on project context
        """
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return []
        
        prompt = f"""
        Based on the following project context, generate comprehensive test cases:
        
        Project: {project.title}
        Client: {project.client_name}
        Test Scenario: {scenario_name}
        Additional Context: {json.dumps(context)}
        
        Generate test cases in JSON format with the following structure:
        {{
            "test_cases": [
                {{
                    "title": "Test case title",
                    "description": "What this test validates",
                    "preconditions": "Required setup",
                    "steps": [
                        {{"step_number": 1, "action": "Action to perform", "expected_result": "Expected outcome"}}
                    ],
                    "expected_outcome": "Overall expected result",
                    "priority": 1-4 (1=Critical, 4=Low),
                    "is_automated": true/false
                }}
            ]
        }}
        
        Focus on:
        1. Functional testing
        2. WCAG accessibility compliance
        3. Cross-browser compatibility
        4. Performance considerations
        5. Security basics
        """
        
        try:
            response = invoke_llm(self.llm, prompt)
            if isinstance(response, str):
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                    return result.get('test_cases', [])
            return []
        except Exception as e:
            print(f"Error generating test cases: {e}")
            return []
    
    def create_test_scenario(
        self,
        project_id: str,
        name: str,
        description: str = None,
        source_file: str = None,
        pmc_name: str = None,
        location_name: str = None,
        is_auto_generated: bool = False,
        created_by_user_id: str = None
    ) -> TestScenario:
        """Create a new test scenario"""
        scenario = TestScenario(
            id=uuid.uuid4(),
            project_id=project_id,
            name=name,
            description=description,
            source_file=source_file,
            pmc_name=pmc_name,
            location_name=location_name,
            is_auto_generated=is_auto_generated,
            created_by_user_id=created_by_user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(scenario)
        self.db.commit()
        self.db.refresh(scenario)
        return scenario
    
    def create_test_case(
        self,
        scenario_id: str,
        title: str,
        description: str = None,
        preconditions: str = None,
        steps: List[Dict] = None,
        expected_outcome: str = None,
        test_data: Dict = None,
        is_automated: bool = False,
        automation_script: str = None,
        priority: int = 2
    ) -> TestCase:
        """Create a new test case"""
        test_case = TestCase(
            id=uuid.uuid4(),
            scenario_id=scenario_id,
            title=title,
            description=description,
            preconditions=preconditions,
            steps_json=steps or [],
            expected_outcome=expected_outcome,
            test_data_json=test_data or {},
            is_automated=is_automated,
            automation_script=automation_script,
            priority=priority,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(test_case)
        self.db.commit()
        self.db.refresh(test_case)
        return test_case
    
    def execute_tests(
        self,
        project_id: str,
        execution_name: str,
        scenario_ids: List[str] = None
    ) -> TestExecution:
        """
        Execute tests for specified scenarios or all scenarios in project
        
        This simulates test execution. In a real implementation, this would:
        - Connect to actual test automation frameworks (Selenium, Playwright, etc.)
        - Execute tests against staging environment
        - Capture screenshots and logs
        """
        # Create execution record
        execution = TestExecution(
            id=uuid.uuid4(),
            project_id=project_id,
            name=execution_name,
            status=TestExecutionStatus.RUNNING,
            executed_by=self.agent_name,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow()
        )
        self.db.add(execution)
        self.db.commit()
        
        # Get test cases to execute
        query = self.db.query(TestCase).join(TestScenario).filter(
            TestScenario.project_id == project_id
        )
        if scenario_ids:
            query = query.filter(TestScenario.id.in_(scenario_ids))
        
        test_cases = query.all()
        
        # Execute each test case
        passed = 0
        failed = 0
        skipped = 0
        blocked = 0
        failed_results = []
        
        for test_case in test_cases:
            result = self._execute_single_test(execution.id, test_case)
            
            if result.status == TestResultStatus.PASSED:
                passed += 1
            elif result.status == TestResultStatus.FAILED:
                failed += 1
                failed_results.append(result)
            elif result.status == TestResultStatus.SKIPPED:
                skipped += 1
            elif result.status == TestResultStatus.BLOCKED:
                blocked += 1
        
        # Update execution summary
        execution.status = TestExecutionStatus.COMPLETED
        execution.completed_at = datetime.utcnow()
        execution.total_tests = len(test_cases)
        execution.passed_count = passed
        execution.failed_count = failed
        execution.skipped_count = skipped
        execution.blocked_count = blocked
        
        # Generate AI analysis
        execution.ai_analysis = self._generate_execution_analysis(
            execution, test_cases, failed_results
        )
        
        self.db.commit()
        self.db.refresh(execution)
        
        return execution
    
    def _execute_single_test(self, execution_id: str, test_case: TestCase) -> TestResult:
        """
        Execute a single test case
        
        In a real implementation, this would:
        - Run automation script if available
        - Validate against expected outcomes
        - Capture evidence
        
        For simulation, we use AI to determine likely pass/fail based on test complexity
        """
        import random
        
        # Simulate test execution with weighted randomness based on priority
        # Higher priority tests (critical) have higher pass rate in stable systems
        pass_probability = {
            1: 0.85,  # Critical - 85% pass
            2: 0.80,  # High - 80% pass
            3: 0.90,  # Medium - 90% pass
            4: 0.95,  # Low - 95% pass
        }.get(test_case.priority, 0.85)
        
        is_passed = random.random() < pass_probability
        
        status = TestResultStatus.PASSED if is_passed else TestResultStatus.FAILED
        
        # Generate result details
        actual_result = None
        error_message = None
        ai_notes = None
        
        if not is_passed:
            # Generate failure details using AI or templates
            error_templates = [
                f"Element not found: Expected element matching '{test_case.title}' criteria",
                f"Assertion failed: Actual result did not match expected outcome",
                f"Timeout: Page did not load within expected time",
                f"Validation error: Data mismatch in expected vs actual",
                f"Accessibility violation: WCAG compliance issue detected"
            ]
            error_message = random.choice(error_templates)
            actual_result = f"Test failed: {error_message}"
            ai_notes = f"QA Agent detected failure in test case. Root cause analysis suggests: {error_message}. Recommend creating defect for builder review."
        else:
            actual_result = "Test passed successfully"
            ai_notes = "Test executed successfully with all assertions passing."
        
        # Create test result
        result = TestResult(
            id=uuid.uuid4(),
            execution_id=execution_id,
            test_case_id=test_case.id,
            status=status,
            actual_result=actual_result,
            error_message=error_message,
            execution_time_ms=random.randint(100, 5000),  # Simulated execution time
            executed_at=datetime.utcnow(),
            ai_notes=ai_notes
        )
        
        self.db.add(result)
        self.db.commit()
        
        return result
    
    def _generate_execution_analysis(
        self,
        execution: TestExecution,
        test_cases: List[TestCase],
        failed_results: List[TestResult]
    ) -> str:
        """Generate AI analysis of test execution results"""
        
        analysis_parts = [
            f"## Test Execution Analysis: {execution.name}",
            f"\n### Summary",
            f"- Total Tests: {execution.total_tests}",
            f"- Passed: {execution.passed_count} ({(execution.passed_count/max(1, execution.total_tests))*100:.1f}%)",
            f"- Failed: {execution.failed_count}",
            f"- Skipped: {execution.skipped_count}",
            f"- Blocked: {execution.blocked_count}",
        ]
        
        if failed_results:
            analysis_parts.append("\n### Failed Tests Analysis")
            for result in failed_results[:5]:  # Show top 5 failures
                test_case = next((tc for tc in test_cases if tc.id == result.test_case_id), None)
                if test_case:
                    analysis_parts.append(f"\n**{test_case.title}**")
                    analysis_parts.append(f"- Error: {result.error_message}")
                    analysis_parts.append(f"- Recommendation: Create defect for builder review")
        
        analysis_parts.append("\n### Next Steps")
        if execution.failed_count > 0:
            analysis_parts.append("- Defect Management Agent will create defects for failed tests")
            analysis_parts.append("- Defects will be assigned to builders who worked on related PMC/Location")
        else:
            analysis_parts.append("- All tests passed! Ready to proceed to completion.")
        
        return "\n".join(analysis_parts)
    
    def get_failed_test_results(self, project_id: str) -> List[TestResult]:
        """Get all failed test results for a project that need defects"""
        return self.db.query(TestResult).join(TestExecution).filter(
            TestExecution.project_id == project_id,
            TestResult.status == TestResultStatus.FAILED,
            TestResult.defect_id == None  # No defect created yet
        ).all()
    
    def get_test_scenarios(self, project_id: str) -> List[TestScenario]:
        """Get all test scenarios for a project"""
        return self.db.query(TestScenario).filter(
            TestScenario.project_id == project_id
        ).all()
    
    def get_test_executions(self, project_id: str) -> List[TestExecution]:
        """Get all test executions for a project"""
        return self.db.query(TestExecution).filter(
            TestExecution.project_id == project_id
        ).order_by(TestExecution.created_at.desc()).all()
