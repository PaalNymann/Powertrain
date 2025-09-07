#!/usr/bin/env python3
"""
Vehicle-Based OEM Lookup Strategy
Use TecDoc vehicle endpoints to find OEMs for specific Nissan X-trail
"""

import requests
import json
import time

def vehicle_based_oem_lookup():
    """Try vehicle-based approach to find OEMs for Nissan X-trail"""
    
    rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    base_url = "https://tecdoc-catalog.p.rapidapi.com"
    headers = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': rapidapi_key
    }
    
    print("🚗 VEHICLE-BASED OEM LOOKUP FOR NISSAN X-TRAIL")
    print("=" * 60)
    
    # Vehicle data from VIN decoder
    make = "Nissan"
    model = "X-trail"
    year = "2001"
    
    print(f"Vehicle: {make} {model} {year}")
    
    # Strategy 1: Try to find manufacturer ID first
    print(f"\n🔍 STEP 1: Finding Nissan manufacturer ID")
    
    try:
        # Try manufacturers endpoint
        manufacturers_endpoints = [
            "/manufacturers",
            "/manufacturers/search",
            "/brands"
        ]
        
        nissan_id = None
        
        for endpoint in manufacturers_endpoints:
            try:
                url = f"{base_url}{endpoint}"
                print(f"   Trying: {endpoint}")
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"   ✅ Success: {len(data) if isinstance(data, list) else 'dict'} results")
                    
                    # Look for Nissan in the data
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                name = str(item.get('name', '')).lower()
                                manufacturer = str(item.get('manufacturer', '')).lower()
                                brand = str(item.get('brand', '')).lower()
                                
                                if 'nissan' in name or 'nissan' in manufacturer or 'nissan' in brand:
                                    nissan_id = item.get('id') or item.get('manufacturerId') or item.get('brandId')
                                    print(f"   🎯 Found Nissan: {item}")
                                    break
                    
                    if nissan_id:
                        break
                        
                else:
                    print(f"   ❌ Failed: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        if nissan_id:
            print(f"   ✅ Nissan ID found: {nissan_id}")
        else:
            print(f"   ⚠️ Nissan ID not found, trying alternative approaches")
    
    except Exception as e:
        print(f"   ❌ Manufacturer lookup error: {e}")
    
    # Strategy 2: Try vehicle search endpoints
    print(f"\n🔍 STEP 2: Searching for Nissan X-trail vehicles")
    
    vehicle_search_endpoints = [
        "/vehicles/search",
        "/vehicle/search", 
        "/cars/search",
        "/models/search"
    ]
    
    vehicle_results = []
    
    for endpoint in vehicle_search_endpoints:
        try:
            # Try different search terms
            search_terms = [
                "Nissan X-trail",
                "Nissan X-Trail", 
                "NISSAN X-TRAIL"
            ]
            
            for term in search_terms:
                try:
                    url = f"{base_url}{endpoint}/{term}"
                    print(f"   Trying: {endpoint} with '{term}'")
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data:  # Non-empty response
                            print(f"   ✅ Success: {len(data) if isinstance(data, list) else 'dict'} results")
                            vehicle_results.extend(data if isinstance(data, list) else [data])
                            break
                    else:
                        print(f"   ❌ {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    
        except Exception as e:
            continue
    
    # Strategy 3: Try product group specific searches
    print(f"\n🔍 STEP 3: Searching by product groups (Drivaksel/Mellomaksel)")
    
    # Product group IDs from previous work
    product_groups = [
        ("100260", "Drivaksel"),
        ("100270", "Mellomaksel")
    ]
    
    all_oems = []
    
    for group_id, group_name in product_groups:
        print(f"\n   🔍 Searching {group_name} (ID: {group_id})")
        
        # Try different product group endpoints
        group_endpoints = [
            f"/articles/product-group/{group_id}",
            f"/products/group/{group_id}",
            f"/parts/group/{group_id}",
            f"/articles/group/{group_id}"
        ]
        
        for endpoint in group_endpoints:
            try:
                url = f"{base_url}{endpoint}"
                print(f"      Trying: {endpoint}")
                
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        print(f"      ✅ Success: {len(data) if isinstance(data, list) else 'dict'} results")
                        
                        # Look for OEMs in the response
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    # Check for OEM fields
                                    for oem_field in ['oemNumbers', 'oems', 'oemNumber', 'partNumbers']:
                                        if oem_field in item:
                                            oem_data = item[oem_field]
                                            if isinstance(oem_data, list):
                                                for oem in oem_data:
                                                    if isinstance(oem, dict):
                                                        oem_num = oem.get('oemNumber') or oem.get('number')
                                                        if oem_num:
                                                            all_oems.append(oem_num)
                                                    elif isinstance(oem, str):
                                                        all_oems.append(oem)
                        
                        if all_oems:
                            print(f"      🎯 Found {len(all_oems)} OEMs so far")
                            break
                            
                else:
                    print(f"      ❌ {response.status_code}")
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
    
    # Strategy 4: Try direct OEM search with known customer OEMs
    print(f"\n🔍 STEP 4: Reverse lookup with customer-verified OEMs")
    
    customer_oems = ['370008H310', '370008H510', '370008H800', '37000-8H310', '37000-8H510', '37000-8H800']
    
    for customer_oem in customer_oems:
        try:
            # Try to find articles that have this OEM
            search_endpoints = [
                f"/articles-oem/search/lang-id/4/article-oem-search-no/{customer_oem}",
                f"/oem/{customer_oem}",
                f"/articles/oem/{customer_oem}"
            ]
            
            for endpoint in search_endpoints:
                try:
                    url = f"{base_url}{endpoint}"
                    print(f"   Trying reverse lookup: {customer_oem} via {endpoint}")
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            print(f"   ✅ Found articles for {customer_oem}: {len(data) if isinstance(data, list) else 'dict'}")
                            print(f"      Sample: {str(data)[:200]}...")
                            
                            # This confirms the OEM exists in TecDoc
                            if customer_oem not in all_oems:
                                all_oems.append(customer_oem)
                            break
                    else:
                        print(f"   ❌ {response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    
        except Exception as e:
            continue
    
    # Summary
    print(f"\n🎯 FINAL SUMMARY:")
    print("=" * 60)
    
    unique_oems = list(set(all_oems))
    
    if unique_oems:
        print(f"✅ Total unique OEMs found: {len(unique_oems)}")
        print(f"All OEMs: {unique_oems}")
        
        # Check for customer matches
        customer_matches = [oem for oem in unique_oems if any(
            oem.replace('-', '').replace(' ', '').upper() == 
            customer.replace('-', '').replace(' ', '').upper() 
            for customer in customer_oems
        )]
        
        if customer_matches:
            print(f"🎉 CUSTOMER-VERIFIED OEMs FOUND: {customer_matches}")
        else:
            print(f"⚠️ No customer-verified OEMs found")
            print(f"Expected: {customer_oems}")
        
        return unique_oems
    else:
        print(f"❌ No OEMs found through any strategy")
        print(f"This suggests TecDoc may not have comprehensive OEM data for Nissan X-trail 2001")
        print(f"or the endpoints/approach needs adjustment")
        return []

if __name__ == "__main__":
    vehicle_based_oem_lookup()
