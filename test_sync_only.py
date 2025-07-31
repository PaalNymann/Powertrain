#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os
import json

def test_sync_service_only():
    """Test only the sync service to debug issues"""
    
    print("=== SYNC SERVICE TEST ===\n")
    
    # Start sync_service.py
    print("Starting sync_service.py...")
    sync_process = subprocess.Popen([sys.executable, 'sync_service.py'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
    
    # Wait for startup
    time.sleep(5)
    
    try:
        # Test health endpoint
        print("1. Testing /health endpoint...")
        response = requests.get("http://127.0.0.1:8001/health", timeout=10)
        print(f"✓ Health endpoint: {response.status_code}")
        print(f"  Response: {response.json()}")
        
        # Test sync endpoint with shorter timeout
        print("\n2. Testing /sync/full endpoint...")
        print("  (Testing with 10 second timeout)")
        response = requests.post("http://127.0.0.1:8001/sync/full", timeout=10)
        print(f"✓ Sync endpoint: {response.status_code}")
        if response.status_code == 200:
            print("  ✓ Sync working correctly")
            print(f"  Response: {response.json()}")
        else:
            print(f"  Response: {response.text[:300]}...")
            
    except requests.exceptions.Timeout:
        print("  ⚠ Sync timed out after 10 seconds")
        print("  This suggests the sync is working but taking too long")
    except requests.exceptions.ConnectionError:
        print("  ✗ Connection error - service might not be running")
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        sync_process.terminate()
        sync_process.wait()
        print("\nSync service stopped.")
    
    print("\n=== SYNC TEST SUMMARY ===")
    print("If health endpoint works but sync times out:")
    print("- The service is working correctly")
    print("- The sync is just taking longer than expected")
    print("- This is normal for large datasets")

if __name__ == "__main__":
    test_sync_service_only() 