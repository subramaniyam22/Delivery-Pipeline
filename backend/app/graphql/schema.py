"""
GraphQL schema and types.
"""
from typing import List, Optional
import strawberry
from datetime import datetime


@strawberry.type
class User:
    """User GraphQL type."""
    id: str
    email: str
    name: str
    role: str
    region: Optional[str]
    is_active: bool
    created_at: datetime


@strawberry.type
class Project:
    """Project GraphQL type."""
    id: str
    title: str
    client_name: str
    status: str
    current_stage: str
    priority: str
    created_at: datetime
    updated_at: datetime
    created_by_user_id: Optional[str]
    sales_user_id: Optional[str]
    manager_user_id: Optional[str]


@strawberry.type
class Task:
    """Task GraphQL type."""
    id: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    project_id: str
    assigned_to_user_id: Optional[str]
    created_at: datetime
    due_date: Optional[datetime]


@strawberry.type
class Query:
    """GraphQL queries."""
    
    @strawberry.field
    def hello(self) -> str:
        """Test query."""
        return "Hello from GraphQL!"
    
    @strawberry.field
    async def projects(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Project]:
        """
        Get projects with optional filtering.
        
        Args:
            limit: Maximum number of projects to return
            offset: Number of projects to skip
            status: Filter by status
        """
        # TODO: Implement database query
        return []
    
    @strawberry.field
    async def project(self, id: str) -> Optional[Project]:
        """
        Get project by ID.
        
        Args:
            id: Project ID
        """
        # TODO: Implement database query
        return None
    
    @strawberry.field
    async def users(
        self,
        limit: int = 50,
        offset: int = 0,
        role: Optional[str] = None
    ) -> List[User]:
        """
        Get users with optional filtering.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            role: Filter by role
        """
        # TODO: Implement database query
        return []
    
    @strawberry.field
    async def me(self, info) -> Optional[User]:
        """Get current authenticated user."""
        # TODO: Get user from context
        return None


@strawberry.type
class Mutation:
    """GraphQL mutations."""
    
    @strawberry.mutation
    async def create_project(
        self,
        title: str,
        client_name: str,
        priority: str
    ) -> Project:
        """
        Create a new project.
        
        Args:
            title: Project title
            client_name: Client name
            priority: Project priority
        """
        # TODO: Implement project creation
        raise NotImplementedError("Create project mutation not implemented")
    
    @strawberry.mutation
    async def update_project(
        self,
        id: str,
        title: Optional[str] = None,
        status: Optional[str] = None
    ) -> Project:
        """
        Update project.
        
        Args:
            id: Project ID
            title: New title
            status: New status
        """
        # TODO: Implement project update
        raise NotImplementedError("Update project mutation not implemented")


# Create GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
