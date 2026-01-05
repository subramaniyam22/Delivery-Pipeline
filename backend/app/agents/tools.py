# Connector stub tools for external integrations
# These return mock data and should be replaced with actual API calls

def fetch_requirement(requirement_id: str) -> dict:
    """
    Fetch requirement details from external system
    TODO: Implement actual API call to requirements management system
    """
    return {
        "id": requirement_id,
        "title": f"Mock Requirement {requirement_id}",
        "description": "This is a mock requirement. Replace with actual API call.",
        "status": "APPROVED",
        "priority": "HIGH"
    }


def fetch_external_task(task_id: str) -> dict:
    """
    Fetch task details from external project management system
    TODO: Implement actual API call to project management tool (Jira, etc.)
    """
    return {
        "id": task_id,
        "title": f"Mock External Task {task_id}",
        "status": "IN_PROGRESS",
        "assignee": "external_user@example.com",
        "due_date": "2025-01-15"
    }


def fetch_staging_url(project_id: str) -> str:
    """
    Fetch staging environment URL for the project
    TODO: Implement actual API call to deployment system
    """
    return f"https://staging-{project_id}.example.com"


def fetch_defect_from_tracker(external_id: str) -> dict:
    """
    Fetch defect details from external defect tracking system
    TODO: Implement actual API call to defect tracker (Jira, Bugzilla, etc.)
    """
    return {
        "id": external_id,
        "title": f"Mock Defect {external_id}",
        "severity": "HIGH",
        "status": "OPEN",
        "description": "This is a mock defect. Replace with actual API call.",
        "reporter": "tester@example.com"
    }


def fetch_logs(project_id: str) -> list:
    """
    Fetch application logs from logging system
    TODO: Implement actual API call to logging infrastructure (CloudWatch, ELK, etc.)
    """
    return [
        {
            "timestamp": "2025-12-28T10:00:00Z",
            "level": "INFO",
            "message": f"Mock log entry for project {project_id}",
            "source": "application"
        },
        {
            "timestamp": "2025-12-28T10:05:00Z",
            "level": "ERROR",
            "message": "Mock error log. Replace with actual log fetching.",
            "source": "application"
        }
    ]
