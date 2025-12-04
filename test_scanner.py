"""Property-based tests for file scanner module."""

import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings, assume
import pytest

from config import Config
from scanner import FileScanner, FileMetadata


# Custom strategies for generating test data
@st.composite
def valid_filename(draw):
    """Generate a valid filename."""
    # Generate filename with letters, numbers, and common characters
    name = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters='_-. '
        )
    ))
    # Ensure it's not empty after stripping
    name = name.strip()
    assume(len(name) > 0)
    # Ensure it doesn't start with a dot (hidden file)
    assume(not name.startswith('.'))
    # Ensure it doesn't contain path separators
    assume('/' not in name and '\\' not in name)
    return name


@st.composite
def file_extension(draw):
    """Generate a file extension."""
    ext = draw(st.sampled_from(['txt', 'pdf', 'jpg', 'png', 'zip', 'doc', 'mp4', 'py', 'json', '']))
    return ext


# Feature: smart-workspace-automator, Property 1: Complete file discovery
# Validates: Requirements 1.1
@settings(max_examples=100)
@given(
    num_files=st.integers(min_value=0, max_value=20),
    num_system_files=st.integers(min_value=0, max_value=5)
)
def test_property_complete_file_discovery(num_files, num_system_files):
    """
    Property 1: Complete file discovery
    For any Downloads folder with files, scanning should identify all 
    non-system files present in the folder.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create regular files
        regular_files = []
        for i in range(num_files):
            file_path = temp_path / f"file_{i}.txt"
            file_path.write_text(f"content {i}")
            regular_files.append(file_path)
        
        # Create system files (should be excluded)
        system_files = []
        system_patterns = ['.tmp', '.part', '.DS_Store']
        for i in range(num_system_files):
            pattern = system_patterns[i % len(system_patterns)]
            file_path = temp_path / f"system_{i}{pattern}"
            file_path.write_text(f"system content {i}")
            system_files.append(file_path)
        
        # Create scanner
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        # Scan the folder
        metadata_list = scanner.scan(temp_path)
        
        # Verify all regular files are discovered
        assert len(metadata_list) == num_files
        
        # Verify all discovered files are regular files
        discovered_paths = {m.path for m in metadata_list}
        for regular_file in regular_files:
            assert regular_file in discovered_paths
        
        # Verify no system files are discovered
        for system_file in system_files:
            assert system_file not in discovered_paths


# Feature: smart-workspace-automator, Property 2: Metadata completeness
# Validates: Requirements 1.2
@settings(max_examples=100)
@given(
    filename=valid_filename(),
    extension=file_extension(),
    content=st.text(min_size=0, max_size=1000)
)
def test_property_metadata_completeness(filename, extension, content):
    """
    Property 2: Metadata completeness
    For any scanned file, the extracted metadata should contain filename, 
    extension, MIME type, and size fields.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a file with the given properties
        if extension:
            full_filename = f"{filename}.{extension}"
        else:
            full_filename = filename
        
        file_path = temp_path / full_filename
        file_path.write_text(content, encoding='utf-8')
        
        # Create scanner
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        # Scan the folder
        metadata_list = scanner.scan(temp_path)
        
        # Should find exactly one file
        assert len(metadata_list) == 1
        
        metadata = metadata_list[0]
        
        # Verify all required fields are present and non-None
        assert metadata.path is not None
        assert metadata.name is not None
        assert metadata.extension is not None  # Can be empty string
        assert metadata.mime_type is not None
        assert metadata.size is not None
        assert metadata.modified_time is not None
        
        # Verify field values are correct
        assert metadata.name == full_filename
        assert metadata.extension == extension.lower()
        # Note: We verify size is non-negative, but don't check exact value
        # because write_text() may convert line endings on Windows
        assert metadata.size >= 0


# Feature: smart-workspace-automator, Property 3: System file exclusion
# Validates: Requirements 1.3
@settings(max_examples=100)
@given(
    system_pattern=st.sampled_from(['.tmp', '.part', '.DS_Store', '.crdownload']),
    num_regular_files=st.integers(min_value=1, max_value=10)
)
def test_property_system_file_exclusion(system_pattern, num_regular_files):
    """
    Property 3: System file exclusion
    For any file with extension .tmp, .part, or hidden status, scanning 
    should exclude it from the results.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create regular files
        for i in range(num_regular_files):
            file_path = temp_path / f"regular_{i}.txt"
            file_path.write_text(f"content {i}")
        
        # Create a system file
        system_file = temp_path / f"system_file{system_pattern}"
        system_file.write_text("system content")
        
        # Create scanner
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        # Scan the folder
        metadata_list = scanner.scan(temp_path)
        
        # Verify system file is excluded
        discovered_paths = {m.path for m in metadata_list}
        assert system_file not in discovered_paths
        
        # Verify only regular files are discovered
        assert len(metadata_list) == num_regular_files


@settings(max_examples=100)
@given(num_hidden_files=st.integers(min_value=1, max_value=5))
def test_property_hidden_file_exclusion(num_hidden_files):
    """
    Property 3: System file exclusion (hidden files)
    For any hidden file (starting with dot), scanning should exclude it.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create regular file
        regular_file = temp_path / "regular.txt"
        regular_file.write_text("content")
        
        # Create hidden files
        for i in range(num_hidden_files):
            hidden_file = temp_path / f".hidden_{i}.txt"
            hidden_file.write_text(f"hidden content {i}")
        
        # Create scanner
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        # Scan the folder
        metadata_list = scanner.scan(temp_path)
        
        # Verify only the regular file is discovered
        assert len(metadata_list) == 1
        assert metadata_list[0].name == "regular.txt"


# Unit tests for edge cases
def test_empty_folder_handling():
    """Test that scanning an empty folder returns an empty list."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        metadata_list = scanner.scan(temp_path)
        
        assert len(metadata_list) == 0


def test_file_with_no_extension():
    """Test that files without extensions are handled correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a file without extension
        file_path = temp_path / "README"
        file_path.write_text("readme content")
        
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        metadata_list = scanner.scan(temp_path)
        
        assert len(metadata_list) == 1
        assert metadata_list[0].name == "README"
        assert metadata_list[0].extension == ""
        assert metadata_list[0].mime_type is not None


def test_file_with_special_characters():
    """Test that files with special characters in names are handled correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create files with special characters
        special_names = [
            "file with spaces.txt",
            "file_with_underscores.txt",
            "file-with-dashes.txt",
            "file.multiple.dots.txt"
        ]
        
        for name in special_names:
            file_path = temp_path / name
            file_path.write_text("content")
        
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        metadata_list = scanner.scan(temp_path)
        
        # All files should be discovered
        assert len(metadata_list) == len(special_names)
        
        # Verify all names are present
        discovered_names = {m.name for m in metadata_list}
        for name in special_names:
            assert name in discovered_names


def test_nonexistent_folder():
    """Test that scanning a nonexistent folder raises FileNotFoundError."""
    config = Config.get_default_config()
    scanner = FileScanner(config)
    
    nonexistent_path = Path("/nonexistent/folder/path")
    
    with pytest.raises(FileNotFoundError):
        scanner.scan(nonexistent_path)


def test_scan_ignores_subdirectories():
    """Test that scanning only processes files, not subdirectories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create files
        file1 = temp_path / "file1.txt"
        file1.write_text("content1")
        
        # Create subdirectory with files
        subdir = temp_path / "subdir"
        subdir.mkdir()
        file2 = subdir / "file2.txt"
        file2.write_text("content2")
        
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        metadata_list = scanner.scan(temp_path)
        
        # Should only find file1, not file2 in subdirectory
        assert len(metadata_list) == 1
        assert metadata_list[0].name == "file1.txt"


def test_very_large_file():
    """Test that very large files are handled without loading content into memory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a large file (1 MB)
        file_path = temp_path / "large_file.bin"
        with open(file_path, 'wb') as f:
            f.write(b'0' * (1024 * 1024))  # 1 MB
        
        config = Config.get_default_config()
        scanner = FileScanner(config)
        
        metadata_list = scanner.scan(temp_path)
        
        assert len(metadata_list) == 1
        assert metadata_list[0].size == 1024 * 1024
