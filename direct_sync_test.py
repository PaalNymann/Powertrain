#!/usr/bin/env python3
"""
Direct sync test - bypass get_all_shopify_ids and create products directly
"""
import os, sys, time, json, requests
from dotenv import load_dotenv
load_dotenv()

# Import functions from main sync service
sys.path.append('.')
from sync_service import (
    rb_page, filter_keep, map_to_shop_payload, 
    get_collection_id, assign_to_collection,
    RACKBEAT_API, HEAD_RACK, SHOP_DOMAIN, HEAD_SHOP
)

def create_or_update_product_direct(payload, metafields):
    """Create or update product directly without checking existing IDs"""
    try:
        sku = payload['product']['variants'][0]['sku']
        title = payload['product']['title']
        
        print(f"🔄 Creating product: {title[:50]}... (SKU: {sku})")
        
        # Try to create product
        response = requests.post(
            f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json",
            headers=HEAD_SHOP,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            # Product created successfully
            product_data = response.json()
            product = product_data.get("product", {})
            product_id = product.get("id")
            
            print(f"   ✅ Product created: ID {product_id}")
            
            # Add metafields if any
            if metafields and product_id:
                for metafield in metafields:
                    metafield_payload = {
                        "metafield": {
                            **metafield,
                            "owner_id": product_id,
                            "owner_resource": "product"
                        }
                    }
                    
                    meta_response = requests.post(
                        f"https://{SHOP_DOMAIN}/admin/api/2023-10/metafields.json",
                        headers=HEAD_SHOP,
                        json=metafield_payload,
                        timeout=20
                    )
                    
                    if meta_response.status_code == 201:
                        print(f"   ✅ Metafield added: {metafield.get('key', 'N/A')}")
                    else:
                        print(f"   ⚠️ Metafield failed: {meta_response.status_code}")
            
            return product_id
            
        elif response.status_code == 422:
            # Product might already exist, try to find and update it
            error_data = response.json()
            errors = error_data.get("errors", {})
            
            if "Title has already been taken" in str(errors) or "SKU" in str(errors):
                print(f"   ⚠️ Product exists, searching for update...")
                
                # Search for existing product by SKU
                search_response = requests.get(
                    f"https://{SHOP_DOMAIN}/admin/api/2023-10/products.json?limit=1&fields=id,variants&sku={sku}",
                    headers=HEAD_SHOP,
                    timeout=20
                )
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    products = search_data.get("products", [])
                    
                    for product in products:
                        for variant in product.get("variants", []):
                            if variant.get("sku") == sku:
                                existing_id = product.get("id")
                                print(f"   🔄 Updating existing product: ID {existing_id}")
                                
                                # Update existing product
                                update_payload = {
                                    "product": {
                                        "id": existing_id,
                                        **payload['product']
                                    }
                                }
                                
                                update_response = requests.put(
                                    f"https://{SHOP_DOMAIN}/admin/api/2023-10/products/{existing_id}.json",
                                    headers=HEAD_SHOP,
                                    json=update_payload,
                                    timeout=30
                                )
                                
                                if update_response.status_code == 200:
                                    print(f"   ✅ Product updated: ID {existing_id}")
                                    return existing_id
                                else:
                                    print(f"   ❌ Update failed: {update_response.status_code}")
                
                print(f"   ❌ Could not find existing product for update")
                return None
            else:
                print(f"   ❌ Creation failed: {response.status_code} - {errors}")
                return None
        else:
            print(f"   ❌ Unexpected error: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"   ❌ Exception creating product: {e}")
        return None

def direct_sync_test(max_products=5):
    """Direct sync test without get_all_shopify_ids"""
    print(f"🚀 STARTING DIRECT SYNC TEST (max {max_products} products)")
    print("=" * 60)
    
    try:
        # Step 1: Get Rackbeat products and filter
        print("📥 Fetching and filtering Rackbeat products...")
        all_products = []
        page = 1
        
        while len(all_products) < 1000 and page <= 5:
            products, pages = rb_page(page)
            all_products.extend(products)
            page += 1
        
        # Filter products
        filtered = []
        for p in all_products:
            if filter_keep(p):
                filtered.append(p)
                if len(filtered) >= max_products:
                    break
        
        print(f"✅ Found {len(filtered)} eligible products")
        
        if not filtered:
            print("❌ No products passed filtering!")
            return
        
        # Step 2: Get collection IDs
        print("🔄 Getting collection IDs...")
        drivaksler_id = get_collection_id("Drivaksler")
        mellomaksler_id = get_collection_id("Mellomaksler")
        
        print(f"   Drivaksler collection ID: {drivaksler_id}")
        print(f"   Mellomaksler collection ID: {mellomaksler_id}")
        
        # Step 3: Process each product directly
        print("🔄 Processing products directly...")
        success_count = 0
        
        for i, p in enumerate(filtered):
            try:
                print(f"\n📦 Processing {i+1}/{len(filtered)}:")
                print(f"   Name: {p.get('name', 'N/A')[:50]}")
                print(f"   Group: {p.get('group', {}).get('name', 'N/A')}")
                print(f"   SKU: {p.get('number', 'N/A')}")
                
                # Map to Shopify payload
                payload, metafields = map_to_shop_payload(p)
                
                # Create product directly
                product_id = create_or_update_product_direct(payload, metafields)
                
                if product_id:
                    success_count += 1
                    
                    # Assign to collection
                    group_name = p.get('group', {}).get('name', '')
                    if group_name == "Drivaksel" and drivaksler_id:
                        print(f"   🔄 Assigning to Drivaksler collection...")
                        assign_result = assign_to_collection(product_id, "Drivaksler")
                        if assign_result:
                            print(f"   ✅ Collection assignment successful")
                    elif group_name == "Mellomaksel" and mellomaksler_id:
                        print(f"   🔄 Assigning to Mellomaksler collection...")
                        assign_result = assign_to_collection(product_id, "Mellomaksler")
                        if assign_result:
                            print(f"   ✅ Collection assignment successful")
                
                # Small delay to avoid rate limits
                time.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Error processing product: {e}")
        
        print(f"\n🎉 DIRECT SYNC TEST COMPLETED!")
        print(f"   Products processed: {len(filtered)}")
        print(f"   Successful syncs: {success_count}")
        print(f"   Success rate: {success_count/len(filtered)*100:.1f}%")
        
        # Verify collections now have products
        print("\n🔍 Verifying collection assignments...")
        
        for collection_name in ["Drivaksler", "Mellomaksler"]:
            response = requests.get(
                f"https://{SHOP_DOMAIN}/admin/api/2023-10/custom_collections.json",
                headers=HEAD_SHOP,
                timeout=20
            )
            
            if response.status_code == 200:
                collections_data = response.json()
                collections = collections_data.get("custom_collections", [])
                
                for collection in collections:
                    if collection.get("title") == collection_name:
                        product_count = collection.get("products_count", 0)
                        print(f"   {collection_name}: {product_count} products")
                        break
        
        return success_count
        
    except Exception as e:
        print(f"❌ Direct sync test error: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    # Test with 3 products first
    direct_sync_test(3)
