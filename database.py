import os
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text, Column, Integer, String, Text, DateTime, or_, func, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Define models directly here
Base = declarative_base()

class ShopifyProduct(Base):
    __tablename__ = 'shopify_products'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    handle = Column(String)
    body_html = Column(Text)
    vendor = Column(String)
    product_type = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    published_at = Column(DateTime)
    template_suffix = Column(String)
    status = Column(String)
    published_scope = Column(String)
    tags = Column(String)
    admin_graphql_api_id = Column(String)

class ProductMetafield(Base):
    __tablename__ = 'product_metafields'
    
    id = Column(String, primary_key=True)
    product_id = Column(String)
    namespace = Column(String)
    key = Column(String)
    value = Column(Text)
    created_at = Column(DateTime)
import logging
import requests
import json
from datetime import datetime

Base = declarative_base()

class ShopifyProduct(Base):
    __tablename__ = 'shopify_products'
    
    id = Column(String, primary_key=True)  # Shopify product ID is string
    title = Column(String(500), nullable=False)
    handle = Column(String(500), nullable=False)
    sku = Column(String(100))  # SKU column that exists in Railway DB
    price = Column(String(50))  # Price column that exists in Railway DB
    inventory_quantity = Column(Integer, default=0)
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
        shopify_token = os.getenv('SHOPIFY_TOKEN')
        shopify_shop = os.getenv('SHOPIFY_DOMAIN')
        
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

def get_shopify_product_data(product_id):
    """Get real Shopify product data (price, SKU, variant_id) for a specific product"""
    try:
        shopify_token = os.getenv('SHOPIFY_TOKEN')
        shopify_shop = os.getenv('SHOPIFY_DOMAIN')
        
        if not shopify_token or not shopify_shop:
            print("❌ Missing Shopify credentials")
            return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}
        
        # Fix domain name - remove .myshopify.com if already present
        if shopify_shop.endswith('.myshopify.com'):
            base_domain = shopify_shop
        else:
            base_domain = f"{shopify_shop}.myshopify.com"
        
        url = f"https://{base_domain}/admin/api/2023-10/products/{product_id}.json"
        headers = {
            'X-Shopify-Access-Token': shopify_token,
            'Content-Type': 'application/json'
        }
        
        print(f"🔍 Fetching Shopify data for product {product_id}")
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code == 429:
            print(f"⚠️ Rate limited for product {product_id}, using Railway DB data")
            return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}
        elif response.status_code != 200:
            print(f"❌ Shopify API error for product {product_id}: {response.status_code} - {response.text[:200]}")
            return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}
        
        product_data = response.json().get('product', {})
        variants = product_data.get('variants', [])
        
        if variants:
            first_variant = variants[0]
            price = str(first_variant.get('price', '0'))
            sku = first_variant.get('sku', '')
            variant_id = str(first_variant.get('id', ''))
            inventory = first_variant.get('inventory_quantity', 0)
            
            print(f"✅ Got Shopify data for {product_id}: Price={price}, SKU={sku}")
            
            return {
                'price': price,
                'sku': sku,
                'variant_id': variant_id,
                'inventory_quantity': inventory
            }
        else:
            print(f"⚠️ No variants found for product {product_id}")
        
        return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}
        
    except Exception as e:
        print(f"❌ Error getting Shopify product data for {product_id}: {e}")
        return {'price': '0', 'sku': '', 'variant_id': '', 'inventory_quantity': 0}

def search_products_by_oem(oem_numbers):
    """Search for products by OEM numbers in Railway DB metafields - returns unique products with price and SKU"""
    try:
        session = SessionLocal()
        
        print(f"🔍 Searching Railway DB metafields for {len(oem_numbers)} OEM numbers")
        
        matching_products = []
        seen_skus = set()  # Track SKUs to avoid duplicates
        
        # Normalize OEM numbers for search
        normalized_oems = []
        for oem in oem_numbers:
            # Add both original and normalized versions
            normalized_oems.append(oem.upper())
            clean = oem.replace('-', '').replace(' ', '').strip().upper()
            if clean != oem.upper():
                normalized_oems.append(clean)
        
        # Search in product_metafields table for OEM numbers
        from sqlalchemy import or_, func
        
        # Build OR conditions for all OEM variations in metafields
        oem_conditions = []
        for oem in normalized_oems[:20]:  # Limit to avoid too complex query
            oem_conditions.append(func.upper(ProductMetafield.value).contains(oem))
        
        if oem_conditions:
            # Find metafields that match OEM numbers
            metafields = session.query(ProductMetafield).filter(
                and_(
                    ProductMetafield.namespace == 'custom',
                    or_(
                        ProductMetafield.key == 'original_nummer',
                        ProductMetafield.key == 'original-nummer'
                    ),
                    or_(*oem_conditions)
                )
            ).limit(50).all()
            
            print(f"📦 Found {len(metafields)} metafields matching OEM numbers")
            
            # Get unique product IDs from metafields
            product_ids = list(set([mf.product_id for mf in metafields]))
            
            # Fetch products by IDs
            products = session.query(ShopifyProduct).filter(
                ShopifyProduct.id.in_(product_ids)
            ).all()
            
            print(f"📦 Found {len(products)} products in Railway DB")
            
            for product in products:
                # Skip if we've already seen this SKU (deduplicate)
                if product.sku in seen_skus:
                    continue
                
                seen_skus.add(product.sku)
                
                # Get OEM numbers for this product
                product_metafields = [mf for mf in metafields if mf.product_id == product.id]
                oem_values = [mf.value for mf in product_metafields if mf.value]
                oem_string = ', '.join(oem_values) if oem_values else ''
                
                product_dict = {
                    'id': str(product.id),
                    'title': product.title or '',
                    'handle': product.handle or '',
                    'oem': oem_string,
                    'price': str(product.price or '0'),
                    'sku': product.sku or '',
                    'variant_id': str(product.id),
                    'inventory_quantity': product.inventory_quantity or 0
                }
                matching_products.append(product_dict)
                print(f"✅ Found product: {product.title} - SKU: {product.sku} - Price: {product.price} NOK - OEM: {oem_string[:50]}...")
        
        session.close()
        print(f"✅ Returning {len(matching_products)} unique products (deduplicated by SKU)")
        return matching_products
        
    except Exception as e:
        print(f"❌ Error searching Railway DB: {e}")
        import traceback
        traceback.print_exc()
        return []

def search_products_by_vehicle(make, model=None):
    """Search for products by vehicle make/model DIRECTLY in Shopify API"""
    try:
        shopify_token = os.getenv('SHOPIFY_TOKEN')
        shopify_shop = os.getenv('SHOPIFY_DOMAIN')
        
        if not shopify_token or not shopify_shop:
            print("❌ Missing Shopify credentials")
            return []
        
        # Fix domain name - remove .myshopify.com if already present
        if shopify_shop.endswith('.myshopify.com'):
            base_domain = shopify_shop
        else:
            base_domain = f"{shopify_shop}.myshopify.com"
        
        # Build search query for Shopify
        if model:
            search_term = f"{make} {model}"
            print(f"🔍 Vehicle search for {make} {model}: searching DIRECTLY in Shopify")
        else:
            search_term = make
            print(f"🔍 Vehicle search for {make}: searching DIRECTLY in Shopify")
        
        url = f"https://{base_domain}/admin/api/2023-10/products.json"
        headers = {
            'X-Shopify-Access-Token': shopify_token,
            'Content-Type': 'application/json'
        }
        
        params = {
            'limit': 20,
            'status': 'active',
            'title': search_term,  # Search by title containing vehicle info
            'fields': 'id,title,handle,variants'  # Include variants for pricing
        }
        
        response = requests.get(url, headers=headers, verify=False)
        
        if response.status_code != 200:
            print(f"❌ Shopify API error: {response.status_code}")
            return []
        
        shopify_data = response.json()
        products = shopify_data.get('products', [])
        
        print(f"🔍 Vehicle search for {search_term}: found {len(products)} REAL Shopify matches")
        
        # Convert to the expected format with REAL Shopify data
        results = []
        for product in products:
            variants = product.get('variants', [])
            if variants:
                first_variant = variants[0]
                
                product_dict = {
                    'id': str(product.get('id', '')),
                    'title': product.get('title', ''),
                    'handle': product.get('handle', ''),
                    'oem': search_term,  # Use the search term as OEM
                    'price': str(first_variant.get('price', '0')),  # REAL Shopify price
                    'sku': first_variant.get('sku', ''),  # REAL Shopify SKU
                    'variant_id': str(first_variant.get('id', '')),  # REAL variant ID
                    'inventory_quantity': first_variant.get('inventory_quantity', 0)
                }
                results.append(product_dict)
                print(f"✅ Found REAL Shopify product: {product.get('title')} - Price: {first_variant.get('price')} NOK")
        
        return results
        
    except Exception as e:
        print(f"❌ Error in vehicle search: {e}")
        return []

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