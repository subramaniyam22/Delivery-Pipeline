"""
Retry logic with exponential backoff for external service calls.
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)
import logging
from typing import Callable, Any
import httpx
from app.custom_exceptions import ExternalServiceException

logger = logging.getLogger(__name__)


# Retry decorator for external API calls
retry_external_api = retry(
    stop=stop_after_attempt(3),  # Max 3 attempts
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 8s
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO)
)


# Retry decorator for database operations
retry_database = retry(
    stop=stop_after_attempt(2),  # Max 2 attempts
    wait=wait_exponential(multiplier=0.5, min=1, max=5),  # 1s, 2.5s
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)


# Retry decorator for S3 operations
retry_s3 = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)


# Retry decorator for email sending
retry_email = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),  # 4s, 8s, 16s
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.ERROR)
)


def with_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    exception_types: tuple = (Exception,)
) -> Callable:
    """
    Custom retry decorator factory.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        exception_types: Tuple of exception types to retry on
        
    Returns:
        Retry decorator
        
    Usage:
        @with_retry(max_attempts=5, min_wait=2, max_wait=20)
        def my_function():
            # Your code here
            pass
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exception_types),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO)
    )


# Example usage in services:
"""
from app.utils.retry import retry_external_api, retry_s3, retry_email

class S3Service:
    @retry_s3
    def upload_file(self, file_path: str, bucket: str):
        # S3 upload logic
        pass

class EmailService:
    @retry_email
    def send_email(self, to: str, subject: str, body: str):
        # Email sending logic
        pass

class ExternalAPIService:
    @retry_external_api
    async def fetch_data(self, url: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            return response.json()
"""
