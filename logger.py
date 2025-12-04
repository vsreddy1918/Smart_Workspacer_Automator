"""Logging system for Smart Workspace Automator."""

import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass

from config import Config
from organizer import FileOperation
from classifier import ClassificationResult
from scanner import FileMetadata


@dataclass
class LogEntry:
    """A single log entry."""
    
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR, etc.
    message: str
    file_path: Optional[Path] = None
    category: Optional[str] = None
    classification: Optional[ClassificationResult] = None
    error_type: Optional[str] = None
    error_details: Optional[str] = None


class ActionLogger:
    """Logs all file operations and system actions."""
    
    def __init__(self, config: Config):
        """Initialize the action logger.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.log_entries: List[LogEntry] = []
        self.log_file_path: Optional[Path] = None
        
        # Create logs directory if it doesn't exist
        self.logs_dir = Path(config.logs_folder)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = self.logs_dir / f"cleanup_{timestamp}.log"
        
        # Set up Python logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up structured logging with timestamps."""
        # Create logger
        self.logger = logging.getLogger('smart_workspace_automator')
        self.logger.setLevel(logging.DEBUG)
        
        # Remove any existing handlers
        self.logger.handlers.clear()
        
        # Create file handler with UTF-8 encoding
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Create formatter with timestamps
        formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
    
    def log_scan_start(self, folder_path: Path):
        """Log the start of a folder scan.
        
        Args:
            folder_path: Path to the folder being scanned
        """
        message = f"Scanning folder: {folder_path}"
        self.logger.info(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=message,
            file_path=folder_path
        )
        self.log_entries.append(entry)
    
    def log_scan_complete(self, file_count: int):
        """Log the completion of a folder scan.
        
        Args:
            file_count: Number of files found
        """
        message = f"Found {file_count} files to process"
        self.logger.info(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=message
        )
        self.log_entries.append(entry)
    
    def log_classification(self, metadata: FileMetadata, result: ClassificationResult):
        """Log a file classification.
        
        Args:
            metadata: File metadata
            result: Classification result
        """
        message = f"Classifying: {metadata.name}"
        self.logger.info(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=message,
            file_path=metadata.path,
            category=result.category,
            classification=result
        )
        self.log_entries.append(entry)
        
        # Log the classification details
        detail_message = (
            f"{result.method.capitalize()} classification: {result.category} "
            f"(confidence: {result.confidence:.2f})"
        )
        self.logger.info(detail_message)
        
        detail_entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=detail_message,
            file_path=metadata.path,
            category=result.category,
            classification=result
        )
        self.log_entries.append(detail_entry)
        
        # Log the explanation
        if result.explanation:
            explanation_message = f"Explanation: {result.explanation}"
            self.logger.info(explanation_message)
            
            explanation_entry = LogEntry(
                timestamp=datetime.now(),
                level='INFO',
                message=explanation_message,
                file_path=metadata.path,
                category=result.category,
                classification=result
            )
            self.log_entries.append(explanation_entry)
    
    def log_ai_invocation(self, metadata: FileMetadata, prompt: str, response: str):
        """Log an AI classifier invocation.
        
        Args:
            metadata: File metadata
            prompt: Input prompt sent to AI
            response: Response received from AI
        """
        message = f"Invoking AI classifier for ambiguous file: {metadata.name}"
        self.logger.info(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=message,
            file_path=metadata.path
        )
        self.log_entries.append(entry)
        
        # Log the prompt
        prompt_message = f"AI Prompt: {prompt}"
        self.logger.debug(prompt_message)
        
        prompt_entry = LogEntry(
            timestamp=datetime.now(),
            level='DEBUG',
            message=prompt_message,
            file_path=metadata.path
        )
        self.log_entries.append(prompt_entry)
        
        # Log the response
        response_message = f"AI Response: {response}"
        self.logger.debug(response_message)
        
        response_entry = LogEntry(
            timestamp=datetime.now(),
            level='DEBUG',
            message=response_message,
            file_path=metadata.path
        )
        self.log_entries.append(response_entry)
    
    def log_move_operation(self, operation: FileOperation):
        """Log a file move operation.
        
        Args:
            operation: FileOperation record
        """
        if operation.success:
            message = f"Moving: {operation.source_path.name} → {operation.destination_path}"
            self.logger.info(message)
            
            entry = LogEntry(
                timestamp=operation.timestamp,
                level='INFO',
                message=message,
                file_path=operation.source_path,
                category=operation.category,
                classification=operation.classification
            )
            self.log_entries.append(entry)
            
            # Log success
            success_message = f"Moved: {operation.source_path.name}"
            self.logger.info(success_message)
            
            success_entry = LogEntry(
                timestamp=operation.timestamp,
                level='SUCCESS',
                message=success_message,
                file_path=operation.source_path,
                category=operation.category,
                classification=operation.classification
            )
            self.log_entries.append(success_entry)
        else:
            # Log failure
            error_message = (
                f"Failed to move {operation.source_path.name}: "
                f"{operation.error_message}"
            )
            self.logger.error(error_message)
            
            entry = LogEntry(
                timestamp=operation.timestamp,
                level='ERROR',
                message=error_message,
                file_path=operation.source_path,
                category=operation.category,
                classification=operation.classification,
                error_type='MoveError',
                error_details=operation.error_message
            )
            self.log_entries.append(entry)
    
    def log_error(self, error_type: str, file_path: Optional[Path], 
                  error_message: str, stack_trace: Optional[str] = None):
        """Log an error with full details.
        
        Args:
            error_type: Type of error (e.g., 'PermissionError', 'FileNotFoundError')
            file_path: Path to the affected file (if applicable)
            error_message: Error message
            stack_trace: Optional stack trace
        """
        message = f"{error_type}: {error_message}"
        if file_path:
            message = f"{error_type} for {file_path}: {error_message}"
        
        self.logger.error(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='ERROR',
            message=message,
            file_path=file_path,
            error_type=error_type,
            error_details=error_message
        )
        self.log_entries.append(entry)
        
        # Log stack trace if provided
        if stack_trace:
            self.logger.debug(f"Stack trace: {stack_trace}")
    
    def log_operation_start(self):
        """Log the start of the cleanup operation."""
        message = "Starting cleanup operation"
        self.logger.info(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=message
        )
        self.log_entries.append(entry)
    
    def log_operation_complete(self, files_moved: int, errors: int):
        """Log the completion of the cleanup operation.
        
        Args:
            files_moved: Number of files successfully moved
            errors: Number of errors encountered
        """
        message = f"Cleanup complete: {files_moved} files moved, {errors} errors"
        self.logger.info(message)
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level='INFO',
            message=message
        )
        self.log_entries.append(entry)
    
    def get_log_file_path(self) -> Path:
        """Get the path to the current log file.
        
        Returns:
            Path to the log file
        """
        return self.log_file_path
    
    def get_log_entries(self) -> List[LogEntry]:
        """Get all log entries.
        
        Returns:
            List of LogEntry objects
        """
        return self.log_entries.copy()
    
    def close(self):
        """Close the logger and flush all handlers."""
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
