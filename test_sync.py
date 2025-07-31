#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os

def test_sync_service():
    """Test the sync service endpoints"""
    
    # Start the sync service in background
    print("Starting sync service...")
    process = subprocess.Popen([sys.executable, 'sync_service.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Wait for service to start
    time.sleep(5)
    
    try:
        # Test health endpoint
        print("Testing sync service health endpoint...")
        response = requests.get("http://127.0.0.1:8001/health", timeout=10)
        print(f"Health response: {response.status_code}")
        print(f"Health content: {response.text}")
        
        # Test sync endpoint (this will take longer)
        print("\nTesting sync endpoint...")
        response = requests.post("http://127.0.0.1:8001/sync/full", timeout=30)
        print(f"Sync response: {response.status_code}")
        print(f"Sync content: {response.text[:500]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Kill the process
        process.terminate()
        process.wait()
        print("Sync service stopped.")

if __name__ == "__main__":
    test_sync_service() 