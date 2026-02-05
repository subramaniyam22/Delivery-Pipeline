"""
Cache service for managing application-level caching.
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.utils.cache import cache, invalidate_cache
from app.models import Project, User, SLAConfiguration

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing cache operations."""
    
    # Cache TTL constants (in seconds)
    USER_TTL = 900  # 15 minutes
    PROJECT_TTL = 300  # 5 minutes
    PROJECT_LIST_TTL = 300  # 5 minutes
    CONFIG_TTL = 3600  # 1 hour
    SLA_TTL = 1800  # 30 minutes
    
    @staticmethod
    def get_user(user_id: str, db: Session) -> Optional[Dict]:
        """Get user from cache or database."""
        cache_key = f"user:{user_id}"
        
        # Try cache first
        cached_user = cache.get(cache_key)
        if cached_user:
            logger.debug(f"User cache hit: {user_id}")
            return cached_user
        
        # Cache miss - query database
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "is_active": user.is_active,
                "region": user.region.value if user.region else None
            }
            cache.set(cache_key, user_dict, ttl=CacheService.USER_TTL)
            logger.debug(f"User cached: {user_id}")
            return user_dict
        
        return None
    
    @staticmethod
    def invalidate_user(user_id: str):
        """Invalidate user cache."""
        cache_key = f"user:{user_id}"
        cache.delete(cache_key)
        logger.info(f"User cache invalidated: {user_id}")
    
    @staticmethod
    def get_project(project_id: str, db: Session) -> Optional[Dict]:
        """Get project from cache or database."""
        cache_key = f"project:{project_id}"
        
        # Try cache first
        cached_project = cache.get(cache_key)
        if cached_project:
            logger.debug(f"Project cache hit: {project_id}")
            return cached_project
        
        # Cache miss - query database
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project_dict = {
                "id": str(project.id),
                "title": project.title,
                "status": project.status.value,
                "current_stage": project.current_stage.value,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            }
            cache.set(cache_key, project_dict, ttl=CacheService.PROJECT_TTL)
            logger.debug(f"Project cached: {project_id}")
            return project_dict
        
        return None
    
    @staticmethod
    def invalidate_project(project_id: str):
        """Invalidate project cache."""
        cache_key = f"project:{project_id}"
        cache.delete(cache_key)
        # Also invalidate project lists
        invalidate_cache("projects:list:*")
        logger.info(f"Project cache invalidated: {project_id}")
    
    @staticmethod
    def invalidate_all_projects():
        """Invalidate all project caches."""
        invalidate_cache("project:*")
        invalidate_cache("projects:list:*")
        logger.info("All project caches invalidated")
    
    @staticmethod
    def get_sla_configs(db: Session) -> Dict[str, Any]:
        """Get SLA configurations from cache or database."""
        cache_key = "config:sla"
        
        # Try cache first
        cached_configs = cache.get(cache_key)
        if cached_configs:
            logger.debug("SLA config cache hit")
            return cached_configs
        
        # Cache miss - query database
        configs = db.query(SLAConfiguration).all()
        config_dict = {
            config.stage.value: {
                "default_days": config.default_days,
                "warning_threshold_days": config.warning_threshold_days,
                "critical_threshold_days": config.critical_threshold_days
            }
            for config in configs
        }
        
        cache.set(cache_key, config_dict, ttl=CacheService.SLA_TTL)
        logger.debug("SLA configs cached")
        return config_dict
    
    @staticmethod
    def invalidate_sla_configs():
        """Invalidate SLA configuration cache."""
        cache.delete("config:sla")
        logger.info("SLA config cache invalidated")
    
    @staticmethod
    def get_cache_stats() -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            if not cache.client:
                return {"status": "disconnected"}
            
            info = cache.client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": cache.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100,
                    2
                )
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"status": "error", "message": str(e)}


# Global cache service instance
cache_service = CacheService()
