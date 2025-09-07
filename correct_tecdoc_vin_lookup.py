#!/usr/bin/env python3
"""
Correct TecDoc VIN Decoder v3 Implementation
Using the right endpoints from TecDoc RapidAPI
"""

import requests
import json
import time
from typing import List, Dict, Tuple, Optional

class CorrectTecDocVinLookup:
    """Correct TecDoc VIN lookup using the right v3 decoder endpoint"""
    
    def __init__(self):
        self.rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
        self.base_url = "https://tecdoc-catalog.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
            'x-rapidapi-key': self.rapidapi_key
        }
    
    def decode_vin_v3(self, vin: str) -> Optional[Dict]:
        """
        Decode VIN using the correct v3 decoder endpoint
        """
        print(f"🔍 DECODING VIN v3: {vin}")
        
        try:
            url = f"{self.base_url}/vin/decoder-v3/{vin}"
            print(f"   URL: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS: VIN decoded successfully")
                print(f"   Response type: {type(data)}")
                
                if isinstance(data, dict):
                    # Show key fields
                    keys = list(data.keys())
                    print(f"   Keys: {keys}")
                    
                    # Extract important vehicle info
                    make = data.get('make') or data.get('manufacturer') or data.get('brand')
                    model = data.get('model') or data.get('modelName')
                    year = data.get('year') or data.get('modelYear') or data.get('yearFrom')
                    
                    print(f"   Make: {make}")
                    print(f"   Model: {model}")
                    print(f"   Year: {year}")
                    
                elif isinstance(data, list):
                    print(f"   Array with {len(data)} items")
                    if data:
                        print(f"   First item: {data[0]}")
                
                return data
                
            else:
                error_text = response.text[:200] if response.text else f"HTTP {response.status_code}"
                print(f"   ❌ FAILED: {response.status_code} - {error_text}")
                return None
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            return None
    
    def get_vehicle_oems_v3(self, vin: str) -> Tuple[bool, List[str], Dict]:
        """
        Get OEMs for vehicle using correct v3 decoder + additional endpoints
        """
        print(f"🚀 GETTING VEHICLE OEMS v3: {vin}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Decode VIN to get vehicle info
        vehicle_data = self.decode_vin_v3(vin)
        if not vehicle_data:
            elapsed = time.time() - start_time
            print(f"\n❌ FAILURE: VIN decode failed in {elapsed:.2f}s")
            return False, [], {}
        
        # Step 2: Try to find OEMs using vehicle data
        # This will depend on what the v3 decoder returns
        print(f"\n🔍 STEP 2: Looking for OEM endpoints using vehicle data")
        
        # Try different OEM lookup strategies based on vehicle data
        all_oems = []
        
        # Strategy 1: Look for direct OEM data in VIN response
        if isinstance(vehicle_data, dict):
            # Check if OEMs are directly in the response
            oems_direct = vehicle_data.get('oems') or vehicle_data.get('oemNumbers') or vehicle_data.get('partNumbers')
            if oems_direct:
                if isinstance(oems_direct, list):
                    all_oems.extend(oems_direct)
                    print(f"   ✅ Found {len(oems_direct)} OEMs directly in VIN response")
        
        # Strategy 2: Use vehicle ID if available
        vehicle_id = None
        if isinstance(vehicle_data, dict):
            vehicle_id = (vehicle_data.get('vehicleId') or 
                         vehicle_data.get('id') or 
                         vehicle_data.get('tecdocId') or
                         vehicle_data.get('vehicle_id'))
        
        if vehicle_id:
            print(f"   Vehicle ID found: {vehicle_id}")
            vehicle_oems = self.get_oems_by_vehicle_id(vehicle_id)
            all_oems.extend(vehicle_oems)
        
        # Strategy 3: Try other endpoints based on make/model/year
        if isinstance(vehicle_data, dict):
            make = vehicle_data.get('make') or vehicle_data.get('manufacturer')
            model = vehicle_data.get('model') or vehicle_data.get('modelName')
            year = vehicle_data.get('year') or vehicle_data.get('modelYear')
            
            if make and model:
                print(f"   Trying make/model lookup: {make} {model} {year}")
                make_model_oems = self.get_oems_by_make_model(make, model, year)
                all_oems.extend(make_model_oems)
        
        elapsed = time.time() - start_time
        
        # Remove duplicates
        unique_oems = list(dict.fromkeys(all_oems))  # Preserves order
        
        if unique_oems:
            print(f"\n🎉 SUCCESS: {len(unique_oems)} unique OEMs found in {elapsed:.2f}s")
            print(f"   Sample OEMs: {unique_oems[:10]}")
            return True, unique_oems, vehicle_data
        else:
            print(f"\n❌ FAILURE: No OEMs found in {elapsed:.2f}s")
            return False, [], vehicle_data
    
    def get_oems_by_vehicle_id(self, vehicle_id: str) -> List[str]:
        """Get OEMs using vehicle ID"""
        print(f"   🔍 Getting OEMs by vehicle ID: {vehicle_id}")
        
        oems = []
        
        # Try different vehicle ID endpoints
        endpoints = [
            f"/articles/vehicle/{vehicle_id}",
            f"/parts/vehicle/{vehicle_id}",
            f"/oems/vehicle/{vehicle_id}",
            f"/vehicle/{vehicle_id}/articles",
            f"/vehicle/{vehicle_id}/parts",
            f"/vehicle/{vehicle_id}/oems"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                item_oems = item.get('oems') or item.get('oemNumbers') or item.get('partNumbers')
                                if isinstance(item_oems, list):
                                    oems.extend(item_oems)
                    
                    if oems:
                        print(f"      ✅ Found {len(oems)} OEMs via {endpoint}")
                        break
                        
            except Exception as e:
                continue
        
        return oems
    
    def get_oems_by_make_model(self, make: str, model: str, year: str = None) -> List[str]:
        """Get OEMs using make/model/year"""
        print(f"   🔍 Getting OEMs by make/model: {make} {model} {year}")
        
        # This would require finding the right endpoints for make/model lookup
        # For now, return empty list - will implement based on API documentation
        return []

def test_zt41818_correct_vin_lookup():
    """Test correct VIN lookup for ZT41818"""
    print("🎯 TESTING ZT41818 WITH CORRECT TECDOC VIN DECODER V3")
    print("=" * 70)
    
    vin = "JN1TENT30U0217281"  # ZT41818 VIN from SVV
    
    lookup = CorrectTecDocVinLookup()
    success, oems, vehicle_data = lookup.get_vehicle_oems_v3(vin)
    
    if success:
        print(f"\n✅ ZT41818 CORRECT VIN LOOKUP SUCCESS!")
        print(f"   VIN: {vin}")
        print(f"   Vehicle data keys: {list(vehicle_data.keys()) if isinstance(vehicle_data, dict) else 'N/A'}")
        print(f"   OEMs found: {len(oems)}")
        print(f"   All OEMs: {oems}")
        
        # Check for customer-verified OEMs
        customer_oems = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
        found_customer_oems = [oem for oem in customer_oems if oem in oems]
        
        if found_customer_oems:
            print(f"   🎉 CUSTOMER-VERIFIED OEMs FOUND: {found_customer_oems}")
        else:
            print(f"   ⚠️ Customer-verified OEMs not found in TecDoc response")
            print(f"   Expected: {customer_oems}")
        
        return oems, vehicle_data
    else:
        print(f"\n❌ ZT41818 CORRECT VIN LOOKUP FAILED")
        print(f"   VIN: {vin}")
        print(f"   Vehicle data: {vehicle_data}")
        return [], vehicle_data

if __name__ == "__main__":
    test_zt41818_correct_vin_lookup()
