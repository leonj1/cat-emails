#!/usr/bin/env python3
"""
Table-driven tests for Gmail label consolidation
"""
import unittest
from typing import List, Dict, Any
import json

from label_consolidation.models import (
    Label, LabelGroup, ConsolidationConfig, 
    ConsolidationResult, SimilarityMetrics
)
from label_consolidation.label_consolidation_service import LabelConsolidationService


class TestLabelConsolidation(unittest.TestCase):
    """Test cases for label consolidation service"""
    
    # Table-driven test cases
    NORMALIZATION_TEST_CASES = [
        # (input, expected_output, description)
        ("Announcement", "announcement", "Basic lowercase"),
        ("announcement.", "announcement", "Remove trailing period"),
        ("Announcement...", "announcement", "Remove multiple trailing punctuation"),
        ("  Announcement  ", "announcement", "Trim whitespace"),
        ("Announcement-", "announcement", "Remove trailing dash"),
        ("Work - Related", "work related", "Remove internal punctuation (aggressive)"),
        ("Work_Related", "workrelated", "Remove underscore (aggressive)"),
        ("News!!!", "news", "Remove exclamation marks"),
        ("@Special#Label$", "speciallabel", "Remove special characters (aggressive)"),
        ("Multiple   Spaces", "multiple spaces", "Normalize multiple spaces"),
    ]
    
    SIMILARITY_TEST_CASES = [
        # (label1, label2, min_similarity, max_similarity, description)
        ("announcement", "announcements", 0.85, 1.0, "Plural form"),
        ("work", "work-related", 0.3, 0.7, "Compound term"),
        ("newsletter", "news letter", 0.7, 0.95, "Space variation"),
        ("receipts", "receipt", 0.8, 1.0, "Singular/plural"),
        ("todo", "to do", 0.4, 0.8, "Space separation"),
        ("email", "e-mail", 0.6, 0.9, "Hyphen variation"),
        ("completely different", "another label", 0.0, 0.3, "Unrelated labels"),
    ]
    
    CONSOLIDATION_TEST_CASES = [
        {
            "name": "exact_duplicates",
            "input": ["Announcement", "announcement", "ANNOUNCEMENT", "announcement."],
            "max_categories": 25,
            "expected_groups": 1,
            "expected_canonical": "announcement",
            "description": "Exact duplicates after normalization"
        },
        {
            "name": "news_variants",
            "input": ["Fox News", "CNN News", "BBC News", "News", "news updates", "Daily News"],
            "max_categories": 25,
            "expected_groups": 1,
            "expected_canonical_contains": "news",
            "description": "News-related labels"
        },
        {
            "name": "work_variants",
            "input": ["Work", "work-related", "Work stuff", "Office", "work_", "WORK"],
            "max_categories": 25,
            "expected_groups": 2,  # "work" group and "office" might be separate
            "description": "Work-related labels"
        },
        {
            "name": "force_consolidation",
            "input": [f"Label{i}" for i in range(50)],  # 50 unique labels
            "max_categories": 10,
            "expected_groups": 10,
            "description": "Force consolidation to limit"
        },
        {
            "name": "mixed_categories",
            "input": [
                "Personal", "personal-emails", "Personal stuff",
                "Work", "work-related", "Office",
                "Newsletter", "Newsletters", "newsletter-subscription",
                "Receipts", "Order Receipts", "receipt",
                "Social", "Facebook", "Twitter",
                "Finance", "Banking", "Financial"
            ],
            "max_categories": 6,
            "expected_groups": 6,
            "description": "Mixed category consolidation"
        },
        {
            "name": "single_label",
            "input": ["OnlyOne"],
            "max_categories": 25,
            "expected_groups": 1,
            "expected_canonical": "onlyone",
            "description": "Single label handling"
        },
        {
            "name": "empty_labels",
            "input": ["", "  ", "Valid", None],
            "max_categories": 25,
            "expected_groups": 1,
            "expected_canonical": "valid",
            "description": "Empty label filtering"
        }
    ]
    
    def setUp(self):
        """Set up test fixtures"""
        self.service = LabelConsolidationService()
        
    def test_label_normalization(self):
        """Test label normalization with table-driven cases"""
        for input_label, expected, description in self.NORMALIZATION_TEST_CASES:
            with self.subTest(input=input_label, description=description):
                result = self.service.normalize_label(input_label)
                self.assertEqual(result, expected, 
                               f"Failed for {description}: '{input_label}' -> '{result}' (expected '{expected}')")
    
    def test_similarity_calculations(self):
        """Test similarity metric calculations"""
        for label1, label2, min_sim, max_sim, description in self.SIMILARITY_TEST_CASES:
            with self.subTest(label1=label1, label2=label2, description=description):
                metrics = self.service.calculate_similarity(label1, label2)
                combined = metrics.combined_score
                
                self.assertGreaterEqual(combined, min_sim,
                    f"{description}: similarity {combined:.2f} < {min_sim}")
                self.assertLessEqual(combined, max_sim,
                    f"{description}: similarity {combined:.2f} > {max_sim}")
                
                # Ensure all metrics are in valid range
                self.assertGreaterEqual(metrics.levenshtein_ratio, 0.0)
                self.assertLessEqual(metrics.levenshtein_ratio, 1.0)
                self.assertGreaterEqual(metrics.jaccard_ngram, 0.0)
                self.assertLessEqual(metrics.jaccard_ngram, 1.0)
    
    def test_consolidation_scenarios(self):
        """Test complete consolidation scenarios"""
        for test_case in self.CONSOLIDATION_TEST_CASES:
            with self.subTest(name=test_case["name"]):
                # Filter out None values
                labels = [l for l in test_case["input"] if l is not None]
                
                config = ConsolidationConfig(max_categories=test_case["max_categories"])
                service = LabelConsolidationService(config)
                
                result = service.consolidate(labels)
                
                # Check number of groups
                self.assertEqual(result.final_count, test_case["expected_groups"],
                    f"{test_case['description']}: got {result.final_count} groups, "
                    f"expected {test_case['expected_groups']}")
                
                # Check canonical name if specified
                if "expected_canonical" in test_case:
                    canonical_names = [g.canonical_name for g in result.label_groups]
                    self.assertIn(test_case["expected_canonical"], canonical_names,
                        f"{test_case['description']}: expected canonical name "
                        f"'{test_case['expected_canonical']}' not found in {canonical_names}")
                
                if "expected_canonical_contains" in test_case:
                    contains = test_case["expected_canonical_contains"]
                    found = any(contains in g.canonical_name for g in result.label_groups)
                    self.assertTrue(found,
                        f"{test_case['description']}: no canonical name contains '{contains}'")
                
                # Verify all original labels are mapped
                mapped_labels = set(result.mapping.keys())
                original_labels = set(l for l in labels if l and l.strip())
                self.assertEqual(mapped_labels, original_labels,
                    f"{test_case['description']}: not all labels mapped")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        # Empty list
        result = self.service.consolidate([])
        self.assertEqual(result.original_count, 0)
        self.assertEqual(result.final_count, 0)
        
        # All empty strings
        result = self.service.consolidate(["", "  ", "\t", "\n"])
        self.assertEqual(result.original_count, 0)
        self.assertEqual(result.final_count, 0)
        
        # Very long label
        long_label = "a" * 1000
        result = self.service.consolidate([long_label, "normal"])
        self.assertEqual(result.final_count, 2)
        
        # Unicode labels
        unicode_labels = ["café", "naïve", "résumé", "🏷️label"]
        result = self.service.consolidate(unicode_labels)
        self.assertGreater(result.final_count, 0)
    
    def test_configuration_options(self):
        """Test different configuration options"""
        labels = ["work", "Work!", "WORK-", "working", "workplace"]
        
        # Test with high similarity threshold
        config = ConsolidationConfig(similarity_threshold=0.95)
        service = LabelConsolidationService(config)
        result = service.consolidate(labels)
        # Should create more groups with higher threshold
        self.assertGreater(result.final_count, 1)
        
        # Test with low similarity threshold
        config = ConsolidationConfig(similarity_threshold=0.3)
        service = LabelConsolidationService(config)
        result = service.consolidate(labels)
        # Should create fewer groups with lower threshold
        self.assertLessEqual(result.final_count, 3)
        
        # Test non-aggressive normalization
        config = ConsolidationConfig(normalization_aggressive=False)
        service = LabelConsolidationService(config)
        normalized = service.normalize_label("Work-Related@2023")
        self.assertIn("-", normalized)  # Should keep some punctuation
    
    def test_result_object_methods(self):
        """Test ConsolidationResult methods"""
        labels = ["Work", "Personal", "Finance", "work-related", "personal-emails"]
        result = self.service.consolidate(labels)
        
        # Test get_consolidated_label
        self.assertIsNotNone(result.get_consolidated_label("Work"))
        self.assertIsNone(result.get_consolidated_label("NonExistent"))
        
        # Test get_group_for_label
        group = result.get_group_for_label("Work")
        self.assertIsNotNone(group)
        self.assertIsInstance(group, LabelGroup)
        
        # Test reduction percentage
        self.assertGreaterEqual(result.reduction_percentage, 0)
        self.assertLessEqual(result.reduction_percentage, 100)
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger datasets"""
        import time
        
        # Generate 1000 labels with some patterns
        labels = []
        base_categories = ["work", "personal", "news", "social", "finance", 
                          "travel", "shopping", "tech", "health", "education"]
        
        for i in range(100):
            for category in base_categories:
                labels.append(f"{category}{i}")
                labels.append(f"{category}-{i}")
                labels.append(f"{category}_{i}")
        
        config = ConsolidationConfig(max_categories=25)
        service = LabelConsolidationService(config)
        
        start_time = time.time()
        result = service.consolidate(labels)
        end_time = time.time()
        
        # Should complete in reasonable time
        self.assertLess(end_time - start_time, 10.0)  # 10 seconds max
        
        # Should consolidate to target
        self.assertEqual(result.final_count, 25)
        
        # All labels should be mapped
        self.assertEqual(len(result.mapping), len(labels))


class TestModels(unittest.TestCase):
    """Test Pydantic models"""
    
    def test_label_model(self):
        """Test Label model validation"""
        # Valid label
        label = Label(original_name="Test Label")
        self.assertEqual(label.original_name, "Test Label")
        self.assertEqual(label.email_count, 0)
        
        # Invalid label
        with self.assertRaises(ValueError):
            Label(original_name="")
    
    def test_consolidation_config(self):
        """Test ConsolidationConfig validation"""
        # Default config
        config = ConsolidationConfig()
        self.assertEqual(config.max_categories, 25)
        self.assertEqual(config.similarity_threshold, 0.8)
        
        # Valid custom config
        config = ConsolidationConfig(max_categories=10, similarity_threshold=0.5)
        self.assertEqual(config.max_categories, 10)
        
        # Invalid config
        with self.assertRaises(ValueError):
            ConsolidationConfig(max_categories=0)
        
        with self.assertRaises(ValueError):
            ConsolidationConfig(similarity_threshold=1.5)
    
    def test_similarity_metrics(self):
        """Test SimilarityMetrics calculations"""
        metrics = SimilarityMetrics(
            levenshtein_ratio=0.8,
            jaccard_ngram=0.6,
            semantic_similarity=0.7
        )
        
        # Combined score should be average
        expected = (0.8 + 0.6 + 0.7) / 3
        self.assertAlmostEqual(metrics.combined_score, expected, places=2)
        
        # Without semantic similarity
        metrics = SimilarityMetrics(
            levenshtein_ratio=0.8,
            jaccard_ngram=0.6
        )
        expected = (0.8 + 0.6) / 2
        self.assertAlmostEqual(metrics.combined_score, expected, places=2)


if __name__ == "__main__":
    unittest.main()