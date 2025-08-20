#!/usr/bin/env python3
"""
RapidAPI TecDoc Integration Module
Replaces Apify TecDoc workflow with direct RapidAPI TecDoc calls
"""

import requests
import json
import time
from typing import List, Dict, Optional, Tuple

# RapidAPI TecDoc Configuration
RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
HEADERS = {
    'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
    'x-rapidapi-key': RAPIDAPI_KEY
}

# TecDoc Constants
LANG_ID = 4  # English
COUNTRY_ID = 62  # Germany
TYPE_ID = 1  # Automobile
PRODUCT_GROUP_ID_DRIVAKSLER = 100260  # CV joints/drive shafts

def extract_vin_from_svv(svv_data):
    """Extract VIN from SVV data"""
    try:
        if svv_data and 'kjoretoydataListe' in svv_data:
            kjoretoydata = svv_data['kjoretoydataListe'][0]
            kjoretoy_id = kjoretoydata.get('kjoretoyId', {})
            return kjoretoy_id.get('understellsnummer', '')
    except Exception as e:
        print(f"❌ Error extracting VIN: {e}")
    return ''

def extract_engine_code_from_svv(svv_data):
    """Extract engine code from SVV data"""
    try:
        if svv_data and 'kjoretoydataListe' in svv_data:
            kjoretoydata = svv_data['kjoretoydataListe'][0]
            tekniske_data = kjoretoydata.get('tekniskeData', {})
            motor_drivverk = tekniske_data.get('motorOgDrivverk', {})
            motor_liste = motor_drivverk.get('motor', [])
            if motor_liste:
                return motor_liste[0].get('motorKode', '')
    except Exception as e:
        print(f"❌ Error extracting engine code: {e}")
    return ''

def extract_engine_size_from_svv(svv_data):
    """Extract engine size from SVV data"""
    try:
        if svv_data and 'kjoretoydataListe' in svv_data:
            kjoretoydata = svv_data['kjoretoydataListe'][0]
            tekniske_data = kjoretoydata.get('tekniskeData', {})
            motor_drivverk = tekniske_data.get('motorOgDrivverk', {})
            motor_liste = motor_drivverk.get('motor', [])
            if motor_liste:
                return motor_liste[0].get('slagvolum', 0)
    except Exception as e:
        print(f"❌ Error extracting engine size: {e}")
    return 0

def get_manufacturers() -> Dict:
    """Get all manufacturers from RapidAPI TecDoc"""
    print("📡 Getting manufacturers from RapidAPI TecDoc...")
    
    url = f"{BASE_URL}/manufacturers/list/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # The response is a dict with countManufacturers and manufacturers array
            if isinstance(data, dict):
                count = data.get('countManufacturers', 0)
                print(f"✅ Found {count} manufacturers")
                return data
            # If it's a direct array, wrap it
            elif isinstance(data, list):
                print(f"✅ Found {len(data)} manufacturers")
                return {'countManufacturers': len(data), 'manufacturers': data}
            else:
                print(f"❌ Unexpected response format: {type(data)}")
                return {}
        else:
            print(f"❌ Manufacturers request failed: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Exception getting manufacturers: {e}")
        return {}

def find_manufacturer_id(brand: str, manufacturers: List[Dict]) -> Optional[int]:
    """Find manufacturer ID by brand name"""
    if not manufacturers:
        return None
    
    # Normalize brand name for comparison
    brand_upper = brand.upper().strip()
    
    # Brand name mappings for common variations
    brand_mappings = {
        'VOLKSWAGEN': ['VW', 'VOLKSWAGEN'],
        'VW': ['VW', 'VOLKSWAGEN'],
        'MERCEDES-BENZ': ['MERCEDES-BENZ', 'MERCEDES', 'MB'],
        'BMW': ['BMW'],
        'AUDI': ['AUDI'],
        'VOLVO': ['VOLVO'],
        'FORD': ['FORD'],
        'TOYOTA': ['TOYOTA'],
        'NISSAN': ['NISSAN'],
        'HONDA': ['HONDA'],
        'HYUNDAI': ['HYUNDAI'],
        'KIA': ['KIA'],
        'MAZDA': ['MAZDA'],
        'SUBARU': ['SUBARU'],
        'MITSUBISHI': ['MITSUBISHI'],
        'PEUGEOT': ['PEUGEOT'],
        'CITROEN': ['CITROEN', 'CITROËN'],
        'RENAULT': ['RENAULT'],
        'OPEL': ['OPEL'],
        'FIAT': ['FIAT'],
        'ALFA ROMEO': ['ALFA ROMEO', 'ALFA'],
        'SKODA': ['SKODA', 'ŠKODA'],
        'SEAT': ['SEAT']
    }
    
    # Get possible brand variations
    possible_brands = brand_mappings.get(brand_upper, [brand_upper])
    
    for manufacturer in manufacturers:
        manufacturer_name = manufacturer.get('brand', '').upper().strip()
        
        # Check if any of the possible brand variations match
        for possible_brand in possible_brands:
            # EXACT match first (prevent VW matching SKODA SVW)
            if manufacturer_name == possible_brand:
                manufacturer_id = manufacturer.get('manufacturerId')
                if manufacturer_id:
                    print(f"✅ Found manufacturer (EXACT): {manufacturer_name} (ID: {manufacturer_id})")
                    return manufacturer_id
            
            # Partial match only if exact fails and it's a clear substring
            elif possible_brand in manufacturer_name and len(possible_brand) >= 3:
                # Avoid false positives like VW matching "SKODA (SVW)"
                if not ('SKODA' in manufacturer_name and possible_brand in ['VW', 'VOLKSWAGEN']):
                    manufacturer_id = manufacturer.get('manufacturerId')
                    if manufacturer_id:
                        print(f"✅ Found manufacturer (PARTIAL): {manufacturer_name} (ID: {manufacturer_id})")
                        return manufacturer_id
    
    print(f"❌ Manufacturer '{brand}' not found in TecDoc manufacturers")
    return None

def find_model_id(model: str, year: str, models: List[Dict]) -> Optional[int]:
    """Find vehicle/model ID by model name and year"""
    if not models:
        return None
    
    # Normalize model name for comparison
    model_upper = model.upper().strip()
    year_str = str(year)
    
    print(f"🔍 Searching for model '{model_upper}' year {year_str} in {len(models)} models")
    
    # First pass: exact model name match with year range check
    for model_data in models:
        model_name = model_data.get('modelName', '').upper().strip()
        
        if model_upper in model_name or model_name in model_upper:
            # Check year range if available
            year_from = model_data.get('yearFrom')
            year_to = model_data.get('yearTo')
            
            if year_from and year_to and year_from != 'N/A' and year_to != 'N/A':
                try:
                    year_int = int(year_str)
                    year_from_int = int(year_from)
                    year_to_int = int(year_to)
                    if year_from_int <= year_int <= year_to_int:
                        vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
                        if vehicle_id:
                            print(f"✅ Found exact match: {model_name} ({year_from}-{year_to}) ID: {vehicle_id}")
                            return vehicle_id
                except (ValueError, TypeError):
                    pass
            else:
                # No year range specified, use this model
                vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
                if vehicle_id:
                    print(f"✅ Found model match: {model_name} ID: {vehicle_id}")
                    return vehicle_id
    
    # Second pass: partial model name match
    for model_data in models:
        model_name = model_data.get('modelName', '').upper().strip()
        
        # Check if model name contains our search term or vice versa
        if (len(model_upper) >= 3 and model_upper in model_name) or \
           (len(model_name) >= 3 and model_name in model_upper):
            vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
            if vehicle_id:
                print(f"✅ Found partial match: {model_name} ID: {vehicle_id}")
                return vehicle_id
    
    print(f"❌ Model '{model}' ({year}) not found in TecDoc models")
    return None

def find_vehicle_id_by_vin(vin: str, models: List[Dict], brand: str, model: str, year: str) -> Optional[int]:
    """Find vehicle ID using VIN information for more precise matching"""
    if not vin or not models:
        return None
    
    print(f"🔍 Using VIN {vin} to find precise vehicle ID")
    
    # Extract information from VIN
    # For Volvo VINs like YV1SW494272634416:
    # YV1 = Volvo Cars Sweden
    # S = Model series indicator
    # W494 = Model/engine variant code
    # 27 = Model year code (2007)
    # 2634416 = Serial number
    
    if vin.startswith('YV1') and brand.upper() == 'VOLVO':
        # Extract Volvo-specific information from VIN
        if len(vin) >= 10:
            model_code = vin[3:7]  # e.g., "SW49"
            year_code = vin[9:11]  # e.g., "27"
            
            print(f"   VIN Model Code: {model_code}")
            print(f"   VIN Year Code: {year_code}")
            
            # Try to match model code with available models
            for model_data in models:
                model_name = model_data.get('modelName', '').upper()
                
                # For V70, look for models that might match the VIN pattern
                if 'V70' in model_name:
                    # Check if this could be the right variant
                    # V70 II (285) might be the right one for 2006-2007
                    if 'II' in model_name:
                        vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
                        if vehicle_id:
                            print(f"✅ VIN-based match: {model_name} ID: {vehicle_id}")
                            return vehicle_id
    
    # If VIN-specific matching fails, return None to fallback to regular matching
    print(f"❌ Could not find vehicle ID using VIN {vin}")
    return None

def get_models_for_manufacturer(manufacturer_id: int) -> Dict:
    """Get all models for a manufacturer"""
    print(f"📡 Getting models for manufacturer ID {manufacturer_id}...")
    
    url = f"{BASE_URL}/models/list/manufacturer-id/{manufacturer_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data.get('countModels', 0)} models")
            return data
        else:
            print(f"❌ Models request failed: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Exception getting models: {e}")
        return {}

def find_model_id(model: str, year: int, models_data: Dict) -> Optional[int]:
    """Find model ID for a given model and year"""
    if not models_data or 'models' not in models_data:
        return None
    
    model_upper = model.upper()
    
    # Model name variations
    model_variations = {
        'V70': ['V70', 'VOLVO V70'],
        'V60': ['V60', 'VOLVO V60'],
        'V90': ['V90', 'VOLVO V90'],
        'XC60': ['XC60', 'VOLVO XC60'],
        'XC90': ['XC90', 'VOLVO XC90'],
        'S60': ['S60', 'VOLVO S60'],
        'S80': ['S80', 'VOLVO S80'],
        'S90': ['S90', 'VOLVO S90']
    }
    
    search_variations = model_variations.get(model_upper, [model_upper])
    
    best_match = None
    best_score = 0
    
    for model_data in models_data['models']:
        model_name = model_data.get('modelName', '').upper()
        year_from = model_data.get('yearFrom', 0)
        year_to = model_data.get('yearTo', 9999)
        
        # Check if any variation matches the model name
        for variation in search_variations:
            if variation in model_name:
                # Check if year is within range (ensure proper type conversion)
                try:
                    year_from_int = int(year_from) if year_from else 0
                    year_to_int = int(year_to) if year_to else 9999
                    year_int = int(year)
                    if year_from_int <= year_int <= year_to_int:
                        # Score based on how well the name matches
                        score = len(variation) if model_name.startswith(variation) else len(variation) * 0.5
                        if score > best_score:
                            best_score = score
                            best_match = model_data
                            break
                except (ValueError, TypeError):
                    # If year conversion fails, skip this model
                    continue
    
    if best_match:
        model_id = best_match.get('modelId')
        model_name = best_match.get('modelName')
        year_from = best_match.get('yearFrom')
        year_to = best_match.get('yearTo')
        print(f"✅ Found {model} model ID: {model_id} ({model_name}, {year_from}-{year_to})")
        return model_id
    
    print(f"❌ Could not find model ID for {model} {year}")
    return None

def get_vehicle_types_for_model(manufacturer_id: int, model_id: int) -> Dict:
    """Get vehicle types/engines for a specific model"""
    print(f"📡 Getting vehicle types for manufacturer {manufacturer_id}, model {model_id}...")
    
    url = f"{BASE_URL}/vehicle-types/list/manufacturer-id/{manufacturer_id}/model-id/{model_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data.get('countVehicleTypes', 0)} vehicle types")
            return data
        else:
            print(f"❌ Vehicle types request failed: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Exception getting vehicle types: {e}")
        return {}

def find_vehicle_id(year: int, vehicle_types_data: Dict) -> Optional[int]:
    """Find vehicle ID for a given year from vehicle types"""
    if not vehicle_types_data or 'vehicleTypes' not in vehicle_types_data:
        return None
    
    best_match = None
    best_score = 0
    
    for vehicle_type in vehicle_types_data['vehicleTypes']:
        year_from = vehicle_type.get('yearFrom', 0)
        year_to = vehicle_type.get('yearTo', 9999)
        
        # Check if year is within range
        if year_from <= year <= year_to:
            # Prefer exact year matches, then broader ranges
            year_range = year_to - year_from
            score = 1000 - year_range  # Prefer smaller ranges
            
            if score > best_score:
                best_score = score
                best_match = vehicle_type
    
    if best_match:
        vehicle_id = best_match.get('vehicleId')
        engine_name = best_match.get('engineName', 'Unknown')
        year_from = best_match.get('yearFrom')
        year_to = best_match.get('yearTo')
        print(f"✅ Found vehicle ID: {vehicle_id} ({engine_name}, {year_from}-{year_to})")
        return vehicle_id
    
    print(f"❌ Could not find vehicle ID for year {year}")
    return None

def get_articles_for_vehicle(vehicle_id: int, manufacturer_id: int, product_group_id: int = PRODUCT_GROUP_ID_DRIVAKSLER) -> Dict:
    """Get articles for a specific vehicle and product group"""
    print(f"📡 Getting articles for vehicle {vehicle_id}, product group {product_group_id}...")
    
    url = (f"{BASE_URL}/articles/list/"
           f"vehicle-id/{vehicle_id}/"
           f"product-group-id/{product_group_id}/"
           f"manufacturer-id/{manufacturer_id}/"
           f"lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            article_count = data.get('countArticles', 0)
            print(f"✅ Found {article_count} articles")
            return data
        else:
            print(f"❌ Articles request failed: {response.status_code} - {response.text}")
            return {}
    except Exception as e:
        print(f"❌ Exception getting articles: {e}")
        return {}

def extract_oem_numbers_from_articles(articles_data: Dict) -> List[str]:
    """Extract OEM numbers from articles response"""
    oem_numbers = []
    
    if not articles_data or 'articles' not in articles_data:
        return oem_numbers
    
    for article in articles_data['articles']:
        # Get OEM numbers from the article
        if 'oemNo' in article and isinstance(article['oemNo'], list):
            for oem_entry in article['oemNo']:
                if isinstance(oem_entry, dict):
                    oem_display_no = oem_entry.get('oemDisplayNo', '').strip()
                    if oem_display_no:
                        # Clean up OEM number (remove spaces, standardize format)
                        oem_clean = oem_display_no.replace(' ', '').replace('-', '')
                        oem_numbers.append(oem_clean)
        
        # Also check for direct articleNo (some might be OEM numbers)
        article_no = article.get('articleNo', '').strip()
        if article_no:
            oem_numbers.append(article_no)
    
    # Remove duplicates and return
    unique_oems = list(set(oem_numbers))
    print(f"📦 Extracted {len(unique_oems)} unique OEM numbers")
    return unique_oems

def search_oem_in_tecdoc(oem_number: str) -> Dict:
    """Search for an OEM number in TecDoc using the articles-oem search endpoint"""
    print(f"🔍 Searching TecDoc for OEM: {oem_number}")
    
    url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem_number}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                print(f"✅ Found {len(data)} articles for OEM {oem_number}")
                return {"articles": data, "found": True}
            else:
                print(f"❌ No articles found for OEM {oem_number}")
                return {"articles": [], "found": False}
                
        elif response.status_code == 404:
            print(f"❌ OEM {oem_number} not found in TecDoc")
            return {"articles": [], "found": False}
        else:
            print(f"❌ Error searching OEM {oem_number}: {response.status_code}")
            return {"articles": [], "found": False}
            
    except Exception as e:
        print(f"❌ Exception searching OEM {oem_number}: {e}")
        return {"articles": [], "found": False}

def get_article_details(article_id: int) -> Dict:
    """Get detailed article information including vehicle compatibility"""
    print(f"🔍 Getting article details for {article_id}")
    
    url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            # Look for vehicle compatibility in various possible fields
            compatibility_fields = ['compatibleCars', 'vehicleCompatibility', 'vehicles', 'compatibleVehicles']
            
            vehicles = []
            for field in compatibility_fields:
                if field in data and data[field]:
                    vehicles = data[field]
                    break
            
            return {
                "article_id": article_id,
                "vehicles": vehicles,
                "data": data
            }
            
        else:
            print(f"❌ Error getting article details {article_id}: {response.status_code}")
            return {"article_id": article_id, "vehicles": [], "data": {}}
            
    except Exception as e:
        print(f"❌ Exception getting article details {article_id}: {e}")
        return {"article_id": article_id, "vehicles": [], "data": {}}

def get_vehicle_compatibility_for_article(article_id: int) -> List[Dict]:
    """Get vehicle compatibility for a specific article using the details endpoint"""
    print(f"🔍 Getting vehicle compatibility for article {article_id}")
    
    url = f"{BASE_URL}/articles/details/{article_id}/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            # Look for vehicle compatibility in various possible fields
            compatibility_fields = ['compatibleCars', 'vehicleCompatibility', 'vehicles', 'compatibleVehicles']
            
            for field in compatibility_fields:
                if field in data and data[field]:
                    vehicles = data[field]
                    print(f"✅ Found {len(vehicles)} compatible vehicles for article {article_id}")
                    return vehicles
            
            print(f"❌ No vehicle compatibility found for article {article_id}")
            return []
            
        else:
            print(f"❌ Error getting article details {article_id}: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Exception getting article details {article_id}: {e}")
        return []

def check_oem_compatibility_with_vehicle(oem_number: str, brand: str, model: str, year: int) -> bool:
    """Check if an OEM number is compatible with a specific vehicle using RapidAPI TecDoc"""
    print(f"🔍 Checking OEM {oem_number} compatibility with {brand} {model} {year}")
    
    url = f"{BASE_URL}/articles/article-number-details/lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/article-no/{oem_number}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            
            # Check if we have vehicle compatibility data
            if 'articles' in data and data['articles']:
                for article in data['articles']:
                    if 'compatibleCars' in article:
                        compatible_cars = article['compatibleCars']
                        
                        for car in compatible_cars:
                            car_brand = car.get('manufacturerName', '').upper()
                            car_model = car.get('modelName', '').upper()
                            car_year_start = car.get('constructionIntervalStart', '')
                            car_year_end = car.get('constructionIntervalEnd', '')
                            
                            # Check brand match
                            if brand.upper() in car_brand or car_brand in brand.upper():
                                # Check model match
                                if model.upper() in car_model or any(part in car_model for part in model.upper().split()):
                                    # Check year compatibility
                                    if car_year_start and car_year_end:
                                        try:
                                            start_year = int(car_year_start.split('-')[0])
                                            end_year = int(car_year_end.split('-')[0])
                                            vehicle_year = int(year)
                                            
                                            if start_year <= vehicle_year <= end_year:
                                                print(f"✅ OEM {oem_number} is compatible: {car_brand} {car_model} ({start_year}-{end_year})")
                                                return True
                                        except (ValueError, IndexError):
                                            continue
            
            print(f"❌ OEM {oem_number} not compatible with {brand} {model} {year}")
            return False
            
        elif response.status_code == 404:
            print(f"❌ OEM {oem_number} not found in TecDoc")
            return False
        else:
            print(f"❌ Error checking OEM {oem_number}: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception checking OEM {oem_number}: {e}")
        return False

def get_compatible_oems_for_vehicle(brand: str, model: str, year: int, available_oems: List[str]) -> List[str]:
    """Check which OEMs from available stock are compatible with the vehicle"""
    print(f"🔍 Checking {len(available_oems)} available OEMs for compatibility with {brand} {model} {year}")
    
    compatible_oems = []
    
    for oem in available_oems:
        if check_oem_compatibility_with_vehicle(oem, brand, model, year):
            compatible_oems.append(oem)
    
    print(f"✅ Found {len(compatible_oems)} compatible OEMs: {compatible_oems}")
    return compatible_oems

def get_oem_numbers_from_rapidapi_tecdoc(brand: str, model: str, year: int, svv_data=None) -> List[str]:
    """
    Main function to get OEM numbers from RapidAPI TecDoc
    Uses SVV data (VIN, engine code, etc.) to find exact vehicle ID when available
    """
    print(f"🔍 Starting RapidAPI TecDoc lookup for {brand} {model} {year}")
    
    if not all([brand, model, year]):
        print(f"❌ Missing required parameters: brand={brand}, model={model}, year={year}")
        return []
    
    # Extract detailed vehicle info from SVV if available
    vin = ''
    engine_code = ''
    engine_size = 0
    if svv_data:
        print(f"📋 Using SVV data to find exact vehicle ID...")
        vin = extract_vin_from_svv(svv_data)
        engine_code = extract_engine_code_from_svv(svv_data)
        engine_size = extract_engine_size_from_svv(svv_data)
        print(f"   VIN: {vin}")
        print(f"   Engine Code: {engine_code}")
        print(f"   Engine Size: {engine_size}cc")
    
    try:
        # Step 1: Get manufacturers and find the correct manufacturer ID
        print(f"📋 Step 1: Finding manufacturer ID for {brand}")
        manufacturers_data = get_manufacturers()
        if not manufacturers_data:
            return []
        
        # Extract manufacturers list from the response
        manufacturers_list = manufacturers_data.get('manufacturers', [])
        if not manufacturers_list:
            print("❌ No manufacturers found in response")
            return []
        
        print(f"✅ Found {len(manufacturers_list)} manufacturers")
        
        # Debug: Show first 10 manufacturers to help with debugging
        print(f"🔍 First 10 manufacturers:")
        for i, mfg in enumerate(manufacturers_list[:10]):
            print(f"   {i+1}. {mfg.get('brand', 'Unknown')} (ID: {mfg.get('manufacturerId', 'N/A')})")
        
        manufacturer_id = find_manufacturer_id(brand, manufacturers_list)
        if not manufacturer_id:
            print(f"❌ Manufacturer '{brand}' not found in TecDoc")
            return []
        
        print(f"✅ Found manufacturer ID: {manufacturer_id} for {brand}")
        
        # Step 2: Get models for this manufacturer and find the correct model/vehicle ID
        print(f"📋 Step 2: Finding model/vehicle ID for {model}")
        
        models = get_models_for_manufacturer(manufacturer_id)
        vehicle_id = None
        
        # If we have VIN, try to use it for more precise matching
        if vin:
            vehicle_id = find_vehicle_id_by_vin(vin, models, brand, model, year)
        
        # Fallback to model/year matching if VIN lookup fails
        if not vehicle_id:
            vehicle_id = find_model_id(model, year, models)
        
        if not vehicle_id:
            print(f"❌ Model '{model}' ({year}) not found for manufacturer {brand}")
            return []
        
        print(f"✅ Found vehicle ID: {vehicle_id} for {brand} {model} {year}")
        
        # Step 3: Get articles for this specific vehicle (MULTIPLE product groups for comprehensive coverage)
        print(f"📋 Step 3: Getting articles for vehicle ID {vehicle_id}")
        
        # Search multiple relevant product groups to get comprehensive OEM coverage
        # Start with Drivaksler only to avoid crashes, expand later
        product_groups = [
            (100260, "Drivaksler"),  # CV joints/drive shafts
            # TODO: Add more product groups when we confirm they exist in TecDoc
            # (100270, "Mellomaksler"), # Intermediate shafts (if exists)
            # (100250, "Aksler"),      # General axles (if exists)
        ]
        
        all_oem_numbers = []
        
        for product_group_id, group_name in product_groups:
            print(f"🔍 Searching {group_name} (ID: {product_group_id})...")
            try:
                articles = get_articles_for_vehicle(vehicle_id, manufacturer_id, product_group_id=product_group_id)
                
                if articles and articles.get('articles'):
                    group_oems = extract_oem_numbers_from_articles(articles)
                    if group_oems:
                        print(f"✅ Found {len(group_oems)} OEMs in {group_name}")
                        all_oem_numbers.extend(group_oems)
                    else:
                        print(f"❌ No OEMs extracted from {group_name}")
                else:
                    print(f"❌ No articles found in {group_name}")
                    
            except Exception as e:
                print(f"❌ Error searching {group_name}: {e}")
                continue
        
        # Remove duplicates while preserving order
        oem_numbers = list(dict.fromkeys(all_oem_numbers))
        
        print(f"✅ Found {len(oem_numbers)} OEM numbers for {brand} {model} {year}")
        return oem_numbers
        
    except Exception as e:
        print(f"❌ Error getting OEM numbers from RapidAPI TecDoc: {e}")
        return []

def search_oem_number(oem_number: str) -> List[Dict]:
    """
    Search for articles by OEM number
    Useful for validating OEM numbers or finding additional details
    """
    print(f"🔍 Searching for OEM number: {oem_number}")
    
    url = f"{BASE_URL}/articles-oem/search/lang-id/{LANG_ID}/article-oem-search-no/{oem_number}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"✅ Found {len(data)} articles for OEM {oem_number}")
                return data
            else:
                print(f"❌ Unexpected response format for OEM search")
                return []
        else:
            print(f"❌ OEM search failed: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Exception searching OEM: {e}")
        return []

# Test function
def test_rapidapi_integration():
    """Test the RapidAPI TecDoc integration with known vehicle"""
    print("🧪 Testing RapidAPI TecDoc integration...")
    
    # Test with 2006 Volvo V70 (known from our database)
    oem_numbers = get_oem_numbers_from_rapidapi_tecdoc("VOLVO", "V70", 2006)
    
    if oem_numbers:
        print(f"✅ Test successful: Found {len(oem_numbers)} OEM numbers")
        print(f"First 10 OEMs: {oem_numbers[:10]}")
        
        # Test searching for a known OEM
        if oem_numbers:
            test_oem = oem_numbers[0]
            articles = search_oem_number(test_oem)
            print(f"✅ OEM search test: Found {len(articles)} articles for {test_oem}")
    else:
        print("❌ Test failed: No OEM numbers found")

if __name__ == "__main__":
    test_rapidapi_integration()
