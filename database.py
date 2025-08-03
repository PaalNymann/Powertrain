import sqlite3
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import re

Base = declarative_base()

class ShopifyProduct(Base):
    __tablename__ = 'shopify_products'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    handle = Column(String)
    sku = Column(String)
    price = Column(Float)
    inventory_quantity = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProductMetafield(Base):
    __tablename__ = 'product_metafields'
    
    id = Column(String, primary_key=True)
    product_id = Column(String)
    namespace = Column(String)
    key = Column(String)
    value = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    

def get_database_url():
    """Get database URL from environment or use SQLite"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Convert Railway PostgreSQL URL to SQLAlchemy format
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        return database_url
    else:
        # Use SQLite for local development
        return 'sqlite:///powertrain.db'

def init_db():
    """Initialize database and create tables"""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    print("Database initialized")

def get_db_session():
    """Get database session"""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()

def search_products_by_oem(oem_number):
    """Search products by OEM number in all metafields except 'number'"""
    if not oem_number:
        return []
    
    db = get_db_session()
    try:
        # Clean OEM number
        clean_oem = oem_number.upper().strip()
        
        # Search in all metafields except 'number'
        results = db.query(ProductMetafield).filter(
            ProductMetafield.namespace == 'custom',
            ProductMetafield.key != 'number',
            ProductMetafield.value.ilike(f"%{clean_oem}%")
        ).all()
        
        products = []
        for metafield in results:
            # Get product details
            product = db.query(ShopifyProduct).filter(
                ShopifyProduct.id == metafield.product_id
            ).first()
            
            if product:
                products.append({
                    'id': product.id,
                    'title': product.title,
                    'handle': product.handle,
                    'sku': product.sku,
                    'price': product.price,
                    'inventory_quantity': product.inventory_quantity,
                    'matching_part_number': clean_oem,
                    'metafield_key': metafield.key,
                    'metafield_value': metafield.value
                })
        
        return products
    except Exception as e:
        print(f"Error in search_products_by_oem: {e}")
        return []
    finally:
        db.close()

def update_shopify_cache(products_data):
    """Update Shopify product cache"""
    db = get_db_session()
    try:
        # Clear existing data and commit immediately
        print(f"🗑️  Clearing existing data...")
        db.query(ShopifyProduct).delete()
        db.query(ProductMetafield).delete()
        db.commit()
        print(f"✅ Existing data cleared")
        
        total_products = 0
        total_metafields = 0
        
        print(f"📦 Processing {len(products_data)} products...")
        
        for i, product_data in enumerate(products_data):
            try:
                # Create product
                product = ShopifyProduct(
                    id=product_data['id'],
                    title=product_data['title'],
                    handle=product_data['handle'],
                    sku=product_data.get('sku', ''),
                    price=float(product_data.get('variants', [{}])[0].get('price', 0)),
                    inventory_quantity=int(product_data.get('variants', [{}])[0].get('inventory_quantity', 0))
                )
                db.add(product)
                total_products += 1
                
                # Process metafields
                for metafield_data in product_data.get('metafields', []):
                    metafield = ProductMetafield(
                        id=metafield_data['id'],
                        product_id=product_data['id'],
                        namespace=metafield_data['namespace'],
                        key=metafield_data['key'],
                        value=metafield_data['value']
                    )
                    db.add(metafield)
                    total_metafields += 1
                
                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"   📋 Processed {i + 1}/{len(products_data)} products")
                    
            except Exception as e:
                print(f"⚠️  Error processing product {product_data.get('id', 'unknown')}: {e}")
                continue
                

        
        db.commit()
        return {
            'products': total_products,
            'metafields': total_metafields
        }
    except Exception as e:
        db.rollback()
        print(f"Error updating cache: {e}")
        raise
    finally:
        db.close()

def get_cache_stats():
    """Get cache statistics"""
    db = get_db_session()
    try:
        product_count = db.query(ShopifyProduct).count()
        metafield_count = db.query(ProductMetafield).count()
        
        return {
            'products': product_count,
            'metafields': metafield_count
        }
    except Exception as e:
        print(f"Error getting cache stats: {e}")
        return {'products': 0, 'metafields': 0}
    finally:
        db.close() 