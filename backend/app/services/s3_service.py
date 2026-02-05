"""
Enhanced S3 service with file migration support.
"""
import boto3
import logging
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
from app.config import settings
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class S3Service:
    """AWS S3 service for file storage."""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Upload file to S3.
        
        Args:
            file_obj: File object to upload
            object_name: S3 object name (key)
            content_type: MIME type
            metadata: Additional metadata
        
        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_name,
                ExtraArgs=extra_args
            )
            
            logger.info(f"File uploaded to S3: {object_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
    
    def download_file(self, object_name: str, file_path: str) -> bool:
        """Download file from S3."""
        try:
            self.s3_client.download_file(
                self.bucket_name,
                object_name,
                file_path
            )
            logger.info(f"File downloaded from S3: {object_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
    
    def delete_file(self, object_name: str) -> bool:
        """Delete file from S3."""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            logger.info(f"File deleted from S3: {object_name}")
            return True
        
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def generate_presigned_url(
        self,
        object_name: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary access.
        
        Args:
            object_name: S3 object name
            expiration: URL expiration in seconds (default: 1 hour)
        
        Returns:
            Presigned URL or None
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            return url
        
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            return True
        
        except ClientError:
            return False
    
    def list_files(self, prefix: str = "") -> list:
        """List files in S3 bucket with optional prefix."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                return [obj['Key'] for obj in response['Contents']]
            return []
        
        except ClientError as e:
            logger.error(f"Error listing files in S3: {e}")
            return []
    
    def get_file_metadata(self, object_name: str) -> Optional[dict]:
        """Get file metadata from S3."""
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            
            return {
                'size': response.get('ContentLength'),
                'content_type': response.get('ContentType'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
        
        except ClientError as e:
            logger.error(f"Error getting file metadata: {e}")
            return None


# Global S3 service instance
s3_service = S3Service()
