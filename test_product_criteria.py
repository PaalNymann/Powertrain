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

def check_product_criteria():
    """Check if the product with field values meets our criteria"""
    sku = "MA01032-Kryssvariant"
    
    try:
        print(f"🔍 Checking product criteria for: {sku}")
        response = requests.get(
            f"{RACKBEAT_API}/{sku}",
            headers=headers,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 206]:
            data = response.json()
            product = data.get('product', data)
            
            available_quantity = product.get('available_quantity', 0)
            sales_price = product.get('sales_price', 0)
            name = product.get('name', 'N/A')
            
            print(f"Product: {name}")
            print(f"Available quantity: {available_quantity}")
            print(f"Sales price: {sales_price}")
            print(f"Meets criteria (available_quantity > 0 and sales_price > 0): {available_quantity > 0 and sales_price > 0}")
            
            if available_quantity > 0 and sales_price > 0:
                print("✅ This product would be synced!")
            else:
                print("❌ This product would NOT be synced")
                
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_product_criteria() 