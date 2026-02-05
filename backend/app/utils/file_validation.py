"""
File upload validation utilities.
"""
from fastapi import UploadFile, HTTPException
from pathlib import Path
from typing import Set, Optional
import magic  # python-magic for MIME type detection
import hashlib
import logging

logger = logging.getLogger(__name__)

# Allowed file extensions and their MIME types
ALLOWED_EXTENSIONS = {
    # Images
    '.jpg': {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.png': {'image/png'},
    '.gif': {'image/gif'},
    '.webp': {'image/webp'},
    '.svg': {'image/svg+xml'},
    
    # Documents
    '.pdf': {'application/pdf'},
    '.doc': {'application/msword'},
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
    '.xls': {'application/vnd.ms-excel'},
    '.xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
    '.ppt': {'application/vnd.ms-powerpoint'},
    '.pptx': {'application/vnd.openxmlformats-officedocument.presentationml.presentation'},
    '.txt': {'text/plain'},
    '.csv': {'text/csv', 'application/vnd.ms-excel'},
    
    # Archives
    '.zip': {'application/zip'},
    '.rar': {'application/x-rar-compressed'},
    '.7z': {'application/x-7z-compressed'},
}

# Maximum file sizes by category (in bytes)
MAX_FILE_SIZES = {
    'image': 10 * 1024 * 1024,      # 10MB for images
    'document': 50 * 1024 * 1024,   # 50MB for documents
    'archive': 100 * 1024 * 1024,   # 100MB for archives
    'default': 10 * 1024 * 1024,    # 10MB default
}

# Dangerous file extensions (never allow)
DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
    '.jar', '.msi', '.app', '.deb', '.rpm', '.sh', '.bash', '.ps1'
}


class FileValidator:
    """Comprehensive file validation."""
    
    @staticmethod
    def get_file_category(extension: str) -> str:
        """Determine file category based on extension."""
        if extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            return 'image'
        elif extension in ['.zip', '.rar', '.7z']:
            return 'archive'
        elif extension in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv']:
            return 'document'
        return 'default'
    
    @staticmethod
    async def validate_file(
        file: UploadFile,
        allowed_extensions: Optional[Set[str]] = None,
        max_size: Optional[int] = None,
        check_mime: bool = True
    ) -> dict:
        """
        Comprehensive file validation.
        
        Args:
            file: The uploaded file
            allowed_extensions: Set of allowed extensions (uses default if None)
            max_size: Maximum file size in bytes (uses category default if None)
            check_mime: Whether to verify MIME type matches extension
            
        Returns:
            dict with file info if valid
            
        Raises:
            HTTPException: If validation fails
        """
        # 1. Check if file exists
        if not file or not file.filename:
            raise HTTPException(400, "No file provided")
        
        # 2. Extract and validate extension
        file_ext = Path(file.filename).suffix.lower()
        
        if not file_ext:
            raise HTTPException(400, "File must have an extension")
        
        # 3. Check for dangerous extensions
        if file_ext in DANGEROUS_EXTENSIONS:
            logger.warning(f"Blocked dangerous file upload attempt: {file.filename}")
            raise HTTPException(400, f"File type {file_ext} is not allowed for security reasons")
        
        # 4. Check allowed extensions
        extensions_to_check = allowed_extensions or set(ALLOWED_EXTENSIONS.keys())
        if file_ext not in extensions_to_check:
            raise HTTPException(
                400,
                f"File type {file_ext} not allowed. Allowed types: {', '.join(extensions_to_check)}"
            )
        
        # 5. Check file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        category = FileValidator.get_file_category(file_ext)
        max_allowed_size = max_size or MAX_FILE_SIZES.get(category, MAX_FILE_SIZES['default'])
        
        if file_size > max_allowed_size:
            size_mb = max_allowed_size / (1024 * 1024)
            raise HTTPException(
                400,
                f"File too large. Maximum size: {size_mb:.1f}MB"
            )
        
        if file_size == 0:
            raise HTTPException(400, "File is empty")
        
        # 6. Verify MIME type (if enabled)
        if check_mime:
            content = await file.read(2048)  # Read first 2KB for MIME detection
            await file.seek(0)  # Reset
            
            try:
                # Detect MIME type from content
                mime = magic.from_buffer(content, mime=True)
                
                # Check if MIME matches expected types for this extension
                expected_mimes = ALLOWED_EXTENSIONS.get(file_ext, set())
                if expected_mimes and mime not in expected_mimes:
                    logger.warning(
                        f"MIME type mismatch: {file.filename} has extension {file_ext} "
                        f"but MIME type {mime}. Expected: {expected_mimes}"
                    )
                    raise HTTPException(
                        400,
                        f"File content doesn't match extension. Expected {file_ext} but got {mime}"
                    )
            except Exception as e:
                logger.error(f"MIME type detection failed: {str(e)}")
                # Continue without MIME check if detection fails
        
        # 7. Calculate file hash (for deduplication/integrity)
        file_hash = await FileValidator.calculate_file_hash(file)
        
        return {
            'filename': file.filename,
            'extension': file_ext,
            'size': file_size,
            'category': category,
            'hash': file_hash,
            'content_type': file.content_type
        }
    
    @staticmethod
    async def calculate_file_hash(file: UploadFile) -> str:
        """Calculate SHA256 hash of file content."""
        sha256 = hashlib.sha256()
        
        # Read file in chunks
        chunk_size = 8192
        while chunk := await file.read(chunk_size):
            sha256.update(chunk)
        
        await file.seek(0)  # Reset file pointer
        return sha256.hexdigest()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Get just the filename (remove any path components)
        filename = Path(filename).name
        
        # Remove or replace dangerous characters
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 255:
            ext = Path(filename).suffix
            name = Path(filename).stem[:255 - len(ext)]
            filename = f"{name}{ext}"
        
        return filename


# Convenience function for common use case
async def validate_upload(
    file: UploadFile,
    allowed_types: Optional[Set[str]] = None,
    max_size_mb: Optional[float] = None
) -> dict:
    """
    Validate an uploaded file (convenience wrapper).
    
    Args:
        file: The uploaded file
        allowed_types: Set of allowed extensions (e.g., {'.jpg', '.png'})
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        File info dict if valid
        
    Raises:
        HTTPException: If validation fails
    """
    max_size_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb else None
    return await FileValidator.validate_file(file, allowed_types, max_size_bytes)
