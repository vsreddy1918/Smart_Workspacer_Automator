"""File scanner module for Smart Workspace Automator."""

import os
import mimetypes
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List

from config import Config


@dataclass
class FileMetadata:
    """Metadata for a file in the Downloads folder."""
    
    path: Path
    name: str
    extension: str
    mime_type: str
    size: int
    modified_time: datetime
    is_hidden: bool


class FileScanner:
    """Scans the Downloads folder and extracts file metadata."""
    
    def __init__(self, config: Config):
        """Initialize scanner with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.system_file_patterns = config.system_file_patterns
    
    def is_system_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from processing.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is a system file and should be excluded
        """
        # Check if file is hidden
        if self._is_hidden(file_path):
            return True
        
        # Check if file matches system file patterns
        filename = file_path.name
        for pattern in self.system_file_patterns:
            if filename.endswith(pattern) or filename == pattern:
                return True
        
        return False
    
    def _is_hidden(self, file_path: Path) -> bool:
        """Check if a file is hidden.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file is hidden
        """
        # Check if filename starts with dot (Unix convention, also used cross-platform)
        if file_path.name.startswith('.'):
            return True
        
        # On Windows, also check the hidden attribute
        if os.name == 'nt':
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file_path))
                # FILE_ATTRIBUTE_HIDDEN = 0x2
                if attrs != -1 and bool(attrs & 0x2):
                    return True
            except:
                pass
        
        return False
    
    def extract_metadata(self, file_path: Path) -> FileMetadata:
        """Extract metadata from a single file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            FileMetadata object with extracted information
        """
        # Get file stats
        stats = file_path.stat()
        
        # Extract extension (without the dot)
        extension = file_path.suffix.lstrip('.').lower() if file_path.suffix else ''
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # Get modification time
        modified_time = datetime.fromtimestamp(stats.st_mtime)
        
        # Check if hidden
        is_hidden = self._is_hidden(file_path)
        
        return FileMetadata(
            path=file_path,
            name=file_path.name,
            extension=extension,
            mime_type=mime_type,
            size=stats.st_size,
            modified_time=modified_time,
            is_hidden=is_hidden
        )
    
    def scan(self, folder_path: Path) -> List[FileMetadata]:
        """Scan folder and return list of file metadata.
        
        Args:
            folder_path: Path to the folder to scan
            
        Returns:
            List of FileMetadata objects for all processable files
            
        Raises:
            FileNotFoundError: If the folder doesn't exist
            PermissionError: If the folder cannot be accessed
        """
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {folder_path}")
        
        metadata_list = []
        
        try:
            # Iterate through all files in the folder (non-recursive)
            for item in folder_path.iterdir():
                # Skip directories
                if item.is_dir():
                    continue
                
                # Skip system files
                if self.is_system_file(item):
                    continue
                
                try:
                    # Extract metadata
                    metadata = self.extract_metadata(item)
                    metadata_list.append(metadata)
                except (OSError, PermissionError) as e:
                    # Skip files that can't be accessed
                    # In a production system, we would log this
                    continue
        
        except PermissionError as e:
            raise PermissionError(f"Cannot access folder: {folder_path}") from e
        
        return metadata_list
