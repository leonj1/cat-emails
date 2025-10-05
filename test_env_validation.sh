#!/bin/bash
# Test script to demonstrate environment variable validation

echo "==================================================================="
echo "Testing Cat-Emails API Environment Variable Validation"
echo "==================================================================="
echo ""

echo "Test 1: Missing API key (should fail)"
echo "-------------------------------------------------------------------"
unset REQUESTYAI_API_KEY
unset OPENAI_API_KEY
python3 -c "import api_service" 2>&1 | grep -A 15 "CRITICAL CONFIGURATION ERROR" || echo "Failed to catch error"
echo ""

echo "Test 2: With REQUESTYAI_API_KEY (should succeed)"
echo "-------------------------------------------------------------------"
export REQUESTYAI_API_KEY=test-key
python3 -c "import api_service; print('✓ Service loaded successfully')" 2>&1 | tail -2
unset REQUESTYAI_API_KEY
echo ""

echo "Test 3: With OPENAI_API_KEY (should succeed)"
echo "-------------------------------------------------------------------"
export OPENAI_API_KEY=test-key
python3 -c "import api_service; print('✓ Service loaded successfully')" 2>&1 | tail -2
unset OPENAI_API_KEY
echo ""

echo "==================================================================="
echo "Validation Tests Complete"
echo "==================================================================="
