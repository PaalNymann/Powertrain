import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, or_, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class ProductMetafield(Base):
    __tablename__ = 'product_metafields'
    
    id = Column(String, primary_key=True)
    product_id = Column(String)
    namespace = Column(String)
    key = Column(String)
    value = Column(String)
    created_at = Column(DateTime)
    
    def __repr__(self):
        return f"<ProductMetafield(product_id='{self.product_id}', key='{self.key}', value='{self.value}')>"

class ShopifyProduct(Base):
    __tablename__ = 'shopify_products'
    
    id = Column(String, primary_key=True)
    title = Column(String)
    handle = Column(String)
    sku = Column(String)
    price = Column(String)  # Using String to match Railway's double precision
    inventory_quantity = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    def __repr__(self):
        return f"<ShopifyProduct(id='{self.id}', title='{self.title}', handle='{self.handle}')>"

def get_database_url():
    """Get database URL from environment or use SQLite for local development"""
    database_url = os.getenv('DATABASE_URL')
    print(f"🔧 DATABASE_URL from environment: {database_url}")
    
    if database_url and database_url.startswith('postgresql://'):
        print(f"✅ Using PostgreSQL database")
        return database_url
    elif database_url and database_url.startswith('sqlite://'):
        print(f"✅ Using SQLite database")
        return database_url
    else:
        print(f"⚠️ Falling back to local SQLite database")
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

def product_to_dict(product):
    """Convert ShopifyProduct object to dictionary"""
    return {
        'id': product.id,
        'title': product.title,
        'handle': product.handle,
        'sku': product.sku,
        'price': product.price,
        'inventory_quantity': product.inventory_quantity,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None
    }

def search_products_by_oem(oem_number, include_number=False):
    """Search for products by OEM number in product_metafields and match with shopify_products"""
    session = SessionLocal()
    try:
        # Search in product_metafields for OEM numbers
        metafields_query = session.query(ProductMetafield).filter(
            or_(
                (ProductMetafield.key == 'Original_nummer') & (ProductMetafield.value.contains(oem_number)),
                (ProductMetafield.key == 'number') & (ProductMetafield.value.contains(oem_number))
            )
        ).filter(
            ProductMetafield.value != 'N/A'
        )
        
        # Get matching product IDs from metafields
        product_ids = set()
        for row in metafields_query.all():
            product_ids.add(row.product_id)
        
        # Also search directly in shopify_products handle field as backup
        direct_products = session.query(ShopifyProduct).filter(
            or_(
                ShopifyProduct.handle.contains(oem_number),
                ShopifyProduct.sku.contains(oem_number)
            )
        ).all()
        
        # Add direct product matches
        for product in direct_products:
            product_ids.add(product.id)
        
        if not product_ids:
            print(f"🔍 No products found for OEM: {oem_number}")
            return []
        
        print(f"🔍 Found {len(product_ids)} product IDs matching OEM: {oem_number}")
        
        # Get the actual products from shopify_products table
        products = session.query(ShopifyProduct).filter(
            ShopifyProduct.id.in_(product_ids)
        ).all()
        
        if products:
            print(f"✅ Returning {len(products)} complete products")
            return [product_to_dict(product) for product in products]
        else:
            print(f"🔍 No complete products found for OEM: {oem_number}")
            return []
            
    except Exception as e:
        print(f"❌ Error searching database: {e}")
        import traceback
        traceback.print_exc()
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
            print(f"🔍 Inspecting PostgreSQL database: {get_database_url()[:50]}...")
            
            # First, check what tables exist
            tables_result = session.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in tables_result]
            print(f"📋 Available tables: {tables}")
            
            # Check if shopify_products table exists
            if 'shopify_products' in tables:
                # Get column info for shopify_products
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
                
                print("🔍 shopify_products table structure:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']} (nullable: {col['nullable']})")
                
                # Also check row count
                count_result = session.execute("SELECT COUNT(*) FROM shopify_products;")
                row_count = count_result.scalar()
                print(f"📊 Total rows in shopify_products: {row_count}")
                
                # Sample a few rows to see the data
                if row_count > 0:
                    sample_result = session.execute("SELECT * FROM shopify_products LIMIT 3;")
                    print("📝 Sample data:")
                    for row in sample_result:
                        print(f"  Row: {dict(row._mapping)}")
                
                return columns
            else:
                print("❌ shopify_products table does not exist!")
                return []
            
        else:
            print("⚠️ Not a PostgreSQL database, cannot inspect structure")
            return []
            
    except Exception as e:
        print(f"❌ Error inspecting database structure: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()

def get_products_without_oem():
    """Get products that don't have OEM metafields set"""
    # Since metafield columns don't exist in Railway database,
    # this function cannot work until we fix the database structure
    print(f"⚠️ Cannot get products without OEM - metafield columns don't exist in Railway database")
    return []

def get_all_unique_oem_numbers():
    """
    Get all unique OEM numbers from the database for hybrid matching
    Returns a list of individual OEM numbers (not comma-separated strings)
    """
    try:
        import psycopg2
        import os
        
        # Use direct PostgreSQL connection for raw SQL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found")
            return []
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Get all Original_nummer values that are not empty
        cursor.execute("SELECT DISTINCT value FROM product_metafields WHERE key = 'Original_nummer' AND value != ''")
        oem_strings = [row[0] for row in cursor.fetchall()]
        
        # Split comma-separated OEM strings into individual OEMs
        all_oems = set()
        for oem_string in oem_strings:
            if oem_string:
                # Split by comma and clean up each OEM
                oems = [oem.strip() for oem in oem_string.split(',') if oem.strip()]
                all_oems.update(oems)
        
        # Convert to sorted list for consistency
        unique_oems = sorted(list(all_oems))
        
        print(f"📊 DATABASE OEM EXTRACTION:")
        print(f"   OEM strings found: {len(oem_strings)}")
        print(f"   Unique OEM numbers: {len(unique_oems)}")
        print(f"   First 10 OEMs: {unique_oems[:10]}")
        
        cursor.close()
        conn.close()
        
        return unique_oems
        
    except Exception as e:
        print(f"❌ Database OEM extraction failed: {e}")
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