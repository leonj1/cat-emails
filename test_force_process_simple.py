#!/usr/bin/env python3
"""
Simple test script to verify force process implementation
"""
import sys

# Test 1: Import all new modules
print("Test 1: Importing new modules...")
try:
    from models.force_process_response import ForceProcessResponse, ProcessingInfo
    from services.rate_limiter_service import RateLimiterService
    from services.processing_status_manager import ProcessingStatusManager
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Test ForceProcessResponse model
print("\nTest 2: Testing ForceProcessResponse model...")
try:
    response = ForceProcessResponse(
        status="success",
        message="Test message",
        email_address="test@example.com",
        timestamp="2025-10-07T10:30:00Z",
        processing_info=ProcessingInfo(
            hours=2,
            status_url="/api/processing/current-status",
            websocket_url="/ws/status"
        )
    )
    assert response.status == "success"
    assert response.email_address == "test@example.com"
    assert response.processing_info.hours == 2
    print("✅ ForceProcessResponse model works correctly")
except Exception as e:
    print(f"❌ Model test failed: {e}")
    sys.exit(1)

# Test 3: Test RateLimiterService
print("\nTest 3: Testing RateLimiterService...")
try:
    rate_limiter = RateLimiterService(default_interval_seconds=5)

    # First request should be allowed
    allowed, remaining = rate_limiter.check_rate_limit("test@example.com")
    assert allowed == True
    assert remaining is None
    print("  ✓ First request allowed")

    # Second request immediately should be denied
    allowed, remaining = rate_limiter.check_rate_limit("test@example.com")
    assert allowed == False
    assert remaining is not None
    assert remaining > 0
    print(f"  ✓ Second request denied ({remaining:.1f}s remaining)")

    # Different key should be allowed
    allowed, remaining = rate_limiter.check_rate_limit("other@example.com")
    assert allowed == True
    print("  ✓ Different key allowed")

    # Test reset
    rate_limiter.reset_key("test@example.com")
    allowed, remaining = rate_limiter.check_rate_limit("test@example.com")
    assert allowed == True
    print("  ✓ Reset works correctly")

    print("✅ RateLimiterService works correctly")
except Exception as e:
    print(f"❌ Rate limiter test failed: {e}")
    sys.exit(1)

# Test 4: Test ProcessingStatusManager new method
print("\nTest 4: Testing ProcessingStatusManager.is_processing_account()...")
try:
    manager = ProcessingStatusManager()

    # Should return False when nothing is processing
    assert manager.is_processing_account("test@example.com") == False
    print("  ✓ Returns False when idle")

    # Start processing
    manager.start_processing("test@example.com")
    assert manager.is_processing_account("test@example.com") == True
    print("  ✓ Returns True when processing same account")

    # Different account
    assert manager.is_processing_account("other@example.com") == False
    print("  ✓ Returns False for different account")

    # Case insensitive
    assert manager.is_processing_account("TEST@EXAMPLE.COM") == True
    print("  ✓ Case insensitive matching works")

    # Complete processing
    manager.complete_processing()
    assert manager.is_processing_account("test@example.com") == False
    print("  ✓ Returns False after completion")

    print("✅ ProcessingStatusManager.is_processing_account() works correctly")
except Exception as e:
    print(f"❌ ProcessingStatusManager test failed: {e}")
    sys.exit(1)

# Test 5: Verify API service can import
print("\nTest 5: Verifying API service imports...")
try:
    # Try to import the constants and verify our additions are there
    import api_service
    assert hasattr(api_service, 'force_process_rate_limiter')
    print("  ✓ force_process_rate_limiter is defined in api_service")
    print("✅ API service imports successfully")
except Exception as e:
    print(f"❌ API service import failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("🎉 ALL TESTS PASSED!")
print("="*60)
print("\nThe force process endpoint implementation is ready to use.")
print("\nNext steps:")
print("1. Start the API service: python3 api_service.py")
print("2. Test the endpoint: curl -X POST http://localhost:8001/api/accounts/{email}/process")
print("3. View API docs: http://localhost:8001/docs")
