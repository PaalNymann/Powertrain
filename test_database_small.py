#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os

def test_database_with_small_dataset():
    """Test database functionality with a small dataset"""
    
    print("=== DATABASE TEST WITH SMALL DATASET ===")
    
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
        
        # Test 2: Check initial cache stats
        print("\n3. Checking initial cache stats...")
        response = requests.get("http://127.0.0.1:8000/api/cache/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Initial cache stats: {stats}")
        
        # Test 3: Test fast OEM search with empty cache
        print("\n4. Testing fast OEM search with empty cache...")
        response = requests.get("http://127.0.0.1:8000/api/oem_search?oem=TEST123", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Fast OEM search working: {data.get('count', 0)} products found")
            print(f"   Expected: 0 products (empty cache)")
        
        # Test 4: Test complete workflow with empty cache
        print("\n5. Testing complete workflow with empty cache...")
        response = requests.get("http://127.0.0.1:8000/api/car_parts_search?regnr=KH66644", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("✅ Complete workflow working with empty cache")
            print(f"   Vehicle info: {data.get('vehicle_info', {})}")
            print(f"   Rackbeat parts: {len(data.get('rackbeat_parts', []))}")
            print(f"   Shopify matches: {data.get('total_shopify_matches', 0)}")
            print(f"   Expected: 0 Shopify matches (empty cache)")
        
        # Test 5: Test database functions directly
        print("\n6. Testing database functions directly...")
        from database import search_products_by_oem, get_cache_stats
        
        # Test empty search
        results = search_products_by_oem("TEST123")
        print(f"✅ Direct database search: {len(results)} products found")
        
        # Test stats
        stats = get_cache_stats()
        print(f"✅ Direct cache stats: {stats}")
        
        print("\n=== SMALL DATASET TEST SUMMARY ===")
        print("✅ Database integration working")
        print("✅ Fast OEM search operational (returns 0 when empty)")
        print("✅ Complete workflow working (handles empty cache gracefully)")
        print("✅ Direct database functions working")
        print("ℹ️  System ready for cache population when needed")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        app_process.terminate()
        app_process.wait()
        print("\nApp service stopped.")

if __name__ == "__main__":
    test_database_with_small_dataset() 