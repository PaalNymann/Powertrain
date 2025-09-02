#!/usr/bin/env python3
"""
Inspect TecDoc article details to understand the data structure
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

LANG_ID = 4  # English
COUNTRY_ID = 62  # Germany

def inspect_article_details():
    """Inspect the full structure of article details for Nissan OEM"""
    
    print("🔍 INSPECTING TECDOC ARTICLE DETAILS")
    print("=" * 50)
    
    # Use known working Nissan OEM
    oem = "370008H310"
    
    print(f"🔍 Getting articles for OEM: {oem}")
    
    # Step 1: Get articles for this OEM
    search_url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem}"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        print(f"Search status: {response.status_code}")
        
        if response.status_code == 200:
            articles = response.json()
            if isinstance(articles, list) and articles:
                print(f"✅ Found {len(articles)} articles")
                
                # Take first article
                article = articles[0]
                article_id = article.get('articleId')
                
                print(f"\n📋 First article structure:")
                print(json.dumps(article, indent=2))
                
                if article_id:
                    print(f"\n🔍 Getting details for article ID: {article_id}")
                    
                    # Step 2: Get full article details
                    details_url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}"
                    
                    details_response = requests.get(details_url, headers=HEADERS, timeout=15)
                    print(f"Details status: {details_response.status_code}")
                    
                    if details_response.status_code == 200:
                        details = details_response.json()
                        
                        print(f"\n📋 FULL ARTICLE DETAILS STRUCTURE:")
                        print("=" * 50)
                        print(json.dumps(details, indent=2))
                        
                        print(f"\n🔑 TOP-LEVEL KEYS:")
                        for key in details.keys():
                            value = details[key]
                            if isinstance(value, list):
                                print(f"  {key}: list with {len(value)} items")
                            elif isinstance(value, dict):
                                print(f"  {key}: dict with keys: {list(value.keys())}")
                            else:
                                print(f"  {key}: {type(value).__name__} = {value}")
                        
                        # Look for any vehicle-related data
                        print(f"\n🚗 SEARCHING FOR VEHICLE-RELATED DATA:")
                        vehicle_keys = []
                        for key, value in details.items():
                            if any(term in key.lower() for term in ['vehicle', 'car', 'model', 'manufacturer', 'compatible', 'application']):
                                vehicle_keys.append(key)
                                print(f"  Found: {key} = {value}")
                        
                        if not vehicle_keys:
                            print("  ❌ No obvious vehicle-related keys found")
                            
                        # Check if there are nested objects with vehicle data
                        print(f"\n🔍 CHECKING NESTED OBJECTS FOR VEHICLE DATA:")
                        def search_nested(obj, path=""):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    current_path = f"{path}.{key}" if path else key
                                    if any(term in key.lower() for term in ['vehicle', 'car', 'model', 'manufacturer', 'compatible', 'application']):
                                        print(f"  Found nested: {current_path} = {value}")
                                    if isinstance(value, (dict, list)):
                                        search_nested(value, current_path)
                            elif isinstance(obj, list):
                                for i, item in enumerate(obj):
                                    search_nested(item, f"{path}[{i}]")
                        
                        search_nested(details)
                        
                    else:
                        print(f"❌ Failed to get article details: {details_response.status_code}")
                        print(f"Error: {details_response.text}")
                else:
                    print(f"❌ No article ID found")
            else:
                print(f"❌ No articles found")
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    inspect_article_details()
