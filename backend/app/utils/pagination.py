"""
Pagination utilities for API endpoints.
"""
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Query
from math import ceil

T = TypeVar('T')


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = 1
    page_size: int = 20
    
    class Config:
        frozen = True
    
    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size


class PageMeta(BaseModel):
    """Pagination metadata."""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    meta: PageMeta


def paginate(
    query: Query,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100
) -> tuple[List, PageMeta]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Number of items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Tuple of (items, pagination_meta)
    """
    # Validate and cap page_size
    page_size = min(page_size, max_page_size)
    page = max(1, page)  # Ensure page is at least 1
    
    # Get total count
    total_items = query.count()
    
    # Calculate pagination
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    offset = (page - 1) * page_size
    
    # Get items for current page
    items = query.offset(offset).limit(page_size).all()
    
    # Create metadata
    meta = PageMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )
    
    return items, meta


def create_paginated_response(
    items: List[T],
    page: int,
    page_size: int,
    total_items: int
) -> dict:
    """
    Create a paginated response dictionary.
    
    Args:
        items: List of items for current page
        page: Current page number
        page_size: Items per page
        total_items: Total number of items
        
    Returns:
        Dictionary with items and meta
    """
    total_pages = ceil(total_items / page_size) if total_items > 0 else 1
    
    return {
        "items": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }
