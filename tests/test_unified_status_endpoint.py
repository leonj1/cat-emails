"""
Unit tests for the unified /api/status endpoint.
Tests the new UnifiedStatusResponse model and validates the consolidated endpoint.
"""
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.processing_current_status_response import (
    UnifiedStatusResponse,
    BackgroundStatus,
    BackgroundConfiguration,
    BackgroundThreadInfo,
    ProcessingCurrentStatusResponse
)


class TestUnifiedStatusModels(unittest.TestCase):
    """Test suite for unified status response models"""

    def test_background_thread_info_creation(self):
        """Test creating BackgroundThreadInfo model"""
        thread_info = BackgroundThreadInfo(
            name="GmailBackgroundProcessor",
            is_alive=True,
            daemon=True,
            ident=12345
        )

        self.assertEqual(thread_info.name, "GmailBackgroundProcessor")
        self.assertTrue(thread_info.is_alive)
        self.assertTrue(thread_info.daemon)
        self.assertEqual(thread_info.ident, 12345)

    def test_background_thread_info_optional_fields(self):
        """Test BackgroundThreadInfo with no fields (all optional)"""
        thread_info = BackgroundThreadInfo()

        self.assertIsNone(thread_info.name)
        self.assertIsNone(thread_info.is_alive)
        self.assertIsNone(thread_info.daemon)
        self.assertIsNone(thread_info.ident)

    def test_background_configuration_creation(self):
        """Test creating BackgroundConfiguration model"""
        config = BackgroundConfiguration(
            scan_interval_seconds=300,
            process_hours=24
        )

        self.assertEqual(config.scan_interval_seconds, 300)
        self.assertEqual(config.process_hours, 24)

    def test_background_status_creation(self):
        """Test creating BackgroundStatus model"""
        thread_info = BackgroundThreadInfo(
            name="GmailBackgroundProcessor",
            is_alive=True,
            daemon=True,
            ident=12345
        )
        config = BackgroundConfiguration(
            scan_interval_seconds=300,
            process_hours=24
        )

        status = BackgroundStatus(
            enabled=True,
            running=True,
            thread=thread_info,
            configuration=config
        )

        self.assertTrue(status.enabled)
        self.assertTrue(status.running)
        self.assertIsNotNone(status.thread)
        self.assertEqual(status.thread.name, "GmailBackgroundProcessor")
        self.assertEqual(status.configuration.scan_interval_seconds, 300)

    def test_background_status_without_thread(self):
        """Test BackgroundStatus when thread is not running"""
        config = BackgroundConfiguration(
            scan_interval_seconds=300,
            process_hours=24
        )

        status = BackgroundStatus(
            enabled=True,
            running=False,
            thread=None,
            configuration=config
        )

        self.assertTrue(status.enabled)
        self.assertFalse(status.running)
        self.assertIsNone(status.thread)

    def test_unified_status_response_full(self):
        """Test creating a full UnifiedStatusResponse"""
        thread_info = BackgroundThreadInfo(
            name="GmailBackgroundProcessor",
            is_alive=True,
            daemon=True,
            ident=12345
        )
        config = BackgroundConfiguration(
            scan_interval_seconds=300,
            process_hours=24
        )
        background_status = BackgroundStatus(
            enabled=True,
            running=True,
            thread=thread_info,
            configuration=config
        )

        current_status = {
            "email_address": "test@example.com",
            "state": "PROCESSING",
            "current_step": "Processing email 5 of 20"
        }
        recent_runs = [
            {"run_id": "abc123", "status": "completed"},
            {"run_id": "def456", "status": "completed"}
        ]
        statistics = {
            "total_runs": 100,
            "success_rate": 0.95
        }

        response = UnifiedStatusResponse(
            is_processing=True,
            current_status=current_status,
            background=background_status,
            recent_runs=recent_runs,
            statistics=statistics,
            timestamp="2025-01-15T10:30:00Z",
            websocket_available=True
        )

        self.assertTrue(response.is_processing)
        self.assertIsNotNone(response.current_status)
        self.assertEqual(response.current_status["state"], "PROCESSING")
        self.assertTrue(response.background.running)
        self.assertEqual(len(response.recent_runs), 2)
        self.assertEqual(response.statistics["total_runs"], 100)
        self.assertTrue(response.websocket_available)

    def test_unified_status_response_minimal(self):
        """Test creating a minimal UnifiedStatusResponse (idle state)"""
        config = BackgroundConfiguration(
            scan_interval_seconds=300,
            process_hours=24
        )
        background_status = BackgroundStatus(
            enabled=True,
            running=True,
            thread=None,
            configuration=config
        )

        response = UnifiedStatusResponse(
            is_processing=False,
            current_status=None,
            background=background_status,
            recent_runs=None,
            statistics=None,
            timestamp="2025-01-15T10:30:00Z",
            websocket_available=True
        )

        self.assertFalse(response.is_processing)
        self.assertIsNone(response.current_status)
        self.assertIsNone(response.recent_runs)
        self.assertIsNone(response.statistics)

    def test_unified_status_response_includes_background_info(self):
        """Test that unified response includes all background status fields"""
        thread_info = BackgroundThreadInfo(
            name="GmailBackgroundProcessor",
            is_alive=True,
            daemon=True,
            ident=99999
        )
        config = BackgroundConfiguration(
            scan_interval_seconds=600,
            process_hours=48
        )
        background_status = BackgroundStatus(
            enabled=True,
            running=True,
            thread=thread_info,
            configuration=config
        )

        response = UnifiedStatusResponse(
            is_processing=False,
            background=background_status,
            timestamp="2025-01-15T10:30:00Z",
            websocket_available=False
        )

        # Verify all background info is accessible
        self.assertTrue(response.background.enabled)
        self.assertTrue(response.background.running)
        self.assertEqual(response.background.thread.name, "GmailBackgroundProcessor")
        self.assertTrue(response.background.thread.is_alive)
        self.assertEqual(response.background.thread.ident, 99999)
        self.assertEqual(response.background.configuration.scan_interval_seconds, 600)
        self.assertEqual(response.background.configuration.process_hours, 48)

    def test_unified_response_supersedes_legacy_endpoints(self):
        """Test that UnifiedStatusResponse contains all fields from legacy endpoints"""
        # Fields from /api/processing/status
        processing_status_fields = {'is_processing', 'current_status', 'timestamp'}

        # Fields from /api/background/status (now in 'background' object)
        background_status_fields = {'enabled', 'running', 'thread', 'configuration'}

        # Fields from /api/processing/current-status
        current_status_fields = {'is_processing', 'current_status', 'recent_runs',
                                  'statistics', 'timestamp', 'websocket_available'}

        # Create a unified response
        config = BackgroundConfiguration(scan_interval_seconds=300, process_hours=24)
        background = BackgroundStatus(enabled=True, running=True, thread=None, configuration=config)

        response = UnifiedStatusResponse(
            is_processing=False,
            current_status=None,
            background=background,
            recent_runs=[],
            statistics={},
            timestamp="2025-01-15T10:30:00Z",
            websocket_available=True
        )

        # Get actual fields from response (access from class, not instance)
        response_fields = set(UnifiedStatusResponse.model_fields.keys())
        background_response_fields = set(BackgroundStatus.model_fields.keys())

        # Verify processing status fields are present
        self.assertTrue(processing_status_fields.issubset(response_fields))

        # Verify background status fields are in the background object
        self.assertTrue(background_status_fields.issubset(background_response_fields))

        # Verify current status fields are present
        self.assertTrue(current_status_fields.issubset(response_fields))


class TestLegacyModelCompatibility(unittest.TestCase):
    """Test that legacy ProcessingCurrentStatusResponse still works"""

    def test_legacy_model_still_works(self):
        """Test that ProcessingCurrentStatusResponse is still functional"""
        response = ProcessingCurrentStatusResponse(
            is_processing=True,
            current_status={"state": "PROCESSING"},
            recent_runs=[],
            statistics=None,
            timestamp="2025-01-15T10:30:00Z",
            websocket_available=True
        )

        self.assertTrue(response.is_processing)
        self.assertEqual(response.current_status["state"], "PROCESSING")
        self.assertTrue(response.websocket_available)


if __name__ == '__main__':
    unittest.main()
