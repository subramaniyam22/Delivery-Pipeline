"""
Tests for caching functionality.
"""
import pytest
from app.utils.cache import cache, CacheManager
from app.services.cache_service import cache_service


@pytest.mark.unit
class TestCacheManager:
    """Test cache manager functionality."""
    
    def test_set_and_get(self):
        """Test setting and getting cache values."""
        cache_manager = CacheManager()
        
        # Set value
        success = cache_manager.set("test_key", {"data": "test_value"}, ttl=60)
        assert success is True
        
        # Get value
        value = cache_manager.get("test_key")
        assert value == {"data": "test_value"}
    
    def test_get_nonexistent_key(self):
        """Test getting non-existent key."""
        cache_manager = CacheManager()
        value = cache_manager.get("nonexistent_key")
        assert value is None
    
    def test_delete_key(self):
        """Test deleting cache key."""
        cache_manager = CacheManager()
        
        # Set and verify
        cache_manager.set("delete_test", {"data": "value"})
        assert cache_manager.get("delete_test") is not None
        
        # Delete and verify
        cache_manager.delete("delete_test")
        assert cache_manager.get("delete_test") is None
    
    def test_delete_pattern(self):
        """Test deleting keys by pattern."""
        cache_manager = CacheManager()
        
        # Set multiple keys
        cache_manager.set("project:1", {"id": 1})
        cache_manager.set("project:2", {"id": 2})
        cache_manager.set("user:1", {"id": 1})
        
        # Delete project keys
        deleted = cache_manager.delete_pattern("project:*")
        assert deleted >= 2
        
        # Verify
        assert cache_manager.get("project:1") is None
        assert cache_manager.get("project:2") is None
        assert cache_manager.get("user:1") is not None


@pytest.mark.unit
class TestCacheService:
    """Test cache service functionality."""
    
    def test_invalidate_project(self):
        """Test project cache invalidation."""
        # Set cache
        cache.set("project:123", {"id": "123", "title": "Test"})
        assert cache.get("project:123") is not None
        
        # Invalidate
        cache_service.invalidate_project("123")
        
        # Verify
        assert cache.get("project:123") is None
    
    def test_invalidate_all_projects(self):
        """Test invalidating all project caches."""
        # Set multiple project caches
        cache.set("project:1", {"id": "1"})
        cache.set("project:2", {"id": "2"})
        cache.set("projects:list:page1", [{"id": "1"}, {"id": "2"}])
        
        # Invalidate all
        cache_service.invalidate_all_projects()
        
        # Verify
        assert cache.get("project:1") is None
        assert cache.get("project:2") is None
        assert cache.get("projects:list:page1") is None


@pytest.mark.integration
class TestCacheEndpoints:
    """Test cache management endpoints."""
    
    def test_get_cache_stats(self, client, auth_headers):
        """Test getting cache statistics."""
        response = client.get("/cache/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_invalidate_projects_cache(self, client, auth_headers):
        """Test invalidating projects cache."""
        response = client.post("/cache/invalidate/projects", headers=auth_headers)
        assert response.status_code == 200
        assert "invalidated" in response.json()["message"].lower()
    
    def test_cache_stats_non_admin(self, client, sales_auth_headers):
        """Test cache stats access as non-admin (should fail)."""
        response = client.get("/cache/stats", headers=sales_auth_headers)
        assert response.status_code == 403
