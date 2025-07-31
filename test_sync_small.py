#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

RACKBEAT_API_KEY = os.getenv('RACKBEAT_API_KEY')
RACKBEAT_API = "https://app.rackbeat.com/api/products"
SHOP_DOMAIN = os.getenv('SHOPIFY_DOMAIN')
SHOPIFY_TOKEN = os.getenv('SHOPIFY_TOKEN')

headers = {
    "Authorization": f"Bearer {RACKBEAT_API_KEY}",
    "Content-Type": "application/json"
}

HEAD_SHOP = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}

def fetch_rackbeat_products():
    """Fetch a small sample of products from Rackbeat"""
    try:
        response = requests.get(
            RACKBEAT_API,
            headers=headers,
            params={"limit": 500},  # Get more products to find ones with field values
            timeout=30
        )
        
        if response.status_code in [200, 206]:
            data = response.json()
            products = data.get("products", [])
            print(f"✅ Fetched {len(products)} sample products")
            return products
        else:
            print(f"❌ Failed to fetch products: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Exception fetching products: {e}")
        return []

def filter_products(products):
    """Filter products based on criteria"""
    filtered = []
    for product in products:
        sales_price = product.get('sales_price', 0)
        
        # Sync all products with a sales price, regardless of available quantity
        # This allows products with real part numbers to be synced even if out of stock
        if sales_price > 0:
            filtered.append(product)
    
    print(f"✅ Filtered {len(filtered)} products (sales_price > 0)")
    return filtered

def get_field_values_from_api(sku):
    """Get field values from Rackbeat API for a specific product"""
    try:
        field_response = requests.get(
            f"{RACKBEAT_API}/{sku}/fields",
            headers=headers,
            timeout=30
        )
        
        if field_response.status_code in [200, 206]:
            field_data = field_response.json()
            field_values = field_data.get('field_values', [])
            
            # Extract the values we need
            result = {
                'original_nummer': 'N/A',
                'tirsan_varenummer': 'N/A', 
                'odm_varenummer': 'N/A',
                'ims_varenummer': 'N/A',
                'welte_varenummer': 'N/A',
                'bakkeren_varenummer': 'N/A'
            }
            
            for field_value in field_values:
                field_name = field_value.get('field', {}).get('name', '').lower()
                value = field_value.get('value', '').strip()
                
                if field_name == 'original_nummer':
                    result['original_nummer'] = value if value else 'N/A'
                elif field_name == 'tirsan varenummer':
                    result['tirsan_varenummer'] = value if value else 'N/A'
                elif field_name == 'odm varenummer':
                    result['odm_varenummer'] = value if value else 'N/A'
                elif field_name == 'ims varenummer':
                    result['ims_varenummer'] = value if value else 'N/A'
                elif field_name == 'welte varenummer':
                    result['welte_varenummer'] = value if value else 'N/A'
                elif field_name == 'bakkeren varenummer':
                    result['bakkeren_varenummer'] = value if value else 'N/A'
            
            return result
        else:
            print(f"⚠️  Failed to get field values for {sku}: {field_response.status_code}")
            return None
            
    except Exception as e:
        print(f"⚠️  Error getting field values for {sku}: {e}")
        return None

def create_product_in_shopify(product):
    """Create a single product in Shopify with real field values"""
    sku = product.get('number', '')
    name = product.get('name', '')
    sales_price = product.get('sales_price', 0)
    
    print(f"\n📦 Processing: {name} (SKU: {sku})")
    
    # Create product payload
    payload = {
        "product": {
            "title": name or sku,
            "status": "active",
            "variants": [{
                "sku": sku,
                "price": str(sales_price)
            }],
            "handle": sku.lower().replace(" ", "-")
        }
    }
    
    # Create product
    try:
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json",
            headers=HEAD_SHOP,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            product_data = response.json()["product"]
            product_id = product_data["id"]
            print(f"✅ Created product {sku} (ID: {product_id})")
            
            # Get field values from API
            field_data = get_field_values_from_api(sku)
            if not field_data:
                # Fallback to N/A if we can't get field values
                field_data = {
                    'original_nummer': 'N/A',
                    'tirsan_varenummer': 'N/A', 
                    'odm_varenummer': 'N/A',
                    'ims_varenummer': 'N/A',
                    'welte_varenummer': 'N/A',
                    'bakkeren_varenummer': 'N/A'
                }
            
            print(f"📋 Field values for {sku}:")
            for key, value in field_data.items():
                print(f"  {key}: {value}")
            
            # Add metafields with real values from Rackbeat
            metafields = [
                {"namespace": "custom", "key": "number", "type": "single_line_text_field", "value": sku},
                {"namespace": "custom", "key": "original_nummer", "type": "single_line_text_field", "value": field_data['original_nummer']},
                {"namespace": "custom", "key": "tirsan_varenummer", "type": "single_line_text_field", "value": field_data['tirsan_varenummer']},
                {"namespace": "custom", "key": "odm_varenummer", "type": "single_line_text_field", "value": field_data['odm_varenummer']},
                {"namespace": "custom", "key": "ims_varenummer", "type": "single_line_text_field", "value": field_data['ims_varenummer']},
                {"namespace": "custom", "key": "welte_varenummer", "type": "single_line_text_field", "value": field_data['welte_varenummer']},
                {"namespace": "custom", "key": "bakkeren_varenummer", "type": "single_line_text_field", "value": field_data['bakkeren_varenummer']}
            ]
            
            for mf in metafields:
                mf["owner_id"] = product_id
                mf["owner_resource"] = "product"
                mf_response = requests.post(
                    f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                    headers=HEAD_SHOP,
                    json={"metafield": mf},
                    timeout=30
                )
                if mf_response.status_code != 201:
                    print(f"⚠️  Failed to create metafield {mf['key']} for {sku}: {mf_response.status_code} - {mf_response.text}")
                else:
                    print(f"✅ Created metafield {mf['key']} for {sku}")
            
            return True
        else:
            print(f"❌ Failed to create product {sku}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception creating product {sku}: {e}")
        return False

def main():
    print("🚀 Starting small sync test...")
    
    # Fetch products from Rackbeat
    all_products = fetch_rackbeat_products()
    if not all_products:
        print("❌ No products fetched from Rackbeat")
        return
    
    # Filter products
    filtered_products = filter_products(all_products)
    if not filtered_products:
        print("❌ No products to sync after filtering")
        return
    
    # Sync products to Shopify
    print(f"🔄 Syncing {len(filtered_products)} products to Shopify...")
    success_count = 0
    
    for i, product in enumerate(filtered_products):
        print(f"📦 Processing {i+1}/{len(filtered_products)}: {product.get('number', 'N/A')}")
        if create_product_in_shopify(product):
            success_count += 1
    
    print(f"✅ Sync completed! {success_count}/{len(filtered_products)} products created successfully")

if __name__ == "__main__":
    main() 