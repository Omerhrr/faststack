"""
FastStack File Upload Module

Provides file upload handling with validation, resizing, and storage.
Includes security features:
- Path traversal prevention
- Magic byte validation
- Filename sanitization
"""

import hashlib
import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Callable
import re

from fastapi import UploadFile, HTTPException, status

from faststack.config import settings


# Magic bytes for common file types
MAGIC_BYTES = {
    # Images
    b'\xff\xd8\xff': 'jpeg',
    b'\x89PNG\r\n\x1a\n': 'png',
    b'GIF87a': 'gif',
    b'GIF89a': 'gif',
    b'RIFF': 'webp',  # WebP starts with RIFF....WEBP
    b'\x00\x00\x00\x1cftyp': 'heic',
    b'\x00\x00\x00\x20ftyp': 'heic',
    # Documents
    b'%PDF': 'pdf',
    b'PK\x03\x04': 'zip',  # Also docx, xlsx, etc.
    # Audio
    b'ID3': 'mp3',
    b'\xff\xfb': 'mp3',
    b'\xff\xfa': 'mp3',
    b'ftypM4A': 'm4a',
    # Video
    b'\x00\x00\x00\x1cftyp': 'mp4',
    b'\x00\x00\x00\x20ftyp': 'mp4',
}

# Dangerous file types that should never be allowed
DANGEROUS_EXTENSIONS = {
    'exe', 'dll', 'bat', 'cmd', 'sh', 'ps1', 'vbs', 'js', 'jar',
    'msi', 'com', 'scr', 'pif', 'application', 'gadget',
    'py', 'pyc', 'pyo', 'rb', 'pl', 'php', 'asp', 'aspx',
    'jsp', 'cgi', 'shtml', 'htm', 'html',  # html can have XSS
}


@dataclass
class UploadedFile:
    """Represents an uploaded file."""
    filename: str
    original_filename: str
    path: Path
    url: str
    size: int
    content_type: str
    hash: str
    width: int | None = None
    height: int | None = None
    detected_type: str | None = None


class FileUploader:
    """
    Handles file uploads with validation and storage.
    
    Security features:
    - Path traversal prevention
    - Magic byte validation
    - Filename sanitization
    - Size limits
    - Extension validation
    """

    def __init__(
        self,
        upload_dir: str | Path | None = None,
        max_size: int | None = None,
        allowed_extensions: list[str] | None = None,
        image_max_width: int | None = None,
        image_max_height: int | None = None,
        validate_content: bool | None = None,
    ):
        """
        Initialize file uploader.

        Args:
            upload_dir: Directory to store uploads
            max_size: Maximum file size in bytes
            allowed_extensions: Allowed file extensions
            image_max_width: Maximum image width (auto-resize)
            image_max_height: Maximum image height (auto-resize)
            validate_content: Validate file content with magic bytes
        """
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.max_size = max_size or settings.UPLOAD_MAX_SIZE
        self.allowed_extensions = set(
            ext.lower().lstrip('.') 
            for ext in (allowed_extensions or settings.UPLOAD_ALLOWED_EXTENSIONS)
        )
        # Remove dangerous extensions from allowed list
        self.allowed_extensions -= DANGEROUS_EXTENSIONS
        self.image_max_width = image_max_width or settings.UPLOAD_IMAGE_MAX_WIDTH
        self.image_max_height = image_max_height or settings.UPLOAD_IMAGE_MAX_HEIGHT
        self.validate_content = validate_content if validate_content is not None else settings.UPLOAD_VALIDATE_CONTENT

        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to remove dangerous characters.
        
        Args:
            filename: Original filename
        
        Returns:
            Sanitized filename
        """
        # Remove path separators and null bytes
        filename = filename.replace('/', '_').replace('\\', '_').replace('\x00', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*\x00-\x1f]', '_', filename)
        
        # Remove leading dots (hidden files)
        filename = filename.lstrip('.')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:250 - len(ext)] + ext
        
        return filename

    def _generate_filename(self, original_filename: str) -> str:
        """
        Generate a unique, safe filename.
        
        Args:
            original_filename: Original filename
        
        Returns:
            Generated unique filename
        """
        # Sanitize original filename first
        safe_filename = self._sanitize_filename(original_filename)
        
        # Get extension (from sanitized name)
        ext = Path(safe_filename).suffix.lower()
        
        # Ensure extension is safe
        if ext and ext.lstrip('.').lower() in DANGEROUS_EXTENSIONS:
            ext = '.txt'  # Safe default
        
        # Generate unique name
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(8)
        return f"{timestamp}_{random_str}{ext}"

    def _validate_subdirectory(self, subdirectory: str | None) -> str:
        """
        Validate subdirectory to prevent path traversal.
        
        Args:
            subdirectory: Requested subdirectory path
        
        Returns:
            Safe subdirectory path
        
        Raises:
            HTTPException: If path traversal detected
        """
        if not subdirectory:
            return ""
        
        # Normalize path
        subdirectory = subdirectory.strip('/')
        
        # Check for path traversal attempts
        if '..' in subdirectory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subdirectory: path traversal not allowed",
            )
        
        # Check for absolute paths
        if subdirectory.startswith('/') or ':' in subdirectory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subdirectory: absolute paths not allowed",
            )
        
        # Check for null bytes
        if '\x00' in subdirectory:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subdirectory",
            )
        
        # Validate each component
        for part in subdirectory.split('/'):
            if not part or part.startswith('.'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid subdirectory component",
                )
        
        return subdirectory

    def _get_hash(self, content: bytes) -> str:
        """Calculate file hash."""
        return hashlib.sha256(content).hexdigest()

    def _validate_extension(self, filename: str) -> bool:
        """
        Validate file extension.
        
        Args:
            filename: Filename to validate
        
        Returns:
            True if extension is allowed
        """
        ext = Path(filename).suffix.lower().lstrip('.')
        return ext in self.allowed_extensions

    def _detect_file_type(self, content: bytes) -> str | None:
        """
        Detect file type from magic bytes.
        
        Args:
            content: File content bytes
        
        Returns:
            Detected file extension or None
        """
        for magic, ext in MAGIC_BYTES.items():
            if content.startswith(magic):
                # Special case for WebP
                if magic == b'RIFF' and len(content) >= 12:
                    if content[8:12] == b'WEBP':
                        return 'webp'
                # Special case for MP4/MOV
                if b'ftyp' in magic:
                    if len(content) >= 12:
                        ftyp = content[4:8]
                        if ftyp in [b'isom', b'mp41', b'mp42', b'avc1', b'M4V', b'M4A']:
                            return 'mp4'
                return ext
        return None

    def _validate_content_type(self, content: bytes, filename: str) -> tuple[bool, str | None]:
        """
        Validate file content matches extension.
        
        Args:
            content: File content bytes
            filename: Original filename
        
        Returns:
            Tuple of (is_valid, detected_type)
        """
        if not self.validate_content:
            return True, None
        
        # Get expected extension
        expected_ext = Path(filename).suffix.lower().lstrip('.')
        
        # Detect actual type
        detected_ext = self._detect_file_type(content)
        
        # If we detected a type, verify it matches
        if detected_ext:
            # Allow some type equivalence
            equivalent_types = {
                'jpg': ['jpeg', 'jpg'],
                'jpeg': ['jpeg', 'jpg'],
                'docx': ['zip', 'docx'],  # docx is a zip file
                'xlsx': ['zip', 'xlsx'],  # xlsx is a zip file
            }
            
            allowed = equivalent_types.get(expected_ext, [expected_ext])
            if detected_ext not in allowed:
                return False, detected_ext
        
        return True, detected_ext

    def _validate_size(self, size: int) -> bool:
        """Validate file size."""
        return size <= self.max_size

    async def _process_image(self, content: bytes) -> tuple[bytes, int | None, int | None]:
        """
        Process image - resize if needed.

        Returns:
            Tuple of (processed_content, width, height)
        """
        try:
            from PIL import Image
        except ImportError:
            return content, None, None

        try:
            img = Image.open(BytesIO(content))
            width, height = img.size

            # Check if resize is needed
            if width > self.image_max_width or height > self.image_max_height:
                # Calculate new size maintaining aspect ratio
                ratio = min(
                    self.image_max_width / width,
                    self.image_max_height / height,
                )
                new_width = int(width * ratio)
                new_height = int(height * ratio)

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = new_width, new_height

            # Convert back to bytes
            output = BytesIO()
            format = img.format or "JPEG"
            img.save(output, format=format)
            return output.getvalue(), width, height

        except Exception as e:
            # Log error but don't expose to user
            print(f"[FILE UPLOAD] Image processing error: {e}")
            return content, None, None

    def _get_content_type(self, filename: str, content: bytes) -> str:
        """Get content type from filename or content."""
        import mimetypes
        
        # Try to detect from content first
        if self.validate_content:
            detected = self._detect_file_type(content)
            if detected:
                mime_type, _ = mimetypes.guess_type(f"file.{detected}")
                if mime_type:
                    return mime_type
        
        # Fall back to filename
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    async def upload(
        self,
        file: UploadFile,
        subdirectory: str | None = None,
        process_image: bool = True,
    ) -> UploadedFile:
        """
        Upload a file.

        Args:
            file: FastAPI UploadFile
            subdirectory: Subdirectory within upload dir
            process_image: Whether to process images

        Returns:
            UploadedFile with file info

        Raises:
            HTTPException: If validation fails
        """
        # Validate and sanitize subdirectory
        safe_subdirectory = self._validate_subdirectory(subdirectory)
        
        # Get and sanitize filename
        original_filename = self._sanitize_filename(file.filename or "upload")
        
        # Validate extension
        if not self._validate_extension(original_filename):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(sorted(self.allowed_extensions))}",
            )

        # Read content
        content = await file.read()
        size = len(content)

        # Validate size
        if not self._validate_size(size):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {self.max_size // (1024 * 1024)}MB",
            )

        # Validate content type (magic bytes)
        is_valid_content, detected_type = self._validate_content_type(content, original_filename)
        if not is_valid_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content does not match extension. Detected: {detected_type}",
            )

        # Generate safe filename
        filename = self._generate_filename(original_filename)
        
        # If we detected a different type, use that extension
        if detected_type and detected_type not in DANGEROUS_EXTENSIONS:
            base = filename.rsplit('.', 1)[0]
            filename = f"{base}.{detected_type}"

        # Determine upload path (with validated subdirectory)
        if safe_subdirectory:
            upload_path = self.upload_dir / safe_subdirectory
            upload_path.mkdir(parents=True, exist_ok=True)
        else:
            upload_path = self.upload_dir

        file_path = upload_path / filename
        
        # Final safety check - ensure file_path is within upload_dir
        try:
            file_path.resolve().relative_to(self.upload_dir.resolve())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path",
            )

        # Process image if needed
        width, height = None, None
        if process_image and any(
            original_filename.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        ):
            content, width, height = await self._process_image(content)
            size = len(content)

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Build URL
        url = f"/uploads/{safe_subdirectory}/{filename}" if safe_subdirectory else f"/uploads/{filename}"

        return UploadedFile(
            filename=filename,
            original_filename=original_filename,
            path=file_path,
            url=url,
            size=size,
            content_type=file.content_type or self._get_content_type(original_filename, content),
            hash=self._get_hash(content),
            width=width,
            height=height,
            detected_type=detected_type,
        )

    def delete(self, filename: str, subdirectory: str | None = None) -> bool:
        """
        Delete an uploaded file.

        Args:
            filename: Filename to delete
            subdirectory: Subdirectory within upload dir

        Returns:
            True if file was deleted
        """
        # Validate subdirectory
        safe_subdirectory = self._validate_subdirectory(subdirectory)
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        if safe_subdirectory:
            file_path = self.upload_dir / safe_subdirectory / safe_filename
        else:
            file_path = self.upload_dir / safe_filename
        
        # Safety check - ensure within upload_dir
        try:
            file_path.resolve().relative_to(self.upload_dir.resolve())
        except ValueError:
            return False

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
        return False

    def get_file(self, filename: str, subdirectory: str | None = None) -> Path | None:
        """
        Get path to an uploaded file.

        Args:
            filename: Filename to get
            subdirectory: Subdirectory within upload dir

        Returns:
            Path to file or None if not found
        """
        # Validate subdirectory
        safe_subdirectory = self._validate_subdirectory(subdirectory)
        
        # Sanitize filename
        safe_filename = self._sanitize_filename(filename)
        
        if safe_subdirectory:
            file_path = self.upload_dir / safe_subdirectory / safe_filename
        else:
            file_path = self.upload_dir / safe_filename
        
        # Safety check
        try:
            file_path.resolve().relative_to(self.upload_dir.resolve())
        except ValueError:
            return None

        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    def list_files(self, subdirectory: str | None = None) -> list[Path]:
        """
        List all uploaded files.

        Args:
            subdirectory: Subdirectory within upload dir

        Returns:
            List of file paths
        """
        # Validate subdirectory
        safe_subdirectory = self._validate_subdirectory(subdirectory)
        
        if safe_subdirectory:
            dir_path = self.upload_dir / safe_subdirectory
        else:
            dir_path = self.upload_dir

        if not dir_path.exists():
            return []

        return [p for p in dir_path.iterdir() if p.is_file()]


# Global uploader instance
_file_uploader: FileUploader | None = None


def get_file_uploader() -> FileUploader:
    """Get the global file uploader instance."""
    global _file_uploader
    if _file_uploader is None:
        _file_uploader = FileUploader()
    return _file_uploader


async def upload_file(
    file: UploadFile,
    subdirectory: str | None = None,
    process_image: bool = True,
) -> UploadedFile:
    """
    Upload a file using the global uploader.

    Args:
        file: FastAPI UploadFile
        subdirectory: Subdirectory within upload dir
        process_image: Whether to process images

    Returns:
        UploadedFile with file info
    """
    uploader = get_file_uploader()
    return await uploader.upload(file, subdirectory, process_image)


def delete_file(filename: str, subdirectory: str | None = None) -> bool:
    """
    Delete a file using the global uploader.

    Args:
        filename: Filename to delete
        subdirectory: Subdirectory within upload dir

    Returns:
        True if file was deleted
    """
    uploader = get_file_uploader()
    return uploader.delete(filename, subdirectory)
