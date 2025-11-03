#!/bin/bash
# Test the /api/config endpoint using curl

# Start the API server in the background
echo "Starting API server..."
REQUESTYAI_API_KEY=test-key DATABASE_PATH=./test.db python3 api_service.py &
API_PID=$!

# Wait for server to start
sleep 5

# Test the endpoint
echo -e "\n=== Testing /api/config endpoint ===\n"
curl -s http://localhost:8001/api/config | jq '.'

# Cleanup
echo -e "\n\n=== Stopping API server ===\n"
kill $API_PID 2>/dev/null
wait $API_PID 2>/dev/null

echo "Test complete!"
