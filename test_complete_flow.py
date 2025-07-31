#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os

def test_complete_workflow():
    """Test the complete workflow: license plate → vehicle data → parts search → Shopify products"""
    
    print("=== COMPLETE WORKFLOW TEST ===")
    print("Testing: License Plate → Vehicle Data → Parts Search → Shopify Products")
    
    # Start the app service
    print("\n1. Starting app.py...")
    app_process = subprocess.Popen([sys.executable, 'app.py'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE)
    time.sleep(5)
    
    try:
        # Test 1: License plate lookup
        print("\n2. Testing license plate lookup...")
        response = requests.get("http://127.0.0.1:8000/api/statens_vegvesen?regnr=KH66644", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            vehicle_data = response.json()
            print("✅ Vehicle data retrieved successfully")
            
            # Extract vehicle info
            if 'kjoretoydataListe' in vehicle_data and vehicle_data['kjoretoydataListe']:
                vehicle = vehicle_data['kjoretoydataListe'][0]
                print(f"Vehicle: {vehicle.get('merke', 'Unknown')} {vehicle.get('modell', 'Unknown')}")
        
        # Test 2: Car parts search (complete workflow)
        print("\n3. Testing complete car parts search...")
        response = requests.get("http://127.0.0.1:8000/api/car_parts_search?regnr=KH66644", timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            parts_data = response.json()
            print("✅ Car parts search completed")
            print(f"Vehicle info: {parts_data.get('vehicle_info', {})}")
            print(f"Rackbeat parts found: {len(parts_data.get('rackbeat_parts', []))}")
            print(f"Rackbeat status: {parts_data.get('rackbeat_status', 'Unknown')}")
            
            # Show some sample parts
            rackbeat_parts = parts_data.get('rackbeat_parts', [])
            if rackbeat_parts:
                print("\nSample Rackbeat parts:")
                for i, part in enumerate(rackbeat_parts[:3]):
                    print(f"  {i+1}. {part.get('name', 'Unknown')} - SKU: {part.get('number', 'Unknown')} - Price: {part.get('sales_price', 0)}")
        
        # Test 3: OEM search in Shopify
        print("\n4. Testing OEM search in Shopify...")
        # Use a sample OEM number
        sample_oem = "1K0145769AC"  # Common VW part number
        response = requests.get(f"http://127.0.0.1:8000/api/oem_search?oem={sample_oem}", timeout=15)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            shopify_products = response.json()
            print(f"✅ Found {len(shopify_products)} matching Shopify products")
            
            if shopify_products:
                print("\nSample Shopify products:")
                for i, product in enumerate(shopify_products[:3]):
                    print(f"  {i+1}. {product.get('title', 'Unknown')} - SKU: {product.get('variants', [{}])[0].get('sku', 'Unknown')}")
                    
                    # Check metafields
                    if 'metafields' in product:
                        print(f"     Metafields: {len(product['metafields'])} found")
                        for mf in product['metafields'][:2]:
                            print(f"       - {mf.get('key', 'Unknown')}: {mf.get('value', 'Unknown')}")
        
        # Test 4: Check if we have the required metafields
        print("\n5. Testing metafield structure...")
        response = requests.get("http://127.0.0.1:8000/api/rackbeat/parts", timeout=10)
        if response.status_code == 200:
            rackbeat_data = response.json()
            products = rackbeat_data.get('products', [])
            if products:
                sample_product = products[0]
                print(f"Sample product fields: {list(sample_product.keys())}")
                
                # Check for OEM-related fields
                oem_fields = ['description', 'original_nummer', 'oem_number']
                found_oem_fields = [field for field in oem_fields if field in sample_product]
                print(f"OEM-related fields found: {found_oem_fields}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    finally:
        app_process.terminate()
        app_process.wait()
        print("\nApp service stopped.")

if __name__ == "__main__":
    test_complete_workflow() 