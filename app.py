from flask import Flask, request, jsonify, render_template
import requests
from flask_cors import CORS
import os
import time
from dotenv import load_dotenv
from svv_client import hent_kjoretoydata
from database import init_db, search_products_by_oem, update_shopify_cache, get_cache_stats

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app, origins="*")

# API Configuration
RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
SHOPIFY_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')
SHOPIFY_VERSION = os.getenv('SHOPIFY_VERSION', '2023-10')
MECAPARTS_ENDPOINT = "https://bm0did-zc.myshopify.com/apps/mecaparts/api/vehicle_parts"

def extract_vehicle_info(vehicle_data):
    """Extract only essential vehicle info: make, model, year"""
    try:
        vehicle_list = vehicle_data.get('kjoretoydataListe', [])
        if not vehicle_list:
            return None
            
        vehicle = vehicle_list[0]
        
        # Extract make
        make = "Unknown"
        generelt = vehicle.get('godkjenning', {}).get('tekniskGodkjenning', {}).get('tekniskeData', {}).get('generelt', {})
        merke_list = generelt.get('merke', [])
        if merke_list:
            make = merke_list[0].get('merke', 'Unknown')
        
        # Extract model
        model = "Unknown"
        handelsbetegnelse = generelt.get('handelsbetegnelse', [])
        if handelsbetegnelse:
            model = handelsbetegnelse[0]
        
        # Extract year
        year = "Unknown"
        reg_date = vehicle.get('forstegangsregistrering', {}).get('registrertForstegangNorgeDato', '')
        if reg_date:
            year = reg_date.split('-')[0]
        
        return {
            "make": make,
            "model": model,
            "year": year
        }
    except Exception as e:
        return None

def search_shopify_by_oem(oem_number, include_number=False):
    """Search Shopify products by OEM number using database cache"""
    try:
        # Use fast database search
        products = search_products_by_oem(oem_number, include_number=include_number)
        return products
    except Exception as e:
        print(f"Error searching database: {e}")
        return []

def extract_oem_numbers(description):
    """Extract OEM numbers from product description"""
    if not description:
        return []
    
    # Common OEM number patterns (alphanumeric, typically 6-15 characters)
    import re
    oem_pattern = r'\b[A-Z0-9]{6,15}\b'
    matches = re.findall(oem_pattern, description.upper())
    
    # Filter out common non-OEM patterns
    filtered_matches = []
    for match in matches:
        if len(match) >= 6 and len(match) <= 15:
            if not match.isdigit() or len(match) >= 8:
                filtered_matches.append(match)
    
    return filtered_matches

def get_oem_numbers_from_mecaparts(brand, model, year):
    """Get OEM numbers from MecaParts via Shopify API - FUNGERENDE LØSNING"""
    url = MECAPARTS_ENDPOINT
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "brand": brand,
        "model": model,
        "year": year
    }
    
    print(f"🔍 Calling MecaParts API: {url}")
    print(f"📋 Payload: {payload}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload)
        print(f"📡 Response status: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ MecaParts API error: {resp.status_code}")
            return {"error": "Mecaparts API error", "status_code": resp.status_code}
        
        response_data = resp.json()
        print(f"📦 Response data: {response_data}")
        
        oem_numbers = response_data.get("oem_numbers", [])
        print(f"📦 Found {len(oem_numbers)} OEM numbers from MecaParts")
        return oem_numbers
        
    except Exception as e:
        print(f"❌ Error calling MecaParts API: {e}")
        return []

def get_mecaparts_parts(make, model, year):
    """Get OEM numbers from MecaParts via Shopify API - FUNGERENDE LØSNING"""
    try:
        print(f"🔍 Getting MecaParts parts for: {make} {model} {year}")
        
        # Use the working MecaParts API call
        oem_numbers = get_oem_numbers_from_mecaparts(make, model, year)
        
        if isinstance(oem_numbers, list):
            print(f"📦 Found {len(oem_numbers)} OEM numbers for {make} {model} {year}")
            return oem_numbers
        else:
            print(f"⚠️ Error from MecaParts: {oem_numbers}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting MecaParts parts: {e}")
        return []

def query_tecdoc_api(vehicle_info):
    """Query TecDoc API via MecaParts for OEM numbers - FUNGERENDE LØSNING"""
    try:
        brand = vehicle_info.get("make", "").upper()
        model = vehicle_info.get("model", "").upper()
        year = vehicle_info.get("year", "")
        
        print(f"🔍 Querying MecaParts/TecDoc for: {brand} {model} {year}")
        
        # Use the working MecaParts function
        oem_numbers = get_mecaparts_parts(brand, model, year)
        
        if isinstance(oem_numbers, list):
            print(f"📦 Found {len(oem_numbers)} OEM numbers for {brand} {model} {year}")
            return oem_numbers
        else:
            print(f"⚠️ Error from MecaParts: {oem_numbers}")
            return []
        
    except Exception as e:
        print(f"❌ Error querying MecaParts/TecDoc API: {e}")
        return []

def extract_oem_numbers_from_mecaparts(mecaparts_data):
    """Extract OEM numbers from MecaParts/TecDoc API response"""
    oem_numbers = []
    
    try:
        print(f"🔍 Parsing MecaParts response...")
        print(f"📋 Response keys: {list(mecaparts_data.keys()) if isinstance(mecaparts_data, dict) else 'Not a dict'}")
        
        # Handle different possible response structures
        if isinstance(mecaparts_data, dict):
            # Try different possible response formats
            if 'parts' in mecaparts_data:
                parts = mecaparts_data['parts']
                print(f"📦 Found {len(parts)} parts in response")
                
                for part in parts:
                    # Extract OEM numbers from various possible fields
                    oem_fields = ['oem_numbers', 'oem', 'original_numbers', 'original_nummer', 'part_numbers']
                    
                    for field in oem_fields:
                        if field in part and part[field]:
                            if isinstance(part[field], list):
                                oem_numbers.extend(part[field])
                            elif isinstance(part[field], str):
                                # Handle comma-separated OEM numbers
                                numbers = [num.strip() for num in part[field].split(',') if num.strip()]
                                oem_numbers.extend(numbers)
                            break
                    
                    # Also check if OEM number is directly in the part
                    if 'oem_number' in part and part['oem_number']:
                        oem_numbers.append(part['oem_number'])
                        
            elif 'oem_numbers' in mecaparts_data:
                # Direct OEM numbers array
                oem_numbers = mecaparts_data['oem_numbers']
                
            elif 'data' in mecaparts_data:
                # Nested data structure
                data = mecaparts_data['data']
                if isinstance(data, list):
                    for item in data:
                        if 'oem_number' in item:
                            oem_numbers.append(item['oem_number'])
                elif isinstance(data, dict):
                    oem_numbers = extract_oem_numbers_from_mecaparts(data)
        
        # Remove duplicates and clean up
        oem_numbers = list(set([str(num).strip() for num in oem_numbers if num and str(num).strip()]))
        
        print(f"✅ Extracted {len(oem_numbers)} unique OEM numbers: {oem_numbers[:10]}...")
        return oem_numbers
        
    except Exception as e:
        print(f"❌ Error extracting OEM numbers from MecaParts: {e}")
        print(f"📋 Full response: {mecaparts_data}")
        return oem_numbers

@app.route('/api/statens_vegvesen')
def get_vehicle_info():
    kjennemerke = request.args.get('kjennemerke') or request.args.get('regnr')
    if not kjennemerke:
        return jsonify({"error": "Missing kjennemerke or regnr parameter"}), 400

    try:
        vehicle_data = hent_kjoretoydata(kjennemerke)
        return jsonify(vehicle_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/car_parts_search')
def car_parts_search():
    """Car parts search endpoint - FUNGERENDE LØSNING basert på Sintras dokumentasjon"""
    regnr = request.args.get('regnr')
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400

    try:
        print(f"🚗 Starting car parts search for license plate: {regnr}")
        
        # Step 1: Get vehicle data from Statens Vegvesen
        print(f"📡 Step 1: Getting vehicle data from SVV for {regnr}")
        try:
            vehicle_data = hent_kjoretoydata(regnr)
            vehicle_info = extract_vehicle_info(vehicle_data)
            
            if not vehicle_info:
                return jsonify({"error": "Could not extract vehicle information"}), 400
        except Exception as svv_error:
            print(f"❌ SVV/Maskinporten error: {svv_error}")
            return jsonify({
                "error": "Kunne ikke koble til serveren. Prøv igjen senere.",
                "details": str(svv_error)
            }), 500
        
        print(f"✅ Vehicle info extracted: {vehicle_info}")
        
        # Step 2: Get OEM numbers from MecaParts via Shopify
        print(f"🔍 Step 2: Getting OEM numbers from MecaParts for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
        tecdoc_oem_numbers = query_tecdoc_api(vehicle_info)
        tecdoc_status = "Success" if tecdoc_oem_numbers else "No OEM numbers found"
        
        print(f"📦 Found {len(tecdoc_oem_numbers)} OEM numbers from MecaParts: {tecdoc_oem_numbers[:5]}...")
        
        # Step 3: Match OEM numbers against Shopify products
        print(f"🛍️ Step 3: Searching Shopify products for OEM numbers")
        shopify_matches = []
        shopify_parts = []
        
        for oem in tecdoc_oem_numbers:
            # Clean OEM number
            clean_oem = oem.replace(" ", "").upper()
            
            # Search Shopify products
            shopify_products = search_shopify_by_oem(clean_oem, include_number=False)
            
            # If no exact match, try partial matches
            if not shopify_products and len(clean_oem) >= 3:
                partial_searches = [
                    clean_oem[:3],  # First 3 chars
                    clean_oem[:4],  # First 4 chars
                    clean_oem[:6]   # First 6 chars
                ]
                
                for partial in partial_searches:
                    if len(partial) >= 3:
                        shopify_products = search_shopify_by_oem(partial, include_number=False)
                        if shopify_products:
                            break
            
            # Add matches
            for shopify_product in shopify_products:
                shopify_matches.append({
                    "matching_oem": oem,
                    "shopify_product": shopify_product
                })
                shopify_parts.append(shopify_product)
        
        print(f"✅ Found {len(shopify_parts)} matching Shopify products")
        
        # Step 4: Get Rackbeat parts (placeholder for now)
        rackbeat_parts = []
        rackbeat_status = "Not implemented - using Shopify data"
        
        return jsonify({
            "vehicle_info": vehicle_info,
            "tecdoc_status": tecdoc_status,
            "tecdoc_oem_numbers": tecdoc_oem_numbers,
            "rackbeat_parts": rackbeat_parts,
            "rackbeat_status": rackbeat_status,
            "shopify_matches": shopify_matches,
            "shopify_parts": shopify_parts,
            "total_shopify_matches": len(shopify_parts),
            "search_summary": {
                "license_plate": regnr,
                "vehicle": f"{vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}",
                "oem_numbers_found": len(tecdoc_oem_numbers),
                "shopify_products_found": len(shopify_parts)
            }
        })
        
    except Exception as e:
        print(f"❌ Error in car_parts_search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/part_number_search')
def part_number_search():
    part_number = request.args.get("part_number")
    if not part_number:
        return jsonify({"error": "Missing part_number parameter"}), 400

    try:
        print(f"🔍 Searching for part number: {part_number}")
        matched_products = search_shopify_by_oem(part_number, include_number=True)
        print(f"🔍 Found {len(matched_products)} products")
        return jsonify({
            "part_number": part_number,
            "products": matched_products,
            "count": len(matched_products)
        })
    except Exception as e:
        print(f"❌ Error in part_number_search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/rackbeat/parts')
def get_rackbeat_parts():
    try:
        url = "https://app.rackbeat.com/api/products"
        headers = {"Authorization": f"Bearer {RACKBEAT_API_KEY}"}
        params = {"limit": 20}  # Limit to 20 products for faster response
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code in [200, 206]:
            data = response.json()
            products = data.get('products', [])
            return jsonify({"products": products})
        else:
            return jsonify({"error": f"Rackbeat API error: {response.status_code}"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/shopify/products', methods=['POST'])
def create_shopify_product():
    try:
        data = request.json
        # Implementation for creating Shopify products
        return jsonify({"message": "Shopify product creation endpoint"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/shopify/variant/<product_id>')
def get_variant_id(product_id):
    """Get variant ID for a given product ID"""
    try:
        url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products/{product_id}.json"
        headers = {
            'X-Shopify-Access-Token': SHOPIFY_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            product_data = response.json().get('product', {})
            variants = product_data.get('variants', [])
            if variants:
                return jsonify({
                    'variant_id': str(variants[0]['id']),
                    'product_id': product_id
                })
        
        return jsonify({'error': 'No variant found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "service": "license-plate-service"})

@app.route('/api/test_mecaparts')
def test_mecaparts():
    """Test MecaParts integration directly"""
    try:
        # Test with Volkswagen Tiguan 2009
        vehicle_info = {
            "make": "VOLKSWAGEN",
            "model": "TIGUAN", 
            "year": "2009"
        }
        
        print(f"🧪 Testing MecaParts integration with: {vehicle_info}")
        
        # Get OEM numbers from MecaParts
        oem_numbers = query_tecdoc_api(vehicle_info)
        
        return jsonify({
            "vehicle_info": vehicle_info,
            "oem_numbers": oem_numbers,
            "count": len(oem_numbers),
            "status": "success"
        })
        
    except Exception as e:
        print(f"❌ Error testing MecaParts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/cache/update', methods=['POST'])
def update_cache():
    """Update Shopify products cache"""
    try:
        # Fetch all Shopify products with metafields
        shopify_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products.json?limit=250"
        headers = {
            "X-Shopify-Access-Token": SHOPIFY_TOKEN,
            "Content-Type": "application/json"
        }

        all_products = []
        page_info = None
        page_count = 0
        debug_info = []
        
        # Fetch products with pagination using Link headers
        while True:
            page_count += 1
            current_url = shopify_url
            if page_info:
                current_url += f"&page_info={page_info}"
            
            debug_msg = f"📥 Fetching page {page_count}..."
            print(debug_msg)
            debug_info.append(debug_msg)
            
            debug_msg = f"   URL: {current_url}"
            print(debug_msg)
            debug_info.append(debug_msg)
            
            # Rate limiting: wait 0.5 seconds between requests to respect Shopify's 2 calls/second limit
            if page_count > 1:
                time.sleep(0.5)
                
            res = requests.get(current_url, headers=headers, timeout=30)
            
            debug_msg = f"   Status: {res.status_code}"
            print(debug_msg)
            debug_info.append(debug_msg)
            
            if res.status_code != 200:
                debug_msg = f"❌ Error on page {page_count}: {res.status_code}"
                print(debug_msg)
                debug_info.append(debug_msg)
                debug_msg = f"   Response: {res.text}"
                print(debug_msg)
                debug_info.append(debug_msg)
                break

            data = res.json().get("products", [])
            debug_msg = f"📦 Found {len(data)} products on page {page_count}"
            print(debug_msg)
            debug_info.append(debug_msg)
            
            if len(data) == 0:
                debug_msg = f"   ⚠️  No products in response"
                print(debug_msg)
                debug_info.append(debug_msg)
                debug_msg = f"   Response keys: {list(res.json().keys())}"
                print(debug_msg)
                debug_info.append(debug_msg)
            
            if not data:  # No more products
                debug_msg = f"✅ No more products found on page {page_count}"
                print(debug_msg)
                debug_info.append(debug_msg)
                break
            
            # Fetch metafields for each product
            for i, product in enumerate(data):
                product_id = product["id"]
                metafields_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products/{product_id}/metafields.json"
                
                # Rate limiting for metafield calls
                if i > 0 and i % 2 == 0:  # Wait every 2 calls
                    time.sleep(0.5)
                    
                meta_res = requests.get(metafields_url, headers=headers, timeout=10)
                
                if meta_res.status_code == 200:
                    product['metafields'] = meta_res.json().get("metafields", [])
                else:
                    product['metafields'] = []
                
                all_products.append(product)
                
                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"   📋 Processed {i + 1}/{len(data)} products on page {page_count}")

            # Check for pagination using Link headers
            link = res.headers.get("link", "")
            debug_msg = f"   🔗 Link header: {link}"
            print(debug_msg)
            debug_info.append(debug_msg)
            
            if 'rel="next"' in link:
                # Find the next page_info specifically
                next_link = [l for l in link.split(',') if 'rel="next"' in l]
                if next_link:
                    page_info = next_link[0].split("page_info=")[1].split(">")[0]
                    debug_msg = f"   ➡️  Next page_info: {page_info}"
                    print(debug_msg)
                    debug_info.append(debug_msg)
                else:
                    debug_msg = f"   ❌ Could not find next page_info"
                    print(debug_msg)
                    debug_info.append(debug_msg)
                    break
            else:
                debug_msg = f"   ✅ No more pages available"
                print(debug_msg)
                debug_info.append(debug_msg)
                break
            
            # Safety check - don't go beyond reasonable page count
            if page_count > 100:  # Max 25000 products (100 pages * 250)
                print(f"⚠️  Reached maximum page limit ({page_count})")
                break

        # Update database cache
        success = update_shopify_cache(all_products)
        
        if success:
            stats = get_cache_stats()
            return jsonify({
                "status": "success",
                "message": f"Cache updated with {len(all_products)} products",
                "stats": stats,
                "debug": debug_info
            })
        else:
            return jsonify({"status": "error", "message": "Failed to update cache", "debug": debug_info}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/cache/stats')
def cache_stats():
    """Get cache statistics"""
    try:
        stats = get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



if __name__ == '__main__':
    # Initialize database
    init_db()
    print("Database initialized")
    
    app.run(port=int(os.getenv('PORT', 8000)), host='0.0.0.0')

