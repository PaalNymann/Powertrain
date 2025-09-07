#!/usr/bin/env python3
"""
Debug VIN Decoder v3 Response Format
Find out exactly what the v3 decoder returns
"""

import requests
import json

def debug_vin_decoder_v3():
    """Debug what VIN decoder v3 actually returns"""
    
    rapidapi_key = "48a6ede874mshe38f052cb6a6109p12916fjsn0d0c0912c5ed"
    base_url = "https://tecdoc-catalog.p.rapidapi.com"
    headers = {
        'x-rapidapi-host': 'tecdoc-catalog.p.rapidapi.com',
        'x-rapidapi-key': rapidapi_key
    }
    
    vin = "JN1TENT30U0217281"  # ZT41818 VIN
    
    print(f"🔍 DEBUGGING VIN DECODER V3 RESPONSE")
    print(f"VIN: {vin}")
    print("=" * 60)
    
    try:
        url = f"{base_url}/vin/decoder-v3/{vin}"
        print(f"URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📋 FULL RESPONSE:")
            print(f"Type: {type(data)}")
            print(f"Content: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            print(f"\n🔍 ANALYSIS:")
            if isinstance(data, dict):
                print(f"Dictionary with {len(data)} keys:")
                for key, value in data.items():
                    print(f"  {key}: {value} (type: {type(value).__name__})")
                    
            elif isinstance(data, list):
                print(f"List with {len(data)} items:")
                for i, item in enumerate(data):
                    print(f"  [{i}]: {item} (type: {type(item).__name__})")
                    if isinstance(item, dict):
                        for key, value in item.items():
                            print(f"    {key}: {value}")
            
            else:
                print(f"Unexpected type: {type(data)}")
                print(f"Value: {data}")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_vin_decoder_v3()
