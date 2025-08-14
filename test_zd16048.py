#!/usr/bin/env python3
"""
Simple test script for ZD16048 workflow without Flask dependencies
"""

import requests
import json

def test_svv_lookup(license_plate):
    """Test SVV lookup for license plate"""
    print(f"🔍 Testing SVV lookup for {license_plate}...")
    
    url = f"https://akfell-datautlevering.atlas.vegvesen.no/enkeltoppslag/kjoretoydata?kjennemerke={license_plate}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if 'kjoretoydataListe' in data and data['kjoretoydataListe']:
                kjoretoy = data['kjoretoydataListe'][0]
                tekniske_data = kjoretoy.get('tekniskeData', {})
                generelt = tekniske_data.get('generelt', {})
                
                # Extract vehicle info
                merke = generelt.get('merke', [])
                if merke:
                    brand = merke[0].get('merke', 'Unknown')
                else:
                    brand = 'Unknown'
                    
                model = generelt.get('handelsbetegnelse', ['Unknown'])[0] if generelt.get('handelsbetegnelse') else 'Unknown'
                
                reg_dato = kjoretoy.get('forstegangsregistrering', {}).get('registrertForstegangNorgeDato', '')
                year = reg_dato.split('-')[0] if reg_dato else 'Unknown'
                
                vehicle_info = {
                    'make': brand.upper(),
                    'model': model.upper(),
                    'year': year
                }
                
                print(f"✅ Vehicle: {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}")
                return vehicle_info
            else:
                print("❌ No vehicle data found")
                return None
                
        else:
            print(f"❌ SVV API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ SVV lookup failed: {e}")
        return None

def test_rapidapi_tecdoc_oem_search(oem_number):
    """Test RapidAPI TecDoc OEM search"""
    print(f"🔍 Testing RapidAPI TecDoc for OEM: {oem_number}")
    
    url = f"https://tecdoc-catalog.p.rapidapi.com/articles-oem/search/lang-id/4/article-oem-search-no/{oem_number}"
    headers = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': '48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                print(f"✅ Found {len(data)} articles for OEM {oem_number}")
                
                # Show first article
                first = data[0]
                print(f"  Article ID: {first.get('articleId', 'N/A')}")
                print(f"  Product: {first.get('articleProductName', 'N/A')}")
                print(f"  Manufacturer: {first.get('manufacturerName', 'N/A')}")
                
                return data
            else:
                print(f"❌ No articles found for OEM {oem_number}")
                return []
                
        else:
            print(f"❌ RapidAPI TecDoc error: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ RapidAPI TecDoc failed: {e}")
        return []

def main():
    """Test complete workflow for ZD16048"""
    print("🚀 Testing complete workflow for ZD16048")
    print("=" * 50)
    
    # Step 1: SVV lookup
    vehicle_info = test_svv_lookup("ZD16048")
    
    if not vehicle_info:
        print("❌ Cannot proceed without vehicle info")
        return
    
    # Step 2: Test with known working OEM numbers
    print(f"\n🔍 Step 2: Testing RapidAPI TecDoc with known OEMs...")
    test_oems = ['30735120', '8252034', '30735349']  # Known Rackbeat OEMs
    
    compatible_oems = []
    for oem in test_oems:
        articles = test_rapidapi_tecdoc_oem_search(oem)
        if articles:
            compatible_oems.append(oem)
    
    print(f"\n✅ Summary for {vehicle_info['make']} {vehicle_info['model']} {vehicle_info['year']}:")
    print(f"   Compatible OEMs found: {len(compatible_oems)}")
    print(f"   OEMs: {compatible_oems}")
    
    if compatible_oems:
        print("🎉 Workflow successful! Found compatible parts.")
    else:
        print("❌ No compatible parts found.")

if __name__ == "__main__":
    main()
