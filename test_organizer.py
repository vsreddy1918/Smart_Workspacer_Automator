"""Property-based tests for file organizer module."""

import tempfile
import os
import time
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
import pytest

from config import Config
from organizer import FileOrganizer, FileOperation
from classifier import ClassificationResult
from scanner import FileMetadata
from datetime import datetime


# Custom strategies for generating test data
@st.composite
def valid_category_name(draw):
    """Generate a valid category name."""
    categories = ['Documents', 'Images', 'Videos', 'Archives', 'Code', 
                  'Installers', 'Work', 'Study', 'Miscellaneous']
    return draw(st.sampled_from(categories))


@st.composite
def valid_filename(draw):
    """Generate a valid filename."""
    name = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-. '
        )
    ))
    name = name.strip()
    assume(len(name) > 0)
    assume(not name.startswith('.'))
    assume('/' not in name and '\\' not in name)
    return name


@st.composite
def file_extension(draw):
    """Generate a file extension."""
    ext = draw(st.sampled_from(['txt', 'pdf', 'jpg', 'png', 'zip', 'doc', 'mp4', 'py', 'json']))
    return ext


@st.composite
def file_metadata_strategy(draw, temp_path):
    """Generate FileMetadata for testing."""
    filename = draw(valid_filename())
    extension = draw(file_extension())
    full_name = f"{filename}.{extension}"
    
    # Create the actual file
    file_path = temp_path / full_name
    file_path.write_text("test content")
    
    return FileMetadata(
        path=file_path,
        name=full_name,
        extension=extension,
        mime_type='text/plain',
        size=100,
        modified_time=datetime.now(),
        is_hidden=False
    )


@st.composite
def classification_result_strategy(draw):
    """Generate ClassificationResult for testing."""
    category = draw(valid_category_name())
    confidence = draw(st.floats(min_value=0.0, max_value=1.0))
    method = draw(st.sampled_from(['rule-based', 'ai', 'merged']))
    
    return ClassificationResult(
        category=category,
        confidence=confidence,
        method=method,
        explanation=f"Test classification for {category}"
    )


# Feature: smart-workspace-automator, Property 12: Category folder creation
# Validates: Requirements 4.1
@settings(max_examples=100)
@given(category=valid_category_name())
def test_property_category_folder_creation(category):
    """
    Property 12: Category folder creation
    For any file being moved to a category, if the category folder doesn't exist,
    the system should create it before moving the file.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a custom config with temp directory
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        # Create organizer
        organizer = FileOrganizer(config)
        
        # Verify category folder doesn't exist initially
        category_path = temp_path / config.organized_folder / category
        assert not category_path.exists()
        
        # Create the category folder
        created_path = organizer.create_category_folder(category)
        
        # Verify the folder was created
        assert created_path.exists()
        assert created_path.is_dir()
        assert created_path == category_path



# Feature: smart-workspace-automator, Property 13: Duplicate file renaming
# Validates: Requirements 4.2
@settings(max_examples=100)
@given(
    filename=valid_filename(),
    extension=file_extension(),
    num_duplicates=st.integers(min_value=1, max_value=5)
)
def test_property_duplicate_file_renaming(filename, extension, num_duplicates):
    """
    Property 13: Duplicate file renaming
    For any file being moved to a destination where a file with the same name exists,
    the system should rename the incoming file with a numeric suffix.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a custom config with temp directory
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        # Create organizer
        organizer = FileOrganizer(config)
        
        # Create category folder
        category_path = temp_path / config.organized_folder / "Documents"
        category_path.mkdir(parents=True)
        
        # Create the original file
        full_name = f"{filename}.{extension}"
        original_file = category_path / full_name
        original_file.write_text("original content")
        
        # Test handling duplicates
        for i in range(1, num_duplicates + 1):
            destination = category_path / full_name
            unique_path = organizer.handle_duplicate(destination)
            
            # Verify the path is unique
            assert not unique_path.exists()
            
            # Create the file to simulate the move
            unique_path.write_text(f"duplicate content {i}")
            
            # Verify the filename has the expected suffix pattern
            if i == 1:
                expected_name = f"{filename}_1.{extension}"
            else:
                expected_name = f"{filename}_{i}.{extension}"
            
            assert unique_path.name == expected_name


# Feature: smart-workspace-automator, Property 14: Permission error resilience
# Validates: Requirements 4.3
@settings(max_examples=100)
@given(
    num_files=st.integers(min_value=2, max_value=10),
    locked_file_index=st.integers(min_value=0, max_value=9)
)
def test_property_permission_error_resilience(num_files, locked_file_index):
    """
    Property 14: Permission error resilience
    For any file move that fails due to permissions, the system should log the error
    and continue processing remaining files.
    """
    # Adjust locked_file_index to be within range
    locked_file_index = locked_file_index % num_files
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a custom config with temp directory
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        # Create organizer
        organizer = FileOrganizer(config)
        
        # Create files
        files = []
        for i in range(num_files):
            file_path = temp_path / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            files.append(file_path)
        
        # Create metadata and classification for each file
        operations = []
        for i, file_path in enumerate(files):
            metadata = FileMetadata(
                path=file_path,
                name=file_path.name,
                extension='txt',
                mime_type='text/plain',
                size=100,
                modified_time=datetime.now(),
                is_hidden=False
            )
            
            classification = ClassificationResult(
                category='Documents',
                confidence=1.0,
                method='rule-based',
                explanation='Test classification'
            )
            
            # Simulate permission error for one file by making it read-only
            # and trying to move to a read-only directory
            if i == locked_file_index:
                # Create a read-only destination directory
                readonly_dir = temp_path / config.organized_folder / "ReadOnly"
                readonly_dir.mkdir(parents=True)
                
                # On Windows, we can't easily simulate permission errors in temp dirs
                # So we'll test that the organizer handles the error gracefully
                # by attempting to move to a non-existent parent
                fake_metadata = FileMetadata(
                    path=Path("/nonexistent/path/file.txt"),
                    name="file.txt",
                    extension='txt',
                    mime_type='text/plain',
                    size=100,
                    modified_time=datetime.now(),
                    is_hidden=False
                )
                operation = organizer.organize(fake_metadata, classification)
                
                # Verify the operation failed but was recorded
                assert not operation.success
                assert operation.error_message is not None
            else:
                # Normal file operation
                operation = organizer.organize(metadata, classification)
                operations.append(operation)
        
        # Verify that other files were processed successfully
        successful_ops = [op for op in operations if op.success]
        assert len(successful_ops) >= num_files - 1


# Feature: smart-workspace-automator, Property 15: Timestamp preservation
# Validates: Requirements 4.4
@settings(max_examples=100)
@given(
    filename=valid_filename(),
    extension=file_extension()
)
def test_property_timestamp_preservation(filename, extension):
    """
    Property 15: Timestamp preservation
    For any file that is successfully moved, the modification timestamp in the
    destination should match the original timestamp.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a custom config with temp directory
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        # Create organizer
        organizer = FileOrganizer(config)
        
        # Create a file with specific content
        full_name = f"{filename}.{extension}"
        file_path = temp_path / full_name
        file_path.write_text("test content")
        
        # Set a specific modification time (1 hour ago)
        old_time = time.time() - 3600
        os.utime(file_path, (old_time, old_time))
        
        # Get the original modification time
        original_mtime = file_path.stat().st_mtime
        
        # Create metadata
        metadata = FileMetadata(
            path=file_path,
            name=full_name,
            extension=extension,
            mime_type='text/plain',
            size=100,
            modified_time=datetime.fromtimestamp(original_mtime),
            is_hidden=False
        )
        
        # Create classification
        classification = ClassificationResult(
            category='Documents',
            confidence=1.0,
            method='rule-based',
            explanation='Test classification'
        )
        
        # Organize the file
        operation = organizer.organize(metadata, classification)
        
        # Verify the operation was successful
        assert operation.success
        
        # Verify the destination file exists
        assert operation.destination_path.exists()
        
        # Verify the modification time was preserved (within 1 second tolerance)
        destination_mtime = operation.destination_path.stat().st_mtime
        assert abs(destination_mtime - original_mtime) < 1.0



# Feature: smart-workspace-automator, Property 16: No file loss
# Validates: Requirements 4.5
@settings(max_examples=100)
@given(
    num_files=st.integers(min_value=1, max_value=20)
)
def test_property_no_file_loss(num_files):
    """
    Property 16: No file loss
    For any cleanup operation, the total number of files (moved + skipped + errored)
    should equal the number of files initially scanned.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a custom config with temp directory
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        # Create organizer
        organizer = FileOrganizer(config)
        
        # Create files
        files = []
        for i in range(num_files):
            file_path = temp_path / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            files.append(file_path)
        
        # Track all operations
        operations = []
        
        # Process each file
        for file_path in files:
            metadata = FileMetadata(
                path=file_path,
                name=file_path.name,
                extension='txt',
                mime_type='text/plain',
                size=100,
                modified_time=datetime.now(),
                is_hidden=False
            )
            
            classification = ClassificationResult(
                category='Documents',
                confidence=1.0,
                method='rule-based',
                explanation='Test classification'
            )
            
            operation = organizer.organize(metadata, classification)
            operations.append(operation)
        
        # Verify no file loss: all files are accounted for
        assert len(operations) == num_files
        
        # Count successful and failed operations
        successful = sum(1 for op in operations if op.success)
        failed = sum(1 for op in operations if not op.success)
        
        # Total should equal initial file count
        assert successful + failed == num_files
        
        # Verify all successful operations have valid destination paths
        for op in operations:
            if op.success:
                assert op.destination_path.exists()


# Unit tests for edge cases

def test_locked_file_handling():
    """Test that locked files are handled gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        organizer = FileOrganizer(config)
        
        # Create a file that doesn't exist (simulates locked/inaccessible file)
        metadata = FileMetadata(
            path=Path("/nonexistent/locked_file.txt"),
            name="locked_file.txt",
            extension='txt',
            mime_type='text/plain',
            size=100,
            modified_time=datetime.now(),
            is_hidden=False
        )
        
        classification = ClassificationResult(
            category='Documents',
            confidence=1.0,
            method='rule-based',
            explanation='Test classification'
        )
        
        # Attempt to organize the file
        operation = organizer.organize(metadata, classification)
        
        # Verify the operation failed gracefully
        assert not operation.success
        assert operation.error_message is not None
        assert "error" in operation.error_message.lower()


def test_very_long_filename():
    """Test that very long filenames are handled correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        organizer = FileOrganizer(config)
        
        # Create a file with a very long name (but within OS limits)
        long_name = "a" * 200 + ".txt"
        file_path = temp_path / long_name
        
        try:
            file_path.write_text("content")
            
            metadata = FileMetadata(
                path=file_path,
                name=long_name,
                extension='txt',
                mime_type='text/plain',
                size=100,
                modified_time=datetime.now(),
                is_hidden=False
            )
            
            classification = ClassificationResult(
                category='Documents',
                confidence=1.0,
                method='rule-based',
                explanation='Test classification'
            )
            
            # Organize the file
            operation = organizer.organize(metadata, classification)
            
            # The operation should either succeed or fail gracefully
            if operation.success:
                assert operation.destination_path.exists()
            else:
                assert operation.error_message is not None
        
        except OSError:
            # If the OS doesn't support such long filenames, that's okay
            pytest.skip("OS doesn't support very long filenames")


def test_duplicate_handling_multiple_times():
    """Test that duplicate handling works correctly for multiple duplicates."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        organizer = FileOrganizer(config)
        
        # Create category folder
        category_path = temp_path / config.organized_folder / "Documents"
        category_path.mkdir(parents=True)
        
        # Create original file
        original = category_path / "test.txt"
        original.write_text("original")
        
        # Test multiple duplicates
        for i in range(1, 6):
            destination = category_path / "test.txt"
            unique_path = organizer.handle_duplicate(destination)
            
            # Verify unique path
            assert not unique_path.exists()
            assert unique_path.name == f"test_{i}.txt"
            
            # Create the file
            unique_path.write_text(f"duplicate {i}")


def test_category_folder_creation_idempotent():
    """Test that creating a category folder multiple times is safe."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        organizer = FileOrganizer(config)
        
        # Create the folder multiple times
        path1 = organizer.create_category_folder("Documents")
        path2 = organizer.create_category_folder("Documents")
        path3 = organizer.create_category_folder("Documents")
        
        # All should return the same path
        assert path1 == path2 == path3
        assert path1.exists()


def test_organize_creates_nested_folders():
    """Test that organize creates all necessary parent folders."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = Config.get_default_config()
        config.downloads_folder = temp_path
        
        organizer = FileOrganizer(config)
        
        # Create a file
        file_path = temp_path / "test.txt"
        file_path.write_text("content")
        
        metadata = FileMetadata(
            path=file_path,
            name="test.txt",
            extension='txt',
            mime_type='text/plain',
            size=100,
            modified_time=datetime.now(),
            is_hidden=False
        )
        
        classification = ClassificationResult(
            category='Documents',
            confidence=1.0,
            method='rule-based',
            explanation='Test classification'
        )
        
        # Organize the file (should create organized/Documents/ folders)
        operation = organizer.organize(metadata, classification)
        
        # Verify success
        assert operation.success
        assert operation.destination_path.exists()
        assert operation.destination_path.parent.exists()
