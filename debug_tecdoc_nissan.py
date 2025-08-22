#!/usr/bin/env python3
"""
Debug TecDoc lookup for Nissan X-Trail 2006 (ZT41818)
Find out why we get wrong OEMs (LXS 41/1) instead of correct ones (370008H310)
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
TYPE_ID = 1  # Automobile

def debug_nissan_lookup():
    """Debug step-by-step TecDoc lookup for Nissan X-Trail 2006"""
    
    print("🔍 DEBUGGING: TecDoc lookup for NISSAN X-TRAIL 2006")
    print("=" * 60)
    
    # Step 1: Get all manufacturers
    print("\n📋 Step 1: Getting manufacturers...")
    url = f"{BASE_URL}/manufacturers/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            manufacturers = data.get('manufacturers', [])
            print(f"✅ Found {len(manufacturers)} manufacturers")
            
            # Find Nissan
            nissan_id = None
            for mfg in manufacturers:
                brand = mfg.get('brand', '').upper()
                if 'NISSAN' in brand:
                    nissan_id = mfg.get('manufacturerId')
                    print(f"✅ Found Nissan: {brand} (ID: {nissan_id})")
                    break
            
            if not nissan_id:
                print("❌ Nissan not found in manufacturers!")
                return
                
        else:
            print(f"❌ Failed to get manufacturers: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error getting manufacturers: {e}")
        return
    
    # Step 2: Get models for Nissan
    print(f"\n📋 Step 2: Getting models for Nissan (ID: {nissan_id})...")
    url = f"{BASE_URL}/models/list/manufacturer-id/{nissan_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"✅ Found {len(models)} Nissan models")
            
            # Find X-Trail models
            xtrail_models = []
            for model in models:
                model_name = model.get('modelName', '').upper()
                if 'X-TRAIL' in model_name or 'XTRAIL' in model_name:
                    year_from = model.get('yearFrom', 'N/A')
                    year_to = model.get('yearTo', 'N/A')
                    vehicle_id = model.get('vehicleId') or model.get('modelId')
                    xtrail_models.append({
                        'name': model_name,
                        'year_from': year_from,
                        'year_to': year_to,
                        'vehicle_id': vehicle_id,
                        'full_data': model
                    })
                    print(f"🔍 X-Trail variant: {model_name} ({year_from}-{year_to}) ID: {vehicle_id}")
            
            if not xtrail_models:
                print("❌ No X-Trail models found!")
                return
                
            # Find best match for 2006
            best_match = None
            for model in xtrail_models:
                year_from = model['year_from']
                year_to = model['year_to']
                
                if year_from != 'N/A' and year_to != 'N/A':
                    try:
                        if int(year_from) <= 2006 <= int(year_to):
                            best_match = model
                            print(f"✅ Best match for 2006: {model['name']} ({year_from}-{year_to}) ID: {model['vehicle_id']}")
                            break
                    except ValueError:
                        pass
            
            if not best_match:
                # Use first X-Trail if no year match
                best_match = xtrail_models[0]
                print(f"⚠️ No year match, using first: {best_match['name']} ID: {best_match['vehicle_id']}")
                
        else:
            print(f"❌ Failed to get models: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error getting models: {e}")
        return
    
    # Step 3: Get articles for this vehicle
    vehicle_id = best_match['vehicle_id']
    print(f"\n📋 Step 3: Getting articles for vehicle ID {vehicle_id}...")
    
    # Try both product groups
    product_groups = [
        (100260, "Drivaksler"),
        (100270, "Mellomaksler")
    ]
    
    all_oems = []
    
    for product_group_id, group_name in product_groups:
        print(f"\n🔍 Searching {group_name} (ID: {product_group_id})...")
        url = (f"{BASE_URL}/articles/list/"
               f"vehicle-id/{vehicle_id}/"
               f"product-group-id/{product_group_id}/"
               f"manufacturer-id/{nissan_id}/"
               f"lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                print(f"✅ Found {len(articles)} articles in {group_name}")
                
                # Extract OEMs from articles
                group_oems = []
                for article in articles[:10]:  # Show first 10
                    oem_numbers = article.get('oemNumbers', [])
                    if oem_numbers:
                        for oem_data in oem_numbers:
                            if isinstance(oem_data, dict):
                                oem = oem_data.get('oemNumber', '')
                            else:
                                oem = str(oem_data)
                            
                            if oem and oem not in group_oems:
                                group_oems.append(oem)
                                print(f"   📝 OEM: {oem}")
                
                all_oems.extend(group_oems)
                print(f"✅ Extracted {len(group_oems)} OEMs from {group_name}")
                
            else:
                print(f"❌ Failed to get articles for {group_name}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error getting articles for {group_name}: {e}")
    
    print(f"\n🎯 FINAL RESULT:")
    print(f"Total OEMs found: {len(all_oems)}")
    print(f"First 10 OEMs: {all_oems[:10]}")
    print()
    print("🔍 ANALYSIS:")
    print("Expected OEMs for MA18002: 370008H310, 370008H510, 370008H800")
    
    expected_oems = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
    found_expected = [oem for oem in expected_oems if any(expected in str(found_oem) for found_oem in all_oems)]
    
    if found_expected:
        print(f"✅ Found expected OEMs: {found_expected}")
    else:
        print("❌ None of the expected OEMs found!")
        print("❌ This explains why MA18002 doesn't appear in search results")
        print("❌ TecDoc is returning wrong vehicle ID or wrong product group")

if __name__ == "__main__":
    debug_nissan_lookup()
