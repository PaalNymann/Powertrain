#!/usr/bin/env python3
"""
Test direct OEM search strategy locally to debug why it's not working for ZT41818
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

def test_direct_oem_search_for_nissan():
    """Test direct OEM search for known Nissan X-Trail OEMs"""
    
    print("🔍 TESTING DIRECT OEM SEARCH FOR NISSAN X-TRAIL 2006")
    print("=" * 60)
    
    # Known OEMs for MA18002 (customer-verified Nissan X-Trail part)
    test_oems = [
        '370008H310',
        '370008H510', 
        '370008H800',
        '37000-8H310',
        '37000-8H510',
        '37000-8H800'
    ]
    
    brand = "NISSAN"
    model = "X-TRAIL"
    year = 2006
    
    compatible_oems = []
    
    for oem in test_oems:
        print(f"\n🔍 Testing OEM: {oem}")
        
        # Step 1: Search for articles with this OEM
        search_url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem}"
        
        try:
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            print(f"   Search status: {response.status_code}")
            
            if response.status_code == 200:
                articles = response.json()
                if isinstance(articles, list) and articles:
                    print(f"   ✅ Found {len(articles)} articles for OEM {oem}")
                    
                    # Step 2: Check vehicle compatibility for first article
                    article = articles[0]
                    article_id = article.get('articleId')
                    
                    if article_id:
                        print(f"   🔍 Checking compatibility for article ID: {article_id}")
                        
                        details_url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}"
                        
                        details_response = requests.get(details_url, headers=HEADERS, timeout=15)
                        print(f"   Details status: {details_response.status_code}")
                        
                        if details_response.status_code == 200:
                            details = details_response.json()
                            
                            # Look for vehicle compatibility data
                            vehicles = (details.get('compatibleCars', []) or 
                                      details.get('vehicles', []) or
                                      details.get('vehicleCompatibility', []))
                            
                            print(f"   📋 Found {len(vehicles)} compatible vehicles")
                            
                            if vehicles:
                                # Check if any vehicle matches Nissan X-Trail
                                for vehicle in vehicles[:5]:  # Check first 5
                                    vehicle_brand = vehicle.get('manufacturerName', '').upper()
                                    vehicle_model = vehicle.get('modelName', '').upper()
                                    year_start = vehicle.get('constructionIntervalStart', '')
                                    year_end = vehicle.get('constructionIntervalEnd', '')
                                    
                                    print(f"      🚗 {vehicle_brand} {vehicle_model} ({year_start}-{year_end})")
                                    
                                    # Check if this matches our search criteria
                                    if ('NISSAN' in vehicle_brand and 
                                        'X-TRAIL' in vehicle_model):
                                        
                                        # Check year compatibility
                                        year_compatible = False
                                        if year_start and year_end:
                                            try:
                                                if int(year_start) <= year <= int(year_end):
                                                    year_compatible = True
                                            except:
                                                pass
                                        else:
                                            year_compatible = True  # No year info, assume compatible
                                        
                                        if year_compatible:
                                            print(f"      ✅ COMPATIBLE! {oem} matches {brand} {model} {year}")
                                            compatible_oems.append(oem)
                                            break
                                        else:
                                            print(f"      ❌ Wrong year range: {year_start}-{year_end}")
                            else:
                                print(f"   ❌ No vehicle compatibility data found")
                        else:
                            print(f"   ❌ Failed to get article details: {details_response.status_code}")
                    else:
                        print(f"   ❌ No article ID found")
                else:
                    print(f"   ❌ No articles found for OEM {oem}")
            else:
                print(f"   ❌ OEM search failed: {response.status_code}")
                if response.status_code == 404:
                    print(f"   ❌ OEM {oem} not found in TecDoc")
                    
        except Exception as e:
            print(f"   ❌ Error testing OEM {oem}: {e}")
    
    print(f"\n🎯 RESULTS:")
    print(f"Compatible OEMs found: {len(compatible_oems)}")
    print(f"Compatible OEMs: {compatible_oems}")
    
    if compatible_oems:
        print(f"✅ SUCCESS! Direct OEM search found {len(compatible_oems)} compatible OEMs")
        print(f"✅ This proves the strategy works - need to debug production implementation")
    else:
        print(f"❌ FAILURE! No compatible OEMs found")
        print(f"❌ Either the OEMs are wrong or TecDoc doesn't have this data")

if __name__ == "__main__":
    test_direct_oem_search_for_nissan()
