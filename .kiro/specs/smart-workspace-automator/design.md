# Design Document

## Overview

The Smart Workspace Automator is a Python-based command-line application that automatically organizes files in the Downloads folder using a hybrid classification approach. The system combines rule-based pattern matching with AI-powered reasoning to intelligently categorize files and move them into appropriate folders.

The architecture follows a pipeline design with six distinct stages:
1. **Initialization** - Load configuration and prepare the environment
2. **File Discovery** - Scan the Downloads folder and extract metadata
3. **Classification** - Apply rule-based and AI classification
4. **Organization** - Move files to category folders safely
5. **Reporting** - Generate summary and logs
6. **Completion** - Display results to the user

The system is designed to be fully automated, requiring no user interaction during execution, while providing complete transparency through detailed logging and explainable decisions.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Main Controller                      │
│                          (main.py)                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──────────────────────────────────────────────────┐
             │                                                  │
             ▼                                                  ▼
┌────────────────────────┐                    ┌────────────────────────┐
│   Configuration Loader │                    │    File Scanner        │
│      (config.py)       │                    │     (scanner.py)       │
└────────────────────────┘                    └───────────┬────────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────────┐
                                              │  Classification Engine │
                                              │   (classifier.py)      │
                                              │                        │
                                              │  ┌──────────────────┐  │
                                              │  │ Rule-Based       │  │
                                              │  │ Classifier       │  │
                                              │  └──────────────────┘  │
                                              │  ┌──────────────────┐  │
                                              │  │ AI Classifier    │  │
                                              │  └──────────────────┘  │
                                              │  ┌──────────────────┐  │
                                              │  │ Decision Merger  │  │
                                              │  └──────────────────┘  │
                                              └───────────┬────────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────────┐
                                              │   File Organizer       │
                                              │   (organizer.py)       │
                                              └───────────┬────────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────────┐
                                              │   Report Generator     │
                                              │    (reporter.py)       │
                                              └────────────────────────┘
```

### Component Responsibilities

**Main Controller** (`main.py`)
- Orchestrates the entire workflow
- Handles command-line arguments
- Manages error handling at the application level
- Displays progress and completion messages

**Configuration Loader** (`config.py`)
- Loads and validates configuration from JSON
- Provides default values for missing configuration
- Detects the default Downloads folder per OS
- Exposes configuration to other components

**File Scanner** (`scanner.py`)
- Traverses the Downloads folder
- Extracts file metadata (name, extension, MIME type, size, mtime)
- Filters out system files and temporary files
- Returns a list of FileMetadata objects

**Classification Engine** (`classifier.py`)
- Implements rule-based classification using extension mappings
- Implements AI classification for ambiguous files
- Merges classification results to determine final category
- Provides confidence scores and explanations

**File Organizer** (`organizer.py`)
- Creates category folders as needed
- Moves files safely with duplicate handling
- Preserves file timestamps
- Handles permission errors gracefully

**Report Generator** (`reporter.py`)
- Aggregates statistics from the operation
- Generates markdown summary report
- Creates detailed action logs
- Produces category breakdown statistics

### Data Flow

```
Downloads Folder
      │
      ▼
[File Scanner] → List<FileMetadata>
      │
      ▼
[Rule-Based Classifier] → Classification Result (confidence, category)
      │
      ▼
[AI Classifier] → AI Prediction (purpose, explanation)
      │
      ▼
[Decision Merger] → Final Category
      │
      ▼
[File Organizer] → File Moved + Log Entry
      │
      ▼
[Report Generator] → summary.md + actions.log
```

## Components and Interfaces

### FileMetadata

A data class representing file information:

```python
@dataclass
class FileMetadata:
    path: Path
    name: str
    extension: str
    mime_type: str
    size: int
    modified_time: datetime
    is_hidden: bool
```

### ClassificationResult

A data class representing classification output:

```python
@dataclass
class ClassificationResult:
    category: str
    confidence: float  # 0.0 to 1.0
    method: str  # "rule-based" or "ai" or "merged"
    explanation: str
```

### FileOperation

A data class representing a file move operation:

```python
@dataclass
class FileOperation:
    source_path: Path
    destination_path: Path
    category: str
    classification: ClassificationResult
    timestamp: datetime
    success: bool
    error_message: Optional[str]
```

### Configuration Interface

```python
class Config:
    def __init__(self, config_path: str):
        """Load configuration from JSON file"""
        
    def get_downloads_folder(self) -> Path:
        """Get Downloads folder path, auto-detect if not configured"""
        
    def get_category_folders(self) -> Dict[str, str]:
        """Get mapping of category names to folder names"""
        
    def get_extension_mappings(self) -> Dict[str, str]:
        """Get mapping of file extensions to categories"""
        
    def get_ai_prompt_template(self) -> str:
        """Get AI classifier prompt template"""
        
    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
```

### Scanner Interface

```python
class FileScanner:
    def __init__(self, config: Config):
        """Initialize scanner with configuration"""
        
    def scan(self, folder_path: Path) -> List[FileMetadata]:
        """Scan folder and return list of file metadata"""
        
    def is_system_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from processing"""
        
    def extract_metadata(self, file_path: Path) -> FileMetadata:
        """Extract metadata from a single file"""
```

### Classifier Interface

```python
class RuleBasedClassifier:
    def __init__(self, extension_mappings: Dict[str, str]):
        """Initialize with extension to category mappings"""
        
    def classify(self, metadata: FileMetadata) -> ClassificationResult:
        """Classify file based on extension and MIME type"""

class AIClassifier:
    def __init__(self, prompt_template: str):
        """Initialize with AI prompt template"""
        
    def classify(self, metadata: FileMetadata) -> ClassificationResult:
        """Classify file using AI reasoning"""
        
    def is_ambiguous(self, metadata: FileMetadata, rule_result: ClassificationResult) -> bool:
        """Determine if file needs AI classification"""

class ClassificationEngine:
    def __init__(self, config: Config):
        """Initialize with both classifiers"""
        
    def classify(self, metadata: FileMetadata) -> ClassificationResult:
        """Apply hybrid classification and return final result"""
```

### Organizer Interface

```python
class FileOrganizer:
    def __init__(self, config: Config):
        """Initialize organizer with configuration"""
        
    def organize(self, metadata: FileMetadata, classification: ClassificationResult) -> FileOperation:
        """Move file to appropriate category folder"""
        
    def create_category_folder(self, category: str) -> Path:
        """Create category folder if it doesn't exist"""
        
    def handle_duplicate(self, destination: Path) -> Path:
        """Generate unique filename for duplicate files"""
        
    def move_file_safely(self, source: Path, destination: Path) -> bool:
        """Move file with error handling"""
```

### Reporter Interface

```python
class ReportGenerator:
    def __init__(self, config: Config):
        """Initialize reporter with configuration"""
        
    def add_operation(self, operation: FileOperation):
        """Record a file operation"""
        
    def generate_summary(self) -> str:
        """Generate markdown summary report"""
        
    def write_action_log(self, log_path: Path):
        """Write detailed action log"""
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get operation statistics"""
```

## Data Models

### Configuration Schema (config.json)

```json
{
  "downloads_folder": null,
  "organized_folder": "organized",
  "logs_folder": "logs",
  "categories": {
    "Documents": ["pdf", "doc", "docx", "txt", "rtf", "odt"],
    "Images": ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"],
    "Videos": ["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm"],
    "Archives": ["zip", "rar", "7z", "tar", "gz", "bz2"],
    "Code": ["py", "js", "html", "css", "java", "cpp", "c", "h"],
    "Installers": ["exe", "msi", "dmg", "pkg", "deb", "rpm"],
    "Work": [],
    "Study": [],
    "Miscellaneous": []
  },
  "system_file_patterns": [".tmp", ".part", ".DS_Store", ".crdownload"],
  "ai_classifier": {
    "enabled": true,
    "prompt_template": "Given the filename '{filename}', predict its purpose from these options: work, study, media, misc. Consider patterns like 'assignment', 'project', 'report' for study; 'invoice', 'contract', 'meeting' for work. Respond with JSON: {\"purpose\": \"<category>\", \"explanation\": \"<reason>\"}",
    "ambiguity_threshold": 0.7
  },
  "duplicate_handling": {
    "strategy": "rename",
    "suffix_pattern": "_{n}"
  }
}
```

### Summary Report Schema (summary.md)

```markdown
# Cleanup Summary

**Date:** 2025-12-04 14:30:00
**Duration:** 2.5 seconds
**Total Files Processed:** 47
**Total Files Moved:** 45
**Files Skipped:** 2

## Category Breakdown

| Category | Files Moved | Percentage |
|----------|-------------|------------|
| Documents | 15 | 33.3% |
| Images | 12 | 26.7% |
| Videos | 5 | 11.1% |
| Archives | 8 | 17.8% |
| Code | 3 | 6.7% |
| Study | 2 | 4.4% |

## Sample Operations

### Documents
- `report_final.pdf` → Documents/report_final.pdf (Rule-based: PDF extension)
- `assignment_v2.docx` → Documents/assignment_v2.docx (Rule-based: DOCX extension)

### Study
- `lecture_notes_final(1).pdf` → Study/lecture_notes_final(1).pdf (AI: Detected 'lecture' keyword indicating study material)

### Images
- `screenshot_2024.png` → Images/screenshot_2024.png (Rule-based: PNG extension)

## Errors

- `locked_file.pdf`: Permission denied (file in use)
- `corrupted.zip`: Unable to read file metadata
```

### Action Log Schema (actions.log)

```
2025-12-04 14:30:00.123 | INFO | Starting cleanup operation
2025-12-04 14:30:00.234 | INFO | Scanning folder: /Users/john/Downloads
2025-12-04 14:30:00.345 | INFO | Found 47 files to process
2025-12-04 14:30:00.456 | INFO | Classifying: report.pdf
2025-12-04 14:30:00.567 | INFO | Rule-based classification: Documents (confidence: 1.0)
2025-12-04 14:30:00.678 | INFO | Moving: report.pdf → organized/Documents/report.pdf
2025-12-04 14:30:00.789 | SUCCESS | Moved: report.pdf
2025-12-04 14:30:00.890 | INFO | Classifying: assignment_final(1).pdf
2025-12-04 14:30:01.001 | INFO | Rule-based classification: Documents (confidence: 0.6)
2025-12-04 14:30:01.112 | INFO | Invoking AI classifier for ambiguous file
2025-12-04 14:30:01.223 | INFO | AI classification: Study (explanation: Filename contains 'assignment' indicating academic work)
2025-12-04 14:30:01.334 | INFO | Final classification: Study (merged result)
2025-12-04 14:30:01.445 | INFO | Moving: assignment_final(1).pdf → organized/Study/assignment_final(1).pdf
2025-12-04 14:30:01.556 | SUCCESS | Moved: assignment_final(1).pdf
2025-12-04 14:30:02.667 | ERROR | Failed to move locked_file.pdf: Permission denied
2025-12-04 14:30:02.778 | INFO | Cleanup complete: 45 files moved, 2 errors
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

After analyzing the acceptance criteria, I've identified the following properties that eliminate redundancy and provide comprehensive validation:

### Property Reflection

Several acceptance criteria were identified as redundant:
- Requirement 1.4 is subsumed by 1.1 and 1.2 (if all files are identified and metadata is extracted, we have a structured list)
- Requirement 5.5 is subsumed by 5.1, 5.2, and 5.3 (if we log classification reasons, AI explanations, and move details, decisions are explainable)

The following properties provide unique validation value:

**Property 1: Complete file discovery**
*For any* Downloads folder with files, scanning should identify all non-system files present in the folder
**Validates: Requirements 1.1**

**Property 2: Metadata completeness**
*For any* scanned file, the extracted metadata should contain filename, extension, MIME type, and size fields
**Validates: Requirements 1.2**

**Property 3: System file exclusion**
*For any* file with extension .tmp, .part, or hidden status, scanning should exclude it from the results
**Validates: Requirements 1.3**

**Property 4: Known extension classification**
*For any* file with a known extension (e.g., .pdf, .jpg, .zip), rule-based classification should assign the correct category with high confidence (>0.7)
**Validates: Requirements 2.2**

**Property 5: Ambiguous file AI invocation**
*For any* file with low rule-based confidence (<0.7), the classification engine should invoke the AI classifier
**Validates: Requirements 2.3**

**Property 6: AI classifier interface**
*For any* AI classification request, the classifier should receive the filename and return both a purpose prediction and an explanation
**Validates: Requirements 2.4**

**Property 7: Classification merge produces result**
*For any* file with both rule-based and AI classifications, the merge operation should produce a single final category
**Validates: Requirements 2.5**

**Property 8: Document file categorization**
*For any* file classified as a document type (.pdf, .doc, .docx, .txt), the system should assign it to the Documents category
**Validates: Requirements 3.2**

**Property 9: Media file categorization**
*For any* file classified as media content, the system should assign it to either Images or Videos category based on the media type
**Validates: Requirements 3.3**

**Property 10: Purpose-based categorization**
*For any* file classified by purpose (work/study keywords), the system should assign it to the appropriate purpose category (Work, Study, or Miscellaneous)
**Validates: Requirements 3.4**

**Property 11: Low confidence fallback**
*For any* file that cannot be confidently classified (confidence <0.5), the system should assign it to the Miscellaneous category
**Validates: Requirements 3.5**

**Property 12: Category folder creation**
*For any* file being moved to a category, if the category folder doesn't exist, the system should create it before moving the file
**Validates: Requirements 4.1**

**Property 13: Duplicate file renaming**
*For any* file being moved to a destination where a file with the same name exists, the system should rename the incoming file with a numeric suffix
**Validates: Requirements 4.2**

**Property 14: Permission error resilience**
*For any* file move that fails due to permissions, the system should log the error and continue processing remaining files
**Validates: Requirements 4.3**

**Property 15: Timestamp preservation**
*For any* file that is successfully moved, the modification timestamp in the destination should match the original timestamp
**Validates: Requirements 4.4**

**Property 16: No file loss**
*For any* cleanup operation, the total number of files (moved + skipped + errored) should equal the number of files initially scanned
**Validates: Requirements 4.5**

**Property 17: Classification reason recording**
*For any* classified file, the classification result should include the method used (rule-based, AI, or merged)
**Validates: Requirements 5.1**

**Property 18: AI explanation storage**
*For any* file classified by AI, the classification result should include the AI-generated explanation
**Validates: Requirements 5.2**

**Property 19: Move operation logging**
*For any* file that is moved, the action log should contain the original location, new location, category, and classification reason
**Validates: Requirements 5.3**

**Property 20: Log timestamp inclusion**
*For any* operation logged, the log entry should include a timestamp
**Validates: Requirements 5.4**

**Property 21: Summary file count accuracy**
*For any* cleanup operation, the summary report should contain total files processed and total files moved that match the actual counts
**Validates: Requirements 6.2**

**Property 22: Summary category breakdown**
*For any* cleanup operation, the summary report should include a breakdown showing the number of files in each category
**Validates: Requirements 6.3**

**Property 23: Summary sample inclusion**
*For any* cleanup operation with moved files, the summary report should include at least one sample file movement with its classification reason
**Validates: Requirements 6.4**

**Property 24: Summary duration inclusion**
*For any* cleanup operation, the summary report should include the total time taken
**Validates: Requirements 6.5**

**Property 25: Configuration loading**
*For any* valid configuration JSON file, the system should successfully load folder paths, extension mappings, and category definitions
**Validates: Requirements 8.1**

**Property 26: AI prompt template loading**
*For any* configuration with a custom AI prompt template, the system should load and use that template for AI classification
**Validates: Requirements 8.4**

**Property 27: Configuration validation**
*For any* invalid configuration file (missing required fields, invalid JSON), the system should report specific validation errors
**Validates: Requirements 8.5**

**Property 28: Timestamped log file creation**
*For any* execution, the system should create a log file with a timestamp in its name
**Validates: Requirements 10.1**

**Property 29: File operation logging completeness**
*For any* file processed, the log should contain entries for scan, classify, and move (or skip) operations
**Validates: Requirements 10.2**

**Property 30: Error logging completeness**
*For any* error that occurs, the log should contain the error type, affected file path, and error message
**Validates: Requirements 10.3**

**Property 31: AI invocation logging**
*For any* AI classifier invocation, the log should contain the input prompt and the received response
**Validates: Requirements 10.4**

## Error Handling

The system implements comprehensive error handling at multiple levels:

### File-Level Errors

**Permission Errors**
- When a file cannot be read or moved due to permissions, the system logs the error and continues
- The file is marked as "skipped" in the summary report
- The error is recorded in the action log with full details

**Locked Files**
- Files that are currently in use by another process are detected during the move operation
- The system logs a warning and skips the file
- The user is notified in the summary report

**Corrupted Files**
- If metadata extraction fails (e.g., corrupted file), the system logs the error
- The file is skipped and reported in the error section of the summary

**Missing Files**
- If a file is deleted between scanning and moving, the system handles the FileNotFoundError gracefully
- The operation is logged as skipped

### System-Level Errors

**Configuration Errors**
- Invalid JSON syntax: System reports parsing error and exits with error code
- Missing required fields: System reports validation errors and exits
- Invalid paths: System reports path errors and exits

**Folder Access Errors**
- If the Downloads folder doesn't exist or isn't accessible, the system reports a clear error message
- If the organized folder cannot be created, the system reports the error and exits

**AI Classifier Errors**
- If the AI classifier fails to respond, the system falls back to rule-based classification only
- The error is logged but doesn't stop processing
- The file is classified using only rule-based results

### Error Recovery Strategies

**Graceful Degradation**
- AI classifier failures don't stop the entire operation
- Individual file errors don't stop processing of other files
- The system always completes and generates a report, even if some operations failed

**Detailed Error Reporting**
- All errors are logged with timestamps, file paths, and error messages
- The summary report includes an "Errors" section listing all failures
- Error counts are included in the statistics

**Atomic Operations**
- File moves are atomic (either complete or fail, no partial moves)
- If a move fails, the original file remains in place
- No data loss occurs due to failed operations

## Testing Strategy

The Smart Workspace Automator will use a dual testing approach combining unit tests and property-based tests to ensure comprehensive correctness validation.

### Property-Based Testing

**Framework**: We will use **Hypothesis** for Python, which is the standard property-based testing library for Python projects.

**Configuration**: Each property-based test will be configured to run a minimum of 100 iterations to ensure thorough coverage of the input space.

**Test Tagging**: Each property-based test will include a comment explicitly referencing the correctness property from this design document using the format:
```python
# Feature: smart-workspace-automator, Property 1: Complete file discovery
```

**Property Implementation**: Each correctness property listed in the Correctness Properties section will be implemented as a single property-based test. The test will generate random inputs appropriate to the property and verify the expected behavior holds across all generated cases.

**Test Organization**: Property-based tests will be organized by component:
- `test_scanner_properties.py` - Properties 1-3 (file discovery and metadata)
- `test_classifier_properties.py` - Properties 4-11 (classification logic)
- `test_organizer_properties.py` - Properties 12-16 (file organization)
- `test_logging_properties.py` - Properties 17-20, 28-31 (logging and tracing)
- `test_reporter_properties.py` - Properties 21-24 (summary generation)
- `test_config_properties.py` - Properties 25-27 (configuration)

**Generators**: Custom Hypothesis strategies will be created for:
- Random file structures (various extensions, sizes, names)
- Random configuration objects
- Random classification results
- File metadata with various edge cases (special characters, long names, no extensions)

### Unit Testing

**Framework**: We will use **pytest** as the unit testing framework.

**Coverage Areas**: Unit tests will focus on:
- Specific examples that demonstrate correct behavior (e.g., "test_pdf_classified_as_document")
- Edge cases identified in Requirement 7 (locked files, empty folders, special characters, extensionless files)
- Integration points between components (e.g., scanner → classifier → organizer pipeline)
- Error conditions (permission errors, invalid configs, missing files)
- Configuration loading and validation with specific examples

**Test Organization**: Unit tests will be co-located with source files:
- `scanner.py` → `test_scanner.py`
- `classifier.py` → `test_classifier.py`
- `organizer.py` → `test_organizer.py`
- `reporter.py` → `test_reporter.py`
- `config.py` → `test_config.py`

**Mocking Strategy**: Minimal mocking will be used. Where necessary:
- File system operations may be mocked for specific error condition tests
- AI classifier may be mocked in integration tests to ensure deterministic behavior

### Integration Testing

**End-to-End Tests**: A small number of integration tests will verify the complete workflow:
- Create a temporary Downloads folder with known files
- Run the complete cleanup operation
- Verify files are in correct categories
- Verify summary report is accurate
- Verify logs contain expected entries

**Test Data**: Integration tests will use fixture files representing common scenarios:
- Mixed file types (documents, images, videos, archives)
- Ambiguous files requiring AI classification
- Duplicate files
- Files with special characters

### Test Execution

**Continuous Testing**: Tests will be run:
- Before each commit (via pre-commit hook)
- On each pull request (via CI/CD)
- After each implementation task

**Coverage Goals**:
- Minimum 80% code coverage for core logic
- 100% coverage of error handling paths
- All 31 correctness properties implemented as property-based tests

### Complementary Nature of Tests

Unit tests and property-based tests work together:
- **Unit tests** catch specific bugs with concrete examples (e.g., "PDF files go to Documents folder")
- **Property tests** verify general correctness across all inputs (e.g., "All files with known extensions get high confidence scores")
- **Integration tests** ensure components work together correctly in realistic scenarios

This dual approach ensures both specific correctness (unit tests) and universal correctness (property tests), providing confidence that the system behaves correctly across the entire input space.

## Implementation Notes

### Technology Choices

**Python 3.8+**: Chosen for cross-platform compatibility, rich standard library, and excellent file system support.

**Standard Library Modules**:
- `pathlib`: Modern, object-oriented path handling
- `shutil`: High-level file operations
- `mimetypes`: MIME type detection
- `json`: Configuration file parsing
- `datetime`: Timestamp handling
- `logging`: Structured logging

**Optional Dependencies**:
- `python-magic`: Enhanced MIME type detection (fallback to `mimetypes` if not available)
- `hypothesis`: Property-based testing framework
- `pytest`: Unit testing framework

### AI Classifier Implementation

The AI classifier will use a simple prompt-based approach:
- Prompt template is loaded from configuration
- Filename is inserted into the template
- Response is parsed as JSON containing purpose and explanation
- The implementation is agnostic to the specific AI backend (can use OpenAI, Anthropic, local models, etc.)

For the initial implementation, the AI classifier can be a simple rule-based heuristic that looks for keywords:
- "assignment", "homework", "lecture" → Study
- "invoice", "contract", "meeting", "report" → Work
- Everything else → Miscellaneous

This allows the system to work without requiring API keys, while maintaining the interface for future AI integration.

### Performance Considerations

**Lazy Processing**: Files are processed one at a time, not loaded into memory all at once.

**Streaming Metadata**: File content is not read unless necessary for MIME type detection.

**Efficient File Operations**: Using `shutil.move()` which is optimized for same-filesystem moves.

**Progress Indication**: For large folders, progress is displayed every 10 files processed.

### Cross-Platform Compatibility

**Path Handling**: All paths use `pathlib.Path` for cross-platform compatibility.

**Default Folders**: Downloads folder detection uses platform-specific logic:
- Windows: `%USERPROFILE%\Downloads`
- macOS: `~/Downloads`
- Linux: `~/Downloads` or `~/downloads`

**File Operations**: All file operations use Python standard library functions that work across platforms.

**Line Endings**: Log files use platform-appropriate line endings.

### Extensibility Points

**New Categories**: Add to the `categories` section in `config.json`.

**New File Extensions**: Add to the extension mappings in `config.json`.

**Custom AI Prompts**: Modify the `ai_classifier.prompt_template` in `config.json`.

**Custom Duplicate Handling**: Modify the `duplicate_handling.strategy` in `config.json` (future: support "overwrite", "skip", "rename").

**Plugin Architecture** (future): The classification engine can be extended to support custom classifier plugins.

## Security Considerations

**Path Traversal Prevention**: All file paths are validated to ensure they remain within the Downloads and organized folders.

**Symbolic Link Handling**: Symbolic links are followed but validated to prevent escaping the allowed directories.

**Permission Checks**: Before moving files, the system checks write permissions on the target folder.

**No Code Execution**: The system never executes file contents, only reads metadata.

**Configuration Validation**: All configuration values are validated before use to prevent injection attacks.

**Logging Sanitization**: File paths in logs are sanitized to prevent log injection attacks.
