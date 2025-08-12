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
    # Remove product_id field since it doesn't exist in Railway database
    title = Column(String(500), nullable=False)
    handle = Column(String(500), nullable=False)
    vendor = Column(String(200))
    product_type = Column(String(200))
    tags = Column(Text)
    # Metafields som faktisk finnes i databasen
    oem_metafield = Column(Text)
    original_nummer_metafield = Column(Text)
    number_metafield = Column(Text)
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

def search_products_by_oem(oem_number, include_number=False):
    """Search for products by OEM number"""
    if not oem_number:
        print("❌ No OEM number provided for search")
        return []
    
    session = SessionLocal()
    try:
        print(f"🔍 Searching database for OEM: {oem_number}")
        
        # Clean and normalize the OEM number
        clean_oem = oem_number.strip().upper().replace('-', '').replace(' ', '')
        
        # Search in OEM metafield
        oem_condition = or_(
            ShopifyProduct.oem_metafield.like(f'%{clean_oem}%'),
            ShopifyProduct.oem_metafield.like(f'%{oem_number}%'),
            func.upper(ShopifyProduct.oem_metafield).like(f'%{clean_oem}%')
        )
        
        # Search in original nummer metafield
        original_condition = or_(
            ShopifyProduct.original_nummer_metafield.like(f'%{clean_oem}%'),
            ShopifyProduct.original_nummer_metafield.like(f'%{oem_number}%'),
            func.upper(ShopifyProduct.original_nummer_metafield).like(f'%{clean_oem}%')
        )
        
        # Search in number metafield (only if include_number is True for free-text search)
        if include_number:
            number_condition = or_(
                ShopifyProduct.number_metafield.like(f'%{clean_oem}%'),
                ShopifyProduct.number_metafield.like(f'%{oem_number}%'),
                func.upper(ShopifyProduct.number_metafield).like(f'%{clean_oem}%')
            )
            query = session.query(ShopifyProduct).filter(
                or_(oem_condition, original_condition, number_condition)
            )
        else:
            query = session.query(ShopifyProduct).filter(
                or_(oem_condition, original_condition)
            )
        
        # Check if database has any products
        total_products = session.query(ShopifyProduct).count()
        print(f"📊 Total products in database: {total_products}")
        
        if total_products == 0:
            print("⚠️ Database is empty - no products to search")
            return []
        
        products = query.all()
        print(f"🔍 Query returned {len(products)} products")
        
        # Convert to dictionary format
        result = []
        for product in products:
            try:
                product_dict = {
                    'id': str(product.id),  # Use id instead of product_id
                    'title': product.title or 'Unknown',
                    'handle': product.handle or '',
                    'vendor': product.vendor or '',
                    'product_type': product.product_type or '',
                    'tags': product.tags or '',
                    'oem': product.oem_metafield or '',
                    'original_nummer': product.original_nummer_metafield or '',
                    'number': product.number_metafield or '',
                    'inventory_quantity': product.inventory_quantity or 0,
                    'price': product.price or '',
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                    'updated_at': product.updated_at.isoformat() if product.updated_at else None
                }
                result.append(product_dict)
            except Exception as e:
                print(f"❌ Error converting product {getattr(product, 'id', 'unknown')} to dict: {e}")
                continue
        
        print(f"🔍 Successfully converted {len(result)} products to dict format")
        return result
        
    except Exception as e:
        print(f"❌ Error searching database: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()

def update_shopify_cache(products_data):
    """Update Shopify product cache in database"""
    session = SessionLocal()
    try:
        for product_data in products_data:
            # Check if product exists by id (not product_id)
            existing_product = session.query(ShopifyProduct).filter(
                ShopifyProduct.id == int(product_data['id'])
            ).first()
            
            if existing_product:
                # Update existing product - use id directly
                existing_product.title = product_data.get('title', '')
                existing_product.handle = product_data.get('handle', '')
                existing_product.vendor = product_data.get('vendor', '')
                existing_product.product_type = product_data.get('product_type', '')
                existing_product.tags = product_data.get('tags', '')
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
                # Create new product - use id directly
                new_product = ShopifyProduct(
                    id=int(product_data.get('id', 0)),  # Use id as primary key
                    title=product_data.get('title', ''),
                    handle=product_data.get('handle', ''),
                    vendor=product_data.get('vendor', ''),
                    product_type=product_data.get('product_type', ''),
                    tags=product_data.get('tags', ''),
                    price=product_data.get('variants', [{}])[0].get('price', '') if product_data.get('variants') else '',
                    inventory_quantity=0
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

def update_product_oem_metafields(product_id, oem_numbers):
    """Update product metafields with OEM numbers from TecDoc"""
    session = SessionLocal()
    try:
        # Find the product by id (not product_id)
        product = session.query(ShopifyProduct).filter(
            ShopifyProduct.id == int(product_id)
        ).first()
        
        if not product:
            print(f"❌ Product not found: {product_id}")
            return False
        
        # Update OEM metafield with the first OEM number found
        if oem_numbers and len(oem_numbers) > 0:
            product.oem_metafield = oem_numbers[0]
            print(f"✅ Updated OEM metafield for product {product_id}: {oem_numbers[0]}")
        
        session.commit()
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
        
        return [product.id for product in products]  # Return id instead of product_id
        
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