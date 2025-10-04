"""
Gmail Label Consolidation Service
Core logic for consolidating Gmail labels into a maximum number of categories
"""
import re
import logging
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

from .models import (
    Label, LabelGroup, ConsolidationConfig, 
    ConsolidationResult, SimilarityMetrics,
    ConsolidationStats
)

logger = logging.getLogger(__name__)


class LabelConsolidationService:
    """Service for consolidating Gmail labels into categories"""
    
    def __init__(self, config: Optional[ConsolidationConfig] = None):
        self.config = config or ConsolidationConfig()
        self.stats = None
        
    def normalize_label(self, label: str) -> str:
        """
        Normalize a label for comparison
        - Convert to lowercase
        - Remove trailing punctuation
        - Remove extra whitespace
        - Remove special characters
        """
        if not label:
            return ""

        # Convert to lowercase
        normalized = label.lower()

        # Remove leading/trailing whitespace
        normalized = normalized.strip()

        # Remove trailing punctuation
        normalized = re.sub(r'[.,;:!?\-_\s]+$', '', normalized)

        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)

        if self.config.normalization_aggressive:
            # Remove all special characters, keep only alphanumeric and spaces
            normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
            # Collapse multiple spaces again (removing chars can create new double spaces)
            normalized = re.sub(r'\s+', ' ', normalized)

        return normalized.strip()
    
    def calculate_levenshtein_similarity(self, str1: str, str2: str) -> float:
        """Calculate normalized Levenshtein similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1, str2).ratio()
    
    def calculate_jaccard_ngram_similarity(self, str1: str, str2: str, n: int = 3) -> float:
        """Calculate Jaccard similarity based on character n-grams"""
        if not str1 or not str2:
            return 0.0
            
        # Handle strings shorter than n
        if len(str1) < n or len(str2) < n:
            return self.calculate_levenshtein_similarity(str1, str2)
        
        # Generate n-grams
        ngrams1 = set([str1[i:i+n] for i in range(len(str1)-n+1)])
        ngrams2 = set([str2[i:i+n] for i in range(len(str2)-n+1)])
        
        if not ngrams1 or not ngrams2:
            return 0.0
        
        intersection = ngrams1.intersection(ngrams2)
        union = ngrams1.union(ngrams2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def calculate_similarity(self, label1: str, label2: str) -> SimilarityMetrics:
        """Calculate multiple similarity metrics between two labels"""
        norm1 = self.normalize_label(label1)
        norm2 = self.normalize_label(label2)
        
        # If normalized forms are identical, perfect match
        if norm1 == norm2:
            return SimilarityMetrics(
                levenshtein_ratio=1.0,
                jaccard_ngram=1.0,
                semantic_similarity=1.0
            )
        
        levenshtein = self.calculate_levenshtein_similarity(norm1, norm2)
        jaccard = self.calculate_jaccard_ngram_similarity(norm1, norm2)
        
        return SimilarityMetrics(
            levenshtein_ratio=levenshtein,
            jaccard_ngram=jaccard
        )
    
    def build_similarity_matrix(self, labels: List[str]) -> np.ndarray:
        """Build a similarity matrix for all labels"""
        n = len(labels)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            matrix[i, i] = 1.0  # Self-similarity
            for j in range(i + 1, n):
                metrics = self.calculate_similarity(labels[i], labels[j])
                similarity = metrics.combined_score
                matrix[i, j] = similarity
                matrix[j, i] = similarity
                
        return matrix
    
    def _extract_common_terms(self, label: str) -> Set[str]:
        """Extract all significant terms from a label (words >= 3 chars)"""
        normalized = self.normalize_label(label)
        words = normalized.split()
        # Return all words that are at least 3 characters
        return set(w for w in words if len(w) >= 3)

    def _extract_common_term(self, label: str) -> str:
        """Extract the most significant term from a label"""
        normalized = self.normalize_label(label)
        words = normalized.split()

        if not words:
            return normalized

        # Return the longest meaningful word (>= 3 chars)
        meaningful_words = [w for w in words if len(w) >= 3]
        if meaningful_words:
            return max(meaningful_words, key=len)

        # Fallback to longest word or normalized label
        return max(words, key=len) if words else normalized

    def group_similar_labels(self, labels: List[str]) -> List[LabelGroup]:
        """Group labels based on string similarity using graph-based clustering"""
        if not labels:
            return []

        normalized_map = {label: self.normalize_label(label) for label in labels}

        # Group by exact normalized match first
        exact_groups = defaultdict(list)
        for label, normalized in normalized_map.items():
            exact_groups[normalized].append(label)

        # Create initial groups from exact matches
        groups = []
        group_id = 0

        for normalized, original_labels in exact_groups.items():
            if len(original_labels) > 1:
                # Multiple labels normalize to the same thing
                group = LabelGroup(
                    group_id=f"group_{group_id}",
                    canonical_name=self._select_canonical_name(original_labels),
                    original_labels=[Label(original_name=label) for label in original_labels],
                    similarity_score=1.0
                )
                groups.append(group)
                group_id += 1
            else:
                # Single label, check for fuzzy matches with other singles
                label = original_labels[0]

                # Extract all significant terms from this label
                label_terms = self._extract_common_terms(label)

                # Check similarity with existing groups
                best_match = None
                best_score = 0.0

                for group in groups:
                    # Check similarity against group's canonical name
                    metrics = self.calculate_similarity(label, group.canonical_name)
                    score = metrics.combined_score

                    # Also check if labels share any common terms
                    group_terms = self._extract_common_terms(group.canonical_name)
                    common_terms = label_terms.intersection(group_terms)

                    # Also check for substring/containment matches
                    # (e.g., "work" in "workrelated" or vice versa)
                    contains_match = False
                    for label_term in label_terms:
                        for group_term in group_terms:
                            if len(label_term) >= 4 and len(group_term) >= 4:
                                if label_term in group_term or group_term in label_term:
                                    contains_match = True
                                    break
                        if contains_match:
                            break

                    if common_terms or contains_match:
                        # Strong match if they share any significant term or have substring match
                        score = max(score, 0.9)

                    if score >= self.config.similarity_threshold and score > best_score:
                        best_match = group
                        best_score = score

                if best_match:
                    best_match.add_label(Label(original_name=label))
                else:
                    # Create new group
                    group = LabelGroup(
                        group_id=f"group_{group_id}",
                        canonical_name=label,
                        original_labels=[Label(original_name=label)],
                        similarity_score=1.0
                    )
                    groups.append(group)
                    group_id += 1

        return groups
    
    def _select_canonical_name(self, labels: List[str]) -> str:
        """Select the best canonical name from a list of similar labels"""
        if not labels:
            return ""
        
        # Strategy 1: Choose the most common form
        counter = Counter(labels)
        most_common = counter.most_common(1)[0][0]
        
        # Strategy 2: If all equally common, choose the shortest
        if len(set(counter.values())) == 1:
            return min(labels, key=len)
        
        return most_common
    
    def hierarchical_consolidation(self, groups: List[LabelGroup], target_count: int) -> List[LabelGroup]:
        """Use hierarchical clustering to consolidate groups to target count"""
        if len(groups) <= target_count:
            return groups
        
        # Extract features (using canonical names for now)
        canonical_names = [g.canonical_name for g in groups]
        
        # Build similarity matrix
        similarity_matrix = self.build_similarity_matrix(canonical_names)
        
        # Convert similarity to distance
        distance_matrix = 1 - similarity_matrix
        
        # Perform hierarchical clustering
        condensed_dist = squareform(distance_matrix)
        linkage_matrix = linkage(condensed_dist, method='ward')
        
        # Cut tree to get target number of clusters
        cluster_labels = fcluster(linkage_matrix, target_count, criterion='maxclust')
        
        # Reorganize groups based on clustering
        new_groups = defaultdict(list)
        for i, cluster_id in enumerate(cluster_labels):
            new_groups[cluster_id].append(groups[i])
        
        # Create consolidated groups
        consolidated = []
        for cluster_id, cluster_groups in new_groups.items():
            # Merge all labels from cluster groups
            all_labels = []
            for g in cluster_groups:
                all_labels.extend(g.original_labels)
            
            # Select canonical name (from most populous group)
            largest_group = max(cluster_groups, key=lambda g: g.member_count)
            
            consolidated_group = LabelGroup(
                group_id=f"consolidated_{cluster_id}",
                canonical_name=largest_group.canonical_name,
                original_labels=all_labels,
                similarity_score=0.7  # Lower score for consolidated groups
            )
            consolidated.append(consolidated_group)
        
        return consolidated
    
    def force_consolidate_to_limit(self, groups: List[LabelGroup]) -> List[LabelGroup]:
        """Force consolidation to meet the maximum category limit"""
        if len(groups) <= self.config.max_categories:
            return groups
        
        # Sort by member count (keep larger groups)
        sorted_groups = sorted(groups, key=lambda g: g.member_count, reverse=True)
        
        # Keep top groups up to limit
        keep_groups = sorted_groups[:self.config.max_categories - 1]
        merge_groups = sorted_groups[self.config.max_categories - 1:]
        
        # Create an "Other" category for remaining groups
        all_other_labels = []
        for g in merge_groups:
            all_other_labels.extend(g.original_labels)
        
        other_group = LabelGroup(
            group_id="group_other",
            canonical_name="other",
            original_labels=all_other_labels,
            similarity_score=0.5
        )
        
        keep_groups.append(other_group)
        return keep_groups
    
    def generate_meaningful_names(self, groups: List[LabelGroup]) -> List[LabelGroup]:
        """Generate meaningful names for consolidated groups"""
        for group in groups:
            if group.canonical_name == "other":
                continue
                
            # Extract common terms from member labels
            all_terms = []
            for label in group.original_labels:
                terms = self.normalize_label(label.original_name).split()
                all_terms.extend(terms)
            
            # Find most common term
            if all_terms:
                term_counter = Counter(all_terms)
                most_common_term = term_counter.most_common(1)[0][0]
                
                # Use most common term if it's meaningful
                if len(most_common_term) > 2:  # Skip very short terms
                    group.canonical_name = most_common_term
        
        return groups
    
    def consolidate(self, labels: List[str]) -> ConsolidationResult:
        """Main consolidation pipeline"""
        import time
        start_time = time.time()
        
        # Initialize stats
        self.stats = ConsolidationStats(
            total_labels_processed=len(labels),
            duplicate_labels_found=0,
            semantic_groups_created=0,
            processing_time_seconds=0,
            largest_group_size=0,
            smallest_group_size=0,
            average_group_size=0
        )
        
        # Remove empty labels
        labels = [l for l in labels if l and l.strip()]
        
        if not labels:
            return ConsolidationResult(
                original_count=0,
                final_count=0,
                consolidation_ratio=0.0,
                label_groups=[],
                mapping={},
                config_used=self.config,
                warnings=["No valid labels provided"]
            )
        
        logger.info(f"Starting consolidation of {len(labels)} labels")
        
        # Phase 1: String-based deduplication
        groups = self.group_similar_labels(labels)
        logger.info(f"Phase 1 complete: {len(groups)} groups created")
        
        # Count duplicates
        for group in groups:
            if group.member_count > 1:
                self.stats.duplicate_labels_found += group.member_count - 1
        
        # Phase 2: Hierarchical consolidation if needed
        if len(groups) > self.config.max_categories:
            logger.info(f"Phase 2: Consolidating {len(groups)} groups to {self.config.max_categories}")
            groups = self.hierarchical_consolidation(groups, self.config.max_categories)
            self.stats.semantic_groups_created = len(groups)
        
        # Phase 3: Force consolidation if still over limit
        if len(groups) > self.config.max_categories:
            logger.warning(f"Force consolidating {len(groups)} groups to {self.config.max_categories}")
            groups = self.force_consolidate_to_limit(groups)
            self.stats.forced_merges = len(labels) - sum(g.member_count for g in groups[:self.config.max_categories-1])
        
        # Generate meaningful names
        groups = self.generate_meaningful_names(groups)
        
        # Create mapping
        mapping = {}
        for group in groups:
            for label in group.original_labels:
                mapping[label.original_name] = group.canonical_name
        
        # Update stats
        processing_time = time.time() - start_time
        self.stats.processing_time_seconds = processing_time
        
        if groups:
            group_sizes = [g.member_count for g in groups]
            self.stats.largest_group_size = max(group_sizes)
            self.stats.smallest_group_size = min(group_sizes)
            self.stats.average_group_size = sum(group_sizes) / len(group_sizes)
        
        # Create result
        result = ConsolidationResult(
            original_count=len(labels),
            final_count=len(groups),
            consolidation_ratio=len(groups) / len(labels) if labels else 0,
            label_groups=groups,
            mapping=mapping,
            config_used=self.config,
            warnings=[]
        )
        
        logger.info(f"Consolidation complete: {result.original_count} -> {result.final_count} "
                   f"({result.reduction_percentage:.1f}% reduction)")
        
        return result