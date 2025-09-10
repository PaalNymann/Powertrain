import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, or_, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
from typing import List

load_dotenv()
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

def get_cached_oems_for_article(article_id: str) -> List[str]:
    """Return cached OEMs for a TecDoc article_id, or [] if not cached."""
    session = SessionLocal()
    try:
        row = session.query(TecdocArticleOem).filter(TecdocArticleOem.article_id == str(article_id)).first()
        if not row or not row.oem_numbers:
            return []
        try:
            data = json.loads(row.oem_numbers)
            if isinstance(data, list):
                return [str(x).strip() for x in data if x]
            return []
        except Exception:
            return []
    finally:
        session.close()

def upsert_article_oems(
    article_id: str,
    product_group_id: int,
    supplier_id: int,
    supplier_name: str,
    article_product_name: str,
    oem_numbers: List[str],
):
    """Insert or update cached OEMs for an articleId."""
    session = SessionLocal()
    try:
        now = datetime.utcnow()
        payload = json.dumps(sorted({str(x).strip() for x in (oem_numbers or []) if x}))
        row = session.query(TecdocArticleOem).filter(TecdocArticleOem.article_id == str(article_id)).first()
        if row:
            row.product_group_id = product_group_id
            row.supplier_id = supplier_id
            row.supplier_name = supplier_name
            row.article_product_name = article_product_name
            row.oem_numbers = payload
            row.updated_at = now
        else:
            row = TecdocArticleOem(
                article_id=str(article_id),
                product_group_id=product_group_id,
                supplier_id=supplier_id,
                supplier_name=supplier_name,
                article_product_name=article_product_name,
                oem_numbers=payload,
                updated_at=now,
            )
            session.add(row)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"⚠️ upsert_article_oems failed for {article_id}: {e}")
    finally:
        session.close()

# TecDoc article OEM cache for performance (stores OEMs per articleId)
class TecdocArticleOem(Base):
    __tablename__ = 'tecdoc_article_oems'
    # Store article_id as string to be safe across providers
    article_id = Column(String, primary_key=True)
    product_group_id = Column(Integer)
    supplier_id = Column(Integer)
    supplier_name = Column(String)
    article_product_name = Column(String)
    # JSON-encoded list of OEM strings
    oem_numbers = Column(Text)
    updated_at = Column(DateTime)

def get_database_url():
    """Get database URL from environment or use SQLite for local development"""
    database_url = os.getenv('DATABASE_URL')
    print(f"🔧 DATABASE_URL from environment: {database_url}")
    
    if database_url and database_url.startswith('postgresql://'):
        print(f"✅ Using PostgreSQL database, switching to psycopg driver")
        return database_url.replace('postgresql://', 'postgresql+psycopg://')
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
        # Search in product_metafields for OEM numbers - SIMPLIFIED AND FIXED
        # User confirmed OEMs ARE in database, search logic was wrong
        
        print(f"🔍 Searching for OEM: {oem_number}")
        
        # Simple search in original_nummer field (case-insensitive)
        metafields_query = session.query(ProductMetafield).filter(
            ProductMetafield.key == 'original_nummer'
        ).filter(
            ProductMetafield.value.ilike(f'%{oem_number}%')
        ).filter(
            ProductMetafield.value != 'N/A'
        )
        
        print(f"🔍 SQL Query: {str(metafields_query)}")
        
        # Get results
        metafield_results = metafields_query.all()
        print(f"🔍 Found {len(metafield_results)} metafield matches")
        
        # Show what we found
        for result in metafield_results[:3]:
            print(f"   Product {result.product_id}: {result.value}")
        
        # If no matches with original format, try without hyphens
        if not metafield_results and '-' in oem_number:
            oem_no_hyphen = oem_number.replace('-', '')
            print(f"🔍 Trying without hyphen: {oem_no_hyphen}")
            
            metafields_query = session.query(ProductMetafield).filter(
                ProductMetafield.key == 'original_nummer'
            ).filter(
                ProductMetafield.value.ilike(f'%{oem_no_hyphen}%')
            ).filter(
                ProductMetafield.value != 'N/A'
            )
            
            metafield_results = metafields_query.all()
            print(f"🔍 Found {len(metafield_results)} matches without hyphen")
        
        
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
            return products  # Return product objects directly, not dicts
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

def search_products_by_oems(oem_numbers: List[str]):
    """Strict search by a list of OEM numbers against original_nummer metafield only.
    Returns a list of ShopifyProduct rows. No handle/SKU fallback, per requirement.
    """
    session = SessionLocal()
    try:
        if not oem_numbers:
            return []

        # Build OR conditions for ilike against each OEM and a hyphenless variant
        ilike_conditions = []
        for oem in oem_numbers:
            if not oem:
                continue
            oem_str = str(oem).strip()
            if not oem_str:
                continue
            ilike_conditions.append(ProductMetafield.value.ilike(f"%{oem_str}%"))
            if '-' in oem_str:
                ilike_conditions.append(ProductMetafield.value.ilike(f"%{oem_str.replace('-', '')}%"))

        if not ilike_conditions:
            return []

        print(f"🔍 OEM list size for DB search: {len(oem_numbers)} (unique ilike conditions: {len(ilike_conditions)})")

        product_ids_subq = (
            session.query(ProductMetafield.product_id)
            .filter(ProductMetafield.key == 'original_nummer')
            .filter(or_(*ilike_conditions))
            .distinct()
            .subquery()
        )

        products = (
            session.query(ShopifyProduct)
            .filter(ShopifyProduct.id.in_(product_ids_subq))
            .all()
        )

        print(f"✅ Strict OEM search matched {len(products)} products")
        return products
    except Exception as e:
        print(f"❌ Error in search_products_by_oems: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()

def search_products_by_number(number: str):
    """Direct search for customer's own part number (Number field) in metafields.
    No external calls; returns ShopifyProduct rows.
    """
    session = SessionLocal()
    try:
        if not number:
            return []

        print(f"🔎 Searching by customer Number: {number}")

        number_ids_subq = (
            session.query(ProductMetafield.product_id)
            .filter(func.lower(ProductMetafield.key) == 'number')
            .filter(ProductMetafield.value.ilike(f"%{number}%"))
            .distinct()
            .subquery()
        )

        products = (
            session.query(ShopifyProduct)
            .filter(ShopifyProduct.id.in_(number_ids_subq))
            .all()
        )

        print(f"✅ Number search matched {len(products)} products")
        return products
    except Exception as e:
        print(f"❌ Error in search_products_by_number: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        session.close()

def update_shopify_cache(products_data):
    """Update local database cache with Shopify product data, correctly handling metafields."""
    session = SessionLocal()
    products_updated = 0
    products_created = 0
    metafields_updated = 0
    metafields_created = 0

    try:
        for product_data in products_data:
            product_id_str = str(product_data['id'])

            # Part 1: Update or Create ShopifyProduct
            existing_product = session.query(ShopifyProduct).filter_by(id=product_id_str).first()
            product_fields = {
                'title': product_data.get('title'),
                'handle': product_data.get('handle'),
                'sku': product_data.get('variants')[0].get('sku') if product_data.get('variants') else '',
                'price': product_data.get('variants')[0].get('price') if product_data.get('variants') else '0',
                'inventory_quantity': product_data.get('variants')[0].get('inventory_quantity') if product_data.get('variants') else 0,
                'created_at': datetime.fromisoformat(product_data['created_at'].replace('Z', '+00:00')) if product_data.get('created_at') else None,
                'updated_at': datetime.fromisoformat(product_data['updated_at'].replace('Z', '+00:00')) if product_data.get('updated_at') else None,
            }
            if existing_product:
                for key, value in product_fields.items():
                    setattr(existing_product, key, value)
                products_updated += 1
            else:
                new_product = ShopifyProduct(id=product_id_str, **product_fields)
                session.add(new_product)
                products_created += 1

            # Part 2: Update or Create ProductMetafields
            if 'metafields' in product_data:
                for mf_data in product_data['metafields']:
                    metafield_id_str = str(mf_data['id'])
                    existing_metafield = session.query(ProductMetafield).filter_by(id=metafield_id_str).first()
                    metafield_fields = {
                        'product_id': product_id_str,
                        'namespace': mf_data.get('namespace'),
                        'key': mf_data.get('key'),
                        'value': str(mf_data.get('value')),
                        'created_at': datetime.fromisoformat(mf_data['created_at'].replace('Z', '+00:00')) if mf_data.get('created_at') else None,
                    }
                    if existing_metafield:
                        for key, value in metafield_fields.items():
                            setattr(existing_metafield, key, value)
                        metafields_updated += 1
                    else:
                        new_metafield = ProductMetafield(id=metafield_id_str, **metafield_fields)
                        session.add(new_metafield)
                        metafields_created += 1
        
        session.commit()
        print(f"✅ Cache update complete.")
        print(f"   Products: {products_created} created, {products_updated} updated.")
        print(f"   Metafields: {metafields_created} created, {metafields_updated} updated.")

    except Exception as e:
        session.rollback()
        print(f"❌ Database cache update failed: {e}")
        import traceback
        traceback.print_exc()
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

def get_all_oems_from_db(categories: list) -> list:
    """Gets all unique OEM numbers from the database for products in specific categories."""
    session = SessionLocal()
    try:
        # Find product IDs for the given categories
        product_ids_in_category = session.query(ProductMetafield.product_id)\
            .filter(ProductMetafield.key == 'Produktgruppe')\
            .filter(ProductMetafield.value.in_(categories)).distinct().subquery()

        # Get all OEM number strings for those products
        oem_metafields = session.query(ProductMetafield.value)\
            .filter(ProductMetafield.product_id.in_(product_ids_in_category))\
            .filter(ProductMetafield.key == 'original_nummer')\
            .filter(ProductMetafield.value != '')\
            .filter(ProductMetafield.value != None).all()

        all_oems = set()
        for oem_string, in oem_metafields:
            if oem_string:
                oems = [oem.strip() for oem in oem_string.split(',') if oem.strip()]
                all_oems.update(oems)

        unique_oems = sorted(list(all_oems))
        print(f"📊 Found {len(unique_oems)} unique OEM numbers in the database for categories: {categories}")
        return unique_oems

    except Exception as e:
        print(f"❌ Database OEM extraction failed: {e}")
        return []
    finally:
        session.close()

def debug_get_product_groups():
    """Prints all distinct product_group values from the database for debugging."""
    session = SessionLocal()
    try:
        print("\n--- 🕵️‍♂️ DEBUGGING PRODUCT GROUPS ---")
        groups = session.query(ProductMetafield.value).filter(ProductMetafield.key == 'Produktgruppe').distinct().all()
        
        if not groups:
            print("   -> No 'Produktgruppe' metafields found in the database.")
            return

        print(f"   -> Found {len(groups)} distinct product groups:")
        for group, in groups:
            print(f"      - '{group}'")
        
    except Exception as e:
        print(f"   -> ❌ Error during debug query: {e}")
    finally:
        session.close()

def debug_get_product_groups():
    """Prints all distinct product_group values from the database for debugging."""
    session = SessionLocal()
    try:
        print("\n--- 🕵️‍♂️ DEBUGGING PRODUCT GROUPS ---")
        groups = session.query(ProductMetafield.value).filter(ProductMetafield.key == 'Produktgruppe').distinct().all()
        
        if not groups:
            print("   -> No 'Produktgruppe' metafields found in the database.")
            return

        print(f"   -> Found {len(groups)} distinct product groups:")
        for group, in groups:
            print(f"      - '{group}'")
        
    except Exception as e:
        print(f"   -> ❌ Error during debug query: {e}")
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