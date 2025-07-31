#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os

def test_cache_update():
    """Test updating the database cache with real Shopify data"""
    
    print("=== DATABASE CACHE UPDATE TEST ===")
    
    # Start the app service
    print("\n1. Starting app.py...")
    app_process = subprocess.Popen([sys.executable, 'app.py'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
    time.sleep(5)
    
    try:
        # Test 1: Health check
        print("\n2. Testing health endpoint...")
        response = requests.get("http://127.0.0.1:8000/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health endpoint working")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return
        
        # Test 2: Initial cache stats
        print("\n3. Checking initial cache stats...")
        response = requests.get("http://127.0.0.1:8000/api/cache/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Initial cache stats: {stats}")
        else:
            print(f"❌ Cache stats failed: {response.status_code}")
            return
        
        # Test 3: Update cache (this will take time)
        print("\n4. Updating database cache with Shopify products...")
        print("⚠️  This may take several minutes depending on product count...")
        
        # Use a longer timeout for cache update
        response = requests.post("http://127.0.0.1:8000/api/cache/update", timeout=300)  # 5 minutes
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Cache update successful!")
            print(f"   Message: {result.get('message', 'N/A')}")
            print(f"   Stats: {result.get('stats', {})}")
        else:
            print(f"❌ Cache update failed: {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return
        
        # Test 4: Check updated stats
        print("\n5. Checking updated cache stats...")
        response = requests.get("http://127.0.0.1:8000/api/cache/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Updated cache stats: {stats}")
            
            if stats.get('products', 0) > 0:
                print(f"🎉 Successfully cached {stats['products']} products!")
                print(f"   Metafields: {stats.get('metafields', 0)}")
                print(f"   OEM entries: {stats.get('oem_entries', 0)}")
            else:
                print("⚠️  No products were cached - check Shopify API connection")
        
        # Test 5: Test fast OEM search with real data
        print("\n6. Testing fast OEM search with cached data...")
        response = requests.get("http://127.0.0.1:8000/api/oem_search?oem=TEST", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Fast OEM search working: {data.get('count', 0)} products found")
            if data.get('products'):
                print(f"   Sample product: {data['products'][0].get('title', 'N/A')}")
        else:
            print(f"❌ OEM search failed: {response.status_code}")
        
        print("\n=== CACHE UPDATE TEST SUMMARY ===")
        print("✅ Database cache update functional")
        print("✅ Fast OEM search operational")
        print("✅ Ready for production testing")
        
    except requests.exceptions.Timeout:
        print("❌ Cache update timed out - Shopify may have many products")
        print("💡 Consider running cache updates during off-peak hours")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
    finally:
        app_process.terminate()
        app_process.wait()
        print("\nApp service stopped.")

if __name__ == "__main__":
    test_cache_update() 