"""
Pydantic models for Gmail label consolidation system
"""
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field, validator
from datetime import datetime


class Label(BaseModel):
    """Represents a Gmail label"""
    original_name: str
    normalized_name: Optional[str] = None
    email_count: Optional[int] = 0
    sample_emails: Optional[List[str]] = Field(default_factory=list)
    
    @validator('original_name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Label name cannot be empty")
        return v


class LabelGroup(BaseModel):
    """Represents a group of similar labels"""
    group_id: str
    canonical_name: str
    original_labels: List[Label]
    similarity_score: float = Field(ge=0.0, le=1.0)
    total_email_count: int = 0
    
    @property
    def member_count(self) -> int:
        return len(self.original_labels)
    
    def add_label(self, label: Label):
        self.original_labels.append(label)
        self.total_email_count += label.email_count or 0


class ConsolidationConfig(BaseModel):
    """Configuration for label consolidation"""
    max_categories: int = Field(default=25, ge=1, le=100)
    similarity_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    use_content_analysis: bool = False
    normalization_aggressive: bool = True
    min_emails_for_content: int = Field(default=10, ge=1)
    clustering_method: str = Field(default="hierarchical", pattern="^(hierarchical|kmeans|dbscan)$")
    
    @validator('max_categories')
    def validate_max_categories(cls, v):
        if v < 1:
            raise ValueError("Must have at least 1 category")
        return v


class SimilarityMetrics(BaseModel):
    """Metrics for label similarity"""
    levenshtein_ratio: float = Field(ge=0.0, le=1.0)
    jaccard_ngram: float = Field(ge=0.0, le=1.0)
    semantic_similarity: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    @property
    def combined_score(self) -> float:
        scores = [self.levenshtein_ratio, self.jaccard_ngram]
        if self.semantic_similarity is not None:
            scores.append(self.semantic_similarity)
        return sum(scores) / len(scores)


class ConsolidationResult(BaseModel):
    """Result of label consolidation process"""
    original_count: int
    final_count: int
    consolidation_ratio: float
    label_groups: List[LabelGroup]
    mapping: Dict[str, str]  # original -> consolidated
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    config_used: ConsolidationConfig
    warnings: List[str] = Field(default_factory=list)
    
    @property
    def reduction_percentage(self) -> float:
        if self.original_count == 0:
            return 0.0
        return ((self.original_count - self.final_count) / self.original_count) * 100
    
    def get_consolidated_label(self, original: str) -> Optional[str]:
        return self.mapping.get(original)
    
    def get_group_for_label(self, original: str) -> Optional[LabelGroup]:
        consolidated = self.get_consolidated_label(original)
        if consolidated:
            for group in self.label_groups:
                if group.canonical_name == consolidated:
                    return group
        return None


class ConsolidationStats(BaseModel):
    """Statistics about the consolidation process"""
    total_labels_processed: int
    duplicate_labels_found: int
    semantic_groups_created: int
    forced_merges: int = 0
    processing_time_seconds: float
    similarity_distribution: Dict[str, int] = Field(default_factory=dict)
    largest_group_size: int
    smallest_group_size: int
    average_group_size: float
    
    def add_similarity_score(self, score: float):
        bucket = f"{int(score * 10) / 10:.1f}"
        self.similarity_distribution[bucket] = self.similarity_distribution.get(bucket, 0) + 1