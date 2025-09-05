#!/usr/bin/env python3
"""
Get real VIN from SVV for ZT41818 (Nissan X-Trail 2006)
Then test TecDoc VIN-based OEM lookup
"""

import requests
import json

def get_vin_from_svv(license_plate):
    """Get VIN/chassis number from SVV for a license plate"""
    print(f"🚗 GETTING VIN FROM SVV FOR: {license_plate}")
    print("=" * 50)
    
    try:
        # SVV API call
        url = f"https://www.vegvesen.no/ws/no/vegvesen/kjoretoy/felles/datautlevering/enkeltoppslag/kjoretoydata?kjennemerke={license_plate}"
        
        response = requests.get(url, timeout=30)
        print(f"SVV Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract VIN from the correct field
            kjoretoy_data = data.get('kjoretoydataListe', [])
            if kjoretoy_data:
                kjoretoy_id = kjoretoy_data[0].get('kjoretoyId', {})
                vin = kjoretoy_id.get('understellsnummer')
                
                if vin:
                    print(f"✅ VIN FOUND: {vin}")
                    
                    # Also extract other useful info
                    tekniske_data = kjoretoy_data[0].get('tekniskeData', {})
                    generelt = tekniske_data.get('generelt', {})
                    
                    print(f"📋 Merke: {generelt.get('merke', {}).get('merkenavn', 'N/A')}")
                    print(f"📋 Modell: {generelt.get('handelsbetegnelse', 'N/A')}")
                    print(f"📋 År: {generelt.get('forstegangsregistrering', 'N/A')}")
                    
                    return vin
                else:
                    print("❌ VIN not found in understellsnummer field")
                    
                    # Debug: show available fields
                    print("🔍 Available kjoretoyId fields:")
                    for key in kjoretoy_id.keys():
                        print(f"   - {key}: {kjoretoy_id[key]}")
            else:
                print("❌ No kjoretoydata found")
                
        else:
            print(f"❌ SVV API failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    return None

def test_vin_in_tecdoc(vin):
    """Test VIN lookup in TecDoc"""
    print(f"\n🔍 TESTING VIN IN TECDOC: {vin}")
    print("=" * 50)
    
    # RapidAPI TecDoc Configuration
    RAPIDAPI_KEY = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    BASE_URL = "https://tecdoc-catalog.p.rapidapi.com"
    HEADERS = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    
    # Try different VIN endpoint formats
    vin_endpoints = [
        f"/vehicles/vin/{vin}/lang-id/4",
        f"/vehicles/vin/{vin}",
        f"/vehicle/vin/{vin}/lang-id/4", 
        f"/vin/{vin}/lang-id/4",
        f"/vin-lookup/{vin}",
        f"/vehicle-lookup/vin/{vin}",
        f"/decode/vin/{vin}"
    ]
    
    for endpoint in vin_endpoints:
        print(f"\n🔍 Testing: {BASE_URL}{endpoint}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, timeout=30)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS!")
                print(f"   📋 Response: {json.dumps(data, indent=2)[:500]}...")
                
                # Extract vehicle ID if available
                vehicle_id = None
                if isinstance(data, dict):
                    vehicle_id = data.get('vehicleId') or data.get('id') or data.get('vehicle_id')
                
                if vehicle_id:
                    print(f"   🎯 Vehicle ID found: {vehicle_id}")
                    test_oems_for_vehicle_id(vehicle_id, HEADERS, BASE_URL)
                
                return data
                
            elif response.status_code == 404:
                print(f"   ❌ Not found")
            else:
                print(f"   ❌ Error: {response.status_code}")
                if len(response.text) < 200:
                    print(f"   Response: {response.text}")
                    
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print(f"\n❌ VIN {vin} not found in any TecDoc endpoint")
    return None

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

def main():
    """Main function to test VIN-based TecDoc lookup"""
    license_plate = "ZT41818"
    
    # Step 1: Get VIN from SVV
    vin = get_vin_from_svv(license_plate)
    
    if vin:
        # Step 2: Test VIN in TecDoc
        tecdoc_result = test_vin_in_tecdoc(vin)
        
        if tecdoc_result:
            print(f"\n🎉 SUCCESS! VIN-based TecDoc lookup works for {license_plate}")
        else:
            print(f"\n❌ VIN-based TecDoc lookup failed for {license_plate}")
            print(f"   VIN: {vin}")
            print(f"   Need to investigate TecDoc VIN format requirements")
    else:
        print(f"\n❌ Could not get VIN for {license_plate}")

if __name__ == "__main__":
    main()
