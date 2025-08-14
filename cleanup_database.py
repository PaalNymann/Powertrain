#!/usr/bin/env python3
"""
Database Cleanup Script
Removes products from Railway database that don't have i_nettbutikk: ja in Rackbeat
"""

import os
import requests
from dotenv import load_dotenv
from database import SessionLocal, ShopifyProduct, ProductMetafield
from sqlalchemy import text

# Load environment variables
load_dotenv()

def get_rackbeat_product_status(product_number):
    """Check if a specific product has i_nettbutikk: ja in Rackbeat"""
    api_key = os.getenv('RACKBEAT_API_KEY')
    if not api_key:
        print("❌ RACKBEAT_API_KEY not found")
        return None
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    try:
        # Search for product by number
        response = requests.get(f'https://app.rackbeat.io/api/products?search={product_number}', headers=headers)
        if response.status_code == 200:
            products = response.json().get('data', [])
            for product in products:
                if product.get('number') == product_number:
                    i_nettbutikk = product.get('i_nettbutikk', '').lower()
                    group_name = product.get('group', {}).get('name', '')
                    return {
                        'i_nettbutikk': i_nettbutikk,
                        'group': group_name,
                        'has_webshop_access': i_nettbutikk == 'ja'
                    }
        return None
    except Exception as e:
        print(f"❌ Error checking product {product_number}: {e}")
        return None

def cleanup_database():
    """Remove products that don't have i_nettbutikk: ja in Rackbeat"""
    db_session = SessionLocal()
    
    try:
        # Get all products from database
        products = db_session.query(ShopifyProduct).all()
        print(f"🔍 Found {len(products)} products in database")
        
        products_to_remove = []
        products_checked = 0
        
        for product in products:
            products_checked += 1
            if products_checked % 10 == 0:
                print(f"📊 Checked {products_checked}/{len(products)} products...")
            
            # Get product number from metafields
            product_number = None
            metafields = db_session.query(ProductMetafield).filter_by(product_id=product.id).all()
            for metafield in metafields:
                if metafield.key == 'number':
                    product_number = metafield.value
                    break
            
            if not product_number:
                print(f"⚠️ No product number found for {product.title}")
                continue
            
            # Check Rackbeat status
            rackbeat_status = get_rackbeat_product_status(product_number)
            if rackbeat_status is None:
                print(f"⚠️ Could not verify status for {product.title} ({product_number})")
                continue
            
            # Check BOTH criteria: product group AND webshop access
            valid_group = rackbeat_status['group'] in ['Drivaksel', 'Mellomaksel']
            has_webshop_access = rackbeat_status['has_webshop_access']
            
            if not (valid_group and has_webshop_access):
                reason = []
                if not valid_group:
                    reason.append(f"wrong group: {rackbeat_status['group']}")
                if not has_webshop_access:
                    reason.append(f"i_nettbutikk: {rackbeat_status['i_nettbutikk']}")
                
                print(f"🚫 REMOVING: {product.title} - {' + '.join(reason)}")
                products_to_remove.append(product)
            else:
                print(f"✅ KEEPING: {product.title} - Group: {rackbeat_status['group']}, i_nettbutikk: {rackbeat_status['i_nettbutikk']}")
        
        # Remove products that don't belong in webshop
        print(f"\n🗑️ Removing {len(products_to_remove)} products without webshop access...")
        
        for product in products_to_remove:
            # Remove metafields first
            db_session.query(ProductMetafield).filter_by(product_id=product.id).delete()
            # Remove product
            db_session.delete(product)
        
        # Update categories for remaining products
        print(f"\n📂 Updating categories for remaining products...")
        remaining_products = db_session.query(ShopifyProduct).all()
        
        for product in remaining_products:
            # Get product group from metafields
            metafields = db_session.query(ProductMetafield).filter_by(product_id=product.id, key='product_group').first()
            if metafields:
                group_name = metafields.value
                shopify_category = group_name if group_name in ["Drivaksel", "Mellomaksel"] else "Uncategorized"
                product.product_type = shopify_category
                print(f"📂 Updated category for {product.title}: {shopify_category}")
            else:
                product.product_type = "Uncategorized"
        
        db_session.commit()
        print(f"✅ Cleanup complete! Removed {len(products_to_remove)} products")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        db_session.rollback()
    finally:
        db_session.close()

if __name__ == "__main__":
    print("🧹 Starting database cleanup...")
    cleanup_database()
