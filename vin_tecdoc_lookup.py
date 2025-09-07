#!/usr/bin/env python3
"""
VIN-Based TecDoc Lookup Implementation
Direct VIN → TecDoc → OEMs → Products flow for robust vehicle compatibility
"""

import requests
import time
from typing import List, Dict, Tuple, Optional

class VinTecDocLookup:
    """VIN-based TecDoc lookup using RapidAPI"""
    
    def __init__(self):
        self.rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
        self.base_url = "https://tecdoc-catalog.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
            'x-rapidapi-key': self.rapidapi_key
        }
        self.lang_id = 4  # English
    
    def lookup_vehicle_by_vin(self, vin: str) -> Optional[Dict]:
        """
        Step 1: Look up vehicle information by VIN
        Returns vehicle data including manufacturer, model, year, etc.
        """
        print(f"🔍 STEP 1: Looking up vehicle by VIN: {vin}")
        
        # Try different VIN lookup endpoints
        endpoints = [
            f"/vehicles/vin/{vin}",
            f"/vehicles/search/vin/{vin}",
            f"/vehicle-data/vin/{vin}",
            f"/vin-decoder/{vin}"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"   Trying: {url}")
                
                response = requests.get(url, headers=self.headers, timeout=15)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data and isinstance(data, (dict, list)):
                        print(f"   ✅ SUCCESS: Vehicle data found via {endpoint}")
                        return data
                        
            except Exception as e:
                print(f"   ❌ Error with {endpoint}: {e}")
                continue
        
        print(f"   ❌ No vehicle data found for VIN {vin}")
        return None
    
    def get_oems_for_vehicle_id(self, vehicle_id: str) -> List[str]:
        """
        Step 2: Get all OEM numbers for a specific vehicle ID
        """
        print(f"🔍 STEP 2: Getting OEMs for vehicle ID: {vehicle_id}")
        
        all_oems = []
        
        # Product groups to search (Drivaksler + Mellomaksler)
        product_groups = [
            (100260, "Drivaksler"),   # CV joints/drive shafts
            (100270, "Mellomaksler")  # Intermediate shafts
        ]
        
        for group_id, group_name in product_groups:
            try:
                url = f"{self.base_url}/articles/search/vehicle-id/{vehicle_id}/product-group-id/{group_id}/lang-id/{self.lang_id}"
                print(f"   Searching {group_name} (ID: {group_id})")
                
                response = requests.get(url, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        group_oems = []
                        for article in data:
                            oem_numbers = article.get('oemNumbers', [])
                            for oem_obj in oem_numbers:
                                oem_number = oem_obj.get('oemNumber', '')
                                if oem_number and oem_number not in all_oems:
                                    all_oems.append(oem_number)
                                    group_oems.append(oem_number)
                        
                        print(f"   ✅ {group_name}: Found {len(group_oems)} OEMs")
                    else:
                        print(f"   ⚠️ {group_name}: Unexpected response format")
                else:
                    print(f"   ❌ {group_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error searching {group_name}: {e}")
                continue
        
        print(f"   ✅ TOTAL: Found {len(all_oems)} OEMs across all product groups")
        return all_oems
    
    def direct_vin_to_oems(self, vin: str) -> Tuple[bool, List[str]]:
        """
        Direct VIN → OEMs lookup (bypassing vehicle ID if needed)
        """
        print(f"🎯 DIRECT VIN → OEMs LOOKUP: {vin}")
        
        # Try direct VIN-based article search
        endpoints = [
            f"/articles/search/vin/{vin}/lang-id/{self.lang_id}",
            f"/articles/vin/{vin}",
            f"/parts/vin/{vin}"
        ]
        
        all_oems = []
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                print(f"   Trying direct VIN search: {endpoint}")
                
                response = requests.get(url, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and data:
                        for article in data:
                            oem_numbers = article.get('oemNumbers', [])
                            for oem_obj in oem_numbers:
                                oem_number = oem_obj.get('oemNumber', '')
                                if oem_number and oem_number not in all_oems:
                                    all_oems.append(oem_number)
                        
                        if all_oems:
                            print(f"   ✅ SUCCESS: Found {len(all_oems)} OEMs via direct VIN search")
                            return True, all_oems
                            
            except Exception as e:
                print(f"   ❌ Error with direct VIN search {endpoint}: {e}")
                continue
        
        return False, []
    
    def comprehensive_vin_lookup(self, vin: str) -> Tuple[bool, List[str]]:
        """
        Comprehensive VIN-based OEM lookup
        Tries multiple strategies to ensure we get OEMs for any VIN
        """
        print(f"🚀 COMPREHENSIVE VIN LOOKUP: {vin}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Strategy 1: Direct VIN → OEMs
        print(f"\n📋 STRATEGY 1: Direct VIN → OEMs")
        success, oems = self.direct_vin_to_oems(vin)
        if success and oems:
            elapsed = time.time() - start_time
            print(f"\n🎉 SUCCESS (Strategy 1): {len(oems)} OEMs in {elapsed:.2f}s")
            return True, oems
        
        # Strategy 2: VIN → Vehicle ID → OEMs
        print(f"\n📋 STRATEGY 2: VIN → Vehicle ID → OEMs")
        vehicle_data = self.lookup_vehicle_by_vin(vin)
        if vehicle_data:
            # Extract vehicle ID from response (format may vary)
            vehicle_id = None
            if isinstance(vehicle_data, dict):
                vehicle_id = vehicle_data.get('vehicleId') or vehicle_data.get('id') or vehicle_data.get('vehicle_id')
            elif isinstance(vehicle_data, list) and vehicle_data:
                vehicle_id = vehicle_data[0].get('vehicleId') or vehicle_data[0].get('id')
            
            if vehicle_id:
                print(f"   Vehicle ID found: {vehicle_id}")
                oems = self.get_oems_for_vehicle_id(str(vehicle_id))
                if oems:
                    elapsed = time.time() - start_time
                    print(f"\n🎉 SUCCESS (Strategy 2): {len(oems)} OEMs in {elapsed:.2f}s")
                    return True, oems
        
        elapsed = time.time() - start_time
        print(f"\n❌ FAILURE: No OEMs found for VIN {vin} in {elapsed:.2f}s")
        return False, []

def test_zt41818_vin_lookup():
    """Test VIN lookup specifically for ZT41818"""
    print("🎯 TESTING ZT41818 VIN LOOKUP")
    print("=" * 50)
    
    vin = "JN1TENT30U0217281"  # ZT41818 VIN from SVV
    
    lookup = VinTecDocLookup()
    success, oems = lookup.comprehensive_vin_lookup(vin)
    
    if success:
        print(f"\n✅ ZT41818 VIN LOOKUP SUCCESS!")
        print(f"   VIN: {vin}")
        print(f"   OEMs found: {len(oems)}")
        print(f"   Sample OEMs: {oems[:10]}")
        
        # Check for customer-verified OEMs
        customer_oems = ['370008H310', '370008H510', '370008H800']
        found_customer_oems = [oem for oem in customer_oems if oem in oems]
        
        if found_customer_oems:
            print(f"   🎉 CUSTOMER-VERIFIED OEMs FOUND: {found_customer_oems}")
        else:
            print(f"   ⚠️ Customer-verified OEMs not found in TecDoc response")
            print(f"   Expected: {customer_oems}")
        
        return oems
    else:
        print(f"\n❌ ZT41818 VIN LOOKUP FAILED")
        print(f"   VIN: {vin}")
        print(f"   No OEMs found via TecDoc RapidAPI")
        return []

if __name__ == "__main__":
    test_zt41818_vin_lookup()
