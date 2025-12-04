"""Configuration loader and validator for Smart Workspace Automator."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration for the Smart Workspace Automator."""
    
    downloads_folder: Path
    organized_folder: str
    logs_folder: str
    categories: Dict[str, List[str]]
    system_file_patterns: List[str]
    ai_classifier_enabled: bool
    ai_prompt_template: str
    ambiguity_threshold: float
    duplicate_handling_strategy: str
    duplicate_suffix_pattern: str
    
    @staticmethod
    def get_default_downloads_folder() -> Path:
        """Get the default Downloads folder for the current OS."""
        home = Path.home()
        
        if os.name == 'nt':  # Windows
            downloads = home / 'Downloads'
        elif os.name == 'posix':
            if os.uname().sysname == 'Darwin':  # macOS
                downloads = home / 'Downloads'
            else:  # Linux
                downloads = home / 'Downloads'
                if not downloads.exists():
                    downloads = home / 'downloads'
        else:
            downloads = home / 'Downloads'
        
        return downloads
    
    @staticmethod
    def load_from_file(config_path: str) -> 'Config':
        """Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration JSON file
            
        Returns:
            Config object with loaded settings
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
            ValueError: If configuration validation fails
        """
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Get downloads folder (use default if not specified)
        downloads_folder_str = config_data.get('downloads_folder')
        if downloads_folder_str is None:
            downloads_folder = Config.get_default_downloads_folder()
        else:
            downloads_folder = Path(downloads_folder_str)
        
        # Extract AI classifier settings
        ai_classifier = config_data.get('ai_classifier', {})
        
        # Extract duplicate handling settings
        duplicate_handling = config_data.get('duplicate_handling', {})
        
        config = Config(
            downloads_folder=downloads_folder,
            organized_folder=config_data.get('organized_folder', 'organized'),
            logs_folder=config_data.get('logs_folder', 'logs'),
            categories=config_data.get('categories', {}),
            system_file_patterns=config_data.get('system_file_patterns', []),
            ai_classifier_enabled=ai_classifier.get('enabled', True),
            ai_prompt_template=ai_classifier.get('prompt_template', ''),
            ambiguity_threshold=ai_classifier.get('ambiguity_threshold', 0.7),
            duplicate_handling_strategy=duplicate_handling.get('strategy', 'rename'),
            duplicate_suffix_pattern=duplicate_handling.get('suffix_pattern', '_{n}')
        )
        
        # Validate the configuration
        errors = config.validate()
        if errors:
            raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
        
        return config
    
    @staticmethod
    def get_default_config() -> 'Config':
        """Get a default configuration with all standard categories and mappings."""
        return Config(
            downloads_folder=Config.get_default_downloads_folder(),
            organized_folder='organized',
            logs_folder='logs',
            categories={
                'Documents': ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'],
                'Images': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'],
                'Videos': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'],
                'Archives': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'],
                'Code': ['py', 'js', 'html', 'css', 'java', 'cpp', 'c', 'h'],
                'Installers': ['exe', 'msi', 'dmg', 'pkg', 'deb', 'rpm'],
                'Work': [],
                'Study': [],
                'Miscellaneous': []
            },
            system_file_patterns=['.tmp', '.part', '.DS_Store', '.crdownload'],
            ai_classifier_enabled=True,
            ai_prompt_template=(
                "Given the filename '{filename}', predict its purpose from these options: "
                "work, study, media, misc. Consider patterns like 'assignment', 'project', "
                "'report' for study; 'invoice', 'contract', 'meeting' for work. "
                "Respond with JSON: {{\"purpose\": \"<category>\", \"explanation\": \"<reason>\"}}"
            ),
            ambiguity_threshold=0.7,
            duplicate_handling_strategy='rename',
            duplicate_suffix_pattern='_{n}'
        )
    
    def validate(self) -> List[str]:
        """Validate the configuration and return a list of error messages.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Validate categories
        if not self.categories:
            errors.append("Configuration must include at least one category")
        
        if not isinstance(self.categories, dict):
            errors.append("Categories must be a dictionary")
        
        # Validate system file patterns
        if not isinstance(self.system_file_patterns, list):
            errors.append("System file patterns must be a list")
        
        # Validate ambiguity threshold
        if not isinstance(self.ambiguity_threshold, (int, float)):
            errors.append("Ambiguity threshold must be a number")
        elif not (0.0 <= self.ambiguity_threshold <= 1.0):
            errors.append("Ambiguity threshold must be between 0.0 and 1.0")
        
        # Validate AI prompt template
        if self.ai_classifier_enabled and not self.ai_prompt_template:
            errors.append("AI prompt template is required when AI classifier is enabled")
        
        # Validate folder names
        if not self.organized_folder:
            errors.append("Organized folder name cannot be empty")
        
        if not self.logs_folder:
            errors.append("Logs folder name cannot be empty")
        
        # Validate duplicate handling strategy
        valid_strategies = ['rename', 'skip', 'overwrite']
        if self.duplicate_handling_strategy not in valid_strategies:
            errors.append(f"Duplicate handling strategy must be one of: {', '.join(valid_strategies)}")
        
        return errors
    
    def get_category_folders(self) -> Dict[str, str]:
        """Get mapping of category names to folder names.
        
        Returns:
            Dictionary mapping category names to folder names
        """
        return {category: category for category in self.categories.keys()}
    
    def get_extension_mappings(self) -> Dict[str, str]:
        """Get mapping of file extensions to categories.
        
        Returns:
            Dictionary mapping extensions to category names
        """
        extension_map = {}
        for category, extensions in self.categories.items():
            for ext in extensions:
                extension_map[ext.lower()] = category
        return extension_map
    
    def get_ai_prompt_template(self) -> str:
        """Get the AI classifier prompt template.
        
        Returns:
            Prompt template string
        """
        return self.ai_prompt_template
    
    def get_downloads_folder(self) -> Path:
        """Get the Downloads folder path.
        
        Returns:
            Path to Downloads folder
        """
        return self.downloads_folder
