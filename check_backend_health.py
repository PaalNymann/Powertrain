#!/usr/bin/env python3
"""
Simple backend health check to see if Railway is responding
"""

import requests
import time

BACKEND_URL = "https://web-production-0809b.up.railway.app"

def check_backend_health():
    """Check if backend is responding at all"""
    
    print("🔍 CHECKING BACKEND HEALTH")
    print("=" * 30)
    
    # Test simple endpoints first
    endpoints = [
        "/",
        "/api/health", 
        "/api/cache/stats",
        "/api/database/inspect"
    ]
    
    for endpoint in endpoints:
        url = f"{BACKEND_URL}{endpoint}"
        print(f"\n📡 Testing: {endpoint}")
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            duration = time.time() - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Time: {duration:.2f}s")
            
            if response.status_code == 200:
                print(f"   ✅ OK")
                if len(response.text) < 500:
                    print(f"   Response: {response.text[:200]}")
            else:
                print(f"   ❌ Error: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT (>10s)")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def test_simple_search():
    """Test a simple search that should be fast"""
    
    print(f"\n🔍 TESTING SIMPLE SEARCH")
    print("=" * 25)
    
    # Try a very simple license plate that might be cached
    test_plates = ["YZ99554", "KH66644"]  # Known test plates
    
    for plate in test_plates:
        print(f"\n📡 Testing search for: {plate}")
        
        try:
            start_time = time.time()
            response = requests.post(
                f"{BACKEND_URL}/api/car_parts_search", 
                json={"license_plate": plate}, 
                timeout=15
            )
            duration = time.time() - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Time: {duration:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                available_oems = data.get('available_oems', 'unknown')
                compatible_oems = data.get('compatible_oems', 'unknown')
                print(f"   ✅ Available OEMs: {available_oems}")
                print(f"   ✅ Compatible OEMs: {compatible_oems}")
                return True
            else:
                print(f"   ❌ Error: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT (>15s)")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    return False

if __name__ == "__main__":
    # Check basic health
    check_backend_health()
    
    # Test simple search
    success = test_simple_search()
    
    if success:
        print(f"\n✅ Backend is responding - ZT41818 timeout may be specific issue")
    else:
        print(f"\n❌ Backend has general issues - need to check Railway logs")
    
    print(f"\n🎯 If backend is healthy, the ZT41818 timeout suggests:")
    print(f"   1. TecDoc API call is hanging/slow for this specific vehicle")
    print(f"   2. New live TecDoc integration has a bug/infinite loop")
    print(f"   3. Railway deployment issue with new code")
