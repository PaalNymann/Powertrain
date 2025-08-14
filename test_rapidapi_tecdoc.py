#!/usr/bin/env python3
"""
RapidAPI TecDoc Test Script

Test script to explore RapidAPI TecDoc endpoints and compare with our current workflow.
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

class RapidAPITecDocTester:
    def __init__(self):
        self.headers = {
            'x-rapidapi-host': RAPIDAPI_HOST,
            'x-rapidapi-key': RAPIDAPI_KEY,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
    def make_request(self, endpoint, method='GET', data=None):
        """Make API request to RapidAPI TecDoc endpoint"""
        try:
            url = f"{BASE_URL}{endpoint}"
            print(f"🔗 {method} {url}")
            
            if method == 'GET':
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, data=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"✅ Success: {len(str(result))} chars response")
                    return result
                except json.JSONDecodeError:
                    print(f"⚠️  Non-JSON response: {response.text[:200]}...")
                    return response.text
            else:
                print(f"❌ Error: {response.text}")
                return None
                
        except Exception as e:
            print(f"💥 Exception: {e}")
            return None
    
    def test_post_endpoints(self):
        """Test POST endpoints for article details"""
        print("🚀 Testing POST TecDoc Endpoints")
        print("=" * 50)
        
        # Test 1: Get Complete Details for Article Number - POST
        print("\n1️⃣ Testing: Get Complete Details for Article Number (POST)")
        
        # Test with a known article number from our database
        test_data = {
            'articleNumber': '18-151101',  # Known driveshaft from our database
            'langId': '4',  # English
            'countryId': '62'  # Germany
        }
        
        article_details = self.make_request("/articles/article-number-details-post", method='POST', data=test_data)
        if article_details:
            print(f"   📋 Article details found: {type(article_details)}")
            if isinstance(article_details, dict):
                print(f"   🔍 Keys: {list(article_details.keys())}")
                if 'oem' in str(article_details).lower() or 'original' in str(article_details).lower():
                    print(f"   ✅ Contains OEM data!")
            print(f"   📄 Sample data: {str(article_details)[:200]}...")
        
        # Test 2: Search Articles by Article Number and Supplier ID (POST)
        print("\n2️⃣ Testing: Search Articles by Article Number (POST)")
        search_data = {
            'articleNumber': '18-151101',
            'langId': '4',
            'countryId': '62'
        }
        
        search_results = self.make_request("/articles/search-post", method='POST', data=search_data)
        if search_results:
            print(f"   📋 Search results: {type(search_results)}")
            print(f"   📄 Sample: {str(search_results)[:200]}...")
        
        return {
            'article_details': article_details,
            'search_results': search_results
        }
    
    def test_basic_endpoints(self):
        """Test basic GET TecDoc endpoints"""
        print("🚀 Testing Basic GET TecDoc Endpoints")
        print("=" * 50)
        
        # Test 1: Get all languages
        print("\n1️⃣ Testing: Get all Languages")
        languages = self.make_request("/languages")
        if languages:
            print(f"   📋 Found {len(languages) if isinstance(languages, list) else 'unknown'} languages")
            if isinstance(languages, list) and len(languages) > 0:
                print(f"   🔍 Sample: {languages[0] if languages else 'None'}")
        
        # Test 2: Get all countries
        print("\n2️⃣ Testing: Get All Countries")
        countries = self.make_request("/countries")
        if countries:
            print(f"   📋 Found {len(countries) if isinstance(countries, list) else 'unknown'} countries")
            if isinstance(countries, list) and len(countries) > 0:
                print(f"   🔍 Sample: {countries[0] if countries else 'None'}")
        
        # Test 3: Get manufacturers
        print("\n3️⃣ Testing: Get Manufacturers")
        manufacturers = self.make_request("/manufacturers?typeId=1&langId=4&countryId=62")
        if manufacturers:
            print(f"   📋 Found {len(manufacturers) if isinstance(manufacturers, list) else 'unknown'} manufacturers")
            if isinstance(manufacturers, list) and len(manufacturers) > 0:
                # Look for VOLVO
                volvo_mfr = None
                for mfr in manufacturers:
                    if isinstance(mfr, dict) and 'name' in mfr and 'VOLVO' in mfr['name'].upper():
                        volvo_mfr = mfr
                        break
                print(f"   🔍 VOLVO found: {volvo_mfr}")
        
        return {
            'languages': languages,
            'countries': countries,
            'manufacturers': manufacturers
        }
    
    def test_search_endpoints(self):
        """Test search-related endpoints"""
        print("\n🔍 Testing Search Endpoints")
        print("=" * 50)
        
        # Test 1: Search by OEM Number (using known OEM from our database)
        print("\n1️⃣ Testing: Search by OEM Number")
        oem_search = self.make_request("/search/oem/30735120")
        if oem_search:
            print(f"   📋 OEM 30735120 results: {len(oem_search) if isinstance(oem_search, list) else 'unknown'}")
            if isinstance(oem_search, list) and len(oem_search) > 0:
                print(f"   🔍 Sample result: {oem_search[0]}")
        
        # Test 2: Search by Article Number
        print("\n2️⃣ Testing: Search by Article Number")
        article_search = self.make_request("/search/article/18-151101")
        if article_search:
            print(f"   📋 Article search results: {len(article_search) if isinstance(article_search, list) else 'unknown'}")
        
        # Test 3: Get all Equal OEMs for an Article OEM Number
        print("\n3️⃣ Testing: Get all Equal OEMs")
        equal_oems = self.make_request("/search/equal-oems/30735120")
        if equal_oems:
            print(f"   📋 Equal OEMs for 30735120: {len(equal_oems) if isinstance(equal_oems, list) else 'unknown'}")
            if isinstance(equal_oems, list) and len(equal_oems) > 0:
                print(f"   🔍 Sample OEMs: {equal_oems[:3]}")
        
        return {
            'oem_search': oem_search,
            'article_search': article_search,
            'equal_oems': equal_oems
        }
    
    def test_vehicle_workflow(self):
        """Test complete vehicle workflow: VOLVO V70 2006"""
        print("\n🚗 Testing Vehicle Workflow: VOLVO V70 2006")
        print("=" * 50)
        
        # Step 1: Get vehicle types
        print("\n1️⃣ Getting vehicle types...")
        vehicle_types = self.make_request("/vehicles/types")
        if vehicle_types:
            print(f"   📋 Found {len(vehicle_types) if isinstance(vehicle_types, list) else 'unknown'} vehicle types")
            if isinstance(vehicle_types, list) and len(vehicle_types) > 0:
                print(f"   🔍 Sample type: {vehicle_types[0]}")
        
        # Step 2: Get manufacturers and find VOLVO
        print("\n2️⃣ Getting manufacturers...")
        manufacturers = self.make_request("/manufacturers?typeId=1&langId=4&countryId=62")
        
        volvo_id = None
        if isinstance(manufacturers, list):
            for mfr in manufacturers:
                if isinstance(mfr, dict) and 'name' in mfr and 'VOLVO' in mfr['name'].upper():
                    volvo_id = mfr.get('id') or mfr.get('manufacturerId')
                    print(f"   ✅ Found VOLVO: ID={volvo_id}, Name={mfr.get('name')}")
                    break
        
        if not volvo_id:
            print("   ❌ VOLVO not found in manufacturers")
            return None
        
        # Step 3: Get models for VOLVO
        print(f"\n3️⃣ Getting models for VOLVO (ID: {volvo_id})...")
        models = self.make_request(f"/models?manufacturerId={volvo_id}&langId=4&countryId=62")
        
        v70_model = None
        if isinstance(models, list):
            for model in models:
                if isinstance(model, dict) and 'name' in model and 'V70' in model['name'].upper():
                    v70_model = model
                    print(f"   ✅ Found V70: {model}")
                    break
        
        if not v70_model:
            print("   ❌ V70 model not found")
            return None
        
        # Step 4: Get vehicle engine types
        print(f"\n4️⃣ Getting vehicle engine types...")
        engine_types = self.make_request("/vehicles/engine-types")
        if engine_types:
            print(f"   📋 Found {len(engine_types) if isinstance(engine_types, list) else 'unknown'} engine types")
        
        # Step 5: Get articles for V70 (driveshafts)
        print(f"\n5️⃣ Getting articles for V70...")
        model_id = v70_model.get('id') or v70_model.get('modelId')
        articles = self.make_request(f"/articles?manufacturerId={volvo_id}&modelId={model_id}&langId=4&countryId=62")
        
        if articles:
            print(f"   📋 Found {len(articles) if isinstance(articles, list) else 'unknown'} articles")
            if isinstance(articles, list) and len(articles) > 0:
                print(f"   🔍 Sample article: {articles[0]}")
        
        return {
            'vehicle_types': vehicle_types,
            'volvo_id': volvo_id,
            'v70_model': v70_model,
            'engine_types': engine_types,
            'articles': articles
        }
    
    def run_full_test(self):
        """Run complete test suite"""
        print("🧪 RapidAPI TecDoc Test Suite")
        print("=" * 60)
        print(f"🕐 Started at: {datetime.now()}")
        print(f"🔑 API Key: {RAPIDAPI_KEY[:10]}...")
        print(f"🌐 Host: {RAPIDAPI_HOST}")
        
        results = {}
        
        try:
            # Test basic endpoints
            results['basic'] = self.test_basic_endpoints()
            
            # Test POST endpoints
            results['post'] = self.test_post_endpoints()
            
            # Test search endpoints
            results['search'] = self.test_search_endpoints()
            
            # Test vehicle workflow
            results['vehicle_workflow'] = self.test_vehicle_workflow()
            
            print(f"\n🏁 Test completed at: {datetime.now()}")
            return results
            
        except Exception as e:
            print(f"💥 Test suite failed: {e}")
            return None

def main():
    """Main function"""
    tester = RapidAPITecDocTester()
    results = tester.run_full_test()
    
    if results:
        print("\n📊 SUMMARY")
        print("=" * 30)
        for category, data in results.items():
            if data:
                print(f"✅ {category}: Success")
            else:
                print(f"❌ {category}: Failed")
    else:
        print("❌ Test suite failed completely")

if __name__ == "__main__":
    main()
