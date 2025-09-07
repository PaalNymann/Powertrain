#!/usr/bin/env python3
"""
Complete VIN to OEM Lookup
Combines correct VIN decoder v3 with existing OEM search endpoints
"""

import requests
import json
import time
from typing import List, Dict, Tuple, Optional

class CompleteVinToOemLookup:
    """Complete VIN → Vehicle Info → OEMs lookup using correct endpoints"""
    
    def __init__(self):
        self.rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
        self.base_url = "https://tecdoc-catalog.p.rapidapi.com"
        self.headers = {
            'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
            'x-rapidapi-key': self.rapidapi_key
        }
        self.lang_id = 4  # English
    
    def decode_vin_v3(self, vin: str) -> Optional[Dict]:
        """
        Step 1: Decode VIN using correct v3 decoder endpoint
        Returns vehicle info (make, model, year, etc.)
        """
        print(f"🔍 STEP 1: Decoding VIN v3: {vin}")
        
        try:
            url = f"{self.base_url}/vin/decoder-v3/{vin}"
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ VIN decoded successfully")
                
                # Parse the correct response structure (list of dicts with 'information' keys)
                vehicle_info = {}
                
                if isinstance(data, list):
                    for section in data:
                        if isinstance(section, dict) and 'information' in section:
                            info = section['information']
                            if isinstance(info, dict):
                                vehicle_info.update(info)
                
                # Extract key vehicle info from parsed data
                make = (vehicle_info.get('Make') or 
                       vehicle_info.get('Manufacturer') or 
                       vehicle_info.get('make') or 
                       vehicle_info.get('manufacturer'))
                
                model = (vehicle_info.get('Model') or 
                        vehicle_info.get('model') or 
                        vehicle_info.get('modelName'))
                
                year = (vehicle_info.get('Model year') or 
                       vehicle_info.get('year') or 
                       vehicle_info.get('modelYear') or 
                       vehicle_info.get('yearFrom'))
                
                print(f"   Make: {make}")
                print(f"   Model: {model}")
                print(f"   Year: {year}")
                
                # Return flattened vehicle info for easier access
                return {
                    'make': make,
                    'model': model,
                    'year': year,
                    'raw_data': data,
                    'parsed_info': vehicle_info
                }
                
            else:
                print(f"   ❌ VIN decode failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ❌ VIN decode error: {e}")
            return None
    
    def search_oems_by_vehicle_data(self, make: str, model: str, year: str = None) -> List[str]:
        """
        Step 2: Search for OEMs using vehicle data and existing OEM endpoints
        Uses the working OEM search endpoints I already have
        """
        print(f"🔍 STEP 2: Searching OEMs for {make} {model} {year}")
        
        all_oems = []
        
        # Strategy 1: Use existing articles-oem search endpoint
        # This is the endpoint that was working before
        try:
            # Try different OEM search patterns
            search_terms = [
                f"{make} {model}",
                f"{make}",
                model
            ]
            
            for term in search_terms:
                print(f"   Trying OEM search for: {term}")
                
                url = f"{self.base_url}/articles-oem/search/lang-id/{self.lang_id}/article-oem-search-no/{term}"
                response = requests.get(url, headers=self.headers, timeout=10)
                
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
                            print(f"   ✅ Found {len(all_oems)} OEMs for '{term}'")
                            break  # Stop on first successful search
                            
        except Exception as e:
            print(f"   ⚠️ OEM search error: {e}")
        
        return all_oems
    
    def complete_vin_to_oem_lookup(self, vin: str) -> Tuple[bool, List[str], Dict]:
        """
        Complete VIN → Vehicle Info → OEMs lookup
        """
        print(f"🚀 COMPLETE VIN TO OEM LOOKUP: {vin}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Decode VIN to get vehicle info
        vehicle_data = self.decode_vin_v3(vin)
        if not vehicle_data:
            elapsed = time.time() - start_time
            print(f"\n❌ FAILURE: VIN decode failed in {elapsed:.2f}s")
            return False, [], {}
        
        # Step 2: Extract vehicle info
        make = None
        model = None
        year = None
        
        if isinstance(vehicle_data, dict):
            make = vehicle_data.get('make') or vehicle_data.get('manufacturer') or vehicle_data.get('brand')
            model = vehicle_data.get('model') or vehicle_data.get('modelName')
            year = str(vehicle_data.get('year') or vehicle_data.get('modelYear') or vehicle_data.get('yearFrom') or '')
        
        if not make or not model:
            elapsed = time.time() - start_time
            print(f"\n❌ FAILURE: Could not extract make/model from VIN data in {elapsed:.2f}s")
            return False, [], vehicle_data
        
        # Step 3: Search for OEMs using vehicle data
        oems = self.search_oems_by_vehicle_data(make, model, year)
        
        elapsed = time.time() - start_time
        
        if oems:
            print(f"\n🎉 SUCCESS: {len(oems)} OEMs found in {elapsed:.2f}s")
            print(f"   Vehicle: {make} {model} {year}")
            print(f"   Sample OEMs: {oems[:10]}")
            return True, oems, vehicle_data
        else:
            print(f"\n❌ FAILURE: No OEMs found for {make} {model} {year} in {elapsed:.2f}s")
            return False, [], vehicle_data

def test_zt41818_complete_lookup():
    """Test complete VIN to OEM lookup for ZT41818"""
    print("🎯 TESTING ZT41818 COMPLETE VIN TO OEM LOOKUP")
    print("Using correct VIN decoder v3 + existing OEM endpoints")
    print("=" * 70)
    
    vin = "JN1TENT30U0217281"  # ZT41818 VIN from SVV
    
    lookup = CompleteVinToOemLookup()
    success, oems, vehicle_data = lookup.complete_vin_to_oem_lookup(vin)
    
    if success:
        print(f"\n✅ ZT41818 COMPLETE LOOKUP SUCCESS!")
        print(f"   VIN: {vin}")
        print(f"   OEMs found: {len(oems)}")
        print(f"   All OEMs: {oems}")
        
        # Check for customer-verified OEMs
        customer_oems = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
        found_customer_oems = [oem for oem in customer_oems if oem in oems]
        
        if found_customer_oems:
            print(f"   🎉 CUSTOMER-VERIFIED OEMs FOUND: {found_customer_oems}")
        else:
            print(f"   ⚠️ Customer-verified OEMs not found")
            print(f"   Expected: {customer_oems}")
            
            # Check for partial matches (different formats)
            partial_matches = []
            for customer_oem in customer_oems:
                for found_oem in oems:
                    if customer_oem.replace('-', '').replace(' ', '').upper() in found_oem.replace('-', '').replace(' ', '').upper():
                        partial_matches.append((customer_oem, found_oem))
            
            if partial_matches:
                print(f"   🔍 PARTIAL MATCHES FOUND: {partial_matches}")
        
        return oems, vehicle_data
    else:
        print(f"\n❌ ZT41818 COMPLETE LOOKUP FAILED")
        print(f"   VIN: {vin}")
        return [], vehicle_data

if __name__ == "__main__":
    test_zt41818_complete_lookup()
