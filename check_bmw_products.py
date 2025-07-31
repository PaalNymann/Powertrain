#!/usr/bin/env python3
"""
Check which BMW products have real field values
"""

from database import SessionLocal, ProductMetafield, ShopifyProduct

def main():
    db = SessionLocal()
    try:
        # Get BMW products
        bmw_products = db.query(ShopifyProduct).filter(ShopifyProduct.title.like('%BMW%')).all()
        print(f"Found {len(bmw_products)} BMW products")
        
        # Check each BMW product for real field values
        products_with_real_values = []
        for product in bmw_products:
            metafields = db.query(ProductMetafield).filter(
                ProductMetafield.product_id == product.id,
                ProductMetafield.key.in_(['original_nummer', 'tirsan_varenummer', 'odm_varenummer', 'ims_varenummer', 'welte_varenummer', 'bakkeren_varenummer'])
            ).all()
            
            has_real_values = any(m.value != 'N/A' for m in metafields)
            if has_real_values:
                products_with_real_values.append((product, metafields))
                print(f"\n✅ Product: {product.title}")
                print(f"   SKU: {product.sku}")
                for m in metafields:
                    if m.value != 'N/A':
                        print(f"   {m.key}: {m.value}")
        
        print(f"\n🎯 Found {len(products_with_real_values)} BMW products with real field values")
        
    finally:
        db.close()

if __name__ == "__main__":
    main() 