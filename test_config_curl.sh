#!/bin/bash
set -e  # Exit on error

# Test the /api/config endpoint using curl

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed"
    exit 1
fi

# Start the API server in the background
echo "Starting API server..."
REQUESTYAI_API_KEY=test-key DATABASE_PATH=./test.db python3 api_service.py &
API_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:8001/api/health &>/dev/null; then
        echo "Server is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "Error: Server failed to start within 30 seconds"
        kill $API_PID 2>/dev/null
        exit 1
    fi
    sleep 1
done

# Test the endpoint
echo -e "\n=== Testing /api/config endpoint ===\n"
curl -s http://localhost:8001/api/config | jq '.'

# Cleanup
echo -e "\n\n=== Stopping API server ===\n"
kill $API_PID 2>/dev/null
wait $API_PID 2>/dev/null
rm -f ./test.db  # Clean up test database

echo "Test complete!"
