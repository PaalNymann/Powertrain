import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, or_, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class ShopifyProduct(Base):
    __tablename__ = 'shopify_products'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    handle = Column(String)
    inventory_quantity = Column(Integer)
    original_nummer_metafield = Column(String)  # Add this column for OEM matching
    
    def __repr__(self):
        return f"<ShopifyProduct(id='{self.id}', title='{self.title}', original_nummer='{self.original_nummer_metafield}')>"

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
    """Search for products by OEM number using the original_nummer metafield"""
    session = SessionLocal()
    try:
        # Search in the original_nummer metafield for exact or partial matches
        query = session.query(ShopifyProduct).filter(
            ShopifyProduct.original_nummer_metafield.contains(oem_number)
        )
        
        products = query.all()
        
        if products:
            print(f"🔍 Found {len(products)} products matching OEM: {oem_number}")
            return [product_to_dict(product) for product in products]
        else:
            print(f"🔍 No products found for OEM: {oem_number}")
            return []
            
    except Exception as e:
        print(f"❌ Error searching database: {e}")
        return []
    finally:
        session.close()

def update_shopify_cache(products_data):
    """Update local database cache with Shopify product data"""
    session = SessionLocal()
    try:
        print(f"🔄 Updating Shopify cache with {len(products_data)} products...")
        
        updated_count = 0
        created_count = 0
        
        for product_data in products_data:
            try:
                # Check if product already exists
                existing_product = session.query(ShopifyProduct).filter(
                    ShopifyProduct.id == str(product_data.get('id'))
                ).first()
                
                if existing_product:
                    # Update existing product
                    existing_product.title = product_data.get('title', '')
                    existing_product.handle = product_data.get('handle', '')
                    existing_product.inventory_quantity = product_data.get('inventory_quantity', 0)
                    
                    # Update original_nummer metafield if available
                    if 'metafields' in product_data:
                        for metafield in product_data['metafields']:
                            if metafield.get('key') == 'original_nummer':
                                existing_product.original_nummer_metafield = metafield.get('value', '')
                                break
                    
                    updated_count += 1
                else:
                    # Create new product
                    new_product = ShopifyProduct(
                        id=str(product_data.get('id')),
                        title=product_data.get('title', ''),
                        handle=product_data.get('handle', ''),
                        inventory_quantity=product_data.get('inventory_quantity', 0),
                        original_nummer_metafield=''  # Initialize empty
                    )
                    
                    # Set original_nummer metafield if available
                    if 'metafields' in product_data:
                        for metafield in product_data['metafields']:
                            if metafield.get('key') == 'original_nummer':
                                new_product.original_nummer_metafield = metafield.get('value', '')
                                break
                    
                    session.add(new_product)
                    created_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing product {product_data.get('id', 'unknown')}: {e}")
                continue
        
        session.commit()
        print(f"✅ Cache update complete: {updated_count} updated, {created_count} created")
        
    except Exception as e:
        print(f"❌ Error updating Shopify cache: {e}")
        session.rollback()
    finally:
        session.close()

def update_product_oem_metafields(product_id, oem_numbers):
    """Update product metafields with OEM numbers from TecDoc"""
    # Since metafield columns don't exist in Railway database,
    # this function cannot work until we fix the database structure
    print(f"⚠️ Cannot update OEM metafields - metafield columns don't exist in Railway database")
    print(f"⚠️ Product ID: {product_id}, OEM numbers: {oem_numbers}")
    return False

def inspect_database_structure():
    """Inspect the actual Railway database structure to see what columns exist"""
    session = SessionLocal()
    try:
        # Get table info from PostgreSQL
        if 'postgresql' in get_database_url():
            # Use raw SQL to inspect table structure
            result = session.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'shopify_products'
                ORDER BY ordinal_position;
            """)
            
            columns = []
            for row in result:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'nullable': row[2]
                })
            
            print("🔍 Railway database structure:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")
            
            return columns
        else:
            print("⚠️ Not a PostgreSQL database, cannot inspect structure")
            return []
            
    except Exception as e:
        print(f"❌ Error inspecting database structure: {e}")
        return []
    finally:
        session.close()

def get_products_without_oem():
    """Get products that don't have OEM metafields set"""
    # Since metafield columns don't exist in Railway database,
    # this function cannot work until we fix the database structure
    print(f"⚠️ Cannot get products without OEM - metafield columns don't exist in Railway database")
    return []

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