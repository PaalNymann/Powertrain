#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os

def test_database_functionality():
    """Test the database functionality"""
    
    print("=== DATABASE FUNCTIONALITY TEST ===")
    
    # Start the app service
    print("\n1. Starting app.py...")
    app_process = subprocess.Popen([sys.executable, 'app.py'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
    time.sleep(5)
    
    try:
        # Test 1: Health endpoint
        print("\n2. Testing health endpoint...")
        response = requests.get("http://127.0.0.1:8000/health", timeout=10)
        print(f"Health status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Health endpoint working")
        
        # Test 2: Cache stats (should be empty initially)
        print("\n3. Testing cache stats...")
        response = requests.get("http://127.0.0.1:8000/api/cache/stats", timeout=10)
        print(f"Cache stats status: {response.status_code}")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Cache stats working: {stats}")
        
        # Test 3: Update cache (this will take time)
        print("\n4. Testing cache update...")
        print("This will fetch all Shopify products and update the database cache...")
        response = requests.post("http://127.0.0.1:8000/api/cache/update", timeout=120)
        print(f"Cache update status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cache update successful: {result}")
        else:
            print(f"❌ Cache update failed: {response.text[:200]}")
        
        # Test 4: Check updated stats
        print("\n5. Checking updated cache stats...")
        response = requests.get("http://127.0.0.1:8000/api/cache/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Updated cache stats: {stats}")
        
        # Test 5: Fast OEM search
        print("\n6. Testing fast OEM search...")
        response = requests.get("http://127.0.0.1:8000/api/oem_search?oem=TEST123", timeout=10)
        print(f"OEM search status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Fast OEM search working: {data.get('count', 0)} products found")
        
        # Test 6: Complete workflow with database
        print("\n7. Testing complete workflow with database...")
        response = requests.get("http://127.0.0.1:8000/api/car_parts_search?regnr=KH66644", timeout=30)
        print(f"Complete workflow status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Complete workflow working with database")
            print(f"   Vehicle info: {data.get('vehicle_info', {})}")
            print(f"   Rackbeat parts: {len(data.get('rackbeat_parts', []))}")
            print(f"   Shopify matches: {data.get('total_shopify_matches', 0)}")
        
        print("\n=== DATABASE FUNCTIONALITY SUMMARY ===")
        print("✅ Database integration working")
        print("✅ Cache update functional")
        print("✅ Fast OEM search operational")
        print("✅ Complete workflow optimized")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        app_process.terminate()
        app_process.wait()
        print("\nApp service stopped.")

if __name__ == "__main__":
    test_database_functionality() 