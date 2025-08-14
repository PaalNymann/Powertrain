#!/usr/bin/env python3
"""
Test script for RapidAPI TecDoc search endpoints
Tests the three main search endpoints needed for vehicle parts lookup
"""

import requests
import json
import time

# RapidAPI TecDoc configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

def test_search_by_oem():
    """Test 1: Search by OEM Number"""
    print("\n" + "="*60)
    print("TEST 1: Search by OEM Number")
    print("="*60)
    
    # Test with known OEM numbers from our database
    test_oem_numbers = [
        "8F0513035N",  # From the example
        "8252034",     # Known CV joint OEM from our database
        "30735120",    # Another known CV joint OEM
        "045115466"    # VAG OEM from previous test
    ]
    
    for oem_no in test_oem_numbers:
        print(f"\n🔍 Testing OEM: {oem_no}")
        url = f"{BASE_URL}/articles-oem/search/lang-id/4/article-oem-search-no/{oem_no}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response type: {type(data)}")
                if isinstance(data, list):
                    print(f"Found {len(data)} articles")
                    if data:
                        print(f"First article: {data[0].get('articleNo', 'N/A')} - {data[0].get('articleProductName', 'N/A')}")
                elif isinstance(data, dict):
                    print(f"Response keys: {list(data.keys())}")
                    if 'articles' in data:
                        print(f"Found {len(data['articles'])} articles")
                else:
                    print(f"Response: {str(data)[:200]}...")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")
        
        time.sleep(1)  # Rate limiting

def test_get_models():
    """Test 2: Get Models for Manufacturer"""
    print("\n" + "="*60)
    print("TEST 2: Get Models for Manufacturer")
    print("="*60)
    
    # Test with known manufacturer IDs
    test_manufacturers = [
        {"id": 184, "name": "Unknown (from example)"},
        {"id": 120, "name": "VOLVO"},  # From our Apify memory
        {"id": 1, "name": "Test manufacturer"}
    ]
    
    for mfg in test_manufacturers:
        print(f"\n🏭 Testing Manufacturer: {mfg['name']} (ID: {mfg['id']})")
        url = f"{BASE_URL}/models/list/manufacturer-id/{mfg['id']}/lang-id/4/country-filter-id/62/type-id/1"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response type: {type(data)}")
                if isinstance(data, list):
                    print(f"Found {len(data)} models")
                    if data:
                        # Show first few models
                        for i, model in enumerate(data[:3]):
                            if isinstance(model, dict):
                                print(f"  Model {i+1}: {model.get('modelName', 'N/A')} (ID: {model.get('modelId', 'N/A')})")
                            else:
                                print(f"  Model {i+1}: {model}")
                elif isinstance(data, dict):
                    print(f"Response keys: {list(data.keys())}")
                else:
                    print(f"Response: {str(data)[:200]}...")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")
        
        time.sleep(1)

def test_get_articles_list():
    """Test 3: Get Articles List for Vehicle"""
    print("\n" + "="*60)
    print("TEST 3: Get Articles List for Vehicle")
    print("="*60)
    
    # Test with parameters from the example
    # vehicle-id/19942/product-group-id/100260/manufacturer-id/184
    test_params = [
        {
            "vehicle_id": 19942,
            "product_group_id": 100260,  # Drivaksler from our memory
            "manufacturer_id": 184,
            "description": "Example from RapidAPI"
        },
        {
            "vehicle_id": 19942,
            "product_group_id": 100260,
            "manufacturer_id": 120,  # VOLVO
            "description": "VOLVO with Drivaksler category"
        }
    ]
    
    for params in test_params:
        print(f"\n🚗 Testing: {params['description']}")
        print(f"   Vehicle ID: {params['vehicle_id']}")
        print(f"   Product Group: {params['product_group_id']} (Drivaksler)")
        print(f"   Manufacturer: {params['manufacturer_id']}")
        
        url = (f"{BASE_URL}/articles/list/"
               f"vehicle-id/{params['vehicle_id']}/"
               f"product-group-id/{params['product_group_id']}/"
               f"manufacturer-id/{params['manufacturer_id']}/"
               f"lang-id/4/country-filter-id/62/type-id/1")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response type: {type(data)}")
                if isinstance(data, list):
                    print(f"Found {len(data)} articles")
                    if data:
                        # Show first article with OEM info
                        article = data[0]
                        if isinstance(article, dict):
                            print(f"  Article: {article.get('articleNo', 'N/A')} - {article.get('articleProductName', 'N/A')}")
                            if 'oemNo' in article:
                                print(f"  OEM Numbers: {len(article['oemNo'])} found")
                                for oem in article['oemNo'][:3]:  # Show first 3
                                    print(f"    {oem.get('oemBrand', 'N/A')}: {oem.get('oemDisplayNo', 'N/A')}")
                elif isinstance(data, dict):
                    print(f"Response keys: {list(data.keys())}")
                    if 'articles' in data:
                        print(f"Found {len(data['articles'])} articles")
                else:
                    print(f"Response: {str(data)[:200]}...")
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")
        
        time.sleep(1)

def main():
    """Run all tests"""
    print("🚀 Starting RapidAPI TecDoc Search Endpoints Test")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key: {RAPIDAPI_KEY[:20]}...")
    
    try:
        # Test 1: Search by OEM
        test_search_by_oem()
        
        # Test 2: Get Models
        test_get_models()
        
        # Test 3: Get Articles List
        test_get_articles_list()
        
        print("\n" + "="*60)
        print("✅ All tests completed!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
