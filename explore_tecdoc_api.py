#!/usr/bin/env python3
"""
Explore TecDoc RapidAPI endpoints to find correct vehicle lookup method
Goal: Find why Nissan X-Trail 2006 returns wrong OEMs and fix it
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

def explore_tecdoc_endpoints():
    """Explore different TecDoc API endpoints for vehicle lookup"""
    
    print("🔍 EXPLORING TECDOC API ENDPOINTS")
    print("=" * 60)
    
    # Test different vehicle lookup approaches
    test_approaches = [
        {
            'name': 'Vehicle Search by Brand/Model/Year',
            'url': f"{BASE_URL}/vehicles/search/brand/NISSAN/model/X-TRAIL/year/2006/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
        },
        {
            'name': 'Vehicle Types by Model ID',
            'url': f"{BASE_URL}/vehicle-types/list/model-id/[MODEL_ID]/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
        },
        {
            'name': 'Direct Vehicle Lookup',
            'url': f"{BASE_URL}/vehicles/list/manufacturer-id/[MFG_ID]/model-id/[MODEL_ID]/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
        }
    ]
    
    # First, get Nissan manufacturer ID
    print("\n📋 Step 1: Getting Nissan manufacturer ID...")
    mfg_url = f"{BASE_URL}/manufacturers/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(mfg_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            manufacturers = data.get('manufacturers', [])
            
            nissan_id = None
            for mfg in manufacturers:
                if 'NISSAN' in mfg.get('brand', '').upper():
                    nissan_id = mfg.get('manufacturerId')
                    print(f"✅ Found Nissan ID: {nissan_id}")
                    break
            
            if not nissan_id:
                print("❌ Nissan not found!")
                return
        else:
            print(f"❌ Failed to get manufacturers: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Get Nissan models
    print(f"\n📋 Step 2: Getting Nissan models...")
    models_url = f"{BASE_URL}/models/list/manufacturer-id/{nissan_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(models_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            
            print(f"✅ Found {len(models)} Nissan models")
            
            # Find all X-Trail variants
            xtrail_models = []
            for model in models:
                model_name = model.get('modelName', '').upper()
                if 'X-TRAIL' in model_name or 'XTRAIL' in model_name:
                    xtrail_models.append(model)
                    print(f"🔍 X-Trail: {model_name} (ID: {model.get('modelId')}) Years: {model.get('yearFrom')}-{model.get('yearTo')}")
            
            if not xtrail_models:
                print("❌ No X-Trail models found!")
                return
                
            # Test different vehicle lookup methods for each X-Trail model
            for i, model in enumerate(xtrail_models):
                model_id = model.get('modelId')
                model_name = model.get('modelName', '')
                year_from = model.get('yearFrom')
                year_to = model.get('yearTo')
                
                print(f"\n🧪 Testing model {i+1}: {model_name} (ID: {model_id})")
                
                # Method 1: Get vehicle types for this model
                print(f"   Method 1: Vehicle types for model {model_id}")
                vt_url = f"{BASE_URL}/vehicle-types/list/model-id/{model_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
                
                try:
                    response = requests.get(vt_url, headers=HEADERS, timeout=30)
                    if response.status_code == 200:
                        vt_data = response.json()
                        vehicle_types = vt_data.get('vehicleTypes', [])
                        print(f"   ✅ Found {len(vehicle_types)} vehicle types")
                        
                        # Show first few vehicle types with year ranges
                        for j, vt in enumerate(vehicle_types[:5]):
                            vt_year_from = vt.get('yearFrom')
                            vt_year_to = vt.get('yearTo')
                            engine = vt.get('engineName', 'Unknown')
                            vehicle_id = vt.get('vehicleId')
                            
                            # Check if 2006 is in range
                            in_range = False
                            if vt_year_from and vt_year_to:
                                try:
                                    if int(vt_year_from) <= 2006 <= int(vt_year_to):
                                        in_range = True
                                except:
                                    pass
                            
                            status = "✅ MATCHES 2006" if in_range else "❌ Wrong year"
                            print(f"      {j+1}. Vehicle ID: {vehicle_id}, Engine: {engine}, Years: {vt_year_from}-{vt_year_to} {status}")
                            
                            # If this matches 2006, test getting articles
                            if in_range:
                                print(f"      🔍 Testing articles for vehicle ID {vehicle_id}...")
                                articles_url = (f"{BASE_URL}/articles/list/"
                                              f"vehicle-id/{vehicle_id}/"
                                              f"product-group-id/100260/"
                                              f"manufacturer-id/{nissan_id}/"
                                              f"lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}")
                                
                                try:
                                    art_response = requests.get(articles_url, headers=HEADERS, timeout=30)
                                    if art_response.status_code == 200:
                                        art_data = art_response.json()
                                        articles = art_data.get('articles', [])
                                        print(f"      ✅ Found {len(articles)} articles for this vehicle")
                                        
                                        # Extract first few OEMs
                                        oems = []
                                        for article in articles[:5]:
                                            oem_numbers = article.get('oemNumbers', [])
                                            for oem_data in oem_numbers:
                                                if isinstance(oem_data, dict):
                                                    oem = oem_data.get('oemNumber', '')
                                                else:
                                                    oem = str(oem_data)
                                                if oem and oem not in oems:
                                                    oems.append(oem)
                                        
                                        print(f"      📝 Sample OEMs: {oems[:5]}")
                                        
                                        # Check if we find expected OEMs
                                        expected = ['370008H310', '370008H510', '37000-8H310']
                                        found_expected = any(exp in str(oem) for exp in expected for oem in oems)
                                        if found_expected:
                                            print(f"      🎯 SUCCESS! Found expected OEMs in this vehicle variant!")
                                        else:
                                            print(f"      ❌ No expected OEMs found")
                                    else:
                                        print(f"      ❌ Articles request failed: {art_response.status_code}")
                                except Exception as e:
                                    print(f"      ❌ Error getting articles: {e}")
                    else:
                        print(f"   ❌ Vehicle types request failed: {response.status_code}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                
                print()  # Blank line between models
                
        else:
            print(f"❌ Failed to get models: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error: {e}")
        return

if __name__ == "__main__":
    explore_tecdoc_endpoints()
