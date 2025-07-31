#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os
import json
import threading

def monitor_output(process, name):
    """Monitor process output in real-time"""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(f"[{name}] {output.strip()}")
    
    # Check for any errors
    stderr_output = process.stderr.read()
    if stderr_output:
        print(f"[{name} ERROR] {stderr_output.decode()}")

def debug_sync_service():
    """Debug the sync service with real-time output"""
    
    print("=== SYNC SERVICE DEBUG ===\n")
    
    # Start sync_service.py with output capture
    print("Starting sync_service.py...")
    sync_process = subprocess.Popen([sys.executable, 'sync_service.py'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   bufsize=1,
                                   universal_newlines=True)
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_output, args=(sync_process, "SYNC"))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Wait for startup
    time.sleep(5)
    
    try:
        # Test health endpoint
        print("\n1. Testing /health endpoint...")
        response = requests.get("http://127.0.0.1:8001/health", timeout=10)
        print(f"✓ Health endpoint: {response.status_code}")
        
        # Test sync endpoint with longer timeout to see progress
        print("\n2. Testing /sync/full endpoint...")
        print("  (Testing with 30 second timeout to see progress)")
        response = requests.post("http://127.0.0.1:8001/sync/full", timeout=30)
        print(f"✓ Sync endpoint: {response.status_code}")
        if response.status_code == 200:
            print("  ✓ Sync completed successfully")
            print(f"  Response: {response.json()}")
        else:
            print(f"  Response: {response.text[:300]}...")
            
    except requests.exceptions.Timeout:
        print("  ⚠ Sync timed out after 30 seconds")
        print("  Check the output above to see where it got stuck")
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
    
    print("\n=== DEBUG SUMMARY ===")
    print("Check the output above to see:")
    print("- Where the sync process gets stuck")
    print("- Any error messages")
    print("- Progress through the sync steps")

if __name__ == "__main__":
    debug_sync_service() 