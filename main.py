"""Main controller and CLI for Smart Workspace Automator."""

import sys
import argparse
from pathlib import Path
from datetime import datetime

from config import Config
from scanner import FileScanner
from classifier import ClassificationEngine
from organizer import FileOrganizer
from reporter import ReportGenerator
from logger import ActionLogger


class SmartWorkspaceAutomator:
    """Main controller that orchestrates the file organization workflow."""
    
    def __init__(self, config: Config):
        """Initialize the automator with configuration.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.scanner = FileScanner(config)
        self.classifier = ClassificationEngine(config)
        self.organizer = FileOrganizer(config)
        self.reporter = ReportGenerator(config)
        self.logger = ActionLogger(config)
    
    def run(self, folder_path: Path) -> Path:
        """Execute the complete file organization workflow.
        
        Args:
            folder_path: Path to the folder to organize
            
        Returns:
            Path to the generated summary report
            
        Raises:
            FileNotFoundError: If the folder doesn't exist
            PermissionError: If the folder cannot be accessed
        """
        # Record start time
        start_time = datetime.now()
        self.reporter.set_start_time(start_time)
        self.logger.log_operation_start()
        
        try:
            # Stage 1: File Discovery
            print("Scanning files...")
            self.logger.log_scan_start(folder_path)
            file_list = self.scanner.scan(folder_path)
            self.logger.log_scan_complete(len(file_list))
            
            if len(file_list) == 0:
                print("No files to process.")
                self.logger.log_operation_complete(0, 0)
                
                # Generate empty report
                end_time = datetime.now()
                self.reporter.set_end_time(end_time)
                summary_path = self._get_summary_path()
                self.reporter.write_summary(summary_path)
                
                return summary_path
            
            print(f"Found {len(file_list)} files to organize.")
            
            # Stage 2-4: Classification and Organization
            print("Classifying and organizing files...")
            files_processed = 0
            errors = 0
            
            for metadata in file_list:
                # Show progress every 10 files
                files_processed += 1
                if files_processed % 10 == 0:
                    print(f"Processing file {files_processed}/{len(file_list)}...")
                
                try:
                    # Classify the file
                    classification = self.classifier.classify(metadata)
                    self.logger.log_classification(metadata, classification)
                    
                    # Organize the file
                    operation = self.organizer.organize(metadata, classification)
                    self.logger.log_move_operation(operation)
                    self.reporter.add_operation(operation)
                    
                    if not operation.success:
                        errors += 1
                
                except Exception as e:
                    # Log unexpected errors
                    self.logger.log_error(
                        error_type=type(e).__name__,
                        file_path=metadata.path,
                        error_message=str(e)
                    )
                    errors += 1
            
            # Stage 5: Reporting
            print("Generating summary report...")
            end_time = datetime.now()
            self.reporter.set_end_time(end_time)
            
            # Calculate statistics
            stats = self.reporter.get_statistics()
            files_moved = stats['total_files_moved']
            
            # Log completion
            self.logger.log_operation_complete(files_moved, errors)
            
            # Write summary report
            summary_path = self._get_summary_path()
            self.reporter.write_summary(summary_path)
            
            return summary_path
        
        finally:
            # Always close the logger
            self.logger.close()
    
    def _get_summary_path(self) -> Path:
        """Get the path for the summary report.
        
        Returns:
            Path to the summary report file
        """
        # Create summary in the organized folder
        summary_dir = self.config.downloads_folder / self.config.organized_folder
        summary_dir.mkdir(parents=True, exist_ok=True)
        return summary_dir / "summary.md"


def parse_arguments():
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description='Smart Workspace Automator - Automatically organize your Downloads folder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Organize default Downloads folder
  %(prog)s /path/to/folder          # Organize specific folder
  %(prog)s --config custom.json     # Use custom configuration
        """
    )
    
    parser.add_argument(
        'folder',
        nargs='?',
        type=str,
        help='Path to the folder to organize (default: auto-detect Downloads folder)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='Path to configuration file (default: config.json)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    # Parse command-line arguments
    args = parse_arguments()
    
    try:
        # Load configuration
        try:
            config = Config.load_from_file(args.config)
        except FileNotFoundError:
            print(f"Configuration file not found: {args.config}")
            print("Using default configuration...")
            config = Config.get_default_config()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration...")
            config = Config.get_default_config()
        
        # Determine folder to organize
        if args.folder:
            folder_path = Path(args.folder)
        else:
            # Auto-detect Downloads folder
            folder_path = config.get_downloads_folder()
            print(f"Auto-detected Downloads folder: {folder_path}")
        
        # Validate folder exists
        if not folder_path.exists():
            print(f"Error: Folder not found: {folder_path}")
            sys.exit(1)
        
        if not folder_path.is_dir():
            print(f"Error: Path is not a directory: {folder_path}")
            sys.exit(1)
        
        # Create and run the automator
        print("\n" + "="*60)
        print("Smart Workspace Automator")
        print("="*60 + "\n")
        
        automator = SmartWorkspaceAutomator(config)
        summary_path = automator.run(folder_path)
        
        # Display success message
        print("\n" + "="*60)
        print("✓ Organization complete!")
        print(f"Summary report: {summary_path}")
        print("="*60 + "\n")
        
        sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
