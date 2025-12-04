"""Integration tests for Smart Workspace Automator.

These tests verify the complete end-to-end workflow of the system.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from config import Config
from main import SmartWorkspaceAutomator


class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @pytest.fixture
    def temp_downloads_folder(self):
        """Create a temporary Downloads folder for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup after test
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def test_config(self, temp_downloads_folder):
        """Create a test configuration."""
        config = Config.get_default_config()
        config.downloads_folder = temp_downloads_folder
        return config
    
    def create_test_file(self, folder: Path, filename: str, content: str = "test content"):
        """Helper to create a test file."""
        file_path = folder / filename
        file_path.write_text(content, encoding='utf-8')
        return file_path
    
    def test_complete_workflow_with_mixed_file_types(self, temp_downloads_folder, test_config):
        """Test complete workflow with mixed file types.
        
        This test verifies:
        - Files are scanned correctly
        - Files are classified by extension
        - Files are moved to correct category folders
        - Summary report is generated
        - Logs are created
        """
        # Create test files with various extensions
        self.create_test_file(temp_downloads_folder, "document.pdf")
        self.create_test_file(temp_downloads_folder, "report.docx")
        self.create_test_file(temp_downloads_folder, "photo.jpg")
        self.create_test_file(temp_downloads_folder, "screenshot.png")
        self.create_test_file(temp_downloads_folder, "video.mp4")
        self.create_test_file(temp_downloads_folder, "archive.zip")
        self.create_test_file(temp_downloads_folder, "script.py")
        self.create_test_file(temp_downloads_folder, "installer.exe")
        
        # Run the automator
        automator = SmartWorkspaceAutomator(test_config)
        summary_path = automator.run(temp_downloads_folder)
        
        # Verify summary report was created
        assert summary_path.exists()
        summary_content = summary_path.read_text(encoding='utf-8')
        
        # Verify summary contains expected information
        assert "Cleanup Summary" in summary_content
        assert "**Total Files Processed:** 8" in summary_content
        assert "**Total Files Moved:** 8" in summary_content
        
        # Verify category breakdown is present
        assert "Category Breakdown" in summary_content
        assert "Documents" in summary_content
        assert "Images" in summary_content
        assert "Videos" in summary_content
        assert "Archives" in summary_content
        assert "Code" in summary_content
        assert "Installers" in summary_content
        
        # Verify files were moved to correct categories
        organized_folder = temp_downloads_folder / test_config.organized_folder
        assert (organized_folder / "Documents" / "document.pdf").exists()
        assert (organized_folder / "Documents" / "report.docx").exists()
        assert (organized_folder / "Images" / "photo.jpg").exists()
        assert (organized_folder / "Images" / "screenshot.png").exists()
        assert (organized_folder / "Videos" / "video.mp4").exists()
        assert (organized_folder / "Archives" / "archive.zip").exists()
        assert (organized_folder / "Code" / "script.py").exists()
        assert (organized_folder / "Installers" / "installer.exe").exists()
        
        # Verify original files are gone
        assert not (temp_downloads_folder / "document.pdf").exists()
        assert not (temp_downloads_folder / "photo.jpg").exists()
        
        # Verify log file was created
        logs_folder = Path(test_config.logs_folder)
        assert logs_folder.exists()
        log_files = sorted(logs_folder.glob("cleanup_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        assert len(log_files) > 0
        
        # Verify log contains expected entries (use most recent log file)
        log_content = log_files[0].read_text(encoding='utf-8')
        assert "Starting cleanup operation" in log_content
        assert "Scanning folder" in log_content
        assert "Found 8 files to process" in log_content
        assert "Cleanup complete" in log_content
    
    def test_workflow_with_ambiguous_files_requiring_ai(self, temp_downloads_folder, test_config):
        """Test workflow with ambiguous files requiring AI classification.
        
        This test verifies:
        - Files with ambiguous names can be classified
        - AI classifier correctly identifies study/work files when triggered
        - Files are moved to appropriate categories
        
        Note: PDF files have high confidence from rule-based classification,
        so they go to Documents by default. To test AI classification, we would
        need files with unknown extensions or lower confidence.
        """
        # Create files with ambiguous names
        # Note: PDFs have confidence 1.0 from rule-based, so they won't trigger AI
        # This test verifies the system handles these files correctly
        self.create_test_file(temp_downloads_folder, "assignment_final.pdf")
        self.create_test_file(temp_downloads_folder, "homework_chapter3.pdf")
        self.create_test_file(temp_downloads_folder, "lecture_notes.pdf")
        self.create_test_file(temp_downloads_folder, "invoice_2024.pdf")
        self.create_test_file(temp_downloads_folder, "meeting_agenda.pdf")
        self.create_test_file(temp_downloads_folder, "contract_draft.pdf")
        
        # Run the automator
        automator = SmartWorkspaceAutomator(test_config)
        summary_path = automator.run(temp_downloads_folder)
        
        # Verify summary report
        assert summary_path.exists()
        summary_content = summary_path.read_text(encoding='utf-8')
        assert "**Total Files Processed:** 6" in summary_content
        assert "**Total Files Moved:** 6" in summary_content
        
        # Verify files were moved to appropriate categories
        organized_folder = temp_downloads_folder / test_config.organized_folder
        
        # Since PDFs have high confidence, they go to Documents
        documents_folder = organized_folder / "Documents"
        assert documents_folder.exists()
        assert (documents_folder / "assignment_final.pdf").exists()
        assert (documents_folder / "homework_chapter3.pdf").exists()
        assert (documents_folder / "lecture_notes.pdf").exists()
        assert (documents_folder / "invoice_2024.pdf").exists()
        assert (documents_folder / "meeting_agenda.pdf").exists()
        assert (documents_folder / "contract_draft.pdf").exists()
        
        # Verify summary mentions Documents category
        assert "Documents" in summary_content
        
        # Verify log contains classification entries
        logs_folder = Path(test_config.logs_folder)
        log_files = sorted(logs_folder.glob("cleanup_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        log_content = log_files[0].read_text(encoding='utf-8')
        
        # Should have classification entries
        assert "Classifying:" in log_content
        assert "classification:" in log_content.lower()
    
    def test_workflow_with_duplicate_files(self, temp_downloads_folder, test_config):
        """Test workflow with duplicate files.
        
        This test verifies:
        - Duplicate files are renamed with numeric suffix
        - Both files are preserved
        - Summary report is accurate
        """
        # Create initial files
        self.create_test_file(temp_downloads_folder, "document.pdf", "first version")
        
        # Run first organization
        automator = SmartWorkspaceAutomator(test_config)
        automator.run(temp_downloads_folder)
        
        # Create duplicate file
        self.create_test_file(temp_downloads_folder, "document.pdf", "second version")
        
        # Run second organization
        automator2 = SmartWorkspaceAutomator(test_config)
        summary_path = automator2.run(temp_downloads_folder)
        
        # Verify both files exist with different names
        organized_folder = temp_downloads_folder / test_config.organized_folder
        documents_folder = organized_folder / "Documents"
        
        assert (documents_folder / "document.pdf").exists()
        assert (documents_folder / "document_1.pdf").exists()
        
        # Verify content is different (both files preserved)
        first_content = (documents_folder / "document.pdf").read_text(encoding='utf-8')
        second_content = (documents_folder / "document_1.pdf").read_text(encoding='utf-8')
        assert first_content == "first version"
        assert second_content == "second version"
        
        # Verify summary report
        summary_content = summary_path.read_text(encoding='utf-8')
        assert "**Total Files Processed:** 1" in summary_content
        assert "**Total Files Moved:** 1" in summary_content
    
    def test_workflow_with_empty_folder(self, temp_downloads_folder, test_config):
        """Test workflow with empty folder.
        
        This test verifies:
        - System handles empty folder gracefully
        - Summary report shows zero files processed
        - No errors occur
        """
        # Run automator on empty folder
        automator = SmartWorkspaceAutomator(test_config)
        summary_path = automator.run(temp_downloads_folder)
        
        # Verify summary report was created
        assert summary_path.exists()
        summary_content = summary_path.read_text(encoding='utf-8')
        
        # Verify summary shows zero files
        assert "**Total Files Processed:** 0" in summary_content
        assert "**Total Files Moved:** 0" in summary_content
        
        # Verify no category breakdown (since no files)
        # The report should still be valid
        assert "Cleanup Summary" in summary_content
        
        # Verify log file was created
        logs_folder = Path(test_config.logs_folder)
        assert logs_folder.exists()
        log_files = list(logs_folder.glob("cleanup_*.log"))
        assert len(log_files) > 0
        
        # Verify log shows operation completed
        log_content = log_files[0].read_text(encoding='utf-8')
        assert "Starting cleanup operation" in log_content
        assert "Found 0 files to process" in log_content
    
    def test_summary_report_accuracy(self, temp_downloads_folder, test_config):
        """Test that summary report accurately reflects operations.
        
        This test verifies:
        - File counts are accurate
        - Category breakdown is correct
        - Sample operations are included
        - Duration is recorded
        """
        # Create a variety of files
        self.create_test_file(temp_downloads_folder, "doc1.pdf")
        self.create_test_file(temp_downloads_folder, "doc2.docx")
        self.create_test_file(temp_downloads_folder, "doc3.txt")
        self.create_test_file(temp_downloads_folder, "image1.jpg")
        self.create_test_file(temp_downloads_folder, "image2.png")
        self.create_test_file(temp_downloads_folder, "video1.mp4")
        
        # Run the automator
        automator = SmartWorkspaceAutomator(test_config)
        summary_path = automator.run(temp_downloads_folder)
        
        # Read summary
        summary_content = summary_path.read_text(encoding='utf-8')
        
        # Verify file counts
        assert "**Total Files Processed:** 6" in summary_content
        assert "**Total Files Moved:** 6" in summary_content
        assert "**Files Skipped:** 0" in summary_content
        
        # Verify category breakdown shows correct counts
        assert "Documents" in summary_content
        assert "Images" in summary_content
        assert "Videos" in summary_content
        
        # The breakdown should show 3 documents, 2 images, 1 video
        # We can verify by checking the table contains these numbers
        assert "| Documents | 3 |" in summary_content
        assert "| Images | 2 |" in summary_content
        assert "| Videos | 1 |" in summary_content
        
        # Verify sample operations are included
        assert "Sample Operations" in summary_content
        assert "doc1.pdf" in summary_content or "doc2.docx" in summary_content
        
        # Verify duration is included
        assert "Duration:" in summary_content
        assert "seconds" in summary_content
        
        # Verify date is included
        assert "Date:" in summary_content
    
    def test_log_completeness(self, temp_downloads_folder, test_config):
        """Test that logs contain all required information.
        
        This test verifies:
        - Scan operations are logged
        - Classification operations are logged
        - Move operations are logged
        - Timestamps are included
        - Error handling is logged (if errors occur)
        """
        # Create test files
        self.create_test_file(temp_downloads_folder, "document.pdf")
        self.create_test_file(temp_downloads_folder, "assignment.pdf")
        self.create_test_file(temp_downloads_folder, "image.jpg")
        
        # Run the automator
        automator = SmartWorkspaceAutomator(test_config)
        automator.run(temp_downloads_folder)
        
        # Read log file - get the most recent one
        logs_folder = Path(test_config.logs_folder)
        log_files = sorted(logs_folder.glob("cleanup_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        assert len(log_files) > 0
        
        log_content = log_files[0].read_text(encoding='utf-8')
        
        # Verify operation start is logged
        assert "Starting cleanup operation" in log_content
        
        # Verify scan operations are logged
        assert "Scanning folder" in log_content
        assert "Found 3 files to process" in log_content
        
        # Verify classification operations are logged
        assert "Classifying: document.pdf" in log_content
        assert "Classifying: assignment.pdf" in log_content
        assert "Classifying: image.jpg" in log_content
        
        # Verify classification results are logged
        assert "classification:" in log_content.lower()
        assert "confidence:" in log_content.lower()
        
        # Verify move operations are logged
        assert "Moving:" in log_content
        assert "Moved:" in log_content
        
        # Verify operation completion is logged
        assert "Cleanup complete" in log_content
        
        # Verify timestamps are present (check for date format)
        # Log format is: YYYY-MM-DD HH:MM:SS.mmm | LEVEL | message
        import re
        timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}'
        timestamps = re.findall(timestamp_pattern, log_content)
        assert len(timestamps) > 0, "Log should contain timestamps"
        
        # Verify log entries are in chronological order
        # (timestamps should be increasing)
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1], "Timestamps should be in order"
    
    def test_workflow_with_system_files_excluded(self, temp_downloads_folder, test_config):
        """Test that system files are properly excluded from processing.
        
        This test verifies:
        - Hidden files are not processed
        - Temporary files are not processed
        - System files don't appear in summary
        """
        # Create regular files
        self.create_test_file(temp_downloads_folder, "document.pdf")
        self.create_test_file(temp_downloads_folder, "image.jpg")
        
        # Create system files that should be excluded
        self.create_test_file(temp_downloads_folder, ".hidden_file")
        self.create_test_file(temp_downloads_folder, "temp.tmp")
        self.create_test_file(temp_downloads_folder, "download.part")
        self.create_test_file(temp_downloads_folder, ".DS_Store")
        
        # Run the automator
        automator = SmartWorkspaceAutomator(test_config)
        summary_path = automator.run(temp_downloads_folder)
        
        # Verify only regular files were processed
        summary_content = summary_path.read_text(encoding='utf-8')
        assert "**Total Files Processed:** 2" in summary_content
        assert "**Total Files Moved:** 2" in summary_content
        
        # Verify system files still exist in original location
        assert (temp_downloads_folder / ".hidden_file").exists()
        assert (temp_downloads_folder / "temp.tmp").exists()
        assert (temp_downloads_folder / "download.part").exists()
        assert (temp_downloads_folder / ".DS_Store").exists()
        
        # Verify regular files were moved
        organized_folder = temp_downloads_folder / test_config.organized_folder
        assert (organized_folder / "Documents" / "document.pdf").exists()
        assert (organized_folder / "Images" / "image.jpg").exists()
    
    def test_workflow_preserves_file_timestamps(self, temp_downloads_folder, test_config):
        """Test that file modification timestamps are preserved after moving.
        
        This test verifies:
        - Original modification time is preserved
        - Timestamps match before and after move
        """
        # Create a test file
        test_file = self.create_test_file(temp_downloads_folder, "document.pdf")
        
        # Set a specific modification time (1 day ago)
        import time
        one_day_ago = time.time() - (24 * 60 * 60)
        import os
        os.utime(test_file, (one_day_ago, one_day_ago))
        
        # Get the original modification time
        original_mtime = test_file.stat().st_mtime
        
        # Run the automator
        automator = SmartWorkspaceAutomator(test_config)
        automator.run(temp_downloads_folder)
        
        # Verify file was moved
        organized_folder = temp_downloads_folder / test_config.organized_folder
        moved_file = organized_folder / "Documents" / "document.pdf"
        assert moved_file.exists()
        
        # Verify modification time is preserved
        new_mtime = moved_file.stat().st_mtime
        
        # Allow for small floating point differences
        assert abs(original_mtime - new_mtime) < 1.0, \
            f"Modification time not preserved: {original_mtime} != {new_mtime}"
    
    def test_workflow_with_multiple_duplicates(self, temp_downloads_folder, test_config):
        """Test workflow with multiple duplicate files.
        
        This test verifies:
        - Multiple duplicates are handled correctly
        - Numeric suffixes increment properly
        - All files are preserved
        """
        # Create and organize first file
        self.create_test_file(temp_downloads_folder, "report.pdf", "version 1")
        automator1 = SmartWorkspaceAutomator(test_config)
        automator1.run(temp_downloads_folder)
        
        # Create and organize second file (duplicate)
        self.create_test_file(temp_downloads_folder, "report.pdf", "version 2")
        automator2 = SmartWorkspaceAutomator(test_config)
        automator2.run(temp_downloads_folder)
        
        # Create and organize third file (another duplicate)
        self.create_test_file(temp_downloads_folder, "report.pdf", "version 3")
        automator3 = SmartWorkspaceAutomator(test_config)
        automator3.run(temp_downloads_folder)
        
        # Verify all three files exist
        organized_folder = temp_downloads_folder / test_config.organized_folder
        documents_folder = organized_folder / "Documents"
        
        assert (documents_folder / "report.pdf").exists()
        assert (documents_folder / "report_1.pdf").exists()
        assert (documents_folder / "report_2.pdf").exists()
        
        # Verify content is preserved
        assert (documents_folder / "report.pdf").read_text() == "version 1"
        assert (documents_folder / "report_1.pdf").read_text() == "version 2"
        assert (documents_folder / "report_2.pdf").read_text() == "version 3"
