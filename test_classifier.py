"""Property-based and unit tests for classification engine."""

import pytest
from pathlib import Path
from datetime import datetime
from hypothesis import given, strategies as st, settings

from classifier import ClassificationResult, RuleBasedClassifier, AIClassifier, ClassificationEngine
from scanner import FileMetadata
from config import Config


# Hypothesis strategies for generating test data

@st.composite
def file_metadata_strategy(draw, extension=None, name=None):
    """Generate random FileMetadata objects."""
    if name is None:
        name = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), 
            whitelist_characters='_-. '
        )))
    
    if extension is None:
        extension = draw(st.text(min_size=0, max_size=10, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd')
        )))
    
    # Add extension to name if provided
    if extension:
        full_name = f"{name}.{extension}"
    else:
        full_name = name
    
    return FileMetadata(
        path=Path(f"/test/{full_name}"),
        name=full_name,
        extension=extension.lower() if extension else '',
        mime_type=draw(st.sampled_from([
            'application/pdf', 'image/jpeg', 'video/mp4', 
            'application/zip', 'text/plain', 'application/octet-stream'
        ])),
        size=draw(st.integers(min_value=0, max_value=1000000)),
        modified_time=datetime.now(),
        is_hidden=False
    )


@st.composite
def known_extension_metadata_strategy(draw, config):
    """Generate FileMetadata with known extensions from config."""
    extension_map = config.get_extension_mappings()
    extension = draw(st.sampled_from(list(extension_map.keys())))
    
    name = draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )))
    
    # Build the full name with extension
    full_name = f"{name}.{extension}"
    
    return FileMetadata(
        path=Path(f"/test/{full_name}"),
        name=full_name,
        extension=extension.lower(),
        mime_type=draw(st.sampled_from([
            'application/pdf', 'image/jpeg', 'video/mp4', 
            'application/zip', 'text/plain', 'application/octet-stream'
        ])),
        size=draw(st.integers(min_value=0, max_value=1000000)),
        modified_time=datetime.now(),
        is_hidden=False
    )


# Property 4: Known extension classification
# Feature: smart-workspace-automator, Property 4: Known extension classification
@settings(max_examples=100)
@given(st.data())
def test_property_known_extension_classification(data):
    """
    Property 4: Known extension classification
    For any file with a known extension (e.g., .pdf, .jpg, .zip), 
    rule-based classification should assign the correct category with high confidence (>0.7)
    
    Validates: Requirements 2.2
    """
    config = Config.get_default_config()
    extension_map = config.get_extension_mappings()
    classifier = RuleBasedClassifier(extension_map)
    
    # Generate metadata with a known extension
    metadata = data.draw(known_extension_metadata_strategy(config))
    
    # Classify the file
    result = classifier.classify(metadata)
    
    # Verify high confidence
    assert result.confidence > 0.7, \
        f"Known extension '{metadata.extension}' should have confidence > 0.7, got {result.confidence}"
    
    # Verify correct category mapping
    expected_category = extension_map[metadata.extension.lower()]
    assert result.category == expected_category, \
        f"Extension '{metadata.extension}' should map to '{expected_category}', got '{result.category}'"
    
    # Verify method is rule-based
    assert result.method == "rule-based", \
        f"Classification method should be 'rule-based', got '{result.method}'"


# Property 5: Ambiguous file AI invocation
# Feature: smart-workspace-automator, Property 5: Ambiguous file AI invocation
@settings(max_examples=100)
@given(st.data())
def test_property_ambiguous_file_ai_invocation(data):
    """
    Property 5: Ambiguous file AI invocation
    For any file with low rule-based confidence (<0.7), 
    the classification engine should invoke the AI classifier
    
    Validates: Requirements 2.3
    """
    config = Config.get_default_config()
    engine = ClassificationEngine(config)
    
    # Generate metadata with unknown extension (will have low confidence)
    unknown_ext = data.draw(st.text(min_size=3, max_size=10, alphabet='xyz'))
    name = data.draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )))
    
    metadata = FileMetadata(
        path=Path(f"/test/{name}.{unknown_ext}"),
        name=f"{name}.{unknown_ext}",
        extension=unknown_ext,
        mime_type='application/octet-stream',
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    # Get rule-based result first
    rule_result = engine.rule_classifier.classify(metadata)
    
    # If rule-based confidence is low, verify AI is invoked
    if rule_result.confidence < config.ambiguity_threshold:
        # Classify with full engine
        final_result = engine.classify(metadata)
        
        # Verify that AI was involved (method should be 'merged' or result differs from rule-based)
        assert final_result.method == 'merged' or final_result.method == 'ai', \
            f"Low confidence file should invoke AI, but method was '{final_result.method}'"


# Property 6: AI classifier interface
# Feature: smart-workspace-automator, Property 6: AI classifier interface
@settings(max_examples=100)
@given(file_metadata_strategy())
def test_property_ai_classifier_interface(metadata):
    """
    Property 6: AI classifier interface
    For any AI classification request, the classifier should receive the filename 
    and return both a purpose prediction and an explanation
    
    Validates: Requirements 2.4
    """
    config = Config.get_default_config()
    ai_classifier = AIClassifier(config.get_ai_prompt_template())
    
    # Classify the file
    result = ai_classifier.classify(metadata)
    
    # Verify result has a category
    assert result.category is not None and result.category != '', \
        "AI classifier should return a category"
    
    # Verify result has an explanation
    assert result.explanation is not None and result.explanation != '', \
        "AI classifier should return an explanation"
    
    # Verify method is 'ai'
    assert result.method == 'ai', \
        f"AI classifier method should be 'ai', got '{result.method}'"
    
    # Verify confidence is between 0 and 1
    assert 0.0 <= result.confidence <= 1.0, \
        f"Confidence should be between 0 and 1, got {result.confidence}"


# Property 7: Classification merge produces result
# Feature: smart-workspace-automator, Property 7: Classification merge produces result
@settings(max_examples=100)
@given(file_metadata_strategy())
def test_property_classification_merge_produces_result(metadata):
    """
    Property 7: Classification merge produces result
    For any file with both rule-based and AI classifications, 
    the merge operation should produce a single final category
    
    Validates: Requirements 2.5
    """
    config = Config.get_default_config()
    engine = ClassificationEngine(config)
    
    # Get both classifications
    rule_result = engine.rule_classifier.classify(metadata)
    ai_result = engine.ai_classifier.classify(metadata)
    
    # Merge them
    merged_result = engine._merge_classifications(rule_result, ai_result)
    
    # Verify merged result has a single category
    assert merged_result.category is not None and merged_result.category != '', \
        "Merged result should have a category"
    
    # Verify method is 'merged'
    assert merged_result.method == 'merged', \
        f"Merged result method should be 'merged', got '{merged_result.method}'"
    
    # Verify the category is one of the two input categories
    assert merged_result.category in [rule_result.category, ai_result.category], \
        f"Merged category should be from one of the inputs, got '{merged_result.category}'"
    
    # Verify confidence is from one of the inputs
    assert merged_result.confidence in [rule_result.confidence, ai_result.confidence], \
        f"Merged confidence should be from one of the inputs"


# Property 8: Document file categorization
# Feature: smart-workspace-automator, Property 8: Document file categorization
@settings(max_examples=100)
@given(st.data())
def test_property_document_file_categorization(data):
    """
    Property 8: Document file categorization
    For any file classified as a document type (.pdf, .doc, .docx, .txt), 
    the system should assign it to the Documents category
    
    Validates: Requirements 3.2
    """
    config = Config.get_default_config()
    engine = ClassificationEngine(config)
    
    # Generate metadata with document extension
    doc_extensions = ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']
    extension = data.draw(st.sampled_from(doc_extensions))
    
    name = data.draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )))
    
    metadata = FileMetadata(
        path=Path(f"/test/{name}.{extension}"),
        name=f"{name}.{extension}",
        extension=extension,
        mime_type='application/pdf' if extension == 'pdf' else 'application/msword',
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    # Classify the file
    result = engine.classify(metadata)
    
    # Verify it's categorized as Documents
    assert result.category == 'Documents', \
        f"Document file with extension '.{extension}' should be categorized as 'Documents', got '{result.category}'"


# Property 9: Media file categorization
# Feature: smart-workspace-automator, Property 9: Media file categorization
@settings(max_examples=100)
@given(st.data())
def test_property_media_file_categorization(data):
    """
    Property 9: Media file categorization
    For any file classified as media content, the system should assign it 
    to either Images or Videos category based on the media type
    
    Validates: Requirements 3.3
    """
    config = Config.get_default_config()
    engine = ClassificationEngine(config)
    
    # Generate metadata with media extension
    media_data = [
        (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'], 'Images', 'image/jpeg'),
        (['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm'], 'Videos', 'video/mp4')
    ]
    
    extensions, expected_category, mime_type = data.draw(st.sampled_from(media_data))
    extension = data.draw(st.sampled_from(extensions))
    
    name = data.draw(st.text(min_size=1, max_size=30, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_-'
    )))
    
    metadata = FileMetadata(
        path=Path(f"/test/{name}.{extension}"),
        name=f"{name}.{extension}",
        extension=extension,
        mime_type=mime_type,
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    # Classify the file
    result = engine.classify(metadata)
    
    # Verify it's categorized correctly
    assert result.category == expected_category, \
        f"Media file with extension '.{extension}' should be categorized as '{expected_category}', got '{result.category}'"


# Property 10: Purpose-based categorization
# Feature: smart-workspace-automator, Property 10: Purpose-based categorization
@settings(max_examples=100)
@given(st.data())
def test_property_purpose_based_categorization(data):
    """
    Property 10: Purpose-based categorization
    For any file classified by purpose (work/study keywords), 
    the system should assign it to the appropriate purpose category (Work, Study, or Miscellaneous)
    
    Validates: Requirements 3.4
    """
    config = Config.get_default_config()
    ai_classifier = AIClassifier(config.get_ai_prompt_template())
    
    # Test with study keywords
    study_keywords = ['assignment', 'homework', 'lecture', 'exam', 'course']
    study_keyword = data.draw(st.sampled_from(study_keywords))
    
    study_name = f"{study_keyword}_final.pdf"
    study_metadata = FileMetadata(
        path=Path(f"/test/{study_name}"),
        name=study_name,
        extension='pdf',
        mime_type='application/pdf',
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    study_result = ai_classifier.classify(study_metadata)
    assert study_result.category == 'Study', \
        f"File with '{study_keyword}' should be categorized as 'Study', got '{study_result.category}'"
    
    # Test with work keywords
    work_keywords = ['invoice', 'contract', 'meeting', 'report', 'business']
    work_keyword = data.draw(st.sampled_from(work_keywords))
    
    work_name = f"{work_keyword}_2024.pdf"
    work_metadata = FileMetadata(
        path=Path(f"/test/{work_name}"),
        name=work_name,
        extension='pdf',
        mime_type='application/pdf',
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    work_result = ai_classifier.classify(work_metadata)
    assert work_result.category == 'Work', \
        f"File with '{work_keyword}' should be categorized as 'Work', got '{work_result.category}'"


# Property 11: Low confidence fallback
# Feature: smart-workspace-automator, Property 11: Low confidence fallback
@settings(max_examples=100)
@given(file_metadata_strategy())
def test_property_low_confidence_fallback(metadata):
    """
    Property 11: Low confidence fallback
    For any file that cannot be confidently classified (confidence <0.5), 
    the system should assign it to the Miscellaneous category
    
    Validates: Requirements 3.5
    """
    config = Config.get_default_config()
    engine = ClassificationEngine(config)
    
    # Classify the file
    result = engine.classify(metadata)
    
    # If confidence is low, verify it's in Miscellaneous
    if result.confidence < 0.5:
        assert result.category == 'Miscellaneous', \
            f"Low confidence file (confidence={result.confidence}) should be in 'Miscellaneous', got '{result.category}'"


# Unit tests for specific examples

def test_pdf_extension_maps_to_documents():
    """Test that PDF files are classified as Documents."""
    config = Config.get_default_config()
    classifier = RuleBasedClassifier(config.get_extension_mappings())
    
    metadata = FileMetadata(
        path=Path("/test/report.pdf"),
        name="report.pdf",
        extension="pdf",
        mime_type="application/pdf",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    result = classifier.classify(metadata)
    
    assert result.category == "Documents"
    assert result.confidence == 1.0
    assert result.method == "rule-based"


def test_jpg_extension_maps_to_images():
    """Test that JPG files are classified as Images."""
    config = Config.get_default_config()
    classifier = RuleBasedClassifier(config.get_extension_mappings())
    
    metadata = FileMetadata(
        path=Path("/test/photo.jpg"),
        name="photo.jpg",
        extension="jpg",
        mime_type="image/jpeg",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    result = classifier.classify(metadata)
    
    assert result.category == "Images"
    assert result.confidence == 1.0


def test_assignment_keyword_detected_as_study():
    """Test that files with 'assignment' keyword are classified as Study."""
    config = Config.get_default_config()
    ai_classifier = AIClassifier(config.get_ai_prompt_template())
    
    metadata = FileMetadata(
        path=Path("/test/assignment_final.pdf"),
        name="assignment_final.pdf",
        extension="pdf",
        mime_type="application/pdf",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    result = ai_classifier.classify(metadata)
    
    assert result.category == "Study"
    assert result.method == "ai"
    assert "assignment" in result.explanation.lower()


def test_invoice_keyword_detected_as_work():
    """Test that files with 'invoice' keyword are classified as Work."""
    config = Config.get_default_config()
    ai_classifier = AIClassifier(config.get_ai_prompt_template())
    
    metadata = FileMetadata(
        path=Path("/test/invoice_2024.pdf"),
        name="invoice_2024.pdf",
        extension="pdf",
        mime_type="application/pdf",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    result = ai_classifier.classify(metadata)
    
    assert result.category == "Work"
    assert result.method == "ai"
    assert "invoice" in result.explanation.lower()


def test_unknown_extension_low_confidence():
    """Test that unknown extensions result in low confidence."""
    config = Config.get_default_config()
    classifier = RuleBasedClassifier(config.get_extension_mappings())
    
    metadata = FileMetadata(
        path=Path("/test/file.xyz"),
        name="file.xyz",
        extension="xyz",
        mime_type="application/octet-stream",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    result = classifier.classify(metadata)
    
    assert result.confidence < 0.7
    assert result.category == "Miscellaneous"


def test_classification_engine_hybrid_workflow():
    """Test the complete hybrid classification workflow."""
    config = Config.get_default_config()
    engine = ClassificationEngine(config)
    
    # Test with known extension (should use rule-based only)
    pdf_metadata = FileMetadata(
        path=Path("/test/document.pdf"),
        name="document.pdf",
        extension="pdf",
        mime_type="application/pdf",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    pdf_result = engine.classify(pdf_metadata)
    assert pdf_result.category == "Documents"
    assert pdf_result.method == "rule-based"
    
    # Test with unknown extension but study keyword (should use AI)
    assignment_metadata = FileMetadata(
        path=Path("/test/assignment.xyz"),
        name="assignment.xyz",
        extension="xyz",
        mime_type="application/octet-stream",
        size=1000,
        modified_time=datetime.now(),
        is_hidden=False
    )
    
    assignment_result = engine.classify(assignment_metadata)
    assert assignment_result.category == "Study"
    assert assignment_result.method == "merged"
