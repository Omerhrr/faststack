"""
FastStack File Upload Module

Provides file upload handling with validation, resizing, and storage.
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

from fastapi import UploadFile, HTTPException, status

from faststack.config import settings


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


class FileUploader:
    """
    Handles file uploads with validation and storage.
    """

    def __init__(
        self,
        upload_dir: str | Path | None = None,
        max_size: int | None = None,
        allowed_extensions: list[str] | None = None,
        image_max_width: int | None = None,
        image_max_height: int | None = None,
    ):
        """
        Initialize file uploader.

        Args:
            upload_dir: Directory to store uploads
            max_size: Maximum file size in bytes
            allowed_extensions: Allowed file extensions
            image_max_width: Maximum image width (auto-resize)
            image_max_height: Maximum image height (auto-resize)
        """
        self.upload_dir = Path(upload_dir or settings.UPLOAD_DIR)
        self.max_size = max_size or settings.UPLOAD_MAX_SIZE
        self.allowed_extensions = allowed_extensions or settings.UPLOAD_ALLOWED_EXTENSIONS
        self.image_max_width = image_max_width or settings.UPLOAD_IMAGE_MAX_WIDTH
        self.image_max_height = image_max_height or settings.UPLOAD_IMAGE_MAX_HEIGHT

        # Ensure upload directory exists
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename."""
        ext = Path(original_filename).suffix.lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_str = secrets.token_hex(8)
        return f"{timestamp}_{random_str}{ext}"

    def _get_hash(self, content: bytes) -> str:
        """Calculate file hash."""
        return hashlib.sha256(content).hexdigest()

    def _validate_extension(self, filename: str) -> bool:
        """Validate file extension."""
        ext = Path(filename).suffix.lower().lstrip(".")
        return ext in self.allowed_extensions

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
            print(f"[FILE UPLOAD] Image processing error: {e}")
            return content, None, None

    def _get_content_type(self, filename: str, content: bytes) -> str:
        """Get content type from filename or content."""
        import mimetypes
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
        # Validate extension
        if not self._validate_extension(file.filename or ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}",
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

        # Generate filename
        filename = self._generate_filename(file.filename or "upload")

        # Determine upload path
        if subdirectory:
            upload_path = self.upload_dir / subdirectory
            upload_path.mkdir(parents=True, exist_ok=True)
        else:
            upload_path = self.upload_dir

        file_path = upload_path / filename

        # Process image if needed
        width, height = None, None
        if process_image and any(
            file.filename.lower().endswith(ext)
            for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        ):
            content, width, height = await self._process_image(content)
            size = len(content)

        # Save file
        with open(file_path, "wb") as f:
            f.write(content)

        # Build URL
        url = f"/uploads/{subdirectory}/{filename}" if subdirectory else f"/uploads/{filename}"

        return UploadedFile(
            filename=filename,
            original_filename=file.filename or "",
            path=file_path,
            url=url,
            size=size,
            content_type=file.content_type or self._get_content_type(file.filename or "", content),
            hash=self._get_hash(content),
            width=width,
            height=height,
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
        if subdirectory:
            file_path = self.upload_dir / subdirectory / filename
        else:
            file_path = self.upload_dir / filename

        if file_path.exists():
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
        if subdirectory:
            file_path = self.upload_dir / subdirectory / filename
        else:
            file_path = self.upload_dir / filename

        if file_path.exists():
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
        if subdirectory:
            dir_path = self.upload_dir / subdirectory
        else:
            dir_path = self.upload_dir

        if not dir_path.exists():
            return []

        return list(dir_path.iterdir())


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
