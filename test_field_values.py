#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
RACKBEAT_API = "https://app.rackbeat.com/api/products"

headers = {
    "Authorization": f"Bearer {RACKBEAT_API_KEY}",
    "Content-Type": "application/json"
}

def test_field_values():
    """Test field values for the product we know has them"""
    sku = "MA01032-Kryssvariant"
    
    try:
        print(f"🔍 Testing field values for: {sku}")
        response = requests.get(
            f"{RACKBEAT_API}/{sku}/fields",
            headers=headers,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 206]:
            data = response.json()
            field_values = data.get('field_values', [])
            
            print(f"Found {len(field_values)} field values:")
            for field_value in field_values:
                field_name = field_value.get('field', {}).get('name', 'N/A')
                value = field_value.get('value', 'N/A')
                print(f"  {field_name}: {value}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_field_values() 