# Smart Workspace Automator

An intelligent file-organization system that automatically cleans and organizes the Downloads folder using a hybrid rule-based and AI-powered approach.

## Project Structure

```
.
├── config.py              # Configuration loader and validator
├── config.json            # Default configuration file
├── scanner.py             # File scanner module
├── test_config.py         # Property-based tests for configuration
├── test_scanner.py        # Property-based tests for scanner
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The system uses a JSON configuration file (`config.json`) with the following structure:

- `downloads_folder`: Path to Downloads folder (null = auto-detect)
- `organized_folder`: Name of the organized files folder
- `logs_folder`: Name of the logs folder
- `categories`: Dictionary mapping category names to file extensions
- `system_file_patterns`: List of patterns for system files to exclude
- `ai_classifier`: AI classifier settings
  - `enabled`: Enable/disable AI classification
  - `prompt_template`: Template for AI prompts
  - `ambiguity_threshold`: Confidence threshold for AI invocation (0.0-1.0)
- `duplicate_handling`: Duplicate file handling settings
  - `strategy`: Strategy for duplicates (rename/skip/overwrite)
  - `suffix_pattern`: Pattern for renaming duplicates

## Testing

Run the property-based tests:
```bash
pytest test_config.py -v
```

## Development Status

✅ Task 1: Project structure and configuration system - COMPLETED
- Configuration loader with JSON support
- Configuration validation with error reporting
- Default configuration with all categories
- Property-based tests for configuration loading, AI prompt templates, and validation

✅ Task 2: File scanner module - COMPLETED
- FileMetadata data class with all required fields
- File scanning that traverses Downloads folder
- Metadata extraction (filename, extension, MIME type, size, mtime)
- System file filtering (.tmp, .part, hidden files)
- Cross-platform Downloads folder detection
- Property-based tests for file discovery, metadata completeness, and system file exclusion
- Unit tests for edge cases (empty folders, no extension, special characters, large files)

## Next Steps

Continue with Task 3: Implement classification engine# Development Status

✅ Task 1: Project structure and configuration system - COMPLETED
- Configuration loader with JSON support
- Configuration validation with error reporting
- Default configuration with all categories
- Property-based tests for configuration loading, AI prompt templates, and validation

✅ Task 2: File scanner module - COMPLETED
- FileMetadata data class with all required fields
- File scanning that traverses Downloads folder
- Metadata extraction (filename, extension, MIME type, size, mtime)
- System file filtering (.tmp, .part, hidden files)
- Cross-platform Downloads folder detection
- Property-based tests for file discovery, metadata completeness, and system file exclusion
- Unit tests for edge cases (empty folders, no extension, special characters, large files)

## Next Steps

Continue with Task 3: Implement classification engine
