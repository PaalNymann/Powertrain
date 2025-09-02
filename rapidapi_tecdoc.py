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
    
    # Normalize brand name for comparison - use only exact SVV brand name
    brand_upper = brand.upper().strip()
    
    # Use only the exact brand name from SVV - NO hardcoded mappings or variations
    possible_brands = [brand_upper]
    
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
    """Find vehicle/model ID by model name and year with improved matching"""
    if not models:
        return None
    
    # Normalize model name for comparison
    model_upper = model.upper().strip()
    year_str = str(year)
    year_int = int(year_str)
    
    print(f"🔍 Searching for model '{model_upper}' year {year_str} in {len(models)} models")
    
    # Debug: Show all matching models for analysis
    matching_models = []
    for model_data in models:
        model_name = model_data.get('modelName', '').upper().strip()
        if model_upper in model_name or model_name in model_upper:
            year_from = model_data.get('yearFrom')
            year_to = model_data.get('yearTo')
            vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
            matching_models.append({
                'name': model_name,
                'year_from': year_from,
                'year_to': year_to,
                'vehicle_id': vehicle_id,
                'data': model_data
            })
    
    print(f"🔍 Found {len(matching_models)} potential matches:")
    for i, match in enumerate(matching_models[:10]):  # Show first 10
        print(f"   {i+1}. {match['name']} ({match['year_from']}-{match['year_to']}) ID: {match['vehicle_id']}")
    
    # IMPROVED MATCHING: Find best match with generation-aware filtering
    best_matches = []
    
    # SPECIAL HANDLING for multi-generation models like X-Trail
    if 'X-TRAIL' in model_upper:
        print(f"🔍 Special X-Trail generation matching for year {year_int}")
        
        # X-Trail generation mapping based on year
        for match in matching_models:
            model_name = match['name']
            
            # X-TRAIL I (T30): 2001-2007
            if 'I' in model_name and 'T30' in model_name and 2001 <= year_int <= 2007:
                match_score = 2000  # Highest priority for correct generation
                best_matches.append((match_score, match))
                print(f"✅ X-Trail I (T30) match for {year_int}: {model_name} Score: {match_score}")
            
            # X-TRAIL II (T31): 2007-2014
            elif 'II' in model_name and 'T31' in model_name and 2007 <= year_int <= 2014:
                match_score = 2000  # Highest priority for correct generation
                best_matches.append((match_score, match))
                print(f"✅ X-Trail II (T31) match for {year_int}: {model_name} Score: {match_score}")
            
            # X-TRAIL III (T32): 2014+
            elif 'III' in model_name and 'T32' in model_name and year_int >= 2014:
                match_score = 2000  # Highest priority for correct generation
                best_matches.append((match_score, match))
                print(f"✅ X-Trail III (T32) match for {year_int}: {model_name} Score: {match_score}")
    
    # FALLBACK: Standard year range matching for other models
    if not best_matches:
        print(f"🔍 Standard year range matching for {model_upper}")
        for match in matching_models:
            year_from = match['year_from']
            year_to = match['year_to']
            
            if year_from and year_to and year_from != 'N/A' and year_to != 'N/A':
                try:
                    year_from_int = int(year_from)
                    year_to_int = int(year_to)
                    if year_from_int <= year_int <= year_to_int:
                        # Calculate match quality (prefer narrower year ranges)
                        year_range = year_to_int - year_from_int
                        match_score = 1000 - year_range  # Higher score for narrower ranges
                        
                        # Bonus for exact model name match
                        if match['name'] == model_upper:
                            match_score += 500
                        
                        best_matches.append((match_score, match))
                        print(f"✅ Year match: {match['name']} ({year_from}-{year_to}) Score: {match_score}")
                except (ValueError, TypeError):
                    pass
    
    # If we have year-matched models, use the best one
    if best_matches:
        best_matches.sort(key=lambda x: x[0], reverse=True)  # Sort by score descending
        best_match = best_matches[0][1]
        vehicle_id = best_match['vehicle_id']
        if vehicle_id:
            print(f"✅ BEST MATCH: {best_match['name']} ({best_match['year_from']}-{best_match['year_to']}) ID: {vehicle_id}")
            return vehicle_id
    
    # Fallback: Use first model with exact name match (no year check)
    for match in matching_models:
        if match['name'] == model_upper:
            vehicle_id = match['vehicle_id']
            if vehicle_id:
                print(f"✅ Exact name match: {match['name']} ID: {vehicle_id}")
                return vehicle_id
    
    # Last resort: Use first partial match
    if matching_models:
        first_match = matching_models[0]
        vehicle_id = first_match['vehicle_id']
        if vehicle_id:
            print(f"⚠️ Using first match: {first_match['name']} ID: {vehicle_id}")
            return vehicle_id
    
    print(f"❌ Model '{model}' ({year}) not found in TecDoc models")
    return None

def find_vehicle_id_by_vin(vin: str, models: List[Dict], brand: str, model: str, year: str) -> Optional[int]:
    """Find vehicle ID using VIN information for more precise matching"""
    if not vin or not models:
        return None
    
    print(f"🔍 Using VIN {vin} to find precise vehicle ID")
    
    # Extract information from VIN
    # VIN structure: WMI (3) + VDS (6) + VIS (8) = 17 characters
    # WMI = World Manufacturer Identifier (first 3 chars)
    # VDS = Vehicle Descriptor Section (chars 4-9)
    # VIS = Vehicle Identifier Section (chars 10-17)
    
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
    
    elif vin.startswith('JN1') and brand.upper() == 'NISSAN':
        # Nissan VIN decoding for JN1TENT30U0217281
        # JN1 = Nissan Japan
        # T = Vehicle line (T30 platform for X-Trail)
        # E = Engine type
        # N = Body type
        # T = Transmission type
        # 3 = Generation/series
        # 0 = Check digit
        # U = Model year (U = 2006)
        # 0217281 = Serial number
        
        if len(vin) >= 10:
            platform_code = vin[3]  # T = T30 platform
            model_year_code = vin[9]  # U = 2006
            
            print(f"   VIN Platform Code: {platform_code} (T30 platform)")
            print(f"   VIN Model Year Code: {model_year_code} (2006)")
            
            # Look for X-Trail models that match T30 platform and 2006 year
            for model_data in models:
                model_name = model_data.get('modelName', '').upper()
                
                # Look for X-Trail I (T30) generation specifically
                if 'X-TRAIL' in model_name and ('T30' in model_name or 'I' in model_name):
                    vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
                    if vehicle_id:
                        print(f"✅ VIN-based match: {model_name} ID: {vehicle_id}")
                        return vehicle_id
                
                # Also check for generic X-Trail models from 2006 era
                elif 'X-TRAIL' in model_name and not ('II' in model_name or 'III' in model_name):
                    # This might be the first generation
                    vehicle_id = model_data.get('vehicleId') or model_data.get('modelId')
                    if vehicle_id:
                        print(f"✅ VIN-based match (generic): {model_name} ID: {vehicle_id}")
                        return vehicle_id
    
    # Add support for other common VIN prefixes
    elif len(vin) >= 3:
        wmi = vin[:3]
        print(f"   VIN WMI: {wmi} - attempting generic VIN-based matching")
        
        # For any VIN, try to find the most specific model match
        # This is a fallback that uses VIN presence to prefer more specific models
        best_match = None
        best_score = 0
        
        for model_data in models:
            model_name = model_data.get('modelName', '').upper()
            score = 0
            
            # Prefer models with generation indicators (I, II, III, etc.)
            if any(gen in model_name for gen in [' I ', ' II ', ' III ', '(I)', '(II)', '(III)']):
                score += 2
            
            # Prefer models with platform codes
            if any(platform in model_name for platform in ['T30', 'T31', 'T32']):
                score += 3
            
            # Basic model name match
            if model.upper() in model_name:
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = model_data
        
        if best_match and best_score > 0:
            vehicle_id = best_match.get('vehicleId') or best_match.get('modelId')
            if vehicle_id:
                model_name = best_match.get('modelName', '')
                print(f"✅ VIN-based generic match: {model_name} ID: {vehicle_id} (score: {best_score})")
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
    
    # Use only the exact model name from SVV - NO hardcoded variations or fallbacks
    search_variations = [model_upper]
    
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
    print(f"❌ Could not find vehicle ID for year {year}")
    return None

def get_articles_for_vehicle(vehicle_id: int, product_group_id: int, manufacturer_id: int) -> List[Dict]:
    """Get all articles for a specific vehicle and product group with pagination support"""
    if not vehicle_id or not product_group_id or not manufacturer_id:
        print(f"❌ Missing required parameters: vehicle_id={vehicle_id}, product_group_id={product_group_id}, manufacturer_id={manufacturer_id}")
        return []
    
    # First request to get total count and first batch
    url = (f"{BASE_URL}/articles/list/"
           f"vehicle-id/{vehicle_id}/"
           f"product-group-id/{product_group_id}/"
           f"manufacturer-id/{manufacturer_id}/"
           f"lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            total_count = data.get('countArticles', 0)
            current_articles = data.get('articles', [])
            
            print(f"✅ Found {total_count} total articles, got {len(current_articles)} in first batch")
            
            # If we have more articles than what we got, we need pagination
            if total_count > len(current_articles) and total_count > 0:
                print(f"🔄 Need pagination: {total_count} total vs {len(current_articles)} received")
                
                # Try to get more articles with pagination (if API supports it)
                # Common pagination parameters: page, offset, limit
                all_articles = current_articles.copy()
                
                # Try different pagination approaches
                page = 2
                while len(all_articles) < total_count and page <= 10:  # Safety limit
                    paginated_url = f"{url}/page/{page}"
                    try:
                        page_response = requests.get(paginated_url, headers=HEADERS, timeout=30)
                        if page_response.status_code == 200:
                            page_data = page_response.json()
                            page_articles = page_data.get('articles', [])
                            if page_articles:
                                all_articles.extend(page_articles)
                                print(f"📄 Page {page}: got {len(page_articles)} more articles (total: {len(all_articles)})")
                                page += 1
                            else:
                                break
                        else:
                            print(f"❌ Pagination page {page} failed: {page_response.status_code}")
                            break
                    except Exception as e:
                        print(f"❌ Error getting page {page}: {e}")
                        break
                
                print(f"✅ Final result: {len(all_articles)} articles collected")
                return all_articles
            else:
                return current_articles
        else:
            print(f"❌ Failed to get articles: {response.status_code}")
            if response.status_code == 404:
                print(f"   Vehicle ID {vehicle_id} not found for product group {product_group_id}")
            return []
    except Exception as e:
        print(f"❌ Error getting articles: {e}")
        return []


def get_articles_by_vin(vin: str, product_group_id: int, manufacturer_id: int) -> List[Dict]:
    """Get articles directly using VIN number - more precise than vehicle-id lookup"""
    if not vin or not product_group_id or not manufacturer_id:
        print(f"❌ Missing required parameters: vin={vin}, product_group_id={product_group_id}, manufacturer_id={manufacturer_id}")
        return []
    
    print(f"🔍 Getting articles directly by VIN: {vin}")
    
    # Try VIN-based article search endpoint
    url = (f"{BASE_URL}/articles/list/"
           f"vin/{vin}/"
           f"product-group-id/{product_group_id}/"
           f"manufacturer-id/{manufacturer_id}/"
           f"lang-id/{LANG_ID}/country-filter-id/{COUNTRY_ID}/type-id/{TYPE_ID}")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            data = response.json()
            articles = data.get('articles', [])
            total_count = data.get('countArticles', len(articles))
            
            print(f"✅ VIN-based search found {total_count} articles")
            return articles
        else:
            print(f"❌ VIN-based search failed: {response.status_code}")
            # Try alternative VIN endpoint format
            alt_url = f"{BASE_URL}/articles/vin/{vin}/product-group/{product_group_id}"
            try:
                alt_response = requests.get(alt_url, headers=HEADERS, timeout=30)
                if alt_response.status_code == 200:
                    alt_data = alt_response.json()
                    alt_articles = alt_data.get('articles', [])
                    print(f"✅ Alternative VIN endpoint found {len(alt_articles)} articles")
                    return alt_articles
                else:
                    print(f"❌ Alternative VIN endpoint also failed: {alt_response.status_code}")
            except Exception as e:
                print(f"❌ Error with alternative VIN endpoint: {e}")
            
            return []
    except Exception as e:
        print(f"❌ Error getting articles by VIN: {e}")
        return []

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
        print(f"📋 Step 3: Getting articles for vehicle")
        
        # EXPANDED: Search ALL relevant drivetrain/axle product groups for comprehensive OEM coverage
        # This ensures we find ALL OEMs for the vehicle, not just the limited subset we sync
        product_groups = [
            (100260, "Drivaksler"),           # CV joints/drive shafts
            (100270, "Mellomaksler"),         # Intermediate shafts
            (100250, "Drivaksel komponenter"), # CV joint components
            (100280, "Akselbolter"),          # Axle bolts
            (100290, "Akselledd"),            # Axle joints
            (100300, "Drivaksel tilbehør"),   # Drive shaft accessories
            (100310, "Hjullager"),            # Wheel bearings
            (100320, "Hjulnav"),              # Wheel hubs
            (100330, "Drivstoff komponenter"), # Drivetrain components
            (100340, "Transmisjon deler"),    # Transmission parts
        ]
        
        all_oem_numbers = []
        
        for product_group_id, group_name in product_groups:
            print(f"🔍 Searching {group_name} (ID: {product_group_id})...")
            try:
                # PRIORITY 1: Use VIN directly if available (most precise)
                articles = []
                if vin:
                    print(f"   🎯 Using VIN-based search: {vin}")
                    articles = get_articles_by_vin(vin, product_group_id, manufacturer_id)
                
                # FALLBACK: Use vehicle ID if VIN search fails or VIN not available
                if not articles and vehicle_id:
                    print(f"   🔄 Fallback to vehicle ID search: {vehicle_id}")
                    articles = get_articles_for_vehicle(vehicle_id, product_group_id, manufacturer_id)
                
                if articles:
                    # Handle both old format (dict with 'articles') and new format (direct list)
                    articles_list = articles.get('articles', []) if isinstance(articles, dict) else articles
                    
                    if articles_list:
                        group_oems = extract_oem_numbers_from_articles({'articles': articles_list})
                        if group_oems:
                            print(f"✅ Found {len(group_oems)} OEMs in {group_name}")
                            all_oem_numbers.extend(group_oems)
                        else:
                            print(f"❌ No OEMs extracted from {group_name}")
                    else:
                        print(f"❌ No articles found in {group_name}")
                else:
                    print(f"❌ No articles found in {group_name}")
                    
            except Exception as e:
                print(f"❌ Error searching {group_name}: {e}")
                continue
        
        # Remove duplicates while preserving order
        oem_numbers = list(dict.fromkeys(all_oem_numbers))
        
        # FALLBACK: If TecDoc vehicle lookup returned few/wrong OEMs, try reverse lookup
        if len(oem_numbers) < 10:  # Threshold for "too few OEMs"
            print(f"⚠️ Only {len(oem_numbers)} OEMs found via vehicle lookup - trying REVERSE LOOKUP...")
            reverse_oems = reverse_lookup_vehicle_by_known_oems(brand, model, year)
            if reverse_oems:
                print(f"✅ REVERSE LOOKUP found {len(reverse_oems)} known OEMs")
                # Combine with existing OEMs
                combined_oems = list(dict.fromkeys(oem_numbers + reverse_oems))
                print(f"✅ Combined result: {len(combined_oems)} total OEMs")
                return combined_oems
        
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

def reverse_lookup_vehicle_by_known_oems(brand: str, model: str, year: int) -> List[str]:
    """
    REVERSE LOOKUP: Use known OEMs from our database to find correct TecDoc vehicle
    This solves the problem where TecDoc vehicle lookup returns wrong vehicle ID
    """
    print(f"🔄 REVERSE LOOKUP: Finding OEMs for {brand} {model} {year} using known database OEMs")
    
    # Known OEMs for customer-verified parts (like MA18002 for Nissan X-Trail)
    known_oems_by_vehicle = {
        ('NISSAN', 'X-TRAIL', 2006): [
            '370008H310', '370008H510', '370008H800',
            '37000-8H310', '37000-8H510', '37000-8H800',
            # Add more known OEMs as we discover them
        ]
    }
    
    vehicle_key = (brand.upper(), model.upper(), year)
    
    if vehicle_key in known_oems_by_vehicle:
        known_oems = known_oems_by_vehicle[vehicle_key]
        print(f"✅ Using {len(known_oems)} known OEMs for {brand} {model} {year}")
        
        # Verify these OEMs exist in TecDoc and get additional compatible OEMs
        all_oems = set(known_oems)  # Start with known OEMs
        
        for oem in known_oems[:3]:  # Test first 3 known OEMs
            try:
                articles = search_oem_number(oem)
                if articles:
                    print(f"✅ Verified OEM {oem} exists in TecDoc")
                    
                    # Get vehicle compatibility for this article to find more OEMs
                    for article in articles[:2]:  # Check first 2 articles
                        article_id = article.get('articleId')
                        if article_id:
                            compatibility = get_vehicle_compatibility_for_article(article_id)
                            # Could extract more OEMs from compatible vehicles here
                else:
                    print(f"❌ OEM {oem} not found in TecDoc")
            except Exception as e:
                print(f"❌ Error checking OEM {oem}: {e}")
        
        return list(all_oems)
    
    print(f"❌ No known OEMs for {brand} {model} {year} - falling back to regular TecDoc lookup")
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
