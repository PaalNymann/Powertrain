#!/usr/bin/env python3
"""
Robust Vehicle Data to TecDoc Lookup
Uses SVV vehicle data (make/model/year) to find TecDoc vehicle ID and get OEMs
"""

import requests
import time
from typing import List, Dict, Tuple, Optional

class RobustVehicleLookup:
    """Robust vehicle lookup using make/model/year data"""
    
    def __init__(self):
        self.rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
        self.base_url = "https://tecdoc-catalog.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
            'x-rapidapi-key': self.rapidapi_key
        }
        self.lang_id = 4  # English
    
    def find_manufacturer_id(self, make: str) -> Optional[int]:
        """Find TecDoc manufacturer ID for a given make"""
        print(f"🔍 Finding manufacturer ID for: {make}")
        
        try:
            url = f"{self.base_url}/manufacturers/lang-id/{self.lang_id}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                manufacturers = response.json()
                if isinstance(manufacturers, list):
                    make_upper = make.upper()
                    
                    # Try exact match first
                    for mfr in manufacturers:
                        mfr_name = mfr.get('manufacturerName', '').upper()
                        if mfr_name == make_upper:
                            mfr_id = mfr.get('manufacturerId')
                            print(f"   ✅ Exact match: {mfr_name} (ID: {mfr_id})")
                            return mfr_id
                    
                    # Try partial match
                    for mfr in manufacturers:
                        mfr_name = mfr.get('manufacturerName', '').upper()
                        if make_upper in mfr_name or mfr_name in make_upper:
                            mfr_id = mfr.get('manufacturerId')
                            print(f"   ✅ Partial match: {mfr_name} (ID: {mfr_id})")
                            return mfr_id
                            
        except Exception as e:
            print(f"   ❌ Error finding manufacturer: {e}")
        
        print(f"   ❌ No manufacturer found for: {make}")
        return None
    
    def find_vehicle_models(self, manufacturer_id: int, model: str, year: str) -> List[Dict]:
        """Find vehicle models for manufacturer"""
        print(f"🔍 Finding models for manufacturer ID {manufacturer_id}, model: {model}, year: {year}")
        
        try:
            url = f"{self.base_url}/vehicles/manufacturer-id/{manufacturer_id}/lang-id/{self.lang_id}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                vehicles = response.json()
                if isinstance(vehicles, list):
                    matching_vehicles = []
                    model_upper = model.upper()
                    
                    for vehicle in vehicles:
                        vehicle_name = vehicle.get('modelName', '').upper()
                        vehicle_year = str(vehicle.get('yearFrom', ''))
                        
                        # Check model match
                        model_match = (
                            model_upper in vehicle_name or 
                            vehicle_name in model_upper or
                            any(word in vehicle_name for word in model_upper.split())
                        )
                        
                        # Check year match (within reasonable range)
                        year_match = False
                        if vehicle_year and year:
                            try:
                                year_from = int(vehicle_year)
                                target_year = int(year)
                                year_match = abs(year_from - target_year) <= 2  # ±2 years tolerance
                            except ValueError:
                                pass
                        
                        if model_match and (year_match or not year):
                            matching_vehicles.append(vehicle)
                            print(f"   ✅ Match: {vehicle_name} ({vehicle_year}) - ID: {vehicle.get('vehicleId')}")
                    
                    return matching_vehicles
                    
        except Exception as e:
            print(f"   ❌ Error finding models: {e}")
        
        return []
    
    def get_oems_for_vehicle_id(self, vehicle_id: str) -> List[str]:
        """Get all OEM numbers for a specific vehicle ID"""
        print(f"🔍 Getting OEMs for vehicle ID: {vehicle_id}")
        
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
                        if group_oems:
                            print(f"      Sample: {group_oems[:3]}")
                    else:
                        print(f"   ⚠️ {group_name}: Unexpected response format")
                else:
                    print(f"   ❌ {group_name}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error searching {group_name}: {e}")
                continue
        
        print(f"   ✅ TOTAL: Found {len(all_oems)} OEMs across all product groups")
        return all_oems
    
    def comprehensive_vehicle_lookup(self, make: str, model: str, year: str) -> Tuple[bool, List[str]]:
        """
        Comprehensive vehicle-based OEM lookup
        make/model/year → manufacturer ID → vehicle models → vehicle ID → OEMs
        """
        print(f"🚀 COMPREHENSIVE VEHICLE LOOKUP: {make} {model} {year}")
        print("=" * 70)
        
        start_time = time.time()
        
        # Step 1: Find manufacturer ID
        manufacturer_id = self.find_manufacturer_id(make)
        if not manufacturer_id:
            elapsed = time.time() - start_time
            print(f"\n❌ FAILURE: No manufacturer found for {make} in {elapsed:.2f}s")
            return False, []
        
        # Step 2: Find matching vehicle models
        vehicles = self.find_vehicle_models(manufacturer_id, model, year)
        if not vehicles:
            elapsed = time.time() - start_time
            print(f"\n❌ FAILURE: No vehicles found for {make} {model} {year} in {elapsed:.2f}s")
            return False, []
        
        # Step 3: Get OEMs for all matching vehicles
        all_oems = []
        for vehicle in vehicles:
            vehicle_id = vehicle.get('vehicleId')
            if vehicle_id:
                vehicle_oems = self.get_oems_for_vehicle_id(str(vehicle_id))
                for oem in vehicle_oems:
                    if oem not in all_oems:
                        all_oems.append(oem)
        
        elapsed = time.time() - start_time
        
        if all_oems:
            print(f"\n🎉 SUCCESS: {len(all_oems)} OEMs found in {elapsed:.2f}s")
            print(f"   Vehicles checked: {len(vehicles)}")
            print(f"   Sample OEMs: {all_oems[:10]}")
            return True, all_oems
        else:
            print(f"\n❌ FAILURE: No OEMs found for {make} {model} {year} in {elapsed:.2f}s")
            return False, []

def test_zt41818_robust_lookup():
    """Test robust lookup specifically for ZT41818"""
    print("🎯 TESTING ZT41818 ROBUST VEHICLE LOOKUP")
    print("=" * 60)
    
    # ZT41818 vehicle data from SVV
    make = "NISSAN"
    model = "X-TRAIL" 
    year = "2006"
    
    lookup = RobustVehicleLookup()
    success, oems = lookup.comprehensive_vehicle_lookup(make, model, year)
    
    if success:
        print(f"\n✅ ZT41818 ROBUST LOOKUP SUCCESS!")
        print(f"   Vehicle: {make} {model} {year}")
        print(f"   OEMs found: {len(oems)}")
        print(f"   All OEMs: {oems}")
        
        # Check for customer-verified OEMs
        customer_oems = ['370008H310', '370008H510', '370008H800']
        found_customer_oems = [oem for oem in customer_oems if oem in oems]
        
        if found_customer_oems:
            print(f"   🎉 CUSTOMER-VERIFIED OEMs FOUND: {found_customer_oems}")
        else:
            print(f"   ⚠️ Customer-verified OEMs not in TecDoc response")
            print(f"   Expected: {customer_oems}")
            print(f"   Found: {oems[:10]} (first 10)")
        
        return oems
    else:
        print(f"\n❌ ZT41818 ROBUST LOOKUP FAILED")
        print(f"   Vehicle: {make} {model} {year}")
        print(f"   No OEMs found via TecDoc RapidAPI")
        return []

if __name__ == "__main__":
    test_zt41818_robust_lookup()
