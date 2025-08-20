#!/usr/bin/env python3
"""
Debug vehicle data lookup and cache compatibility
"""

import requests
import json

def debug_svv_lookup():
    """Debug SVV vehicle lookup for test license plates"""
    
    print("🔍 DEBUGGING SVV VEHICLE LOOKUP")
    print("=" * 50)
    
    test_plates = ["YZ99554", "KH66644", "RJ62438"]
    
    for plate in test_plates:
        print(f"\n🚗 Testing {plate}:")
        print("-" * 30)
        
        try:
            # SVV API call
            svv_url = f"https://www.vegvesen.no/ws/no/vegvesen/kjoretoy/felles/datautlevering/enkeltoppslag/kjoretoydata?kjennemerke={plate}"
            
            response = requests.get(svv_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'kjoretoydataListe' in data and data['kjoretoydataListe']:
                    vehicle_data = data['kjoretoydataListe'][0]
                    
                    # Extract vehicle info
                    make = vehicle_data.get('tekniskGodkjenning', {}).get('tekniskeData', {}).get('generelt', {}).get('merke', {}).get('merkenavn', 'Unknown')
                    
                    model_info = vehicle_data.get('tekniskGodkjenning', {}).get('tekniskeData', {}).get('generelt', {}).get('handelsbetegnelse', [])
                    model = model_info[0] if model_info else 'Unknown'
                    
                    year = vehicle_data.get('forstegangsregistrering', {}).get('registrertForstegangNorgeDato', '')[:4] if vehicle_data.get('forstegangsregistrering', {}).get('registrertForstegangNorgeDato') else 'Unknown'
                    
                    print(f"✅ SVV Data:")
                    print(f"   Make: {make}")
                    print(f"   Model: {model}")
                    print(f"   Year: {year}")
                    
                    # Check what we expect vs what we get
                    expected = {
                        "YZ99554": ("MERCEDES-BENZ", "GLK", "2010"),
                        "KH66644": ("VOLKSWAGEN", "TIGUAN", "2009"), 
                        "RJ62438": ("VOLVO", "V70", "2012")
                    }
                    
                    if plate in expected:
                        exp_make, exp_model, exp_year = expected[plate]
                        print(f"🎯 Expected: {exp_make} {exp_model} {exp_year}")
                        
                        if make.upper() != exp_make or exp_model.upper() not in model.upper():
                            print(f"⚠️  MISMATCH DETECTED!")
                        else:
                            print(f"✅ Match confirmed")
                else:
                    print(f"❌ No vehicle data found")
            else:
                print(f"❌ SVV API error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def debug_cache_lookup():
    """Debug cache lookup for known vehicle models"""
    
    print(f"\n\n🔍 DEBUGGING CACHE LOOKUP")
    print("=" * 50)
    
    # Test with corrected vehicle data
    test_vehicles = [
        ("MERCEDES-BENZ", "GLK", "2010"),
        ("VOLKSWAGEN", "TIGUAN", "2009"),
        ("VOLVO", "V70", "2012")
    ]
    
    for make, model, year in test_vehicles:
        print(f"\n🚗 Testing cache for: {make} {model} {year}")
        print("-" * 40)
        
        # Simulate cache lookup query
        vehicle_key = f"{make} {model} {year}"
        print(f"🔍 Cache key: {vehicle_key}")
        
        # Different variations to try
        variations = [
            f"{make} {model} {year}",
            f"{make.upper()} {model.upper()} {year}",
            f"{make} {model}",  # Without year
            f"{model} {year}",  # Without make
        ]
        
        print(f"🔍 Variations to check:")
        for var in variations:
            print(f"   - {var}")

if __name__ == "__main__":
    debug_svv_lookup()
    debug_cache_lookup()
