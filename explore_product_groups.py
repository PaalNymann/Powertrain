#!/usr/bin/env python3
"""
Explore TecDoc product groups to find correct IDs for drivaksler/mellomaksler
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

LANG_ID = 4  # English
COUNTRY_ID = 62  # Germany
TYPE_ID = 1  # Passenger cars

def explore_product_groups():
    """Explore available product groups in TecDoc"""
    
    print("🔍 EXPLORING TECDOC PRODUCT GROUPS")
    print("=" * 50)
    
    # Try to find product groups endpoint
    possible_endpoints = [
        "/product-groups/list",
        "/productgroups/list",
        "/product-groups",
        "/productgroups",
        "/groups/list",
        "/categories/list",
        f"/product-groups/list/lang-id/{LANG_ID}",
        f"/productgroups/list/lang-id/{LANG_ID}",
        f"/product-groups/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
        f"/productgroups/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}",
    ]
    
    print("🔍 Testing product group endpoints...")
    
    for endpoint in possible_endpoints:
        print(f"\n🔍 Testing: {endpoint}")
        url = BASE_URL + endpoint
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   🎯 SUCCESS! Found product groups endpoint")
                
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())}")
                    
                    # Look for product groups
                    groups = data.get('productGroups', data.get('groups', data.get('categories', [])))
                    if groups:
                        print(f"   Found {len(groups)} product groups:")
                        
                        # Look for drive shaft related groups
                        drive_related = []
                        for group in groups:
                            if isinstance(group, dict):
                                group_id = group.get('productGroupId', group.get('groupId', group.get('id')))
                                group_name = group.get('productGroupName', group.get('groupName', group.get('name', '')))
                                
                                # Check for drive shaft related terms
                                name_lower = group_name.lower()
                                if any(term in name_lower for term in ['drive', 'shaft', 'axle', 'cv', 'joint', 'transmission']):
                                    drive_related.append((group_id, group_name))
                                    print(f"      🎯 DRIVE-RELATED: {group_id} - {group_name}")
                                else:
                                    print(f"         {group_id} - {group_name}")
                        
                        if drive_related:
                            print(f"\n🎯 Found {len(drive_related)} drive-related product groups:")
                            for group_id, group_name in drive_related:
                                print(f"   {group_id}: {group_name}")
                        
                        return groups
                        
                elif isinstance(data, list):
                    print(f"   List with {len(data)} items")
                    if data:
                        print(f"   Sample item: {data[0]}")
                        return data
                        
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            else:
                print(f"   Status {response.status_code}")
                
        except Exception as e:
            print(f"   Exception: {e}")
    
    print(f"\n❌ No product groups endpoint found")
    return None

def test_known_product_groups():
    """Test our known product group IDs with different vehicles"""
    
    print(f"\n🔍 TESTING KNOWN PRODUCT GROUP IDS")
    print("=" * 50)
    
    # Test with different vehicles and product groups
    test_cases = [
        # Mercedes GLK (known working)
        (19942, 184, "Mercedes GLK"),
        # Nissan X-Trail (our target)
        (4784, 80, "Nissan X-Trail"),
        # Try a few other random vehicle IDs
        (1000, 184, "Test Vehicle 1000"),
        (5000, 80, "Test Vehicle 5000"),
    ]
    
    product_groups = [
        (100260, "Drivaksler"),
        (100270, "Mellomaksler"),
        (100000, "Test Group 100000"),
        (100100, "Test Group 100100"),
        (100200, "Test Group 100200"),
        (100300, "Test Group 100300"),
    ]
    
    for vehicle_id, manufacturer_id, vehicle_name in test_cases:
        print(f"\n🔍 Testing vehicle: {vehicle_name} (ID: {vehicle_id})")
        
        for product_group_id, group_name in product_groups:
            url = (f"{BASE_URL}/articles/list/"
                   f"vehicle-id/{vehicle_id}/"
                   f"product-group-id/{product_group_id}/"
                   f"manufacturer-id/{manufacturer_id}/"
                   f"lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}")
            
            try:
                response = requests.get(url, headers=HEADERS, timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    count = data.get('countArticles', 0)
                    if count > 0:
                        articles = data.get('articles', [])
                        sample_article = articles[0] if articles else {}
                        article_name = sample_article.get('articleProductName', 'N/A')
                        print(f"   ✅ {group_name} ({product_group_id}): {count} articles - Sample: {article_name}")
                    else:
                        print(f"   ❌ {group_name} ({product_group_id}): 0 articles")
                else:
                    print(f"   ❌ {group_name} ({product_group_id}): HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {group_name} ({product_group_id}): Exception {e}")

def find_drive_shaft_articles():
    """Search for drive shaft articles using OEM search"""
    
    print(f"\n🔍 SEARCHING FOR DRIVE SHAFT ARTICLES BY OEM")
    print("=" * 50)
    
    # Known Nissan OEMs for drive shafts
    nissan_oems = [
        "370008H310",
        "370008H510", 
        "370008H800"
    ]
    
    for oem in nissan_oems:
        print(f"\n🔍 Searching for OEM: {oem}")
        
        url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                articles = response.json()
                if articles:
                    print(f"   ✅ Found {len(articles)} articles for OEM {oem}")
                    
                    for i, article in enumerate(articles[:3]):
                        article_id = article.get('articleId')
                        article_name = article.get('articleProductName', 'N/A')
                        supplier = article.get('supplierName', 'N/A')
                        print(f"      {i+1}. {article_name} (ID: {article_id}, Supplier: {supplier})")
                        
                        # Try to determine product group from article details
                        details_url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}"
                        try:
                            details_response = requests.get(details_url, headers=HEADERS, timeout=8)
                            if details_response.status_code == 200:
                                details = details_response.json()
                                # Look for any product group information
                                print(f"         Article details keys: {list(details.keys())}")
                        except:
                            pass
                else:
                    print(f"   ❌ No articles found for OEM {oem}")
            else:
                print(f"   ❌ OEM search failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception searching OEM {oem}: {e}")

if __name__ == "__main__":
    # Step 1: Try to find product groups endpoint
    groups = explore_product_groups()
    
    # Step 2: Test known product group IDs
    test_known_product_groups()
    
    # Step 3: Search for drive shaft articles by OEM
    find_drive_shaft_articles()
