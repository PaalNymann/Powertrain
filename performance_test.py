#!/usr/bin/env python3
"""
Performance Test Script
Compare old vs optimized search functions to measure improvements
"""

import time
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_search_performance(license_plate="RJ62438"):
    """Test search performance with the optimized backend"""
    
    print(f"🧪 PERFORMANCE TEST: Testing search for {license_plate}")
    print("=" * 60)
    
    # Test the optimized endpoint
    backend_url = "https://web-production-0809b.up.railway.app"
    
    print(f"🚀 Testing OPTIMIZED search endpoint...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{backend_url}/api/car_parts_search",
            json={"license_plate": license_plate},
            timeout=30
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ OPTIMIZED SEARCH COMPLETED!")
            print(f"⏱️  Total Response Time: {response_time:.2f} seconds")
            
            # Extract performance metrics if available
            performance = data.get('performance', {})
            if performance:
                print(f"📊 DETAILED PERFORMANCE BREAKDOWN:")
                print(f"   - Step 2 (OEM retrieval): {performance.get('step2_time', 'N/A')}s")
                print(f"   - Step 3 (Compatibility): {performance.get('step3_time', 'N/A')}s") 
                print(f"   - Step 4 (Product search): {performance.get('step4_time', 'N/A')}s")
                print(f"   - Cache hits: {performance.get('cache_hits', 'N/A')}")
            
            # Results summary
            print(f"📦 SEARCH RESULTS:")
            print(f"   - Vehicle: {data.get('vehicle_info', {}).get('make', 'N/A')} {data.get('vehicle_info', {}).get('model', 'N/A')}")
            print(f"   - Available OEMs: {data.get('available_oems', 0)}")
            print(f"   - Compatible OEMs: {data.get('compatible_oems', 0)}")
            print(f"   - Matching Products: {len(data.get('shopify_parts', []))}")
            
            return {
                'success': True,
                'response_time': response_time,
                'performance': performance,
                'results': {
                    'available_oems': data.get('available_oems', 0),
                    'compatible_oems': data.get('compatible_oems', 0),
                    'products_found': len(data.get('shopify_parts', []))
                }
            }
            
        else:
            print(f"❌ Search failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return {'success': False, 'error': f"HTTP {response.status_code}"}
            
    except requests.exceptions.Timeout:
        print(f"⏰ Search timed out after 30 seconds")
        return {'success': False, 'error': 'Timeout'}
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return {'success': False, 'error': str(e)}

def test_cache_functionality():
    """Test cache functionality"""
    backend_url = "https://web-production-0809b.up.railway.app"
    
    print(f"\n💾 TESTING CACHE FUNCTIONALITY...")
    print("=" * 40)
    
    try:
        # Get cache stats
        response = requests.get(f"{backend_url}/api/cache/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"📊 Cache Stats: {stats}")
        else:
            print(f"❌ Failed to get cache stats: {response.status_code}")
            
        # Clear cache
        response = requests.post(f"{backend_url}/api/cache/clear")
        if response.status_code == 200:
            print(f"🗑️ Cache cleared successfully")
        else:
            print(f"❌ Failed to clear cache: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Cache test error: {e}")

def run_multiple_tests():
    """Run multiple performance tests"""
    test_plates = ["RJ62438", "ZD16048", "EL12345"]
    
    print(f"🔄 RUNNING MULTIPLE PERFORMANCE TESTS...")
    print("=" * 60)
    
    results = []
    
    for plate in test_plates:
        print(f"\n🧪 Testing license plate: {plate}")
        result = test_search_performance(plate)
        results.append({
            'license_plate': plate,
            'result': result
        })
        
        # Wait between tests to avoid rate limiting
        time.sleep(2)
    
    # Summary
    print(f"\n📊 PERFORMANCE TEST SUMMARY:")
    print("=" * 40)
    
    successful_tests = [r for r in results if r['result'].get('success')]
    
    if successful_tests:
        avg_response_time = sum(r['result']['response_time'] for r in successful_tests) / len(successful_tests)
        print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
        print(f"⏱️  Average response time: {avg_response_time:.2f} seconds")
        
        for result in results:
            plate = result['license_plate']
            if result['result'].get('success'):
                time_taken = result['result']['response_time']
                products = result['result']['results']['products_found']
                print(f"   {plate}: {time_taken:.2f}s → {products} products")
            else:
                error = result['result'].get('error', 'Unknown error')
                print(f"   {plate}: ❌ {error}")
    else:
        print(f"❌ No successful tests")
    
    return results

if __name__ == "__main__":
    print("🚀 STARTING PERFORMANCE TESTS FOR OPTIMIZED SEARCH...")
    print("=" * 60)
    
    # Test cache functionality first
    test_cache_functionality()
    
    # Run performance tests
    results = run_multiple_tests()
    
    print(f"\n🎯 PERFORMANCE TESTING COMPLETED!")
    print(f"Check the results above to see the performance improvements.")
