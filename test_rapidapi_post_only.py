#!/usr/bin/env python3
"""
RapidAPI TecDoc POST Endpoint Test

Focus on testing the working POST endpoints with different parameter combinations.
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# RapidAPI TecDoc configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
RAPIDAPI_HOST = "tecdoc-catalog.p.rapidapi.com"
BASE_URL = f"https://{RAPIDAPI_HOST}"

class RapidAPIPostTester:
    def __init__(self):
        self.headers = {
            'x-rapidapi-host': RAPIDAPI_HOST,
            'x-rapidapi-key': RAPIDAPI_KEY,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
    def test_post_endpoint(self, endpoint, data, description):
        """Test a specific POST endpoint with given data"""
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"\n🔗 Testing: {description}")
            print(f"   URL: POST {url}")
            print(f"   Data: {data}")
            
            response = requests.post(url, headers=self.headers, data=data, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   ✅ Success: {json.dumps(result, indent=2)}")
                    return result
                except json.JSONDecodeError:
                    print(f"   ⚠️  Non-JSON response: {response.text}")
                    return response.text
            else:
                print(f"   ❌ Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
            return None
    
    def test_article_details_variations(self):
        """Test article details POST endpoint with different parameter combinations"""
        print("🧪 Testing Article Details POST Endpoint Variations")
        print("=" * 60)
        
        endpoint = "/articles/article-number-details-post"
        
        # Test 1: Basic parameters
        test_data_1 = {
            'articleNumber': '18-151101',
            'langId': '4',
            'countryId': '62'
        }
        result1 = self.test_post_endpoint(endpoint, test_data_1, "Basic parameters")
        
        # Test 2: Different article number (known OEM from our database)
        test_data_2 = {
            'articleNumber': '30735120',
            'langId': '4',
            'countryId': '62'
        }
        result2 = self.test_post_endpoint(endpoint, test_data_2, "Known OEM as article number")
        
        # Test 3: Add supplier ID
        test_data_3 = {
            'articleNumber': '18-151101',
            'supplierId': '1',
            'langId': '4',
            'countryId': '62'
        }
        result3 = self.test_post_endpoint(endpoint, test_data_3, "With supplier ID")
        
        # Test 4: Different language (German)
        test_data_4 = {
            'articleNumber': '18-151101',
            'langId': '1',  # German
            'countryId': '62'
        }
        result4 = self.test_post_endpoint(endpoint, test_data_4, "German language")
        
        # Test 5: Try with common part numbers
        common_parts = ['CV-1001', 'GSP-1234', 'FEBI-12345', 'SKF-9876']
        for part in common_parts:
            test_data = {
                'articleNumber': part,
                'langId': '4',
                'countryId': '62'
            }
            self.test_post_endpoint(endpoint, test_data, f"Common part: {part}")
        
        return {
            'basic': result1,
            'oem_as_article': result2,
            'with_supplier': result3,
            'german_lang': result4
        }
    
    def test_search_post_variations(self):
        """Test different POST search endpoints"""
        print("\n🔍 Testing Search POST Endpoint Variations")
        print("=" * 60)
        
        # Try different possible search POST endpoints
        search_endpoints = [
            "/search/articles",
            "/articles/search",
            "/search-articles",
            "/search/article-number",
            "/articles/search-by-number"
        ]
        
        test_data = {
            'articleNumber': '18-151101',
            'langId': '4',
            'countryId': '62'
        }
        
        results = {}
        for endpoint in search_endpoints:
            result = self.test_post_endpoint(endpoint, test_data, f"Search endpoint: {endpoint}")
            results[endpoint] = result
        
        return results
    
    def run_focused_test(self):
        """Run focused POST endpoint tests"""
        print("🎯 RapidAPI TecDoc POST-Only Test Suite")
        print("=" * 70)
        print(f"🕐 Started at: {datetime.now()}")
        
        results = {}
        
        try:
            # Test article details variations
            results['article_details'] = self.test_article_details_variations()
            
            # Test search POST variations
            results['search_posts'] = self.test_search_post_variations()
            
            print(f"\n🏁 Test completed at: {datetime.now()}")
            
            # Summary
            print("\n📊 SUMMARY")
            print("=" * 30)
            working_endpoints = []
            for category, tests in results.items():
                if isinstance(tests, dict):
                    for test_name, result in tests.items():
                        if result is not None:
                            working_endpoints.append(f"{category}.{test_name}")
            
            if working_endpoints:
                print("✅ Working tests:")
                for endpoint in working_endpoints:
                    print(f"   - {endpoint}")
            else:
                print("❌ No working endpoints found")
            
            return results
            
        except Exception as e:
            print(f"💥 Test suite failed: {e}")
            return None

def main():
    """Main function"""
    tester = RapidAPIPostTester()
    results = tester.run_focused_test()

if __name__ == "__main__":
    main()
