"""Unit tests for main controller and CLI."""

import pytest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from main import SmartWorkspaceAutomator, parse_arguments, main
from config import Config


class TestSmartWorkspaceAutomator:
    """Tests for the SmartWorkspaceAutomator controller."""
    
    def test_run_with_empty_folder(self, tmp_path):
        """Test running the automator on an empty folder."""
        # Create a temporary empty folder
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        
        # Create config pointing to the test folder
        config = Config.get_default_config()
        config.downloads_folder = test_folder
        
        # Run the automator
        automator = SmartWorkspaceAutomator(config)
        summary_path = automator.run(test_folder)
        
        # Verify summary was created
        assert summary_path.exists()
        
        # Verify summary content
        summary_content = summary_path.read_text()
        assert "**Total Files Processed:** 0" in summary_content
        assert "**Total Files Moved:** 0" in summary_content
    
    def test_run_with_files(self, tmp_path):
        """Test running the automator with actual files."""
        # Create a temporary folder with test files
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        
        # Create test files
        (test_folder / "document.pdf").write_text("test pdf content")
        (test_folder / "image.jpg").write_text("test image content")
        (test_folder / "video.mp4").write_text("test video content")
        
        # Create config pointing to the test folder
        config = Config.get_default_config()
        config.downloads_folder = test_folder
        
        # Run the automator
        automator = SmartWorkspaceAutomator(config)
        summary_path = automator.run(test_folder)
        
        # Verify summary was created
        assert summary_path.exists()
        
        # Verify summary content
        summary_content = summary_path.read_text()
        assert "**Total Files Processed:** 3" in summary_content
        assert "**Total Files Moved:** 3" in summary_content
        
        # Verify files were moved to correct categories
        organized_folder = test_folder / "organized"
        assert (organized_folder / "Documents" / "document.pdf").exists()
        assert (organized_folder / "Images" / "image.jpg").exists()
        assert (organized_folder / "Videos" / "video.mp4").exists()
    
    def test_run_with_nonexistent_folder(self):
        """Test running the automator on a non-existent folder."""
        config = Config.get_default_config()
        automator = SmartWorkspaceAutomator(config)
        
        nonexistent_folder = Path("/nonexistent/folder/path")
        
        with pytest.raises(FileNotFoundError):
            automator.run(nonexistent_folder)


class TestCLIArgumentParsing:
    """Tests for command-line argument parsing."""
    
    def test_parse_arguments_with_folder(self):
        """Test parsing arguments with folder path."""
        with patch('sys.argv', ['main.py', '/path/to/folder']):
            args = parse_arguments()
            assert args.folder == '/path/to/folder'
            assert args.config == 'config.json'
    
    def test_parse_arguments_without_folder(self):
        """Test parsing arguments without folder path (auto-detection)."""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()
            assert args.folder is None
            assert args.config == 'config.json'
    
    def test_parse_arguments_with_custom_config(self):
        """Test parsing arguments with custom config file."""
        with patch('sys.argv', ['main.py', '--config', 'custom.json']):
            args = parse_arguments()
            assert args.folder is None
            assert args.config == 'custom.json'
    
    def test_parse_arguments_with_folder_and_config(self):
        """Test parsing arguments with both folder and config."""
        with patch('sys.argv', ['main.py', '/path/to/folder', '--config', 'custom.json']):
            args = parse_arguments()
            assert args.folder == '/path/to/folder'
            assert args.config == 'custom.json'


class TestCLIMain:
    """Tests for the main CLI entry point."""
    
    def test_main_with_folder_argument(self, tmp_path):
        """Test main function with folder path argument."""
        # Create a temporary folder with test files
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        (test_folder / "test.pdf").write_text("test content")
        
        # Mock sys.argv
        with patch('sys.argv', ['main.py', str(test_folder)]):
            # Capture stdout
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                try:
                    main()
                except SystemExit as e:
                    # main() calls sys.exit(0) on success
                    assert e.code == 0
        
        # Verify output contains success message
        output = captured_output.getvalue()
        assert "Organization complete!" in output
        assert "Summary report:" in output
    
    def test_main_without_folder_argument(self, tmp_path):
        """Test main function without folder path (auto-detection)."""
        # Create a temporary Downloads folder
        downloads_folder = tmp_path / "Downloads"
        downloads_folder.mkdir()
        (downloads_folder / "test.pdf").write_text("test content")
        
        # Mock the auto-detection to return our test folder
        with patch('config.Config.get_default_downloads_folder', return_value=downloads_folder):
            with patch('sys.argv', ['main.py']):
                # Capture stdout
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 0
        
        # Verify output contains auto-detection message
        output = captured_output.getvalue()
        assert "Auto-detected Downloads folder:" in output
        assert "Organization complete!" in output
    
    def test_main_with_nonexistent_folder(self):
        """Test main function with non-existent folder."""
        with patch('sys.argv', ['main.py', '/nonexistent/folder']):
            # Capture stdout
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                try:
                    main()
                except SystemExit as e:
                    # Should exit with error code
                    assert e.code == 1
        
        # Verify error message
        output = captured_output.getvalue()
        assert "Error: Folder not found:" in output
    
    def test_main_with_missing_config_uses_default(self, tmp_path):
        """Test main function with missing config file uses default config."""
        # Create a temporary folder
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        (test_folder / "test.pdf").write_text("test content")
        
        # Mock sys.argv with non-existent config
        with patch('sys.argv', ['main.py', str(test_folder), '--config', 'nonexistent.json']):
            # Capture stdout
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
        
        # Verify output mentions using default config
        output = captured_output.getvalue()
        assert "Configuration file not found:" in output or "Using default configuration" in output
        assert "Organization complete!" in output
    
    def test_main_displays_success_message(self, tmp_path):
        """Test that main displays success message with summary path."""
        # Create a temporary folder
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        (test_folder / "test.pdf").write_text("test content")
        
        with patch('sys.argv', ['main.py', str(test_folder)]):
            # Capture stdout
            captured_output = StringIO()
            with patch('sys.stdout', captured_output):
                try:
                    main()
                except SystemExit as e:
                    assert e.code == 0
        
        # Verify success message format
        output = captured_output.getvalue()
        assert "✓ Organization complete!" in output
        assert "Summary report:" in output
        assert "summary.md" in output
    
    def test_main_handles_keyboard_interrupt(self, tmp_path):
        """Test that main handles keyboard interrupt gracefully."""
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        
        # Mock the automator to raise KeyboardInterrupt
        with patch('main.SmartWorkspaceAutomator.run', side_effect=KeyboardInterrupt()):
            with patch('sys.argv', ['main.py', str(test_folder)]):
                captured_output = StringIO()
                with patch('sys.stdout', captured_output):
                    try:
                        main()
                    except SystemExit as e:
                        assert e.code == 1
        
        # Verify cancellation message
        output = captured_output.getvalue()
        assert "Operation cancelled by user" in output


class TestProgressIndicator:
    """Tests for progress indicator display."""
    
    def test_progress_indicator_shown_for_many_files(self, tmp_path):
        """Test that progress indicator is shown when processing many files."""
        # Create a temporary folder with many test files
        test_folder = tmp_path / "downloads"
        test_folder.mkdir()
        
        # Create 25 test files (should trigger progress messages)
        for i in range(25):
            (test_folder / f"file{i}.txt").write_text(f"content {i}")
        
        # Create config
        config = Config.get_default_config()
        config.downloads_folder = test_folder
        
        # Run the automator and capture output
        automator = SmartWorkspaceAutomator(config)
        
        captured_output = StringIO()
        with patch('sys.stdout', captured_output):
            automator.run(test_folder)
        
        # Verify progress messages were shown
        output = captured_output.getvalue()
        assert "Processing file 10/25" in output
        assert "Processing file 20/25" in output
