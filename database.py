import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, or_, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

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
        # Always use SQLite locally
        return 'sqlite:///powertrain.db'

engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
            
            # Convert to dictionary format
            result = []
            for product in products:
                product_dict = {
                    'id': str(product.id),
                    'title': product.title,
                    'handle': product.handle,
                    'oem': oem_number,  # Use the searched OEM number
                    'price': '0',  # Default since Railway DB has no price column
                    'inventory_quantity': 1  # Assume available since Railway DB has no inventory column
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
                # Update existing product
                existing_product.title = product_data.get('title', '')
                existing_product.handle = product_data.get('handle', '')
                existing_product.oem_metafield = product_data.get('oem_metafield', '')
                existing_product.original_nummer_metafield = product_data.get('original_nummer_metafield', '')
                existing_product.number_metafield = product_data.get('number_metafield', '')
                existing_product.price = product_data.get('variants', [{}])[0].get('price', '') if product_data.get('variants') else ''
                existing_product.updated_at = datetime.utcnow()
                
                # Update metafields if available
                if 'metafields' in product_data:
                    for metafield in product_data['metafields']:
                        key = metafield.get('key', '')
                        value = metafield.get('value', '')
                        
                        if key == 'original_nummer':
                            existing_product.original_nummer_metafield = value
                        elif key == 'oem':
                            existing_product.oem_metafield = value
                        elif key == 'number':
                            existing_product.number_metafield = value
                
                # Update inventory
                if 'variants' in product_data and product_data['variants']:
                    total_inventory = sum(
                        int(variant.get('inventory_quantity', 0)) 
                        for variant in product_data['variants']
                    )
                    existing_product.inventory_quantity = total_inventory
                    
            else:
                # Create new product
                new_product = ShopifyProduct(
                    title=product_data.get('title', ''),
                    handle=product_data.get('handle', ''),
                    oem_metafield=product_data.get('oem_metafield', ''),
                    original_nummer_metafield=product_data.get('original_nummer_metafield', ''),
                    number_metafield=product_data.get('number_metafield', '')
                )
                
                # Set metafields if available
                if 'metafields' in product_data:
                    for metafield in product_data['metafields']:
                        key = metafield.get('key', '')
                        value = metafield.get('value', '')
                        
                        if key == 'original_nummer':
                            new_product.original_nummer_metafield = value
                        elif key == 'oem':
                            new_product.oem_metafield = value
                        elif key == 'number':
                            new_product.number_metafield = value
                
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