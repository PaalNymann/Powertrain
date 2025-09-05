#!/usr/bin/env python3
"""
TEST VIN-BASED TECDOC LOOKUP - The RIGHT way to do it!
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

def test_vin_lookup():
    """Test VIN-based TecDoc lookup for ZT41818"""
    print("🚗 TESTING VIN-BASED TECDOC LOOKUP")
    print("=" * 50)
    
    # ZT41818 VIN from SVV: JNKCV11E06M000000 (example, need real VIN)
    test_vins = [
        "JNKCV11E06M000000",  # Nissan X-Trail format
        "JN1CV11E06M000000",  # Alternative format
        "JNKCV11E06M123456"   # Another test
    ]
    
    for vin in test_vins:
        print(f"\n🔍 Testing VIN: {vin}")
        
        # Try VIN lookup endpoint
        try:
            url = f"{BASE_URL}/vehicles/vin/{vin}/lang-id/4"
            response = requests.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ VIN FOUND: {json.dumps(data, indent=2)[:500]}...")
                
                # Extract vehicle ID if available
                vehicle_id = data.get('vehicleId') or data.get('id')
                if vehicle_id:
                    print(f"   📋 Vehicle ID: {vehicle_id}")
                    
                    # Try to get OEMs for this vehicle
                    test_oems_for_vehicle(vehicle_id)
                    
            elif response.status_code == 404:
                print(f"   ❌ VIN NOT FOUND: {vin}")
            else:
                print(f"   ❌ API ERROR: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")

def test_oems_for_vehicle(vehicle_id):
    """Test getting OEMs for a specific vehicle ID"""
    print(f"\n   🔍 Getting OEMs for vehicle {vehicle_id}...")
    
    # Test both product groups
    product_groups = [
        (100260, "Drivaksler"),
        (100270, "Mellomaksler")
    ]
    
    for group_id, group_name in product_groups:
        try:
            url = f"{BASE_URL}/articles/list/lang-id/4/country-filter-id/62/vehicle-id/{vehicle_id}/product-group-id/{group_id}"
            response = requests.get(url, headers=HEADERS, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                print(f"      ✅ {group_name}: Found {len(articles)} articles")
                
                if articles:
                    # Extract OEMs from first few articles
                    oems_found = []
                    for article in articles[:3]:
                        oem_numbers = article.get('oemNumbers', [])
                        for oem in oem_numbers[:5]:
                            oem_number = oem.get('oemNumber', '')
                            if oem_number:
                                oems_found.append(oem_number)
                    
                    print(f"      📋 Sample OEMs: {oems_found[:10]}")
                    
                    # Check for customer OEMs
                    customer_oems = ['370008H310', '37000-8H310', '370008H510', '370008H800']
                    for customer_oem in customer_oems:
                        if customer_oem in oems_found:
                            print(f"      🎯 FOUND CUSTOMER OEM: {customer_oem}")
            else:
                print(f"      ❌ {group_name}: Failed {response.status_code}")
                
        except Exception as e:
            print(f"      ❌ {group_name}: Exception {e}")

def test_direct_vin_endpoints():
    """Test different VIN endpoint formats"""
    print(f"\n🔍 TESTING DIFFERENT VIN ENDPOINT FORMATS")
    print("=" * 50)
    
    test_vin = "JNKCV11E06M000000"
    
    # Try different VIN endpoint formats
    endpoints = [
        f"/vehicles/vin/{test_vin}/lang-id/4",
        f"/vehicles/vin/{test_vin}",
        f"/vehicle/vin/{test_vin}/lang-id/4",
        f"/vin/{test_vin}/lang-id/4",
        f"/vin-lookup/{test_vin}"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 Testing: {BASE_URL}{endpoint}")
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, timeout=30)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS: {str(data)[:200]}...")
            elif response.status_code != 404:
                print(f"   ⚠️ Response: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

def test_real_zt41818_vin():
    """Test with real ZT41818 VIN if we can extract it"""
    print(f"\n🚗 TESTING REAL ZT41818 VIN EXTRACTION")
    print("=" * 50)
    
    # We need to get the real VIN from SVV for ZT41818
    # For now, let's test the VIN extraction logic
    print("📋 Need to extract real VIN from SVV for ZT41818")
    print("📋 VIN should be in kjoretoydataListe[0].kjoretoyId.understellsnummer")
    print("📋 Once we have real VIN, we can test TecDoc VIN lookup")

if __name__ == "__main__":
    test_direct_vin_endpoints()
    test_vin_lookup()
    test_real_zt41818_vin()
