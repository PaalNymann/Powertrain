#!/usr/bin/env python3
"""
TecDoc RapidAPI Endpoint Explorer
Systematically explore all available endpoints to find working VIN lookup
"""

import requests
import json
import time

class TecDocEndpointExplorer:
    """Explore TecDoc RapidAPI endpoints systematically"""
    
    def __init__(self):
        self.rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
        self.base_url = "https://tecdoc-catalog.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
            'x-rapidapi-key': self.rapidapi_key
        }
        self.lang_id = 4  # English
    
    def test_endpoint(self, endpoint: str, description: str = "") -> dict:
        """Test a single endpoint and return results"""
        print(f"🔍 Testing: {endpoint}")
        if description:
            print(f"   Description: {description}")
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            result = {
                'endpoint': endpoint,
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'response_size': len(response.text) if response.text else 0,
                'content_type': response.headers.get('content-type', ''),
                'data': None,
                'error': None
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result['data'] = data
                    result['data_type'] = type(data).__name__
                    result['data_length'] = len(data) if isinstance(data, (list, dict)) else 0
                    print(f"   ✅ SUCCESS: {response.status_code} - {result['data_type']} with {result['data_length']} items")
                    
                    # Show sample data
                    if isinstance(data, list) and data:
                        print(f"   📋 Sample: {data[0] if len(str(data[0])) < 100 else str(data[0])[:100]+'...'}")
                    elif isinstance(data, dict):
                        keys = list(data.keys())[:5]
                        print(f"   📋 Keys: {keys}")
                        
                except json.JSONDecodeError:
                    result['data'] = response.text[:200]
                    print(f"   ✅ SUCCESS: {response.status_code} - Non-JSON response")
            else:
                result['error'] = response.text[:200] if response.text else f"HTTP {response.status_code}"
                print(f"   ❌ FAILED: {response.status_code} - {result['error']}")
            
            return result
            
        except Exception as e:
            result = {
                'endpoint': endpoint,
                'status_code': None,
                'success': False,
                'error': str(e),
                'data': None
            }
            print(f"   ❌ ERROR: {e}")
            return result
    
    def explore_basic_endpoints(self):
        """Explore basic TecDoc endpoints to understand API structure"""
        print("🚀 EXPLORING BASIC TECDOC ENDPOINTS")
        print("=" * 60)
        
        basic_endpoints = [
            ("/", "Root endpoint"),
            (f"/manufacturers/lang-id/{self.lang_id}", "All manufacturers"),
            (f"/product-groups/lang-id/{self.lang_id}", "All product groups"),
            ("/countries", "All countries"),
            ("/languages", "All languages"),
        ]
        
        results = []
        for endpoint, description in basic_endpoints:
            result = self.test_endpoint(endpoint, description)
            results.append(result)
            time.sleep(0.5)  # Rate limiting
        
        return results
    
    def explore_vin_endpoints(self, vin: str = "JN1TENT30U0217281"):
        """Explore all possible VIN-related endpoints"""
        print(f"\n🎯 EXPLORING VIN ENDPOINTS FOR: {vin}")
        print("=" * 60)
        
        vin_endpoints = [
            # Direct VIN endpoints
            (f"/vin/{vin}", "Direct VIN lookup"),
            (f"/vin-decode/{vin}", "VIN decode"),
            (f"/vin-decoder/{vin}", "VIN decoder"),
            (f"/decode-vin/{vin}", "Decode VIN"),
            (f"/vehicle/vin/{vin}", "Vehicle by VIN"),
            (f"/vehicles/vin/{vin}", "Vehicles by VIN"),
            (f"/vehicle-data/vin/{vin}", "Vehicle data by VIN"),
            (f"/vehicle-info/vin/{vin}", "Vehicle info by VIN"),
            
            # VIN with language
            (f"/vin/{vin}/lang-id/{self.lang_id}", "VIN with language"),
            (f"/vehicle/vin/{vin}/lang-id/{self.lang_id}", "Vehicle VIN with language"),
            (f"/vehicles/vin/{vin}/lang-id/{self.lang_id}", "Vehicles VIN with language"),
            
            # VIN search endpoints
            (f"/search/vin/{vin}", "Search by VIN"),
            (f"/vehicle/search/vin/{vin}", "Vehicle search by VIN"),
            (f"/vehicles/search/vin/{vin}", "Vehicles search by VIN"),
            (f"/articles/search/vin/{vin}", "Articles search by VIN"),
            (f"/parts/search/vin/{vin}", "Parts search by VIN"),
            
            # VIN with language in search
            (f"/search/vin/{vin}/lang-id/{self.lang_id}", "Search VIN with language"),
            (f"/articles/search/vin/{vin}/lang-id/{self.lang_id}", "Articles search VIN with language"),
            (f"/parts/search/vin/{vin}/lang-id/{self.lang_id}", "Parts search VIN with language"),
        ]
        
        results = []
        for endpoint, description in vin_endpoints:
            result = self.test_endpoint(endpoint, description)
            results.append(result)
            time.sleep(0.5)  # Rate limiting
        
        return results
    
    def explore_nissan_endpoints(self):
        """Explore Nissan-specific endpoints"""
        print(f"\n🚗 EXPLORING NISSAN-SPECIFIC ENDPOINTS")
        print("=" * 60)
        
        # First, try to find Nissan manufacturer ID
        manufacturers_result = self.test_endpoint(f"/manufacturers/lang-id/{self.lang_id}", "Get all manufacturers")
        
        nissan_id = None
        if manufacturers_result['success'] and manufacturers_result['data']:
            manufacturers = manufacturers_result['data']
            if isinstance(manufacturers, list):
                for mfr in manufacturers:
                    if isinstance(mfr, dict):
                        name = mfr.get('manufacturerName', '').upper()
                        if 'NISSAN' in name:
                            nissan_id = mfr.get('manufacturerId')
                            print(f"   ✅ Found Nissan: {name} (ID: {nissan_id})")
                            break
        
        if not nissan_id:
            print("   ❌ Nissan manufacturer ID not found")
            return []
        
        # Test Nissan-specific endpoints
        nissan_endpoints = [
            (f"/vehicles/manufacturer-id/{nissan_id}/lang-id/{self.lang_id}", "Nissan vehicles"),
            (f"/models/manufacturer-id/{nissan_id}/lang-id/{self.lang_id}", "Nissan models"),
            (f"/vehicle-types/manufacturer-id/{nissan_id}/lang-id/{self.lang_id}", "Nissan vehicle types"),
        ]
        
        results = []
        for endpoint, description in nissan_endpoints:
            result = self.test_endpoint(endpoint, description)
            results.append(result)
            time.sleep(0.5)
        
        return results
    
    def comprehensive_exploration(self):
        """Run comprehensive exploration of TecDoc endpoints"""
        print("🎯 COMPREHENSIVE TECDOC RAPIDAPI EXPLORATION")
        print("Finding working endpoints for VIN lookup and Nissan support")
        print("=" * 80)
        
        all_results = []
        
        # Basic endpoints
        basic_results = self.explore_basic_endpoints()
        all_results.extend(basic_results)
        
        # VIN endpoints
        vin_results = self.explore_vin_endpoints()
        all_results.extend(vin_results)
        
        # Nissan endpoints
        nissan_results = self.explore_nissan_endpoints()
        all_results.extend(nissan_results)
        
        # Summary
        print(f"\n📊 EXPLORATION SUMMARY")
        print("=" * 40)
        
        successful_endpoints = [r for r in all_results if r['success']]
        failed_endpoints = [r for r in all_results if not r['success']]
        
        print(f"Total endpoints tested: {len(all_results)}")
        print(f"Successful endpoints: {len(successful_endpoints)}")
        print(f"Failed endpoints: {len(failed_endpoints)}")
        
        if successful_endpoints:
            print(f"\n✅ WORKING ENDPOINTS:")
            for result in successful_endpoints:
                print(f"   {result['endpoint']} - {result.get('data_type', 'unknown')} with {result.get('data_length', 0)} items")
        
        if failed_endpoints:
            print(f"\n❌ FAILED ENDPOINTS:")
            for result in failed_endpoints[:10]:  # Show first 10 failures
                print(f"   {result['endpoint']} - {result.get('error', 'Unknown error')}")
        
        return all_results

def main():
    """Main exploration function"""
    explorer = TecDocEndpointExplorer()
    results = explorer.comprehensive_exploration()
    
    # Save results to file for analysis
    with open('/Users/nyman/powertrain_system/tecdoc_exploration_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: tecdoc_exploration_results.json")

if __name__ == "__main__":
    main()
