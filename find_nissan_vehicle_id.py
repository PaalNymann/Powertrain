#!/usr/bin/env python3
"""
Find vehicle-id for Nissan X-Trail 2006 to get compatible articles directly
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
TYPE_ID = 1  # Passenger cars

def find_nissan_xtrail_vehicle_id():
    """Find vehicle-id for Nissan X-Trail 2006"""
    
    print("🔍 FINDING NISSAN X-TRAIL 2006 VEHICLE-ID")
    print("=" * 50)
    
    # Step 1: Get Nissan manufacturer ID
    print("📋 Step 1: Getting Nissan manufacturer ID...")
    
    manufacturers_url = f"{BASE_URL}/manufacturers/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(manufacturers_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            manufacturers_data = response.json()
            manufacturers = manufacturers_data.get('manufacturers', [])
            
            nissan_id = None
            for manufacturer in manufacturers:
                if manufacturer.get('brand', '').upper() == 'NISSAN':
                    nissan_id = manufacturer.get('manufacturerId')
                    print(f"✅ Found Nissan manufacturer ID: {nissan_id}")
                    break
            
            if not nissan_id:
                print("❌ Nissan manufacturer not found")
                return None
                
        else:
            print(f"❌ Failed to get manufacturers: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting manufacturers: {e}")
        return None
    
    # Step 2: Get Nissan models
    print(f"\n📋 Step 2: Getting Nissan models...")
    
    models_url = f"{BASE_URL}/models/list/manufacturer-id/{nissan_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(models_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            models_data = response.json()
            models = models_data.get('models', [])
            
            print(f"✅ Found {len(models)} Nissan models")
            
            # Look for X-Trail models
            xtrail_models = []
            for model in models:
                model_name = model.get('modelName', '').upper()
                if 'X-TRAIL' in model_name or 'XTRAIL' in model_name:
                    xtrail_models.append(model)
                    print(f"🎯 Found X-Trail model: {model}")
            
            if not xtrail_models:
                print("❌ No X-Trail models found")
                print("🔍 Available Nissan models:")
                for model in models[:10]:  # Show first 10
                    print(f"   - {model.get('modelName')} ({model.get('modelYearFrom')}-{model.get('modelYearTo')})")
                return None
                
        else:
            print(f"❌ Failed to get models: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting models: {e}")
        return None
    
    # Step 3: Get vehicle IDs for X-Trail models
    print(f"\n📋 Step 3: Getting vehicle IDs for X-Trail models...")
    
    for model in xtrail_models:
        model_id = model.get('modelId')
        model_name = model.get('modelName')
        year_from = model.get('modelYearFrom')
        year_to = model.get('modelYearTo')
        
        print(f"\n🔍 Checking model: {model_name} ({year_from}-{year_to})")
        
        # Check if this model covers 2006
        try:
            if year_from and year_to:
                # Parse year from date format (e.g., "2001-01-01" -> 2001)
                year_from_int = int(year_from.split('-')[0]) if year_from else 0
                year_to_int = int(year_to.split('-')[0]) if year_to else 9999
                
                if year_from_int <= 2006 <= year_to_int:
                    print(f"✅ Model covers 2006! ({year_from_int}-{year_to_int})")
                    
                    # Get vehicle types/engines for this model
                    # This endpoint might give us vehicle IDs
                    vehicles_url = f"{BASE_URL}/vehicles/list/model-id/{model_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
                    
                    try:
                        vehicles_response = requests.get(vehicles_url, headers=HEADERS, timeout=10)
                        if vehicles_response.status_code == 200:
                            vehicles_data = vehicles_response.json()
                            print(f"✅ Got vehicle data: {type(vehicles_data)}")
                            
                            if isinstance(vehicles_data, dict):
                                print(f"   Keys: {list(vehicles_data.keys())}")
                                
                                # Look for vehicle IDs
                                vehicles = vehicles_data.get('vehicles', [])
                                if vehicles:
                                    print(f"   Found {len(vehicles)} vehicles")
                                    for i, vehicle in enumerate(vehicles[:5]):  # Show first 5
                                        vehicle_id = vehicle.get('vehicleId')
                                        engine_info = vehicle.get('engineInfo', '')
                                        year_info = vehicle.get('constructionYear', '')
                                        print(f"   Vehicle {i+1}: ID={vehicle_id}, Engine={engine_info}, Year={year_info}")
                                        
                                        # Test this vehicle ID with articles
                                        if vehicle_id:
                                            print(f"   🧪 Testing vehicle ID {vehicle_id} with articles...")
                                            test_articles_url = f"{BASE_URL}/articles/list/vehicle-id/{vehicle_id}/product-group-id/100260/manufacturer-id/{nissan_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
                                            
                                            test_response = requests.get(test_articles_url, headers=HEADERS, timeout=10)
                                            if test_response.status_code == 200:
                                                test_data = test_response.json()
                                                article_count = test_data.get('countArticles', 0)
                                                print(f"   ✅ Vehicle ID {vehicle_id} has {article_count} articles!")
                                                
                                                if article_count > 0:
                                                    # Check if any articles have our known Nissan OEMs
                                                    articles = test_data.get('articles', [])
                                                    print(f"   🔍 Checking articles for known Nissan OEMs...")
                                                    
                                                    # Get article details to check OEMs
                                                    for article in articles[:3]:  # Check first 3 articles
                                                        article_id = article.get('articleId')
                                                        if article_id:
                                                            details_url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}"
                                                            details_response = requests.get(details_url, headers=HEADERS, timeout=10)
                                                            if details_response.status_code == 200:
                                                                details_data = details_response.json()
                                                                oem_numbers = details_data.get('articleOemNo', [])
                                                                
                                                                for oem in oem_numbers:
                                                                    oem_no = oem.get('oemDisplayNo', '')
                                                                    if oem_no in ['370008H310', '370008H510', '370008H800']:
                                                                        print(f"   🎯 FOUND MATCHING OEM {oem_no} in vehicle ID {vehicle_id}!")
                                                                        return vehicle_id
                                            else:
                                                print(f"   ❌ No articles for vehicle ID {vehicle_id}")
                                else:
                                    print(f"   No vehicles found in response")
                                    
                            elif isinstance(vehicles_data, list):
                                print(f"   List with {len(vehicles_data)} items")
                                for item in vehicles_data[:3]:
                                    print(f"   Item: {item}")
                                    
                        else:
                            print(f"   ❌ Failed to get vehicles: {vehicles_response.status_code}")
                            
                    except Exception as e:
                        print(f"   ❌ Error getting vehicles: {e}")
                        
                else:
                    print(f"   ❌ Model doesn't cover 2006 ({year_from}-{year_to})")
                    
        except Exception as e:
            print(f"   ❌ Error processing model: {e}")
    
    print(f"\n❌ No matching vehicle ID found for Nissan X-Trail 2006")
    return None

if __name__ == "__main__":
    vehicle_id = find_nissan_xtrail_vehicle_id()
    
    if vehicle_id:
        print(f"\n🎯 SUCCESS! Found vehicle ID: {vehicle_id}")
        print(f"💡 Use this ID with: /articles/list/vehicle-id/{vehicle_id}/product-group-id/100260/...")
    else:
        print(f"\n❌ FAILED! Could not find vehicle ID for Nissan X-Trail 2006")
        print(f"💡 TecDoc might not have detailed vehicle data for this model/year")
