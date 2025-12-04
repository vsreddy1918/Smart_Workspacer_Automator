"""Classification engine for Smart Workspace Automator."""

import json
import re
from dataclasses import dataclass
from typing import Optional

from config import Config
from scanner import FileMetadata


@dataclass
class ClassificationResult:
    """Result of file classification."""
    
    category: str
    confidence: float  # 0.0 to 1.0
    method: str  # "rule-based" or "ai" or "merged"
    explanation: str


class RuleBasedClassifier:
    """Classifies files based on extension and MIME type rules."""
    
    def __init__(self, extension_mappings: dict[str, str]):
        """Initialize with extension to category mappings.
        
        Args:
            extension_mappings: Dictionary mapping extensions to categories
        """
        self.extension_mappings = extension_mappings
    
    def classify(self, metadata: FileMetadata) -> ClassificationResult:
        """Classify file based on extension and MIME type.
        
        Args:
            metadata: File metadata
            
        Returns:
            ClassificationResult with category and confidence
        """
        # Try to classify by extension
        if metadata.extension and metadata.extension.lower() in self.extension_mappings:
            category = self.extension_mappings[metadata.extension.lower()]
            return ClassificationResult(
                category=category,
                confidence=1.0,
                method="rule-based",
                explanation=f"File extension '.{metadata.extension}' maps to {category}"
            )
        
        # Try to classify by MIME type
        mime_category = self._classify_by_mime(metadata.mime_type)
        if mime_category:
            return ClassificationResult(
                category=mime_category,
                confidence=0.8,
                method="rule-based",
                explanation=f"MIME type '{metadata.mime_type}' indicates {mime_category}"
            )
        
        # Unknown file type
        return ClassificationResult(
            category="Miscellaneous",
            confidence=0.3,
            method="rule-based",
            explanation="Unknown file type"
        )
    
    def _classify_by_mime(self, mime_type: str) -> Optional[str]:
        """Classify based on MIME type.
        
        Args:
            mime_type: MIME type string
            
        Returns:
            Category name or None if cannot classify
        """
        if mime_type.startswith('image/'):
            return 'Images'
        elif mime_type.startswith('video/'):
            return 'Videos'
        elif mime_type.startswith('text/'):
            return 'Documents'
        elif mime_type in ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return 'Documents'
        elif mime_type in ['application/zip', 'application/x-rar-compressed',
                          'application/x-7z-compressed', 'application/x-tar',
                          'application/gzip', 'application/x-bzip2']:
            return 'Archives'
        
        return None


class AIClassifier:
    """Classifies files using AI reasoning with keyword-based heuristics."""
    
    def __init__(self, prompt_template: str):
        """Initialize with AI prompt template.
        
        Args:
            prompt_template: Template for AI prompts
        """
        self.prompt_template = prompt_template
    
    def classify(self, metadata: FileMetadata) -> ClassificationResult:
        """Classify file using AI reasoning (keyword-based heuristics).
        
        Args:
            metadata: File metadata
            
        Returns:
            ClassificationResult with AI prediction
        """
        filename_lower = metadata.name.lower()
        
        # Study-related keywords
        study_keywords = ['assignment', 'homework', 'lecture', 'notes', 'study', 
                         'exam', 'quiz', 'course', 'class', 'tutorial', 'lab',
                         'project', 'thesis', 'dissertation', 'research']
        
        # Work-related keywords
        work_keywords = ['invoice', 'contract', 'meeting', 'report', 'proposal',
                        'presentation', 'budget', 'financial', 'business', 'client',
                        'memo', 'agenda', 'minutes', 'quarterly', 'annual']
        
        # Check for study keywords
        for keyword in study_keywords:
            if keyword in filename_lower:
                return ClassificationResult(
                    category='Study',
                    confidence=0.85,
                    method='ai',
                    explanation=f"Filename contains '{keyword}' indicating academic work"
                )
        
        # Check for work keywords
        for keyword in work_keywords:
            if keyword in filename_lower:
                return ClassificationResult(
                    category='Work',
                    confidence=0.85,
                    method='ai',
                    explanation=f"Filename contains '{keyword}' indicating work-related content"
                )
        
        # Default to Miscellaneous with low confidence
        return ClassificationResult(
            category='Miscellaneous',
            confidence=0.4,
            method='ai',
            explanation="No clear purpose indicators found in filename"
        )
    
    def is_ambiguous(self, metadata: FileMetadata, rule_result: ClassificationResult, 
                     threshold: float) -> bool:
        """Determine if file needs AI classification.
        
        Args:
            metadata: File metadata
            rule_result: Result from rule-based classifier
            threshold: Confidence threshold for ambiguity
            
        Returns:
            True if file should be classified by AI
        """
        return rule_result.confidence < threshold


class ClassificationEngine:
    """Hybrid classification engine combining rule-based and AI approaches."""
    
    def __init__(self, config: Config):
        """Initialize with both classifiers.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.rule_classifier = RuleBasedClassifier(config.get_extension_mappings())
        self.ai_classifier = AIClassifier(config.get_ai_prompt_template())
        self.ambiguity_threshold = config.ambiguity_threshold
        self.ai_enabled = config.ai_classifier_enabled
    
    def classify(self, metadata: FileMetadata) -> ClassificationResult:
        """Apply hybrid classification and return final result.
        
        Args:
            metadata: File metadata
            
        Returns:
            Final ClassificationResult
        """
        # First, apply rule-based classification
        rule_result = self.rule_classifier.classify(metadata)
        
        # Check if AI classification is needed
        if self.ai_enabled and self.ai_classifier.is_ambiguous(
            metadata, rule_result, self.ambiguity_threshold
        ):
            # Get AI classification
            ai_result = self.ai_classifier.classify(metadata)
            
            # Merge the results
            return self._merge_classifications(rule_result, ai_result)
        
        # Return rule-based result if confidence is high enough
        return rule_result
    
    def _merge_classifications(self, rule_result: ClassificationResult, 
                              ai_result: ClassificationResult) -> ClassificationResult:
        """Merge rule-based and AI classification results.
        
        Args:
            rule_result: Result from rule-based classifier
            ai_result: Result from AI classifier
            
        Returns:
            Merged ClassificationResult
        """
        # If AI has higher confidence, use AI result
        if ai_result.confidence > rule_result.confidence:
            return ClassificationResult(
                category=ai_result.category,
                confidence=ai_result.confidence,
                method='merged',
                explanation=f"AI classification (confidence {ai_result.confidence:.2f}): {ai_result.explanation}"
            )
        
        # Otherwise, use rule-based result
        return ClassificationResult(
            category=rule_result.category,
            confidence=rule_result.confidence,
            method='merged',
            explanation=f"Rule-based classification (confidence {rule_result.confidence:.2f}): {rule_result.explanation}"
        )
