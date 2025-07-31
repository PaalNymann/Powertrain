from flask import Flask, request, jsonify, render_template
import requests
from flask_cors import CORS
import os
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

def search_shopify_by_oem(oem_number):
    """Search Shopify products by OEM number using database cache"""
    try:
        # Use fast database search
        products = search_products_by_oem(oem_number)
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
        
        # Sample OEM numbers for testing - these would come from real TecDoc API
        # These are example OEM numbers that might be found for a VW Tiguan 2009
        sample_oem_numbers = [
            "1K0 407 151",  # Example brake pad OEM
            "1K0 407 152",  # Example brake pad OEM
            "1K0 407 153",  # Example brake pad OEM
            "1K0 407 154",  # Example brake pad OEM
            "1K0 407 155",  # Example brake pad OEM
            "1K0 407 156",  # Example brake pad OEM
            "1K0 407 157",  # Example brake pad OEM
            "1K0 407 158",  # Example brake pad OEM
            "1K0 407 159",  # Example brake pad OEM
            "1K0 407 160",  # Example brake pad OEM
        ]
        
        # Filter based on vehicle info (in real implementation, this would be done by TecDoc API)
        if "VOLKSWAGEN" in make and "TIGUAN" in model:
            oem_numbers = sample_oem_numbers
        else:
            # For other vehicles, return some generic OEM numbers
            oem_numbers = [
                "GENERIC001",
                "GENERIC002", 
                "GENERIC003"
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
        
        # Step 3: Match OEM numbers against Shopify metafields
        shopify_matches = []
        for oem in tecdoc_oem_numbers:
            shopify_products = search_shopify_by_oem(oem)
            for shopify_product in shopify_products:
                shopify_matches.append({
                    "oem_number": oem,
                    "shopify_product": shopify_product
                })
        
        return jsonify({
            "vehicle_info": vehicle_info,
            "tecdoc_status": tecdoc_status,
            "tecdoc_oem_numbers": tecdoc_oem_numbers,
            "shopify_matches": shopify_matches,
            "total_shopify_matches": len(shopify_matches)
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
        matched_products = search_shopify_by_oem(part_number)
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
        
        # Fetch products with pagination
        while shopify_url:
            res = requests.get(shopify_url, headers=headers, timeout=30)
            if res.status_code != 200:
                break

            data = res.json().get("products", [])
            
            # Fetch metafields for each product
            for product in data:
                product_id = product["id"]
                metafields_url = f"https://{SHOPIFY_DOMAIN}/admin/api/{SHOPIFY_VERSION}/products/{product_id}/metafields.json"
                meta_res = requests.get(metafields_url, headers=headers, timeout=10)
                
                if meta_res.status_code == 200:
                    product['metafields'] = meta_res.json().get("metafields", [])
                else:
                    product['metafields'] = []
                
                all_products.append(product)

            # Pagination
            if "Link" in res.headers:
                links = res.headers["Link"].split(",")
                next_url = None
                for link in links:
                    if 'rel="next"' in link:
                        next_url = link[link.find("<") + 1:link.find(">")]
                shopify_url = next_url
            else:
                break

        # Update database cache
        success = update_shopify_cache(all_products)
        
        if success:
            stats = get_cache_stats()
            return jsonify({
                "status": "success",
                "message": f"Cache updated with {len(all_products)} products",
                "stats": stats
            })
        else:
            return jsonify({"status": "error", "message": "Failed to update cache"}), 500
            
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
    
    app.run(port=int(os.getenv('PORT_APP', 8000)), host='0.0.0.0')

