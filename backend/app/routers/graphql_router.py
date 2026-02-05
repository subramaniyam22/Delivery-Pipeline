"""
GraphQL router.
"""
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter
from app.graphql.schema import schema

# Create GraphQL router
graphql_router = GraphQLRouter(schema)

# Create API router
router = APIRouter(prefix="/graphql", tags=["graphql"])

# Mount GraphQL router
router.include_router(graphql_router, prefix="")
