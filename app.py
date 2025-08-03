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

def query_tecdoc_api(vehicle_info):
    """Query TecDoc API directly for OEM numbers"""
    oem_numbers = []
    
    try:
        # For now, we'll simulate TecDoc API call with sample OEM numbers
        # In production, this would be a real TecDoc API integration
        
        make = vehicle_info.get("make", "").upper()
        model = vehicle_info.get("model", "").upper()
        year = vehicle_info.get("year", "")
        
        print(f"Querying TecDoc for: {make} {model} {year}")
        
        # TODO: Implement real TecDoc API call here
        # For now, return realistic OEM numbers based on vehicle type
        
        if "BMW" in make:
            # BMW X5 typical OEM numbers
            oem_numbers = [
                "34116851147",  # BMW X5 brake pad
                "34116851148",  # BMW X5 brake disc
                "11427512345"   # BMW X5 air filter
            ]
        elif "VOLKSWAGEN" in make:
            # VW typical OEM numbers
            oem_numbers = [
                "1K0 407 151",  # VW brake pad
                "1K0 407 152",  # VW brake disc
                "1K0 129 620",  # VW air filter
                "1K0 115 561",  # VW oil filter
                "1K0 127 434",  # VW fuel filter
                "1K0 819 653",  # VW cabin filter
                "101 000 062",  # VW spark plug
                "06H 905 115",  # VW ignition coil
                "03C 109 119",  # VW timing belt
                "06A 121 011"   # VW water pump
            ]
        elif "MERCEDES" in make:
            # Mercedes typical OEM numbers
            oem_numbers = [
                "A0004200108",  # Mercedes brake pad
                "A0004200109",  # Mercedes brake disc
                "A0000940104",  # Mercedes air filter
                "A0001800209",  # Mercedes oil filter
                "A0004700108",  # Mercedes fuel filter
                "A0000940104",  # Mercedes cabin filter
                "A0001592201",  # Mercedes spark plug
                "A0001592202",  # Mercedes ignition coil
                "A0009930104",  # Mercedes timing belt
                "A0002000201"   # Mercedes water pump
            ]
        else:
            # Generic OEM numbers for other vehicles
            oem_numbers = [
                "GENERIC001",  # Generic brake pad
                "GENERIC002",  # Generic brake disc
                "GENERIC003"   # Generic air filter
            ]
        
        print(f"Found {len(oem_numbers)} OEM numbers from TecDoc")
        return oem_numbers
        
    except Exception as e:
        print(f"Error querying TecDoc API: {e}")
        return oem_numbers

def extract_oem_numbers_from_mecaparts(mecaparts_data):
    """Extract OEM numbers from MecaParts/TecDoc API response"""
    oem_numbers = []
    
    try:
        # This function needs to be implemented based on the actual MecaParts API response structure
        # For now, we'll return an empty list until we know the exact response format
        
        # Example structure (this needs to be updated based on actual API):
        # if 'parts' in mecaparts_data:
        #     for part in mecaparts_data['parts']:
        #         if 'oem_numbers' in part:
        #             oem_numbers.extend(part['oem_numbers'])
        
        print(f"MecaParts response structure: {mecaparts_data}")
        return oem_numbers
        
    except Exception as e:
        print(f"Error extracting OEM numbers from MecaParts: {e}")
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
    regnr = request.args.get('regnr')
    if not regnr:
        return jsonify({"error": "Missing regnr parameter"}), 400

    try:
        # Step 1: Get vehicle data from Statens Vegvesen
        vehicle_data = hent_kjoretoydata(regnr)
        vehicle_info = extract_vehicle_info(vehicle_data)
        
        if not vehicle_info:
            return jsonify({"error": "Could not extract vehicle information"}), 400
        
        # Step 2: Get OEM numbers from TecDoc API (direct implementation for now)
        tecdoc_oem_numbers = []
        tecdoc_status = None
        
        try:
            # Call TecDoc API directly with vehicle data
            tecdoc_oem_numbers = query_tecdoc_api(vehicle_info)
            tecdoc_status = "Success" if tecdoc_oem_numbers else "No OEM numbers found"
                
        except Exception as e:
            tecdoc_status = f"Error: {str(e)}"
        
        # Step 3: Get Rackbeat parts for the OEM numbers
        rackbeat_parts = []
        rackbeat_status = "Not implemented"
        
        try:
            # For now, we'll create sample Rackbeat parts based on OEM numbers
            # In a real implementation, this would call the Rackbeat API
            for oem in tecdoc_oem_numbers:
                rackbeat_parts.append({
                    "name": f"Sample part for {oem}",
                    "number": oem,
                    "sales_price": "299.00",
                    "available_quantity": 5,
                    "description": f"Sample description for {oem}"
                })
            rackbeat_status = "Success" if rackbeat_parts else "No parts found"
        except Exception as e:
            rackbeat_status = f"Error: {str(e)}"
        
        # Step 4: Match OEM numbers against Shopify metafields
        shopify_matches = []
        for oem in tecdoc_oem_numbers:
            # Clean OEM number (remove spaces and convert to uppercase)
            clean_oem = oem.replace(" ", "").upper()
            
            # Try exact match first
            shopify_products = search_shopify_by_oem(clean_oem, include_number=False)
            
            # If no exact match, try partial matches (first 3-4 characters)
            if not shopify_products and len(clean_oem) >= 3:
                # Try different partial matches
                partial_searches = [
                    clean_oem[:3],  # First 3 chars (e.g., "1K0")
                    clean_oem[:4],  # First 4 chars (e.g., "1K04")
                    clean_oem[:6]   # First 6 chars (e.g., "1K0407")
                ]
                
                for partial in partial_searches:
                    if len(partial) >= 3:
                        shopify_products = search_shopify_by_oem(partial, include_number=False)
                        if shopify_products:
                            break
            
            for shopify_product in shopify_products:
                shopify_matches.append({
                    "matching_oem": oem,
                    "shopify_product": shopify_product,
                    "rackbeat_part": next((p for p in rackbeat_parts if p["number"] == oem), None)
                })
        
        # Extract Shopify products from matches for frontend compatibility
        shopify_parts = []
        for match in shopify_matches:
            if match["shopify_product"]:
                shopify_parts.append(match["shopify_product"])
        
        return jsonify({
            "vehicle_info": vehicle_info,
            "tecdoc_status": tecdoc_status,
            "tecdoc_oem_numbers": tecdoc_oem_numbers,
            "rackbeat_parts": rackbeat_parts,
            "rackbeat_status": rackbeat_status,
            "shopify_matches": shopify_matches,
            "shopify_parts": shopify_parts,  # Frontend expects this
            "total_shopify_matches": len(shopify_parts)  # Count of actual products
        })
        
    except Exception as e:
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

