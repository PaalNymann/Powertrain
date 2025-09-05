#!/usr/bin/env python3
"""
Get real VIN from SVV using existing svv_client for ZT41818
Then test TecDoc VIN-based OEM lookup
"""

import requests
import json
from svv_client import hent_kjoretoydata

def extract_vin_from_svv_data(vehicle_data):
    """Extract VIN from SVV vehicle data"""
    try:
        kjoretoydata_liste = vehicle_data.get('kjoretoydataListe', [])
        if not kjoretoydata_liste:
            print("❌ No kjoretoydataListe found")
            return None
            
        kjoretoy_data = kjoretoydata_liste[0]
        kjoretoy_id = kjoretoy_data.get('kjoretoyId', {})
        
        # Extract VIN from understellsnummer
        vin = kjoretoy_id.get('understellsnummer')
        
        if vin:
            print(f"✅ VIN FOUND: {vin}")
            
            # Also show other vehicle info
            tekniske_data = kjoretoy_data.get('tekniskeData', {})
            generelt = tekniske_data.get('generelt', {})
            
            print(f"📋 Merke: {generelt.get('merke', {}).get('merkenavn', 'N/A')}")
            print(f"📋 Modell: {generelt.get('handelsbetegnelse', 'N/A')}")
            print(f"📋 År: {generelt.get('forstegangsregistrering', 'N/A')}")
            
            return vin
        else:
            print("❌ VIN not found in understellsnummer")
            print("🔍 Available kjoretoyId fields:")
            for key, value in kjoretoy_id.items():
                print(f"   - {key}: {value}")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting VIN: {e}")
        return None

def test_vin_in_tecdoc(vin):
    """Test VIN lookup in TecDoc with comprehensive endpoint testing"""
    print(f"\n🔍 TESTING VIN IN TECDOC: {vin}")
    print("=" * 60)
    
    # RapidAPI TecDoc Configuration
    RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
    HEADERS = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    
    # Try comprehensive list of VIN endpoint formats
    vin_endpoints = [
        # Standard VIN endpoints
        f"/vehicles/vin/{vin}/lang-id/4",
        f"/vehicles/vin/{vin}",
        f"/vehicle/vin/{vin}/lang-id/4", 
        f"/vin/{vin}/lang-id/4",
        f"/vin-lookup/{vin}",
        f"/vehicle-lookup/vin/{vin}",
        f"/decode/vin/{vin}",
        
        # Alternative formats
        f"/vehicles/decode/{vin}",
        f"/vehicle/decode/{vin}",
        f"/vin/decode/{vin}",
        f"/decode/{vin}",
        
        # With country filter
        f"/vehicles/vin/{vin}/lang-id/4/country-filter-id/62",
        f"/vehicle/vin/{vin}/lang-id/4/country-filter-id/62",
        
        # Different parameter orders
        f"/lang-id/4/vehicles/vin/{vin}",
        f"/lang-id/4/vehicle/vin/{vin}",
    ]
    
    successful_endpoints = []
    
    for endpoint in vin_endpoints:
        print(f"\n🔍 Testing: {BASE_URL}{endpoint}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ SUCCESS!")
                    print(f"   📋 Response type: {type(data)}")
                    
                    if isinstance(data, dict):
                        print(f"   📋 Keys: {list(data.keys())}")
                        # Extract vehicle ID if available
                        vehicle_id = data.get('vehicleId') or data.get('id') or data.get('vehicle_id')
                        if vehicle_id:
                            print(f"   🎯 Vehicle ID found: {vehicle_id}")
                    elif isinstance(data, list):
                        print(f"   📋 List length: {len(data)}")
                        if data:
                            print(f"   📋 First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'Not dict'}")
                    
                    successful_endpoints.append((endpoint, data))
                    
                    # Show first 300 chars of response
                    response_str = json.dumps(data, indent=2)
                    print(f"   📋 Response preview: {response_str[:300]}{'...' if len(response_str) > 300 else ''}")
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️ SUCCESS but invalid JSON: {response.text[:100]}")
                    successful_endpoints.append((endpoint, response.text))
                
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            else:
                print(f"   ❌ Error: {response.status_code}")
                if len(response.text) < 200:
                    print(f"   Response: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   Tested {len(vin_endpoints)} endpoints")
    print(f"   Successful: {len(successful_endpoints)}")
    
    if successful_endpoints:
        print(f"\n✅ WORKING ENDPOINTS:")
        for endpoint, data in successful_endpoints:
            print(f"   - {endpoint}")
        
        # Try to extract vehicle info from successful responses
        for endpoint, data in successful_endpoints:
            print(f"\n🔍 Analyzing response from {endpoint}:")
            if isinstance(data, dict):
                vehicle_id = data.get('vehicleId') or data.get('id') or data.get('vehicle_id')
                if vehicle_id:
                    print(f"   🎯 Testing OEM extraction for vehicle ID: {vehicle_id}")
                    test_oems_for_vehicle_id(vehicle_id, HEADERS, BASE_URL)
                    break
    else:
        print(f"\n❌ VIN {vin} not found in any TecDoc endpoint")
        print(f"   This could mean:")
        print(f"   1. VIN format is not supported by TecDoc")
        print(f"   2. Vehicle is not in TecDoc database")
        print(f"   3. Different VIN endpoints are needed")
    
    return successful_endpoints

def test_oems_for_vehicle_id(vehicle_id, headers, base_url):
    """Test getting OEMs for a specific vehicle ID"""
    print(f"\n   🔍 Getting OEMs for vehicle {vehicle_id}...")
    
    # Test both product groups
    product_groups = [
        (100260, "Drivaksler"),
        (100270, "Mellomaksler")
    ]
    
    all_oems = []
    
    for group_id, group_name in product_groups:
        try:
            url = f"{base_url}/articles/list/lang-id/4/country-filter-id/62/vehicle-id/{vehicle_id}/product-group-id/{group_id}"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                print(f"      ✅ {group_name}: Found {len(articles)} articles")
                
                if articles:
                    # Extract OEMs from articles
                    group_oems = []
                    for article in articles:
                        oem_numbers = article.get('oemNumbers', [])
                        for oem in oem_numbers:
                            oem_number = oem.get('oemNumber', '')
                            if oem_number and oem_number not in group_oems:
                                group_oems.append(oem_number)
                    
                    all_oems.extend(group_oems)
                    print(f"      📋 Found {len(group_oems)} unique OEMs")
                    print(f"      📋 Sample: {group_oems[:5]}")
                    
                    # Check for customer-verified OEMs
                    customer_oems = ['370008H310', '37000-8H310', '370008H510', '370008H800']
                    found_customer_oems = [oem for oem in customer_oems if oem in group_oems]
                    if found_customer_oems:
                        print(f"      🎯 FOUND CUSTOMER OEMs: {found_customer_oems}")
            else:
                print(f"      ❌ {group_name}: Failed {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ {group_name}: Exception {e}")
    
    print(f"\n   🎯 TOTAL OEMs found: {len(all_oems)}")
    if all_oems:
        print(f"   📋 All OEMs: {all_oems[:20]}{'...' if len(all_oems) > 20 else ''}")
        
        # Check for customer OEMs in all results
        customer_oems = ['370008H310', '37000-8H310', '370008H510', '370008H800']
        found_customer_oems = [oem for oem in customer_oems if oem in all_oems]
        if found_customer_oems:
            print(f"   🎯 CUSTOMER OEMs FOUND IN TOTAL: {found_customer_oems}")

def main():
    """Main function to test VIN-based TecDoc lookup using existing SVV client"""
    license_plate = "ZT41818"
    
    print(f"🚗 TESTING VIN-BASED TECDOC FOR: {license_plate}")
    print("=" * 60)
    
    try:
        # Step 1: Get vehicle data from SVV using existing client
        print(f"1️⃣ Getting vehicle data from SVV...")
        vehicle_data = hent_kjoretoydata(license_plate)
        
        if vehicle_data:
            print(f"✅ SVV data retrieved successfully")
            
            # Step 2: Extract VIN from vehicle data
            print(f"\n2️⃣ Extracting VIN from SVV data...")
            vin = extract_vin_from_svv_data(vehicle_data)
            
            if vin:
                # Step 3: Test VIN in TecDoc
                print(f"\n3️⃣ Testing VIN in TecDoc...")
                successful_endpoints = test_vin_in_tecdoc(vin)
                
                if successful_endpoints:
                    print(f"\n🎉 SUCCESS! VIN-based TecDoc lookup works for {license_plate}")
                    print(f"   VIN: {vin}")
                    print(f"   Working endpoints: {len(successful_endpoints)}")
                else:
                    print(f"\n❌ VIN-based TecDoc lookup failed for {license_plate}")
                    print(f"   VIN: {vin}")
                    print(f"   Need to investigate TecDoc VIN format requirements")
            else:
                print(f"\n❌ Could not extract VIN from SVV data")
        else:
            print(f"❌ Could not get vehicle data from SVV")
            
    except Exception as e:
        print(f"❌ Exception in main: {e}")

if __name__ == "__main__":
    main()
