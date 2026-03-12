"""
File storage service for managing PDF files
"""
import os
import uuid
from pathlib import Path
from typing import Optional

class FileStorageService:
    """Service for managing file storage"""
    
    def __init__(self):
        # Create uploads directory
        self.upload_dir = Path("uploads/resumes")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_bytes: bytes, filename: str) -> str:
        """
        Save a file to disk and return the file path
        
        Args:
            file_bytes: The file content as bytes
            filename: The original filename
            
        Returns:
            The path where the file was saved
        """
        # Generate unique filename
        file_id = str(uuid.uuid4())
        ext = Path(filename).suffix if Path(filename).suffix else ".pdf"
        saved_filename = f"{file_id}{ext}"
        file_path = self.upload_dir / saved_filename
        
        # Save the file
        with open(file_path, 'wb') as f:
            f.write(file_bytes)
        
        return str(file_path)
    
    def get_file(self, file_path: str) -> Optional[bytes]:
        """
        Read a file from disk
        
        Args:
            file_path: The path to the file
            
        Returns:
            The file content as bytes, or None if not found
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except (FileNotFoundError, IOError):
            return None
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from disk
        
        Args:
            file_path: The path to the file
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            Path(file_path).unlink()
            return True
        except (FileNotFoundError, IOError):
            return False
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        return Path(file_path).exists()


# Singleton instance
file_storage_service = FileStorageService()
