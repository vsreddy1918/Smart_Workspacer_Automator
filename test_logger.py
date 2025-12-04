"""Property-based tests for the logging system."""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings

from config import Config
from logger import ActionLogger, LogEntry
from scanner import FileMetadata
from classifier import ClassificationResult
from organizer import FileOperation


# Custom strategies for generating test data
@st.composite
def file_metadata_strategy(draw):
    """Generate random FileMetadata objects."""
    name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='.-_'
    )))
    extension = draw(st.sampled_from(['pdf', 'jpg', 'txt', 'zip', 'py', 'doc', '']))
    
    if extension:
        name = f"{name}.{extension}"
    
    return FileMetadata(
        path=Path(f"/tmp/{name}"),
        name=name,
        extension=extension,
        mime_type=draw(st.sampled_from([
            'application/pdf', 'image/jpeg', 'text/plain', 
            'application/zip', 'text/x-python'
        ])),
        size=draw(st.integers(min_value=0, max_value=1000000)),
        modified_time=datetime.now(),
        is_hidden=False
    )


@st.composite
def classification_result_strategy(draw):
    """Generate random ClassificationResult objects."""
    category = draw(st.sampled_from([
        'Documents', 'Images', 'Videos', 'Archives', 
        'Code', 'Work', 'Study', 'Miscellaneous'
    ]))
    method = draw(st.sampled_from(['rule-based', 'ai', 'merged']))
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    explanation = draw(st.text(min_size=10, max_size=100))
    
    return ClassificationResult(
        category=category,
        confidence=confidence,
        method=method,
        explanation=explanation
    )


@st.composite
def file_operation_strategy(draw):
    """Generate random FileOperation objects."""
    metadata = draw(file_metadata_strategy())
    classification = draw(classification_result_strategy())
    success = draw(st.booleans())
    
    source_path = metadata.path
    dest_path = Path(f"/tmp/organized/{classification.category}/{metadata.name}")
    
    error_message = None
    if not success:
        error_message = draw(st.text(min_size=10, max_size=100))
    
    return FileOperation(
        source_path=source_path,
        destination_path=dest_path,
        category=classification.category,
        classification=classification,
        timestamp=datetime.now(),
        success=success,
        error_message=error_message
    )


# Feature: smart-workspace-automator, Property 17: Classification reason recording
@settings(max_examples=100)
@given(
    metadata=file_metadata_strategy(),
    classification=classification_result_strategy()
)
def test_property_classification_reason_recording(metadata, classification):
    """
    Property 17: Classification reason recording
    
    For any classified file, the classification result should include 
    the method used (rule-based, AI, or merged).
    
    Validates: Requirements 5.1
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Log the classification
        logger.log_classification(metadata, classification)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Find entries related to this classification
        classification_entries = [
            e for e in entries 
            if e.classification is not None and e.file_path == metadata.path
        ]
        
        # Verify that at least one entry has the classification with method
        assert len(classification_entries) > 0, "No classification entries found"
        
        # Verify that the classification method is recorded
        methods_recorded = [e.classification.method for e in classification_entries]
        assert classification.method in methods_recorded, \
            f"Classification method '{classification.method}' not recorded"
        
        # Verify the method is one of the valid values
        for entry in classification_entries:
            assert entry.classification.method in ['rule-based', 'ai', 'merged'], \
                f"Invalid method: {entry.classification.method}"
        
        logger.close()


# Feature: smart-workspace-automator, Property 18: AI explanation storage
@settings(max_examples=100)
@given(
    metadata=file_metadata_strategy(),
    classification=classification_result_strategy().filter(lambda c: c.method == 'ai')
)
def test_property_ai_explanation_storage(metadata, classification):
    """
    Property 18: AI explanation storage
    
    For any file classified by AI, the classification result should include 
    the AI-generated explanation.
    
    Validates: Requirements 5.2
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Log the classification
        logger.log_classification(metadata, classification)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Find entries with explanations
        explanation_entries = [
            e for e in entries 
            if e.classification is not None 
            and e.file_path == metadata.path
            and 'Explanation:' in e.message
        ]
        
        # Verify that the explanation is stored
        assert len(explanation_entries) > 0, "No explanation entries found for AI classification"
        
        # Verify the explanation contains the actual explanation text
        explanation_found = False
        for entry in explanation_entries:
            if classification.explanation in entry.message:
                explanation_found = True
                break
        
        assert explanation_found, \
            f"AI explanation '{classification.explanation}' not found in log entries"
        
        logger.close()


# Feature: smart-workspace-automator, Property 19: Move operation logging
@settings(max_examples=100)
@given(operation=file_operation_strategy())
def test_property_move_operation_logging(operation):
    """
    Property 19: Move operation logging
    
    For any file that is moved, the action log should contain the original location, 
    new location, category, and classification reason.
    
    Validates: Requirements 5.3
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Log the move operation
        logger.log_move_operation(operation)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Find entries related to this operation
        operation_entries = [
            e for e in entries 
            if e.file_path == operation.source_path
        ]
        
        assert len(operation_entries) > 0, "No operation entries found"
        
        # Verify that the log contains information about the move
        log_messages = ' '.join([e.message for e in operation_entries])
        
        # Check for source file name
        assert operation.source_path.name in log_messages, \
            f"Source file name '{operation.source_path.name}' not in log"
        
        # Check for destination path (if successful)
        if operation.success:
            assert str(operation.destination_path) in log_messages, \
                f"Destination path '{operation.destination_path}' not in log"
        
        # Check for category
        category_found = any(e.category == operation.category for e in operation_entries)
        assert category_found, f"Category '{operation.category}' not recorded"
        
        # Check for classification reason (method and explanation)
        classification_found = any(
            e.classification is not None 
            and e.classification.method == operation.classification.method
            for e in operation_entries
        )
        assert classification_found, \
            f"Classification method '{operation.classification.method}' not recorded"
        
        logger.close()


# Feature: smart-workspace-automator, Property 20: Log timestamp inclusion
@settings(max_examples=100)
@given(operation=file_operation_strategy())
def test_property_log_timestamp_inclusion(operation):
    """
    Property 20: Log timestamp inclusion
    
    For any operation logged, the log entry should include a timestamp.
    
    Validates: Requirements 5.4
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Log the move operation
        logger.log_move_operation(operation)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Verify all entries have timestamps
        for entry in entries:
            assert entry.timestamp is not None, "Log entry missing timestamp"
            assert isinstance(entry.timestamp, datetime), \
                f"Timestamp is not a datetime object: {type(entry.timestamp)}"
        
        # Verify the log file contains timestamps
        log_file_path = logger.get_log_file_path()
        
        # Close the logger before reading the file
        logger.close()
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # Check that the log file has timestamp format (YYYY-MM-DD HH:MM:SS)
        import re
        timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        timestamps_in_file = re.findall(timestamp_pattern, log_content)
        
        assert len(timestamps_in_file) > 0, \
            "No timestamps found in log file"


# Feature: smart-workspace-automator, Property 28: Timestamped log file creation
@settings(max_examples=100)
@given(st.integers(min_value=0, max_value=10))
def test_property_timestamped_log_file_creation(dummy):
    """
    Property 28: Timestamped log file creation
    
    For any execution, the system should create a log file with a timestamp in its name.
    
    Validates: Requirements 10.1
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Record time before creating logger (strip microseconds for comparison)
        time_before = datetime.now().replace(microsecond=0)
        
        # Create logger
        logger = ActionLogger(config)
        
        # Record time after creating logger (add 1 second buffer)
        time_after = datetime.now().replace(microsecond=0) + timedelta(seconds=1)
        
        # Get the log file path
        log_file_path = logger.get_log_file_path()
        
        # Close the logger before cleanup
        logger.close()
        
        # Verify the log file exists
        assert log_file_path.exists(), f"Log file does not exist: {log_file_path}"
        
        # Verify the log file name contains a timestamp
        log_filename = log_file_path.name
        
        # Check for timestamp pattern in filename (YYYYMMDD_HHMMSS)
        import re
        timestamp_pattern = r'cleanup_\d{8}_\d{6}\.log'
        assert re.match(timestamp_pattern, log_filename), \
            f"Log filename '{log_filename}' does not contain expected timestamp pattern"
        
        # Extract the timestamp from the filename
        timestamp_str = log_filename.replace('cleanup_', '').replace('.log', '')
        year = int(timestamp_str[0:4])
        month = int(timestamp_str[4:6])
        day = int(timestamp_str[6:8])
        hour = int(timestamp_str[9:11])
        minute = int(timestamp_str[11:13])
        second = int(timestamp_str[13:15])
        
        file_timestamp = datetime(year, month, day, hour, minute, second)
        
        # Verify the timestamp is reasonable (within the time window)
        assert time_before <= file_timestamp <= time_after, \
            f"File timestamp {file_timestamp} is outside expected range [{time_before}, {time_after}]"


# Feature: smart-workspace-automator, Property 29: File operation logging completeness
@settings(max_examples=100)
@given(
    metadata=file_metadata_strategy(),
    classification=classification_result_strategy()
)
def test_property_file_operation_logging_completeness(metadata, classification):
    """
    Property 29: File operation logging completeness
    
    For any file processed, the log should contain entries for scan, classify, 
    and move (or skip) operations.
    
    Validates: Requirements 10.2
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Simulate the complete workflow for a file
        # 1. Scan
        logger.log_scan_start(metadata.path.parent)
        logger.log_scan_complete(1)
        
        # 2. Classify
        logger.log_classification(metadata, classification)
        
        # 3. Move (create a fake operation)
        operation = FileOperation(
            source_path=metadata.path,
            destination_path=Path(f"/tmp/organized/{classification.category}/{metadata.name}"),
            category=classification.category,
            classification=classification,
            timestamp=datetime.now(),
            success=True,
            error_message=None
        )
        logger.log_move_operation(operation)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Verify we have entries for all three operations
        scan_entries = [e for e in entries if 'Scanning' in e.message or 'Found' in e.message]
        classify_entries = [e for e in entries if 'Classifying' in e.message or 'classification' in e.message.lower()]
        move_entries = [e for e in entries if 'Moving' in e.message or 'Moved' in e.message]
        
        assert len(scan_entries) > 0, "No scan entries found"
        assert len(classify_entries) > 0, "No classify entries found"
        assert len(move_entries) > 0, "No move entries found"
        
        # Verify the entries reference the file
        file_related_entries = [e for e in entries if e.file_path == metadata.path or metadata.name in e.message]
        assert len(file_related_entries) > 0, f"No entries found for file {metadata.name}"
        
        logger.close()


# Feature: smart-workspace-automator, Property 30: Error logging completeness
@settings(max_examples=100)
@given(
    metadata=file_metadata_strategy(),
    error_type=st.sampled_from(['PermissionError', 'FileNotFoundError', 'OSError', 'ValueError']),
    error_message=st.text(min_size=10, max_size=100)
)
def test_property_error_logging_completeness(metadata, error_type, error_message):
    """
    Property 30: Error logging completeness
    
    For any error that occurs, the log should contain the error type, 
    affected file path, and error message.
    
    Validates: Requirements 10.3
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Log an error
        logger.log_error(error_type, metadata.path, error_message)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Find error entries
        error_entries = [e for e in entries if e.level == 'ERROR']
        
        assert len(error_entries) > 0, "No error entries found"
        
        # Verify the error entry contains all required information
        error_entry = error_entries[0]
        
        # Check error type
        assert error_entry.error_type == error_type, \
            f"Error type not recorded: expected {error_type}, got {error_entry.error_type}"
        
        # Check file path
        assert error_entry.file_path == metadata.path, \
            f"File path not recorded: expected {metadata.path}, got {error_entry.file_path}"
        
        # Check error message
        assert error_entry.error_details == error_message, \
            f"Error message not recorded: expected {error_message}, got {error_entry.error_details}"
        
        # Verify the error appears in the log message
        assert error_type in error_entry.message, \
            f"Error type '{error_type}' not in log message"
        
        logger.close()


# Feature: smart-workspace-automator, Property 31: AI invocation logging
@settings(max_examples=100)
@given(
    metadata=file_metadata_strategy(),
    prompt=st.text(min_size=20, max_size=200),
    response=st.text(min_size=20, max_size=200)
)
def test_property_ai_invocation_logging(metadata, prompt, response):
    """
    Property 31: AI invocation logging
    
    For any AI classifier invocation, the log should contain the input prompt 
    and the received response.
    
    Validates: Requirements 10.4
    """
    # Create a temporary config
    with tempfile.TemporaryDirectory() as tmpdir:
        config = Config.get_default_config()
        config.logs_folder = tmpdir
        
        # Create logger
        logger = ActionLogger(config)
        
        # Log an AI invocation
        logger.log_ai_invocation(metadata, prompt, response)
        
        # Get log entries
        entries = logger.get_log_entries()
        
        # Find AI-related entries
        ai_entries = [e for e in entries if 'AI' in e.message or 'ai' in e.message.lower()]
        
        assert len(ai_entries) > 0, "No AI invocation entries found"
        
        # Verify the prompt is logged
        prompt_entries = [e for e in entries if 'Prompt' in e.message or prompt in e.message]
        assert len(prompt_entries) > 0, "AI prompt not logged"
        
        # Verify the response is logged
        response_entries = [e for e in entries if 'Response' in e.message or response in e.message]
        assert len(response_entries) > 0, "AI response not logged"
        
        # Verify the file is referenced
        file_entries = [e for e in entries if e.file_path == metadata.path]
        assert len(file_entries) > 0, f"File {metadata.path} not referenced in AI invocation logs"
        
        logger.close()
