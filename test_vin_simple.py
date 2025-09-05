#!/usr/bin/env python3
"""
Simple VIN test for ZT41818 without external dependencies
"""

import requests
import json
import os

def load_env_file():
    """Load .env file manually"""
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ .env file loaded successfully")
    except Exception as e:
        print(f"⚠️ Could not load .env file: {e}")

def get_svv_data_direct(license_plate):
    """Get SVV data directly without svv_client dependency"""
    print(f"🚗 GETTING SVV DATA FOR: {license_plate}")
    print("=" * 50)
    
    # Load .env file first
    load_env_file()
    
    # Try to get SVV API key from environment
    svv_api_key = os.getenv('SVV_API_KEY')
    
    if not svv_api_key:
        print("❌ SVV_API_KEY not found in environment")
        print("🔍 Available env vars starting with SVV:")
        for key in os.environ:
            if key.startswith('SVV'):
                print(f"   - {key}: {os.environ[key][:10]}...")
        return None
    
    print(f"✅ SVV API Key found: {svv_api_key[:8]}...")
    
    try:
        api_url = 'https://akfell-datautlevering.atlas.vegvesen.no/enkeltoppslag/kjoretoydata'
        
        headers = {
            'SVV-Authorization': f'Apikey {svv_api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            api_url,
            params={'kjennemerke': license_plate},
            headers=headers,
            timeout=30
        )
        
        print(f"SVV Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SVV data retrieved successfully")
            return data
        else:
            print(f"❌ SVV API failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def extract_vin_and_test_tecdoc(vehicle_data):
    """Extract VIN and test TecDoc in one function"""
    if not vehicle_data:
        return
    
    print(f"\n🔍 EXTRACTING VIN FROM SVV DATA")
    print("=" * 40)
    
    try:
        kjoretoydata_liste = vehicle_data.get('kjoretoydataListe', [])
        if not kjoretoydata_liste:
            print("❌ No kjoretoydataListe found")
            return
            
        kjoretoy_data = kjoretoydata_liste[0]
        kjoretoy_id = kjoretoy_data.get('kjoretoyId', {})
        
        # Extract VIN
        vin = kjoretoy_id.get('understellsnummer')
        
        if vin:
            print(f"✅ VIN FOUND: {vin}")
            
            # Show vehicle info
            tekniske_data = kjoretoy_data.get('tekniskeData', {})
            generelt = tekniske_data.get('generelt', {})
            
            print(f"📋 Merke: {generelt.get('merke', {}).get('merkenavn', 'N/A')}")
            print(f"📋 Modell: {generelt.get('handelsbetegnelse', 'N/A')}")
            print(f"📋 År: {generelt.get('forstegangsregistrering', 'N/A')}")
            
            # Test VIN in TecDoc
            test_vin_in_tecdoc(vin)
            
        else:
            print("❌ VIN not found in understellsnummer")
            print("🔍 Available kjoretoyId fields:")
            for key, value in kjoretoy_id.items():
                print(f"   - {key}: {value}")
            
    except Exception as e:
        print(f"❌ Error extracting VIN: {e}")

def test_vin_in_tecdoc(vin):
    """Test VIN in TecDoc - focused on most likely endpoints"""
    print(f"\n🔍 TESTING VIN IN TECDOC: {vin}")
    print("=" * 50)
    
    RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
    HEADERS = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    
    # Most likely VIN endpoints based on TecDoc documentation
    priority_endpoints = [
        f"/vehicles/vin/{vin}/lang-id/4",
        f"/vehicle/vin/{vin}/lang-id/4",
        f"/vin/{vin}/lang-id/4",
        f"/decode/vin/{vin}",
        f"/vehicles/decode/{vin}"
    ]
    
    for endpoint in priority_endpoints:
        print(f"\n🔍 Testing: {BASE_URL}{endpoint}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS!")
                print(f"   📋 Response: {json.dumps(data, indent=2)[:300]}...")
                
                # Look for vehicle ID
                vehicle_id = None
                if isinstance(data, dict):
                    vehicle_id = data.get('vehicleId') or data.get('id') or data.get('vehicle_id')
                    
                if vehicle_id:
                    print(f"   🎯 Vehicle ID: {vehicle_id}")
                    test_oems_for_vehicle(vehicle_id, HEADERS, BASE_URL)
                
                return True
                
            elif response.status_code != 404:
                print(f"   ⚠️ Unexpected status: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n❌ VIN {vin} not found in TecDoc")
    return False

def test_oems_for_vehicle(vehicle_id, headers, base_url):
    """Get OEMs for vehicle ID"""
    print(f"\n   🔍 Getting OEMs for vehicle {vehicle_id}...")
    
    product_groups = [(100260, "Drivaksler"), (100270, "Mellomaksler")]
    customer_oems = ['370008H310', '37000-8H310', '370008H510', '370008H800']
    
    for group_id, group_name in product_groups:
        try:
            url = f"{base_url}/articles/list/lang-id/4/country-filter-id/62/vehicle-id/{vehicle_id}/product-group-id/{group_id}"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                print(f"      ✅ {group_name}: {len(articles)} articles")
                
                if articles:
                    # Extract OEMs
                    oems = []
                    for article in articles[:5]:  # First 5 articles
                        for oem in article.get('oemNumbers', []):
                            oem_number = oem.get('oemNumber', '')
                            if oem_number:
                                oems.append(oem_number)
                    
                    print(f"      📋 Sample OEMs: {oems[:10]}")
                    
                    # Check customer OEMs
                    found = [oem for oem in customer_oems if oem in oems]
                    if found:
                        print(f"      🎯 CUSTOMER OEMs: {found}")
            else:
                print(f"      ❌ {group_name}: {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ {group_name}: {e}")

def main():
    """Main test function"""
    license_plate = "ZT41818"
    
    print(f"🚗 VIN-BASED TECDOC TEST FOR: {license_plate}")
    print("=" * 60)
    
    # Get SVV data
    vehicle_data = get_svv_data_direct(license_plate)
    
    # Extract VIN and test TecDoc
    extract_vin_and_test_tecdoc(vehicle_data)

if __name__ == "__main__":
    main()
