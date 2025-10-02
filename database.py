import os
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, or_, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import logging
import requests
import json
from datetime import datetime

Base = declarative_base()

class ShopifyProduct(Base):
    __tablename__ = 'shopify_products'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    handle = Column(String(500), nullable=False)
    # Railway DB has NO metafield columns - only basic product info
    inventory_quantity = Column(Integer, default=0)
    price = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_database_url():
    """Get database URL from environment or use SQLite for local development"""
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgresql://'):
        return database_url
    elif database_url and database_url.startswith('sqlite://'):
        return database_url
    else:
        # Use root database that contains the products
        return 'sqlite:////Users/nyman/powertrain_system/powertrain.db'

engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_shopify_product_data(product_id):
    """Fetch real Shopify product data including price, SKU, variant_id and inventory"""
    try:
        shopify_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        shopify_shop = os.getenv('SHOPIFY_SHOP_NAME')
        
        if not shopify_token or not shopify_shop:
            print("❌ Missing Shopify credentials")
            return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}
        
        url = f"https://{shopify_shop}.myshopify.com/admin/api/2023-10/products/{product_id}.json"
        headers = {
            'X-Shopify-Access-Token': shopify_token,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            product_data = response.json().get('product', {})
            variants = product_data.get('variants', [])
            
            if variants:
                first_variant = variants[0]
                return {
                    'price': str(first_variant.get('price', '0')),
                    'sku': first_variant.get('sku', ''),
                    'variant_id': str(first_variant.get('id', '')),
                    'inventory_quantity': first_variant.get('inventory_quantity', 0)
                }
        
        print(f"❌ Failed to fetch Shopify data for product {product_id}: {response.status_code}")
        return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}
        
    except Exception as e:
        print(f"❌ Error fetching Shopify data: {e}")
        return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}

def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

def search_products_by_oem(oem_numbers):
    """Search for products by OEM numbers in title field (Railway DB has no metafield columns)"""
    session = SessionLocal()
    try:
        all_products = []
        
        for oem_number in oem_numbers:
            clean_oem = oem_number.strip()
            
            # Search in title field for OEM numbers since Railway DB has no metafield columns
            title_condition = or_(
                ShopifyProduct.title.like(f'%{clean_oem}%'),
                ShopifyProduct.title.like(f'%{oem_number}%'),
                func.upper(ShopifyProduct.title).like(f'%{clean_oem.upper()}%'),
                func.upper(ShopifyProduct.title).like(f'%{oem_number.upper()}%')
            )
            
            query = session.query(ShopifyProduct).filter(title_condition)
            products = query.all()
            
            print(f"🔍 Searching for OEM {oem_number} in product titles: found {len(products)} matches")
            
            # Convert to dictionary format with real Shopify data
            result = []
            for product in products:
                # Get real Shopify data via API call
                shopify_data = get_shopify_product_data(product.id)
                
                product_dict = {
                    'id': str(product.id),
                    'title': product.title,
                    'handle': product.handle,
                    'oem': oem_number,  # Use the searched OEM number
                    'price': shopify_data.get('price', '0'),  # Real Shopify price
                    'sku': shopify_data.get('sku', ''),  # Real Shopify SKU
                    'variant_id': shopify_data.get('variant_id', ''),  # Real variant ID for cart
                    'inventory_quantity': shopify_data.get('inventory_quantity', 0)
                }
                result.append(product_dict)
            
            all_products.extend(result)
        
        print(f"✅ Found {len(all_products)} matching Shopify products")
        return all_products
        
    except Exception as e:
        print(f"Error searching database: {e}")
        return []
    finally:
        session.close()

def search_products_by_vehicle(make, model=None):
    """Search for products by vehicle make and model as fallback when OEM search fails"""
    session = SessionLocal()
    try:
        # Build search conditions for vehicle make/model
        conditions = []
        
        # Search for make (required)
        if make:
            make_condition = func.upper(ShopifyProduct.title).like(f'%{make.upper()}%')
            conditions.append(make_condition)
        
        # Add model condition if provided
        if model and model.strip():
            model_condition = func.upper(ShopifyProduct.title).like(f'%{model.upper()}%')
            conditions.append(model_condition)
        
        # Also search for drivaksel/aksel products specifically
        product_type_condition = or_(
            func.upper(ShopifyProduct.title).like('%DRIVAKSEL%'),
            func.upper(ShopifyProduct.title).like('%AKSEL%')
        )
        conditions.append(product_type_condition)
        
        # Combine all conditions
        if conditions:
            query = session.query(ShopifyProduct).filter(*conditions)
            products = query.limit(20).all()  # Limit to prevent too many results
            
            print(f"🔍 Vehicle search for {make} {model or ''}: found {len(products)} matches")
            
            # Convert to dictionary format
            result = []
            for product in products:
                product_dict = {
                    'id': str(product.id),
                    'title': product.title,
                    'handle': product.handle,
                    'oem': f"{make} {model or ''}".strip(),  # Use vehicle info as "OEM"
                    'price': '0',  # Default since Railway DB has no price column
                    'sku': '',  # Default since Railway DB has no SKU column
                    'variant_id': '',  # Default since Railway DB has no variant_id column
                    'inventory_quantity': 1  # Assume available since Railway DB has no inventory column
                }
                result.append(product_dict)
            
            return result
        else:
            return []
        
    except Exception as e:
        print(f"Error searching by vehicle: {e}")
        return []
    finally:
        session.close()

def update_shopify_cache(products_data):
    """Update Shopify product cache in database"""
    session = SessionLocal()
    try:
        for product_data in products_data:
            # Check if product exists by handle (unique identifier)
            existing_product = session.query(ShopifyProduct).filter(
                ShopifyProduct.handle == product_data.get('handle', '')
            ).first()
            
            if existing_product:
                # Update existing product - only use columns that exist in Railway DB schema
                existing_product.title = product_data.get('title', '')
                existing_product.handle = product_data.get('handle', '')
                existing_product.price = product_data.get('variants', [{}])[0].get('price', '') if product_data.get('variants') else ''
                existing_product.updated_at = datetime.utcnow()
                
                # Store OEM numbers in title for searchability since Railway DB has no metafield columns
                oem_info = []
                if 'metafields' in product_data:
                    for metafield in product_data['metafields']:
                        key = metafield.get('key', '')
                        value = metafield.get('value', '')
                        
                        if key in ['original_nummer', 'oem', 'number'] and value:
                            oem_info.append(value)
                
                # Append OEM info to title if not already present
                if oem_info:
                    oem_string = ' '.join(oem_info)
                    if oem_string not in existing_product.title:
                        existing_product.title = f"{existing_product.title} {oem_string}"
                
                # Update inventory
                if 'variants' in product_data and product_data['variants']:
                    total_inventory = sum(
                        int(variant.get('inventory_quantity', 0)) 
                        for variant in product_data['variants']
                    )
                    existing_product.inventory_quantity = total_inventory
                    
            else:
                # Create new product - only use columns that exist in Railway DB schema
                title = product_data.get('title', '')
                
                # Extract OEM info from metafields and append to title for searchability
                oem_info = []
                if 'metafields' in product_data:
                    for metafield in product_data['metafields']:
                        key = metafield.get('key', '')
                        value = metafield.get('value', '')
                        
                        if key in ['original_nummer', 'oem', 'number'] and value:
                            oem_info.append(value)
                
                # Append OEM info to title for searchability
                if oem_info:
                    oem_string = ' '.join(oem_info)
                    if oem_string not in title:
                        title = f"{title} {oem_string}"
                
                new_product = ShopifyProduct(
                    title=title,
                    handle=product_data.get('handle', '')
                )
                
                # Set inventory
                if 'variants' in product_data and product_data['variants']:
                    total_inventory = sum(
                        int(variant.get('inventory_quantity', 0)) 
                        for variant in product_data['variants']
                    )
                    new_product.inventory_quantity = total_inventory
                
                session.add(new_product)
        
        session.commit()
        print(f"Updated cache with {len(products_data)} products")
        
    except Exception as e:
        session.rollback()
        print(f"Error updating cache: {e}")
        raise
    finally:
        session.close()

def update_product_oem_metafields(product_handle, oem_numbers):
    """Update OEM metafields for a specific product"""
    session = SessionLocal()
    try:
        product = session.query(ShopifyProduct).filter(
            ShopifyProduct.handle == product_handle
        ).first()
        
        if product:
            if oem_numbers:
                product.oem_metafield = oem_numbers[0]  # Store first OEM
                session.commit()
                print(f"✅ Updated OEM metafield for product {product_handle}: {oem_numbers[0]}")
            else:
                print(f"❌ No OEM numbers to update for product {product_handle}")
        else:
            print(f"❌ Product not found: {product_handle}")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating OEM metafields: {e}")
        return False
    finally:
        session.close()

def get_products_without_oem():
    """Get products that don't have OEM metafields set"""
    session = SessionLocal()
    try:
        products = session.query(ShopifyProduct).filter(
            or_(
                ShopifyProduct.oem_metafield.is_(None),
                ShopifyProduct.oem_metafield == '',
                ShopifyProduct.oem_metafield == 'N/A'
            )
        ).all()
        
        return [str(product.id) for product in products]
        
    except Exception as e:
        print(f"Error getting products without OEM: {e}")
        return []
    finally:
        session.close()

def get_cache_stats():
    """Get cache statistics"""
    session = SessionLocal()
    try:
        total_products = session.query(ShopifyProduct).count()
        # All Shopify products are considered in stock from Rackbeat's perspective
        in_stock_products = total_products
        
        return {
            'total_products': total_products,
            'in_stock_products': in_stock_products,
            'cache_updated': datetime.utcnow().isoformat()
        }
    finally:
        session.close() 