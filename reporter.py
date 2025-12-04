"""Report generator module for Smart Workspace Automator."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

from config import Config
from organizer import FileOperation


class ReportGenerator:
    """Generates summary reports and statistics for cleanup operations."""
    
    def __init__(self, config: Config):
        """Initialize reporter with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.operations: List[FileOperation] = []
        self.start_time: datetime = datetime.now()
        self.end_time: datetime = datetime.now()
    
    def set_start_time(self, start_time: datetime):
        """Set the start time of the operation.
        
        Args:
            start_time: Start timestamp
        """
        self.start_time = start_time
    
    def set_end_time(self, end_time: datetime):
        """Set the end time of the operation.
        
        Args:
            end_time: End timestamp
        """
        self.end_time = end_time
    
    def add_operation(self, operation: FileOperation):
        """Record a file operation.
        
        Args:
            operation: FileOperation record
        """
        self.operations.append(operation)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get operation statistics.
        
        Returns:
            Dictionary containing statistics about the operation
        """
        total_files = len(self.operations)
        successful_moves = sum(1 for op in self.operations if op.success)
        failed_moves = sum(1 for op in self.operations if not op.success)
        
        # Calculate category breakdown
        category_counts = defaultdict(int)
        for op in self.operations:
            if op.success:
                category_counts[op.category] += 1
        
        # Calculate duration
        duration = (self.end_time - self.start_time).total_seconds()
        
        return {
            'total_files_processed': total_files,
            'total_files_moved': successful_moves,
            'files_skipped': failed_moves,
            'category_breakdown': dict(category_counts),
            'duration_seconds': duration,
            'start_time': self.start_time,
            'end_time': self.end_time
        }
    
    def generate_summary(self) -> str:
        """Generate markdown summary report.
        
        Returns:
            Markdown-formatted summary report as a string
        """
        stats = self.get_statistics()
        
        # Build the markdown report
        lines = []
        lines.append("# Cleanup Summary")
        lines.append("")
        lines.append(f"**Date:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Duration:** {stats['duration_seconds']:.1f} seconds")
        lines.append(f"**Total Files Processed:** {stats['total_files_processed']}")
        lines.append(f"**Total Files Moved:** {stats['total_files_moved']}")
        lines.append(f"**Files Skipped:** {stats['files_skipped']}")
        lines.append("")
        
        # Category breakdown section
        if stats['category_breakdown']:
            lines.append("## Category Breakdown")
            lines.append("")
            lines.append("| Category | Files Moved | Percentage |")
            lines.append("|----------|-------------|------------|")
            
            total_moved = stats['total_files_moved']
            for category in sorted(stats['category_breakdown'].keys()):
                count = stats['category_breakdown'][category]
                percentage = (count / total_moved * 100) if total_moved > 0 else 0
                lines.append(f"| {category} | {count} | {percentage:.1f}% |")
            
            lines.append("")
        
        # Sample operations section
        if self.operations:
            lines.append("## Sample Operations")
            lines.append("")
            
            # Group operations by category
            operations_by_category = defaultdict(list)
            for op in self.operations:
                if op.success:
                    operations_by_category[op.category].append(op)
            
            # Show samples from each category (up to 2 per category)
            for category in sorted(operations_by_category.keys()):
                ops = operations_by_category[category]
                lines.append(f"### {category}")
                
                for op in ops[:2]:  # Show up to 2 samples per category
                    explanation = op.classification.explanation
                    # Try to compute relative path, fall back to absolute if not possible
                    try:
                        dest_display = op.destination_path.relative_to(self.config.downloads_folder)
                    except ValueError:
                        # If paths don't share a common base, just use the destination path
                        dest_display = op.destination_path
                    lines.append(f"- `{op.source_path.name}` → {dest_display} ({explanation})")
                
                lines.append("")
        
        # Errors section
        errors = [op for op in self.operations if not op.success]
        if errors:
            lines.append("## Errors")
            lines.append("")
            for op in errors:
                lines.append(f"- `{op.source_path.name}`: {op.error_message}")
            lines.append("")
        
        return "\n".join(lines)
    
    def write_summary(self, output_path: Path):
        """Write summary report to a file.
        
        Args:
            output_path: Path where the summary should be written
        """
        summary = self.generate_summary()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding='utf-8')
