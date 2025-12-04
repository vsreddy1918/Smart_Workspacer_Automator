"""Property-based tests for configuration system."""

import json
import tempfile
from pathlib import Path
from hypothesis import given, strategies as st, settings
import pytest

from config import Config


# Custom strategies for generating test data
@st.composite
def valid_config_dict(draw):
    """Generate a valid configuration dictionary with unique extensions per category."""
    # Generate a pool of unique extensions
    num_categories = draw(st.integers(min_value=1, max_value=10))
    num_extensions = draw(st.integers(min_value=num_categories, max_value=num_categories * 5))
    
    # Generate unique extensions
    all_extensions = []
    for i in range(num_extensions):
        ext = draw(st.text(min_size=2, max_size=5, alphabet=st.characters(whitelist_categories=('Ll',))))
        if ext not in all_extensions:
            all_extensions.append(ext)
    
    # Generate category names
    category_names = []
    for i in range(num_categories):
        name = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
        if name not in category_names:
            category_names.append(name)
    
    # Distribute extensions among categories (ensuring no duplicates)
    categories = {}
    extension_index = 0
    for category in category_names:
        # Each category gets 0-5 extensions
        num_exts_for_category = draw(st.integers(min_value=0, max_value=min(5, len(all_extensions) - extension_index)))
        category_extensions = all_extensions[extension_index:extension_index + num_exts_for_category]
        categories[category] = category_extensions
        extension_index += num_exts_for_category
    
    system_patterns = draw(st.lists(
        st.text(min_size=1, max_size=10),
        min_size=0,
        max_size=5
    ))
    
    threshold = draw(st.floats(min_value=0.0, max_value=1.0))
    
    prompt_template = draw(st.text(min_size=10, max_size=200))
    
    return {
        'downloads_folder': None,
        'organized_folder': 'organized',
        'logs_folder': 'logs',
        'categories': categories,
        'system_file_patterns': system_patterns,
        'ai_classifier': {
            'enabled': True,
            'prompt_template': prompt_template,
            'ambiguity_threshold': threshold
        },
        'duplicate_handling': {
            'strategy': 'rename',
            'suffix_pattern': '_{n}'
        }
    }


# Feature: smart-workspace-automator, Property 25: Configuration loading
# Validates: Requirements 8.1
@settings(max_examples=100)
@given(config_data=valid_config_dict())
def test_property_configuration_loading(config_data):
    """
    Property 25: Configuration loading
    For any valid configuration JSON file, the system should successfully load 
    folder paths, extension mappings, and category definitions.
    """
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        # Load the configuration
        config = Config.load_from_file(config_path)
        
        # Verify folder paths are loaded
        assert config.downloads_folder is not None
        assert config.organized_folder == config_data['organized_folder']
        assert config.logs_folder == config_data['logs_folder']
        
        # Verify categories are loaded
        assert config.categories == config_data['categories']
        
        # Verify extension mappings can be generated
        extension_mappings = config.get_extension_mappings()
        assert isinstance(extension_mappings, dict)
        
        # Verify all extensions from categories appear in mappings
        for category, extensions in config_data['categories'].items():
            for ext in extensions:
                assert ext.lower() in extension_mappings
                assert extension_mappings[ext.lower()] == category
        
    finally:
        # Clean up temp file
        Path(config_path).unlink()


# Feature: smart-workspace-automator, Property 26: AI prompt template loading
# Validates: Requirements 8.4
@settings(max_examples=100)
@given(
    prompt_template=st.text(min_size=10, max_size=500),
    enabled=st.booleans()
)
def test_property_ai_prompt_template_loading(prompt_template, enabled):
    """
    Property 26: AI prompt template loading
    For any configuration with a custom AI prompt template, the system should 
    load and use that template for AI classification.
    """
    config_data = {
        'downloads_folder': None,
        'organized_folder': 'organized',
        'logs_folder': 'logs',
        'categories': {'Documents': ['pdf'], 'Miscellaneous': []},
        'system_file_patterns': ['.tmp'],
        'ai_classifier': {
            'enabled': enabled,
            'prompt_template': prompt_template,
            'ambiguity_threshold': 0.7
        },
        'duplicate_handling': {
            'strategy': 'rename',
            'suffix_pattern': '_{n}'
        }
    }
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        # Load the configuration
        config = Config.load_from_file(config_path)
        
        # Verify AI prompt template is loaded correctly
        assert config.ai_prompt_template == prompt_template
        assert config.get_ai_prompt_template() == prompt_template
        assert config.ai_classifier_enabled == enabled
        
    finally:
        # Clean up temp file
        Path(config_path).unlink()


# Feature: smart-workspace-automator, Property 27: Configuration validation
# Validates: Requirements 8.5
@settings(max_examples=100)
@given(
    missing_field=st.sampled_from([
        'categories',
        'system_file_patterns',
        'ai_classifier',
        'organized_folder',
        'logs_folder'
    ])
)
def test_property_configuration_validation_missing_fields(missing_field):
    """
    Property 27: Configuration validation
    For any invalid configuration file (missing required fields, invalid JSON), 
    the system should report specific validation errors.
    """
    # Create a config with a missing required field
    config_data = {
        'downloads_folder': None,
        'organized_folder': 'organized',
        'logs_folder': 'logs',
        'categories': {'Documents': ['pdf']},
        'system_file_patterns': ['.tmp'],
        'ai_classifier': {
            'enabled': True,
            'prompt_template': 'test prompt',
            'ambiguity_threshold': 0.7
        },
        'duplicate_handling': {
            'strategy': 'rename',
            'suffix_pattern': '_{n}'
        }
    }
    
    # Remove the field to make config invalid
    if missing_field == 'ai_classifier':
        config_data['ai_classifier'] = {'enabled': True, 'prompt_template': '', 'ambiguity_threshold': 0.7}
    elif missing_field == 'organized_folder':
        config_data['organized_folder'] = ''
    elif missing_field == 'logs_folder':
        config_data['logs_folder'] = ''
    elif missing_field == 'categories':
        config_data['categories'] = {}
    elif missing_field == 'system_file_patterns':
        config_data['system_file_patterns'] = 'not a list'
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        # Attempt to load the configuration - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            Config.load_from_file(config_path)
        
        # Verify that the error message mentions validation failure
        assert 'validation failed' in str(exc_info.value).lower()
        
    finally:
        # Clean up temp file
        Path(config_path).unlink()


@settings(max_examples=100)
@given(threshold=st.floats(min_value=-10.0, max_value=10.0).filter(lambda x: x < 0.0 or x > 1.0))
def test_property_configuration_validation_invalid_threshold(threshold):
    """
    Property 27: Configuration validation (invalid threshold)
    For any configuration with an invalid ambiguity threshold, 
    the system should report validation errors.
    """
    config_data = {
        'downloads_folder': None,
        'organized_folder': 'organized',
        'logs_folder': 'logs',
        'categories': {'Documents': ['pdf']},
        'system_file_patterns': ['.tmp'],
        'ai_classifier': {
            'enabled': True,
            'prompt_template': 'test prompt',
            'ambiguity_threshold': threshold
        },
        'duplicate_handling': {
            'strategy': 'rename',
            'suffix_pattern': '_{n}'
        }
    }
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        # Attempt to load the configuration - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            Config.load_from_file(config_path)
        
        # Verify that the error message mentions validation failure
        assert 'validation failed' in str(exc_info.value).lower()
        
    finally:
        # Clean up temp file
        Path(config_path).unlink()


@settings(max_examples=100)
@given(strategy=st.text(min_size=1, max_size=20).filter(lambda x: x not in ['rename', 'skip', 'overwrite']))
def test_property_configuration_validation_invalid_strategy(strategy):
    """
    Property 27: Configuration validation (invalid duplicate handling strategy)
    For any configuration with an invalid duplicate handling strategy, 
    the system should report validation errors.
    """
    config_data = {
        'downloads_folder': None,
        'organized_folder': 'organized',
        'logs_folder': 'logs',
        'categories': {'Documents': ['pdf']},
        'system_file_patterns': ['.tmp'],
        'ai_classifier': {
            'enabled': True,
            'prompt_template': 'test prompt',
            'ambiguity_threshold': 0.7
        },
        'duplicate_handling': {
            'strategy': strategy,
            'suffix_pattern': '_{n}'
        }
    }
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        config_path = f.name
    
    try:
        # Attempt to load the configuration - should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            Config.load_from_file(config_path)
        
        # Verify that the error message mentions validation failure
        assert 'validation failed' in str(exc_info.value).lower()
        
    finally:
        # Clean up temp file
        Path(config_path).unlink()


def test_property_configuration_validation_invalid_json():
    """
    Property 27: Configuration validation (invalid JSON)
    For any configuration file with invalid JSON syntax, 
    the system should raise a JSONDecodeError.
    """
    # Create a temporary config file with invalid JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write('{ invalid json content }')
        config_path = f.name
    
    try:
        # Attempt to load the configuration - should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            Config.load_from_file(config_path)
        
    finally:
        # Clean up temp file
        Path(config_path).unlink()


def test_default_config_is_valid():
    """Test that the default configuration is valid."""
    config = Config.get_default_config()
    errors = config.validate()
    assert len(errors) == 0, f"Default config has validation errors: {errors}"


def test_config_json_file_is_valid():
    """Test that the provided config.json file is valid."""
    config = Config.load_from_file('config.json')
    errors = config.validate()
    assert len(errors) == 0, f"config.json has validation errors: {errors}"
