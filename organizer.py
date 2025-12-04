"""File organizer module for Smart Workspace Automator."""

import os
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from config import Config
from classifier import ClassificationResult
from scanner import FileMetadata


@dataclass
class FileOperation:
    """Record of a file move operation."""
    
    source_path: Path
    destination_path: Path
    category: str
    classification: ClassificationResult
    timestamp: datetime
    success: bool
    error_message: Optional[str]


class FileOrganizer:
    """Organizes files by moving them to category folders."""
    
    def __init__(self, config: Config):
        """Initialize organizer with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.base_path = config.downloads_folder / config.organized_folder
    
    def create_category_folder(self, category: str) -> Path:
        """Create category folder if it doesn't exist.
        
        Args:
            category: Category name
            
        Returns:
            Path to the category folder
        """
        category_path = self.base_path / category
        category_path.mkdir(parents=True, exist_ok=True)
        return category_path
    
    def handle_duplicate(self, destination: Path) -> Path:
        """Generate unique filename for duplicate files.
        
        Args:
            destination: Original destination path
            
        Returns:
            Unique destination path with numeric suffix if needed
        """
        if not destination.exists():
            return destination
        
        # Extract parts of the filename
        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent
        
        # Try incrementing numbers until we find a unique name
        counter = 1
        while True:
            # Apply the suffix pattern from config
            suffix_str = self.config.duplicate_suffix_pattern.replace('{n}', str(counter))
            new_name = f"{stem}{suffix_str}{suffix}"
            new_path = parent / new_name
            
            if not new_path.exists():
                return new_path
            
            counter += 1

    def move_file_safely(self, source: Path, destination: Path) -> tuple[bool, Optional[str]]:
        """Move file with error handling.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Get the original modification time before moving
            original_mtime = source.stat().st_mtime
            
            # Move the file
            shutil.move(str(source), str(destination))
            
            # Restore the original modification time
            os.utime(destination, (original_mtime, original_mtime))
            
            return True, None
        
        except PermissionError as e:
            return False, f"Permission denied: {str(e)}"
        
        except OSError as e:
            return False, f"OS error: {str(e)}"
        
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def organize(self, metadata: FileMetadata, classification: ClassificationResult) -> FileOperation:
        """Move file to appropriate category folder.
        
        Args:
            metadata: File metadata
            classification: Classification result
            
        Returns:
            FileOperation record of the operation
        """
        timestamp = datetime.now()
        
        try:
            # Create the category folder
            category_folder = self.create_category_folder(classification.category)
            
            # Determine destination path
            destination = category_folder / metadata.name
            
            # Handle duplicates
            destination = self.handle_duplicate(destination)
            
            # Move the file safely
            success, error_message = self.move_file_safely(metadata.path, destination)
            
            return FileOperation(
                source_path=metadata.path,
                destination_path=destination,
                category=classification.category,
                classification=classification,
                timestamp=timestamp,
                success=success,
                error_message=error_message
            )
        
        except Exception as e:
            # Catch any unexpected errors during organization
            return FileOperation(
                source_path=metadata.path,
                destination_path=metadata.path,  # Keep original path on failure
                category=classification.category,
                classification=classification,
                timestamp=timestamp,
                success=False,
                error_message=f"Organization failed: {str(e)}"
            )
