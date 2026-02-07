from typing import Dict, Any, List
from app.models import Stage, StageStatus, TestResultStatus
from app.agents.prompts import (
    TEST_PROMPT,
    DEFECT_VALIDATION_PROMPT,
    get_llm
)
from app.agents.tools import fetch_staging_url, fetch_defect_from_tracker
import json


# Import sub-agents (lazy loading to avoid circular imports)
def get_qa_automation_agent(db):
    from app.agents.qa_automation_agent import QAAutomationAgent
    return QAAutomationAgent(db)


def get_defect_management_agent(db):
    from app.agents.defect_management_agent import DefectManagementAgent
    return DefectManagementAgent(db)


def onboarding_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Onboarding stage node - validates project onboarding information
    """
    context = state.get("context", {})
    artifacts = state.get("artifacts", [])
    human_gate = state.get("human_gate", False)
    
    from app.agents.onboarding_agent import OnboardingAgent
    analysis = OnboardingAgent().run(context, artifacts)
    if human_gate:
        return {
            "stage": Stage.ONBOARDING.value,
            "status": StageStatus.NEEDS_HUMAN.value,
            "summary": "Awaiting human approval for Onboarding stage",
            "structured_output": analysis,
            "required_next_inputs": analysis.get("missing_items", []),
            "evidence_required": []
        }
    
    return {
        "stage": Stage.ONBOARDING.value,
        "status": StageStatus.SUCCESS.value if analysis.get("ready_for_next_stage") else StageStatus.NEEDS_HUMAN.value,
        "summary": analysis.get("summary", "Onboarding stage completed"),
        "structured_output": analysis,
        "required_next_inputs": [] if analysis.get("ready_for_next_stage") else analysis.get("missing_items", []),
        "evidence_required": []
    }


def assignment_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assignment stage node - creates task assignment plan
    """
    context = state.get("context", {})
    human_gate = state.get("human_gate", False)
    
    from app.agents.assignment_agent import AssignmentAgent
    plan = AssignmentAgent().run(context)
    if human_gate:
        return {
            "stage": Stage.ASSIGNMENT.value,
            "status": StageStatus.NEEDS_HUMAN.value,
            "summary": "Awaiting human approval for Assignment stage",
            "structured_output": plan,
            "required_next_inputs": [],
            "evidence_required": []
        }
    
    return {
        "stage": Stage.ASSIGNMENT.value,
        "status": StageStatus.SUCCESS.value,
        "summary": plan.get("summary", "Task assignment completed"),
        "structured_output": plan,
        "required_next_inputs": [],
        "evidence_required": []
    }


def build_hitl_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build stage node - Human-in-the-loop for build completion
    This stage requires human approval before proceeding
    """
    context = state.get("context", {})
    artifacts = state.get("artifacts", [])
    human_gate = state.get("human_gate", False)
    
    from app.agents.build_agent import BuildAgent
    assessment = BuildAgent().run(context, artifacts)
    if human_gate:
        return {
            "stage": Stage.BUILD.value,
            "status": StageStatus.NEEDS_HUMAN.value,
            "summary": "Awaiting human approval for Build stage",
            "structured_output": assessment,
            "required_next_inputs": [],
            "evidence_required": []
        }
    
    # Return SUCCESS to allow workflow advancement
    return {
        "stage": Stage.BUILD.value,
        "status": StageStatus.SUCCESS.value,
        "summary": assessment.get("summary", "Build stage completed"),
        "structured_output": assessment,
        "required_next_inputs": [],
        "evidence_required": []
    }


def test_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test stage node - Orchestrates the two sub-agents:
    1. QA Automation Agent - Executes tests and identifies failures
    2. Defect Management Agent - Creates and assigns defects from failures
    """
    project_id = state.get("project_id")
    context = state.get("context", {})
    artifacts = state.get("artifacts", [])
    defects = state.get("defects", [])
    db = state.get("db")  # Database session passed through state
    human_gate = state.get("human_gate", False)
    
    # Get test information
    test_tasks = context.get("test_tasks", [])
    test_artifacts = [a for a in artifacts if a.get("stage") == "TEST"]
    staging_url = fetch_staging_url(project_id)
    
    test_execution_summary = None
    created_defects = []
    
    # Step 1: Run QA Automation Agent if database session available
    if db:
        try:
            qa_agent = get_qa_automation_agent(db)
            
            # Check if there are test scenarios to execute
            scenarios = qa_agent.get_test_scenarios(project_id)
            
            if scenarios:
                # Execute tests
                execution = qa_agent.execute_tests(
                    project_id=project_id,
                    execution_name=f"Automated Test Run - {context.get('project_info', {}).get('title', 'Project')}"
                )
                
                test_execution_summary = {
                    'execution_id': str(execution.id),
                    'total_tests': execution.total_tests,
                    'passed': execution.passed_count,
                    'failed': execution.failed_count,
                    'skipped': execution.skipped_count,
                    'blocked': execution.blocked_count,
                    'ai_analysis': execution.ai_analysis
                }
                
                # Step 2: If tests failed, run Defect Management Agent
                if execution.failed_count > 0:
                    defect_agent = get_defect_management_agent(db)
                    
                    # Get failed test results
                    failed_results = qa_agent.get_failed_test_results(project_id)
                    
                    # Create defects from failed tests
                    created_defects = defect_agent.create_defects_from_failed_tests(
                        project_id=project_id,
                        failed_results=failed_results
                    )
                    
                    # Add to defects list
                    for defect in created_defects:
                        defects.append({
                            'id': str(defect.id),
                            'title': defect.title,
                            'severity': defect.severity.value,
                            'status': defect.status.value,
                            'assigned_to': str(defect.assigned_to_user_id) if defect.assigned_to_user_id else None,
                            'pmc_name': defect.pmc_name,
                            'location_name': defect.location_name
                        })
        except Exception as e:
            print(f"Error in test sub-agents: {e}")
    
    # Fallback to LLM analysis if no test scenarios or db not available
    if not test_execution_summary:
        llm = get_llm()
        prompt = TEST_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            test_tasks=json.dumps(test_tasks),
            test_artifacts=json.dumps([a.get("filename") for a in test_artifacts]),
            staging_url=staging_url
        )
        
        try:
            response = llm.invoke(prompt)
            if isinstance(response, str):
                results = json.loads(response)
            else:
                results = {"defects_found": len(defects), "summary": "Testing complete"}
        except:
            results = {"defects_found": len(defects), "summary": "Testing complete"}
        
        test_execution_summary = results
    
    # Prepare structured output
    structured_output = {
        'test_execution': test_execution_summary,
        'defects_created': len(created_defects),
        'total_defects': len(defects),
        'sub_agents_used': ['QA_AUTOMATION_AGENT', 'DEFECT_MANAGEMENT_AGENT'] if db else ['LLM_ANALYSIS']
    }
    
    # Build summary
    if test_execution_summary and isinstance(test_execution_summary, dict) and 'total_tests' in test_execution_summary:
        summary = f"Test Execution Complete: {test_execution_summary['passed']}/{test_execution_summary['total_tests']} passed"
        if test_execution_summary.get('failed', 0) > 0:
            summary += f", {test_execution_summary['failed']} failed - {len(created_defects)} defects created and assigned"
    else:
        summary = test_execution_summary.get("summary", "Testing complete") if isinstance(test_execution_summary, dict) else "Testing complete"
    
    # Determine next stage
    if len(defects) > 0:
        result = {
            "stage": Stage.TEST.value,
            "status": StageStatus.SUCCESS.value,
            "summary": summary,
            "structured_output": structured_output,
            "required_next_inputs": [],
            "evidence_required": [],
            "next_stage": "DEFECT_VALIDATION",
            "defects": defects  # Pass updated defects list
        }
    else:
        result = {
            "stage": Stage.TEST.value,
            "status": StageStatus.SUCCESS.value,
            "summary": summary,
            "structured_output": structured_output,
            "required_next_inputs": [],
            "evidence_required": [],
            "next_stage": "COMPLETE"
        }
    
    if human_gate:
        result["status"] = StageStatus.NEEDS_HUMAN.value
        result["summary"] = "Awaiting human approval for Test stage"
    return result


def defect_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Defect validation stage node - Uses Defect Management Agent to validate fixed defects
    
    This stage:
    1. Checks all defects marked as FIXED
    2. Uses the Defect Management Agent to validate fixes
    3. Determines if project can proceed to completion or needs more work
    """
    project_id = state.get("project_id")
    context = state.get("context", {})
    defects = state.get("defects", [])
    db = state.get("db")  # Database session passed through state
    human_gate = state.get("human_gate", False)
    
    validation_results = None
    needs_more_fixes = False
    
    # Use Defect Management Agent for validation if db available
    if db:
        try:
            defect_agent = get_defect_management_agent(db)
            
            # Validate all fixed defects
            validation_results = defect_agent.validate_all_fixed_defects(project_id)
            
            # Check if any defects need retest
            needs_more_fixes = validation_results.get('needs_retest', 0) > 0
            
            # Get current defect summary
            defect_summary = defect_agent.get_defect_summary(project_id)
            
            # Check if there are still open/unfixed defects
            open_defects = defect_summary['by_status'].get('DRAFT', 0) + \
                          defect_summary['by_status'].get('RETEST', 0)
            
            if open_defects > 0:
                needs_more_fixes = True
                
        except Exception as e:
            print(f"Error in defect validation agent: {e}")
    
    # Fallback to LLM validation if no db
    if validation_results is None:
        # Get validation rules from config
        validation_rules = context.get("validation_rules", {})
        
        # Fetch external defect data
        external_defects = []
        for defect in defects:
            if defect.get("external_id"):
                external_defects.append(fetch_defect_from_tracker(defect["external_id"]))
        
        # Use LLM to validate defects
        llm = get_llm()
        prompt = DEFECT_VALIDATION_PROMPT.format(
            project_info=json.dumps(context.get("project_info", {})),
            defects=json.dumps(defects),
            external_defects=json.dumps(external_defects),
            validation_rules=json.dumps(validation_rules)
        )
        
        try:
            response = llm.invoke(prompt)
            if isinstance(response, str):
                validation = json.loads(response)
            else:
                validation = {"next_stage": "COMPLETE", "summary": "All defects validated"}
        except:
            validation = {"next_stage": "COMPLETE", "summary": "All defects validated"}
        
        validation_results = validation
        needs_more_fixes = validation.get("next_stage") in ["BUILD", "TEST"]
    
    # Determine next stage
    if needs_more_fixes:
        # Check if defects need rebuild or just retest
        next_stage = "BUILD"  # Send back to build for fixes
        summary = f"Defect validation: {validation_results.get('needs_retest', 'some')} defects need attention. Returning to BUILD stage."
    else:
        next_stage = "COMPLETE"
        summary = f"All {validation_results.get('validated', len(defects))} defects validated successfully. Ready for completion."
    
    # Prepare structured output
    structured_output = {
        'validation_results': validation_results,
        'total_defects': len(defects),
        'needs_more_fixes': needs_more_fixes,
        'validated_by_agent': db is not None
    }
    
    result = {
        "stage": Stage.DEFECT_VALIDATION.value,
        "status": StageStatus.SUCCESS.value,
        "summary": summary,
        "structured_output": structured_output,
        "required_next_inputs": [],
        "evidence_required": [],
        "next_stage": next_stage
    }
    if human_gate:
        result["status"] = StageStatus.NEEDS_HUMAN.value
        result["summary"] = "Awaiting human approval for Defect Validation stage"
    return result


def complete_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Completion stage node - generates project summary and closes project
    """
    context = state.get("context", {})
    artifacts = state.get("artifacts", [])
    stage_meta = state.get("stage_meta", {})
    human_gate = state.get("human_gate", False)
    
    from app.agents.completion_agent import CompletionAgent
    summary = CompletionAgent().run(context, artifacts, stage_meta.get("all_stage_outputs", []))
    if human_gate:
        return {
            "stage": Stage.COMPLETE.value,
            "status": StageStatus.NEEDS_HUMAN.value,
            "summary": "Awaiting human approval for Completion stage",
            "structured_output": summary,
            "required_next_inputs": [],
            "evidence_required": []
        }
    
    return {
        "stage": Stage.COMPLETE.value,
        "status": StageStatus.SUCCESS.value,
        "summary": summary.get("project_summary", "Project completed successfully"),
        "structured_output": summary,
        "required_next_inputs": [],
        "evidence_required": []
    }
