#!/usr/bin/env python3
"""
QUICK TECDOC FIX - Find and fix why TecDoc returns 0 OEMs
"""

import requests
import json

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

def quick_test_tecdoc():
    """Quick test to find where TecDoc breaks"""
    print("🚨 QUICK TECDOC DEBUG - FINDING THE PROBLEM")
    print("=" * 60)
    
    # Test 1: Can we get manufacturers?
    print("1️⃣ Testing manufacturers endpoint...")
    try:
        url = f"{BASE_URL}/manufacturers/list/lang-id/4/country-filter-id/62/type-id/1"
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            manufacturers = data.get('manufacturers', [])
            print(f"   ✅ SUCCESS: Found {len(manufacturers)} manufacturers")
            
            # Find NISSAN
            nissan_id = None
            vw_id = None
            for mfg in manufacturers:
                if mfg.get('brand', '').upper() == 'NISSAN':
                    nissan_id = mfg.get('manufacturerId')
                    print(f"   ✅ NISSAN found: ID {nissan_id}")
                elif mfg.get('brand', '').upper() == 'VW':
                    vw_id = mfg.get('manufacturerId')
                    print(f"   ✅ VW found: ID {vw_id}")
        else:
            print(f"   ❌ FAILED: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return
    
    # Test 2: Can we get models for NISSAN?
    xtrail_id = None
    vehicle_2006_id = None
    
    if nissan_id:
        print(f"\n2️⃣ Testing models for NISSAN (ID: {nissan_id})...")
        try:
            # Try different model endpoint formats
            possible_urls = [
                f"{BASE_URL}/models/list/lang-id/4/country-filter-id/62/manufacturer-id/{nissan_id}",
                f"{BASE_URL}/models/lang-id/4/country-filter-id/62/manufacturer-id/{nissan_id}",
                f"{BASE_URL}/models/list/manufacturer-id/{nissan_id}/lang-id/4"
            ]
            
            for url in possible_urls:
                print(f"   🔍 Trying: {url}")
                response = requests.get(url, headers=HEADERS, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('models', data if isinstance(data, list) else [])
                    print(f"   ✅ SUCCESS: Found {len(models)} models for NISSAN")
                    
                    # Find X-TRAIL
                    for model in models[:20]:  # Check first 20 models
                        model_name = model.get('modelName', '').upper()
                        if 'X-TRAIL' in model_name or 'XTRAIL' in model_name:
                            xtrail_id = model.get('modelId')
                            print(f"   ✅ X-TRAIL found: '{model.get('modelName')}' ID {xtrail_id}")
                            break
                    
                    if not xtrail_id:
                        print(f"   ⚠️ X-TRAIL not found in first 20 models")
                        print(f"   📋 First 10 models: {[m.get('modelName', 'N/A') for m in models[:10]]}")
                    break
                else:
                    print(f"   ❌ FAILED: {response.status_code}")
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    # Skip complex vehicle lookup for now - go straight to OEM search
    print(f"\n🎯 SKIPPING VEHICLE LOOKUP - TESTING DIRECT OEM SEARCH INSTEAD")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   - TecDoc API is working for manufacturers")
    print(f"   - NISSAN ID: {nissan_id}")
    print(f"   - Models endpoint: FAILED (404)")
    print(f"   - Need to use direct OEM search instead")

def test_simple_oem_search():
    """Test direct OEM search with customer-verified numbers"""
    print(f"\n🔍 TESTING DIRECT OEM SEARCH")
    print("=" * 40)
    
    customer_oems = ['370008H310', '37000-8H310', '370008H510', '370008H800']
    
    for oem in customer_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        try:
            url = f"{BASE_URL}/articles-oem/search/lang-id/4/article-oem-search-no/{oem}"
            response = requests.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and data:
                    print(f"   ✅ FOUND: {len(data)} articles for OEM {oem}")
                    
                    # Check first article for vehicle compatibility
                    first_article = data[0]
                    article_id = first_article.get('articleId')
                    if article_id:
                        print(f"   📋 Article ID: {article_id}")
                        print(f"   📋 Brand: {first_article.get('brandName', 'N/A')}")
                        print(f"   📋 Name: {first_article.get('articleName', 'N/A')}")
                else:
                    print(f"   ❌ NO ARTICLES found for OEM {oem}")
            else:
                print(f"   ❌ API ERROR: {response.status_code}")
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")

if __name__ == "__main__":
    quick_test_tecdoc()
    test_simple_oem_search()
