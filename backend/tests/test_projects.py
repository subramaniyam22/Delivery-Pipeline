"""
Tests for project endpoints.
"""
import pytest
from fastapi import status
from app.models import ProjectStatus, Stage


@pytest.mark.unit
class TestCreateProject:
    """Test project creation."""
    
    def test_create_project_as_sales(self, client, sales_auth_headers, manager_user):
        """Test creating project as sales user."""
        project_data = {
            "title": "Test Project",
            "client_name": "Test Client",
            "priority": "HIGH",
            "pmc_name": "Test PMC",
            "location": "Test Location",
            "client_email_ids": ["client@test.com"],
            "manager_user_id": str(manager_user.id)
        }
        
        response = client.post(
            "/projects",
            json=project_data,
            headers=sales_auth_headers
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "Test Project"
        assert data["client_name"] == "Test Client"
        assert data["status"] == ProjectStatus.DRAFT.value
        assert data["current_stage"] == Stage.SALES.value
    
    def test_create_project_as_non_sales(self, client, manager_auth_headers):
        """Test creating project as non-sales user (should fail)."""
        project_data = {
            "title": "Test Project",
            "client_name": "Test Client",
            "priority": "HIGH"
        }
        
        response = client.post(
            "/projects",
            json=project_data,
            headers=manager_auth_headers
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.unit
class TestListProjects:
    """Test project listing."""
    
    def test_list_projects_empty(self, client, auth_headers):
        """Test listing projects when none exist."""
        response = client.get("/projects", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
    
    def test_list_projects_with_pagination(self, client, sales_auth_headers, manager_user, db_session):
        """Test listing projects with pagination."""
        from app.models import Project
        
        # Create multiple projects
        for i in range(15):
            project = Project(
                title=f"Project {i}",
                client_name=f"Client {i}",
                priority="MEDIUM",
                status=ProjectStatus.DRAFT,
                current_stage=Stage.SALES
            )
            db_session.add(project)
        db_session.commit()
        
        # Test first page
        response = client.get(
            "/projects?page=1&page_size=10",
            headers=sales_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 10
        
        # Test second page
        response = client.get(
            "/projects?page=2&page_size=10",
            headers=sales_auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 5


@pytest.mark.integration
class TestProjectFlow:
    """Test complete project workflow."""
    
    def test_create_and_retrieve_project(self, client, sales_auth_headers, manager_user):
        """Test creating and retrieving a project."""
        # Create project
        project_data = {
            "title": "Integration Test Project",
            "client_name": "Integration Client",
            "priority": "HIGH",
            "pmc_name": "Test PMC",
            "location": "Test Location",
            "client_email_ids": ["client@test.com"],
            "manager_user_id": str(manager_user.id)
        }
        
        create_response = client.post(
            "/projects",
            json=project_data,
            headers=sales_auth_headers
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        project_id = create_response.json()["id"]
        
        # Retrieve project
        get_response = client.get(
            f"/projects/{project_id}",
            headers=sales_auth_headers
        )
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["title"] == "Integration Test Project"
