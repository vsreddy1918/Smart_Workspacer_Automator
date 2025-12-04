"""Tests for the report generator module."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings

from reporter import ReportGenerator
from organizer import FileOperation
from classifier import ClassificationResult
from config import Config


# Hypothesis strategies for generating test data

@st.composite
def classification_result_strategy(draw):
    """Generate random ClassificationResult objects."""
    categories = ['Documents', 'Images', 'Videos', 'Archives', 'Code', 
                  'Installers', 'Work', 'Study', 'Miscellaneous']
    methods = ['rule-based', 'ai', 'merged']
    
    return ClassificationResult(
        category=draw(st.sampled_from(categories)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        method=draw(st.sampled_from(methods)),
        explanation=draw(st.text(min_size=10, max_size=100))
    )


@st.composite
def file_operation_strategy(draw):
    """Generate random FileOperation objects."""
    source_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._-')))
    dest_name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._-')))
    
    classification = draw(classification_result_strategy())
    success = draw(st.booleans())
    
    error_message = None if success else draw(st.text(min_size=5, max_size=50))
    
    return FileOperation(
        source_path=Path(f"/downloads/{source_name}"),
        destination_path=Path(f"/downloads/organized/{classification.category}/{dest_name}"),
        category=classification.category,
        classification=classification,
        timestamp=datetime.now(),
        success=success,
        error_message=error_message
    )


# Property-based tests

# Feature: smart-workspace-automator, Property 21: Summary file count accuracy
@given(operations=st.lists(file_operation_strategy(), min_size=0, max_size=50))
@settings(max_examples=100)
def test_property_summary_file_count_accuracy(operations):
    """
    Property 21: Summary file count accuracy
    For any cleanup operation, the summary report should contain total files 
    processed and total files moved that match the actual counts.
    
    Validates: Requirements 6.2
    """
    # Create config and reporter
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add all operations
    for op in operations:
        reporter.add_operation(op)
    
    # Get statistics
    stats = reporter.get_statistics()
    
    # Calculate expected counts
    expected_total = len(operations)
    expected_moved = sum(1 for op in operations if op.success)
    
    # Verify the counts match
    assert stats['total_files_processed'] == expected_total, \
        f"Total files processed mismatch: expected {expected_total}, got {stats['total_files_processed']}"
    
    assert stats['total_files_moved'] == expected_moved, \
        f"Total files moved mismatch: expected {expected_moved}, got {stats['total_files_moved']}"
    
    # Also verify the summary report contains these counts
    summary = reporter.generate_summary()
    assert f"**Total Files Processed:** {expected_total}" in summary
    assert f"**Total Files Moved:** {expected_moved}" in summary


# Feature: smart-workspace-automator, Property 22: Summary category breakdown
@given(operations=st.lists(file_operation_strategy(), min_size=1, max_size=50))
@settings(max_examples=100)
def test_property_summary_category_breakdown(operations):
    """
    Property 22: Summary category breakdown
    For any cleanup operation, the summary report should include a breakdown 
    showing the number of files in each category.
    
    Validates: Requirements 6.3
    """
    # Create config and reporter
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add all operations
    for op in operations:
        reporter.add_operation(op)
    
    # Get statistics
    stats = reporter.get_statistics()
    
    # Calculate expected category counts (only successful operations)
    expected_counts = {}
    for op in operations:
        if op.success:
            expected_counts[op.category] = expected_counts.get(op.category, 0) + 1
    
    # Verify the category breakdown matches
    assert stats['category_breakdown'] == expected_counts, \
        f"Category breakdown mismatch: expected {expected_counts}, got {stats['category_breakdown']}"
    
    # Verify the summary report contains the category breakdown
    summary = reporter.generate_summary()
    
    if expected_counts:
        assert "## Category Breakdown" in summary
        
        # Check that each category with files appears in the summary
        for category, count in expected_counts.items():
            assert category in summary, f"Category {category} not found in summary"
            # The count should appear in the table
            assert str(count) in summary


# Feature: smart-workspace-automator, Property 23: Summary sample inclusion
@given(operations=st.lists(file_operation_strategy(), min_size=1, max_size=50))
@settings(max_examples=100)
def test_property_summary_sample_inclusion(operations):
    """
    Property 23: Summary sample inclusion
    For any cleanup operation with moved files, the summary report should 
    include at least one sample file movement with its classification reason.
    
    Validates: Requirements 6.4
    """
    # Create config and reporter
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add all operations
    for op in operations:
        reporter.add_operation(op)
    
    # Check if there are any successful operations
    successful_ops = [op for op in operations if op.success]
    
    # Generate summary
    summary = reporter.generate_summary()
    
    if successful_ops:
        # Summary should include sample operations section
        assert "## Sample Operations" in summary
        
        # At least one file should be mentioned in the samples
        # Check that at least one source filename appears
        found_sample = False
        for op in successful_ops:
            if op.source_path.name in summary:
                found_sample = True
                # Also verify the explanation is included
                assert op.classification.explanation in summary or \
                       op.classification.explanation[:50] in summary, \
                       f"Classification explanation not found for {op.source_path.name}"
                break
        
        assert found_sample, "No sample file movements found in summary"


# Feature: smart-workspace-automator, Property 24: Summary duration inclusion
@given(
    operations=st.lists(file_operation_strategy(), min_size=0, max_size=50),
    duration_seconds=st.floats(min_value=0.1, max_value=1000.0)
)
@settings(max_examples=100)
def test_property_summary_duration_inclusion(operations, duration_seconds):
    """
    Property 24: Summary duration inclusion
    For any cleanup operation, the summary report should include the total time taken.
    
    Validates: Requirements 6.5
    """
    # Create config and reporter
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Set start and end times with the specified duration
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration_seconds)
    
    reporter.set_start_time(start_time)
    reporter.set_end_time(end_time)
    
    # Add all operations
    for op in operations:
        reporter.add_operation(op)
    
    # Get statistics
    stats = reporter.get_statistics()
    
    # Verify duration is calculated correctly (within small tolerance for floating point)
    assert abs(stats['duration_seconds'] - duration_seconds) < 0.01, \
        f"Duration mismatch: expected {duration_seconds}, got {stats['duration_seconds']}"
    
    # Verify the summary report contains the duration
    summary = reporter.generate_summary()
    assert "**Duration:**" in summary
    
    # The duration should be formatted and present in the summary
    # Check that some numeric value appears after "Duration:"
    assert f"{duration_seconds:.1f} seconds" in summary


# Unit tests

def test_empty_report():
    """Test report generation with no operations."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    stats = reporter.get_statistics()
    
    assert stats['total_files_processed'] == 0
    assert stats['total_files_moved'] == 0
    assert stats['files_skipped'] == 0
    assert stats['category_breakdown'] == {}
    
    summary = reporter.generate_summary()
    assert "# Cleanup Summary" in summary
    assert "**Total Files Processed:** 0" in summary


def test_markdown_table_generation():
    """Test that category breakdown generates proper markdown table."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add some operations
    classification = ClassificationResult(
        category='Documents',
        confidence=1.0,
        method='rule-based',
        explanation='PDF file'
    )
    
    op = FileOperation(
        source_path=Path('/downloads/test.pdf'),
        destination_path=Path('/downloads/organized/Documents/test.pdf'),
        category='Documents',
        classification=classification,
        timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Check for markdown table structure
    assert "| Category | Files Moved | Percentage |" in summary
    assert "|----------|-------------|------------|" in summary
    assert "| Documents | 1 | 100.0% |" in summary


def test_error_section_in_report():
    """Test that errors are properly included in the report."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add a failed operation
    classification = ClassificationResult(
        category='Documents',
        confidence=1.0,
        method='rule-based',
        explanation='PDF file'
    )
    
    op = FileOperation(
        source_path=Path('/downloads/locked.pdf'),
        destination_path=Path('/downloads/organized/Documents/locked.pdf'),
        category='Documents',
        classification=classification,
        timestamp=datetime.now(),
        success=False,
        error_message='Permission denied'
    )
    
    reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Check for errors section
    assert "## Errors" in summary
    assert "locked.pdf" in summary
    assert "Permission denied" in summary


def test_write_summary_creates_file(tmp_path):
    """Test that write_summary creates a file with the summary content."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add an operation
    classification = ClassificationResult(
        category='Images',
        confidence=1.0,
        method='rule-based',
        explanation='PNG file'
    )
    
    op = FileOperation(
        source_path=Path('/downloads/photo.png'),
        destination_path=Path('/downloads/organized/Images/photo.png'),
        category='Images',
        classification=classification,
        timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    reporter.add_operation(op)
    
    # Write summary to temp file
    output_path = tmp_path / "summary.md"
    reporter.write_summary(output_path)
    
    # Verify file was created
    assert output_path.exists()
    
    # Verify content
    content = output_path.read_text(encoding='utf-8')
    assert "# Cleanup Summary" in content
    assert "photo.png" in content


# Additional unit tests for report formatting (Task 6.5)

def test_markdown_table_with_multiple_categories():
    """Test markdown table generation with multiple categories."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add operations for different categories
    categories_data = [
        ('Documents', 'test.pdf', 'PDF file'),
        ('Documents', 'report.docx', 'DOCX file'),
        ('Images', 'photo.jpg', 'JPEG image'),
        ('Videos', 'clip.mp4', 'MP4 video'),
        ('Archives', 'data.zip', 'ZIP archive'),
    ]
    
    for category, filename, explanation in categories_data:
        classification = ClassificationResult(
            category=category,
            confidence=1.0,
            method='rule-based',
            explanation=explanation
        )
        
        op = FileOperation(
            source_path=Path(f'/downloads/{filename}'),
            destination_path=Path(f'/downloads/organized/{category}/{filename}'),
            category=category,
            classification=classification,
            timestamp=datetime.now(),
            success=True,
            error_message=None
        )
        
        reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Verify table structure
    assert "| Category | Files Moved | Percentage |" in summary
    assert "|----------|-------------|------------|" in summary
    
    # Verify each category appears in the table
    assert "| Archives | 1 | 20.0% |" in summary
    assert "| Documents | 2 | 40.0% |" in summary
    assert "| Images | 1 | 20.0% |" in summary
    assert "| Videos | 1 | 20.0% |" in summary


def test_markdown_table_percentage_calculation():
    """Test that percentages are calculated correctly in the markdown table."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add 3 documents and 1 image (total 4 files)
    for i in range(3):
        classification = ClassificationResult(
            category='Documents',
            confidence=1.0,
            method='rule-based',
            explanation='PDF file'
        )
        
        op = FileOperation(
            source_path=Path(f'/downloads/doc{i}.pdf'),
            destination_path=Path(f'/downloads/organized/Documents/doc{i}.pdf'),
            category='Documents',
            classification=classification,
            timestamp=datetime.now(),
            success=True,
            error_message=None
        )
        
        reporter.add_operation(op)
    
    # Add 1 image
    classification = ClassificationResult(
        category='Images',
        confidence=1.0,
        method='rule-based',
        explanation='PNG image'
    )
    
    op = FileOperation(
        source_path=Path('/downloads/image.png'),
        destination_path=Path('/downloads/organized/Images/image.png'),
        category='Images',
        classification=classification,
        timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Verify percentages: 3/4 = 75%, 1/4 = 25%
    assert "| Documents | 3 | 75.0% |" in summary
    assert "| Images | 1 | 25.0% |" in summary


def test_empty_results_no_category_breakdown():
    """Test that empty results don't show category breakdown section."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Don't add any operations
    summary = reporter.generate_summary()
    
    # Should have basic structure
    assert "# Cleanup Summary" in summary
    assert "**Total Files Processed:** 0" in summary
    assert "**Total Files Moved:** 0" in summary
    
    # Should NOT have category breakdown section
    assert "## Category Breakdown" not in summary
    assert "| Category | Files Moved | Percentage |" not in summary


def test_empty_results_no_sample_operations():
    """Test that empty results don't show sample operations section."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Don't add any operations
    summary = reporter.generate_summary()
    
    # Should NOT have sample operations section
    assert "## Sample Operations" not in summary


def test_empty_results_no_errors_section():
    """Test that reports with no errors don't show errors section."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add a successful operation
    classification = ClassificationResult(
        category='Documents',
        confidence=1.0,
        method='rule-based',
        explanation='PDF file'
    )
    
    op = FileOperation(
        source_path=Path('/downloads/test.pdf'),
        destination_path=Path('/downloads/organized/Documents/test.pdf'),
        category='Documents',
        classification=classification,
        timestamp=datetime.now(),
        success=True,
        error_message=None
    )
    
    reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Should NOT have errors section
    assert "## Errors" not in summary


def test_markdown_table_sorted_categories():
    """Test that categories in the markdown table are sorted alphabetically."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add operations in non-alphabetical order
    categories = ['Videos', 'Archives', 'Documents', 'Images']
    
    for category in categories:
        classification = ClassificationResult(
            category=category,
            confidence=1.0,
            method='rule-based',
            explanation=f'{category} file'
        )
        
        op = FileOperation(
            source_path=Path(f'/downloads/file.{category.lower()}'),
            destination_path=Path(f'/downloads/organized/{category}/file.{category.lower()}'),
            category=category,
            classification=classification,
            timestamp=datetime.now(),
            success=True,
            error_message=None
        )
        
        reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Extract the table section
    lines = summary.split('\n')
    table_start = None
    table_lines = []
    
    for i, line in enumerate(lines):
        if '| Category | Files Moved | Percentage |' in line:
            table_start = i
        elif table_start is not None and line.startswith('|') and 'Category' not in line and '---' not in line:
            table_lines.append(line)
        elif table_start is not None and not line.startswith('|'):
            break
    
    # Extract category names from table
    category_order = []
    for line in table_lines:
        parts = [p.strip() for p in line.split('|')]
        if len(parts) > 1 and parts[1]:
            category_order.append(parts[1])
    
    # Verify they are sorted
    assert category_order == sorted(category_order), \
        f"Categories not sorted: {category_order}"


def test_empty_results_with_failed_operations():
    """Test handling of operations where all failed (no successful moves)."""
    config = Config.get_default_config()
    reporter = ReportGenerator(config)
    
    # Add only failed operations
    classification = ClassificationResult(
        category='Documents',
        confidence=1.0,
        method='rule-based',
        explanation='PDF file'
    )
    
    op = FileOperation(
        source_path=Path('/downloads/locked.pdf'),
        destination_path=Path('/downloads/organized/Documents/locked.pdf'),
        category='Documents',
        classification=classification,
        timestamp=datetime.now(),
        success=False,
        error_message='Permission denied'
    )
    
    reporter.add_operation(op)
    
    summary = reporter.generate_summary()
    
    # Should show 1 processed, 0 moved, 1 skipped
    assert "**Total Files Processed:** 1" in summary
    assert "**Total Files Moved:** 0" in summary
    assert "**Files Skipped:** 1" in summary
    
    # Should NOT have category breakdown (no successful moves)
    assert "## Category Breakdown" not in summary
    
    # Should have errors section
    assert "## Errors" in summary
    assert "locked.pdf" in summary
    assert "Permission denied" in summary
