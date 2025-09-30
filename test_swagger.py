#!/usr/bin/env python3
"""
Quick test script to verify Swagger/OpenAPI endpoints are accessible.
"""
import requests
import sys

def test_swagger_endpoints():
    """Test that Swagger/OpenAPI endpoints are accessible."""
    base_url = "http://localhost:8001"

    endpoints = {
        "OpenAPI JSON Schema": f"{base_url}/openapi.json",
        "Swagger UI": f"{base_url}/docs",
        "ReDoc": f"{base_url}/redoc"
    }

    print("Testing Swagger/OpenAPI Endpoints...")
    print("=" * 60)

    all_passed = True

    for name, url in endpoints.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: {url}")
                print(f"   Status: {response.status_code}")
                if name == "OpenAPI JSON Schema":
                    # Print some key info from the schema
                    data = response.json()
                    print(f"   API Title: {data.get('info', {}).get('title')}")
                    print(f"   API Version: {data.get('info', {}).get('version')}")
                    print(f"   Total Endpoints: {sum(len(methods) for methods in data.get('paths', {}).values())}")
                print()
            else:
                print(f"❌ {name}: {url}")
                print(f"   Status: {response.status_code}")
                print()
                all_passed = False
        except requests.exceptions.ConnectionError:
            print(f"⚠️  {name}: {url}")
            print(f"   Error: Could not connect. Is the API server running?")
            print(f"   Start the server with: python api_service.py")
            print()
            all_passed = False
        except Exception as e:
            print(f"❌ {name}: {url}")
            print(f"   Error: {str(e)}")
            print()
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✅ All Swagger/OpenAPI endpoints are accessible!")
        return 0
    else:
        print("⚠️  Some endpoints failed. Make sure the API server is running:")
        print("   python api_service.py")
        return 1

if __name__ == "__main__":
    sys.exit(test_swagger_endpoints())
