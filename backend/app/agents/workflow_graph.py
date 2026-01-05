from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
from app.models import Stage
from app.agents.nodes import (
    onboarding_node,
    assignment_node,
    build_hitl_node,
    test_node,
    defect_validation_node,
    complete_node
)


class WorkflowState(TypedDict):
    """State schema for the workflow"""
    project_id: str
    current_stage: str
    last_stage_status: str
    context: Dict[str, Any]
    artifacts: List[Dict[str, Any]]
    defects: List[Dict[str, Any]]
    human_gate: bool
    stage_meta: Dict[str, Any]


def should_continue_from_test(state: WorkflowState) -> str:
    """Conditional edge from test node"""
    if len(state.get("defects", [])) > 0:
        return "defect_validation"
    else:
        return "complete"


def should_continue_from_defect_validation(state: WorkflowState) -> str:
    """Conditional edge from defect validation node"""
    # Check the next_stage from the last node output
    stage_meta = state.get("stage_meta", {})
    last_output = stage_meta.get("last_output", {})
    next_stage = last_output.get("next_stage", "COMPLETE")
    
    if next_stage == "BUILD":
        return "build_hitl"
    elif next_stage == "TEST":
        return "test"
    else:
        return "complete"


def create_workflow_graph():
    """Create and compile the LangGraph workflow"""
    
    # Create the graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("onboarding", onboarding_node)
    workflow.add_node("assignment", assignment_node)
    workflow.add_node("build_hitl", build_hitl_node)
    workflow.add_node("test", test_node)
    workflow.add_node("defect_validation", defect_validation_node)
    workflow.add_node("complete", complete_node)
    
    # Set entry point
    workflow.set_entry_point("onboarding")
    
    # Add edges
    workflow.add_edge("onboarding", "assignment")
    workflow.add_edge("assignment", "build_hitl")
    workflow.add_edge("build_hitl", "test")
    
    # Conditional edge from test
    workflow.add_conditional_edges(
        "test",
        should_continue_from_test,
        {
            "defect_validation": "defect_validation",
            "complete": "complete"
        }
    )
    
    # Conditional edge from defect_validation
    workflow.add_conditional_edges(
        "defect_validation",
        should_continue_from_defect_validation,
        {
            "build_hitl": "build_hitl",
            "test": "test",
            "complete": "complete"
        }
    )
    
    # Complete is the end
    workflow.add_edge("complete", END)
    
    # Compile the graph
    return workflow.compile()


# Create the compiled workflow
compiled_workflow = create_workflow_graph()


def execute_workflow_stage(
    project_id: str,
    current_stage: Stage,
    context: Dict[str, Any],
    artifacts: List[Dict[str, Any]],
    defects: List[Dict[str, Any]],
    human_gate: bool = False
) -> Dict[str, Any]:
    """
    Execute a single stage of the workflow
    
    Returns the output from the stage node
    """
    state: WorkflowState = {
        "project_id": project_id,
        "current_stage": current_stage.value,
        "last_stage_status": "",
        "context": context,
        "artifacts": artifacts,
        "defects": defects,
        "human_gate": human_gate,
        "stage_meta": {}
    }
    
    # Execute the appropriate node based on current stage
    if current_stage == Stage.ONBOARDING:
        result = onboarding_node(state)
    elif current_stage == Stage.ASSIGNMENT:
        result = assignment_node(state)
    elif current_stage == Stage.BUILD:
        result = build_hitl_node(state)
    elif current_stage == Stage.TEST:
        result = test_node(state)
    elif current_stage == Stage.DEFECT_VALIDATION:
        result = defect_validation_node(state)
    elif current_stage == Stage.COMPLETE:
        result = complete_node(state)
    else:
        result = {
            "stage": current_stage.value,
            "status": "FAILED",
            "summary": f"Unknown stage: {current_stage.value}",
            "structured_output": {},
            "required_next_inputs": [],
            "evidence_required": []
        }
    
    return result
