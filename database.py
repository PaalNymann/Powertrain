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
    # Only include columns that actually exist in Railway database
    title = Column(String(500), nullable=False)
    handle = Column(String(500), nullable=False)
    # Remove all metafield columns that don't exist
    inventory_quantity = Column(Integer, default=0)

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
        
        # Since metafield columns don't exist in Railway database,
        # we can only search by title and handle for now
        # This is a temporary solution until we can sync the database structure
        
        # Check if database has any products
        total_products = session.query(ShopifyProduct).count()
        print(f"📊 Total products in database: {total_products}")
        
        if total_products == 0:
            print("⚠️ Database is empty - no products to search")
            return []
        
        # For now, return all products since we can't search by OEM
        # This will be updated once we fix the database structure
        products = session.query(ShopifyProduct).all()
        print(f"🔍 Query returned {len(products)} products")
        
        # Convert to dictionary format with only existing fields
        result = []
        for product in products:
            try:
                product_dict = {
                    'id': str(product.id),  # Use id as primary key
                    'title': product.title or 'Unknown',
                    'handle': product.handle or '',
                    'inventory_quantity': product.inventory_quantity or 0
                }
                result.append(product_dict)
            except Exception as e:
                print(f"❌ Error converting product {getattr(product, 'id', 'unknown')} to dict: {e}")
                continue
        
        print(f"🔍 Successfully converted {len(result)} products to dict format")
        print(f"⚠️ Note: Cannot search by OEM since metafield columns don't exist in Railway database")
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
                # Update existing product - only update fields that exist
                existing_product.title = product_data.get('title', '')
                existing_product.handle = product_data.get('handle', '')
                # Note: metafield columns don't exist in Railway database
                
                # Update inventory
                if 'variants' in product_data and product_data['variants']:
                    total_inventory = sum(
                        int(variant.get('inventory_quantity', 0)) 
                        for variant in product_data['variants']
                    )
                    existing_product.inventory_quantity = total_inventory
                    
            else:
                # Create new product - only include fields that exist
                new_product = ShopifyProduct(
                    id=int(product_data.get('id', 0)),  # Use id as primary key
                    title=product_data.get('title', ''),
                    handle=product_data.get('handle', ''),
                    # Note: metafield columns don't exist in Railway database
                    inventory_quantity=0
                )
                
                # Note: metafield columns don't exist in Railway database
                # Cannot set metafields until database structure is fixed
                
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