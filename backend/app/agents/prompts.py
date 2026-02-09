from app.config import settings
from typing import Optional

# LLM prompts for each workflow stage

ONBOARDING_PROMPT = """
You are an AI assistant helping with project onboarding.

Project Information:
{project_info}

Onboarding Data:
{onboarding_data}

Artifacts:
{artifacts}

Task: Analyze the onboarding information and determine if it's complete and ready for assignment.

Check for:
1. Clear project scope and objectives
2. Client requirements documented
3. Necessary onboarding artifacts uploaded
4. All required fields filled

Provide a structured analysis with:
- Completeness score (0-100)
- Missing items (if any)
- Recommendations for next steps
- Whether ready to proceed to assignment stage
"""

ASSIGNMENT_PROMPT = """
You are an AI assistant helping with project task assignment.

Project Information:
{project_info}

Onboarding Summary:
{onboarding_summary}

Available Resources:
{resources}

Task: Create a task assignment plan for this project.

Consider:
1. Project scope and requirements
2. Available team members and their roles
3. Task dependencies
4. Estimated timelines

Provide:
- Recommended task breakdown
- Suggested assignees for each task
- Priority ordering
- Estimated completion timeline
"""

BUILD_PROMPT = """
You are an AI assistant monitoring the build stage.

Project Information:
{project_info}

Build Tasks:
{build_tasks}

Build Artifacts:
{build_artifacts}

Task: Assess the build progress and determine if it's ready for testing.

Check for:
1. All build tasks completed
2. Required build artifacts uploaded (code, documentation, deployment evidence)
3. Build quality indicators
4. Blockers or issues

Provide:
- Build completion status
- Quality assessment
- Missing items (if any)
- Whether ready for human approval to proceed to testing
"""

TEST_PROMPT = """
You are an AI assistant helping with the testing stage.

Project Information:
{project_info}

Test Tasks:
{test_tasks}

Test Artifacts:
{test_artifacts}

Staging URL:
{staging_url}

Task: Analyze test execution and results.

Check for:
1. Test coverage
2. Test results (pass/fail rates)
3. Test artifacts (test reports, screenshots)
4. Defects identified

Provide:
- Test completion status
- Quality metrics
- Defects summary
- Whether ready to proceed to defect validation or completion
"""

DEFECT_VALIDATION_PROMPT = """
You are an AI assistant helping with defect validation.

Project Information:
{project_info}

Defects:
{defects}

External Defect Data:
{external_defects}

Validation Rules:
{validation_rules}

Task: Validate reported defects and determine next actions.

For each defect, determine:
1. Is it a valid defect?
2. Severity assessment
3. Whether it requires:
   - Send back to BUILD (for fixes)
   - RETEST (after claimed fix)
   - Mark as INVALID (not a real issue)

Provide:
- Validation results for each defect
- Recommended next stage
- Priority defects that block completion
"""

COMPLETE_PROMPT = """
You are an AI assistant helping with project completion.

Project Information:
{project_info}

All Stage Outputs:
{stage_outputs}

Final Artifacts:
{artifacts}

Task: Generate a project completion summary.

Provide:
- Overall project summary
- Key deliverables completed
- Quality metrics
- Lessons learned
- Final recommendations
- Completion certificate data
"""


class FakeLLM:
    """
    Fake LLM for deterministic responses when OpenAI API key is not available.
    Returns structured mock responses based on input patterns.
    """
    
    def invoke(self, prompt: str) -> str:
        """Generate deterministic response based on prompt content"""
        
        if "onboarding" in prompt.lower():
            return """
            {
                "completeness_score": 85,
                "missing_items": [],
                "recommendations": ["Proceed to assignment stage"],
                "ready_for_next_stage": true,
                "summary": "Onboarding information is complete and well-documented."
            }
            """
        
        elif "assignment" in prompt.lower():
            return """
            {
                "task_breakdown": [
                    {"title": "Setup development environment", "priority": "HIGH"},
                    {"title": "Implement core features", "priority": "HIGH"},
                    {"title": "Write tests", "priority": "MEDIUM"}
                ],
                "estimated_timeline": "2 weeks",
                "summary": "Assignment plan created with 3 main tasks."
            }
            """
        
        elif "build" in prompt.lower():
            return """
            {
                "completion_status": "COMPLETE",
                "quality_assessment": "Good",
                "missing_items": [],
                "ready_for_approval": true,
                "summary": "Build stage completed successfully with all artifacts."
            }
            """
        
        elif "test" in prompt.lower():
            return """
            {
                "test_coverage": "85%",
                "pass_rate": "92%",
                "defects_found": 2,
                "ready_for_validation": true,
                "summary": "Testing completed with 2 minor defects identified."
            }
            """
        
        elif "defect" in prompt.lower():
            return """
            {
                "validation_results": [
                    {"defect_id": "1", "valid": true, "action": "SEND_TO_BUILD"},
                    {"defect_id": "2", "valid": false, "action": "MARK_INVALID"}
                ],
                "next_stage": "BUILD",
                "summary": "1 valid defect requires fixing."
            }
            """
        
        elif "complete" in prompt.lower():
            return """
            {
                "project_summary": "Project completed successfully",
                "deliverables": ["Feature implementation", "Test reports", "Documentation"],
                "quality_score": 90,
                "summary": "All stages completed. Project ready for delivery."
            }
            """
        
        else:
            return """
            {
                "summary": "Analysis complete",
                "status": "SUCCESS"
            }
            """


def get_llm(task: Optional[str] = None):
    """
    Get LLM instance - returns OpenAI LLM if API key is available,
    otherwise returns FakeLLM for deterministic testing.
    """
    mode = (settings.AI_MODE or "full").lower()
    if mode == "disabled":
        return FakeLLM()
    if mode == "basic" and task not in {"summary", "checklist", "test_plan"}:
        return FakeLLM()
    if settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4",
                temperature=0.7,
                openai_api_key=settings.OPENAI_API_KEY
            )
        except Exception as e:
            print(f"Failed to initialize OpenAI LLM: {e}. Falling back to FakeLLM.")
            return FakeLLM()
    else:
        print("No OpenAI API key found. Using FakeLLM for deterministic responses.")
        return FakeLLM()
