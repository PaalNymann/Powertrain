#!/usr/bin/env python3
"""
Pre-Computed Compatibility Matrix System
Fast product search using pre-computed vehicle-product compatibility
"""

import time
import os
import json
import psycopg2
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import SessionLocal, ProductMetafield, ShopifyProduct
from rapidapi_tecdoc import search_oem_in_tecdoc

# Railway database connection
RAILWAY_DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

Base = declarative_base()

def get_db_connection():
    """Get direct PostgreSQL connection for raw SQL queries"""
    try:
        # Try Railway database first
        database_url = os.getenv('DATABASE_URL', RAILWAY_DATABASE_URL)
        if database_url:
            return psycopg2.connect(database_url)
        else:
            raise Exception("No database URL available")
    except Exception as e:
        print(f"⚠️ Database connection failed: {e}")
        raise

class VehicleProductCompatibility(Base):
    """
    Pre-computed compatibility matrix between vehicles and products
    This table allows instant lookup instead of slow TecDoc API calls
    """
    __tablename__ = 'vehicle_product_compatibility'
    
    # Composite primary key
    vehicle_make = Column(String, primary_key=True)
    vehicle_model = Column(String, primary_key=True) 
    vehicle_year = Column(String, primary_key=True)
    product_id = Column(String, primary_key=True)
    
    # Compatibility data
    is_compatible = Column(Boolean, nullable=False, default=False)
    matched_oem = Column(String)
    manufacturer_name = Column(String)
    
    # Metadata
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for fast lookup
    __table_args__ = (
        Index('idx_vehicle_lookup', 'vehicle_make', 'vehicle_model', 'vehicle_year'),
        Index('idx_product_lookup', 'product_id'),
        Index('idx_compatibility', 'is_compatible'),
    )

def init_compatibility_db():
    """Initialize the compatibility matrix database table"""
    try:
        engine = create_engine(RAILWAY_DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Compatibility matrix table created/verified")
        return engine
    except Exception as e:
        print(f"❌ Error creating compatibility table: {e}")
        raise

def get_all_eligible_products_for_matrix():
    """Get all eligible products for compatibility matrix computation"""
    try:
        engine = create_engine(RAILWAY_DATABASE_URL)
        RailwaySession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = RailwaySession()
        
        print("📦 Getting all eligible products for compatibility matrix...")
        
        products_with_oems = []
        
        # Get all products with correct product_group
        product_group_query = session.query(ProductMetafield).filter(
            ProductMetafield.key == 'product_group',
            ProductMetafield.value.in_(['Drivaksel', 'Mellomaksel'])
        ).all()
        
        print(f"📦 Found {len(product_group_query)} products with correct groups")
        
        for group_metafield in product_group_query:
            product_id = group_metafield.product_id
            
            # Get all metafields for this product
            product_metafields = session.query(ProductMetafield).filter(
                ProductMetafield.product_id == product_id
            ).all()
            
            # Get Shopify product info
            shopify_product = session.query(ShopifyProduct).filter(
                ShopifyProduct.id == product_id
            ).first()
            
            if not shopify_product:
                continue
            
            # Build product data
            product_data = {
                'id': product_id,
                'title': shopify_product.title,
                'handle': shopify_product.handle,
                'sku': shopify_product.sku,
                'price': shopify_product.price,
                'inventory_quantity': shopify_product.inventory_quantity,
                'product_group': group_metafield.value,
                'oem_numbers': [],
                'i_nettbutikk': 'nei'
            }
            
            # Extract metafields
            for metafield in product_metafields:
                if metafield.key == 'Original_nummer' and metafield.value:
                    oem_list = [oem.strip() for oem in metafield.value.split(',') if oem.strip()]
                    product_data['oem_numbers'] = oem_list
                elif metafield.key == 'i_nettbutikk':
                    product_data['i_nettbutikk'] = metafield.value
            
            # Only include products with i_nettbutikk: ja and OEM numbers
            if product_data['i_nettbutikk'] == 'ja' and product_data['oem_numbers']:
                products_with_oems.append(product_data)
        
        session.close()
        print(f"✅ Found {len(products_with_oems)} eligible products for matrix")
        return products_with_oems
        
    except Exception as e:
        print(f"❌ Error getting products for matrix: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_product_vehicle_compatibility(product_data, vehicle_make, vehicle_model, vehicle_year):
    """
    Test if a product is compatible with a specific vehicle
    Returns compatibility result with matched OEM
    """
    oem_numbers = product_data['oem_numbers']
    
    # Test each OEM number for this product
    for oem_number in oem_numbers:
        try:
            # Check TecDoc compatibility
            tecdoc_result = search_oem_in_tecdoc(oem_number)
            
            if tecdoc_result and 'articles' in tecdoc_result:
                articles = tecdoc_result['articles']
                
                for article in articles:
                    # Check brand compatibility
                    manufacturer_name = article.get('manufacturerName', '').upper()
                    
                    # Brand matching logic
                    target_brand = vehicle_make.upper()
                    
                    # Normalize brand names
                    if target_brand == 'VOLKSWAGEN':
                        target_brand = 'VW'
                    elif 'MERCEDES' in target_brand or target_brand == 'MERCEDES-BENZ':
                        target_brand = 'MERCEDES'
                    
                    # Direct brand match
                    brand_match = False
                    if target_brand == manufacturer_name or manufacturer_name == target_brand:
                        brand_match = True
                    elif target_brand in manufacturer_name or manufacturer_name in target_brand:
                        if len(target_brand) >= 3 and len(manufacturer_name) >= 3:
                            brand_match = True
                    
                    # Mercedes-specific matching
                    if 'MERCEDES' in vehicle_make.upper() or vehicle_make.upper() == 'MERCEDES-BENZ':
                        if 'MERCEDES' in manufacturer_name or manufacturer_name == 'MERCEDES-BENZ':
                            brand_match = True
                    
                    if brand_match:
                        return {
                            'compatible': True,
                            'matched_oem': oem_number,
                            'manufacturer': manufacturer_name
                        }
        
        except Exception as e:
            print(f"⚠️ Error testing OEM {oem_number}: {e}")
            continue
    
    return {'compatible': False}

def build_compatibility_matrix(vehicle_types=None):
    """
    Build the complete compatibility matrix
    This is the slow process that runs once/daily
    """
    print("🚀 BUILDING COMPATIBILITY MATRIX...")
    start_time = time.time()
    
    try:
        # Initialize database
        engine = init_compatibility_db()
        MatrixSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = MatrixSession()
        
        # Get all eligible products
        all_products = get_all_eligible_products_for_matrix()
        if not all_products:
            print("❌ No products found for matrix")
            return
        
        # Define vehicle types to test (start with common ones)
        if vehicle_types is None:
            vehicle_types = [
                # Mercedes vehicles (for testing MA01002)
                ('MERCEDES-BENZ', 'GLK 220 CDI 4MATIC', '2010'),
                ('MERCEDES-BENZ', 'C 220 CDI', '2015'),
                ('MERCEDES-BENZ', 'E 220 CDI', '2014'),
                ('MERCEDES-BENZ', 'VITO', '2016'),
                ('MERCEDES-BENZ', 'SPRINTER', '2018'),
                
                # Other common brands
                ('VOLKSWAGEN', 'GOLF', '2015'),
                ('VOLKSWAGEN', 'PASSAT', '2016'),
                ('AUDI', 'A4', '2015'),
                ('BMW', '320D', '2014'),
                ('VOLVO', 'XC60', '2016'),
                ('FORD', 'FOCUS', '2015'),
            ]
        
        print(f"🔍 Testing {len(all_products)} products against {len(vehicle_types)} vehicle types...")
        
        total_tests = len(all_products) * len(vehicle_types)
        completed_tests = 0
        compatible_found = 0
        
        # Clear existing data for these vehicle types
        for vehicle_make, vehicle_model, vehicle_year in vehicle_types:
            session.query(VehicleProductCompatibility).filter(
                VehicleProductCompatibility.vehicle_make == vehicle_make,
                VehicleProductCompatibility.vehicle_model == vehicle_model,
                VehicleProductCompatibility.vehicle_year == vehicle_year
            ).delete()
        
        session.commit()
        print("🗑️ Cleared existing compatibility data")
        
        # Test each product against each vehicle type
        for vehicle_make, vehicle_model, vehicle_year in vehicle_types:
            print(f"\n🚗 Testing against: {vehicle_make} {vehicle_model} {vehicle_year}")
            
            for product_data in all_products:
                completed_tests += 1
                
                if completed_tests % 10 == 0:
                    progress = (completed_tests / total_tests) * 100
                    print(f"📊 Progress: {completed_tests}/{total_tests} ({progress:.1f}%)")
                
                # Test compatibility
                compatibility_result = test_product_vehicle_compatibility(
                    product_data, vehicle_make, vehicle_model, vehicle_year
                )
                
                # Store result in database
                compatibility_entry = VehicleProductCompatibility(
                    vehicle_make=vehicle_make,
                    vehicle_model=vehicle_model,
                    vehicle_year=vehicle_year,
                    product_id=product_data['id'],
                    is_compatible=compatibility_result['compatible'],
                    matched_oem=compatibility_result.get('matched_oem'),
                    manufacturer_name=compatibility_result.get('manufacturer'),
                    computed_at=datetime.utcnow()
                )
                
                session.add(compatibility_entry)
                
                if compatibility_result['compatible']:
                    compatible_found += 1
                    print(f"✅ {product_data['id']} compatible with {vehicle_make} {vehicle_model}")
        
        # Commit all results
        session.commit()
        session.close()
        
        total_time = time.time() - start_time
        print(f"\n🎯 COMPATIBILITY MATRIX COMPLETED!")
        print(f"⏱️ Total time: {total_time:.2f} seconds")
        print(f"📊 Tests completed: {completed_tests}")
        print(f"✅ Compatible combinations found: {compatible_found}")
        print(f"🚀 Matrix ready for fast lookups!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error building compatibility matrix: {e}")
        import traceback
        traceback.print_exc()
        return False

def fast_compatibility_lookup(make, model, year):
    """
    Fast lookup of compatible products from pre-computed matrix
    Returns list of compatible products or empty list if not found
    """
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Normalize vehicle info for consistent lookup
        vehicle_key = f"{make.upper()} {model.upper()} {year}"
        
        print(f"🔍 FAST LOOKUP: {vehicle_key}")
        
        # Query compatibility matrix
        cursor.execute("""
            SELECT product_data 
            FROM compatibility_matrix 
            WHERE vehicle_key = %s
        """, (vehicle_key,))
        
        results = cursor.fetchall()
        
        if results:
            # Combine all compatible products from all matching rows
            all_products = []
            for row in results:
                product_data = json.loads(row[0])
                all_products.append(product_data)
            
            print(f"⚡ Found {len(all_products)} compatible products in matrix")
            return all_products
        else:
            print(f"📭 No compatibility data found for {vehicle_key}")
            return []
            
    except Exception as e:
        print(f"❌ Error in fast lookup: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def cache_compatibility_result(make, model, year, compatible_products):
    """
    Cache compatibility results for future fast lookup
    """
    try:
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Normalize vehicle info for consistent storage
        vehicle_key = f"{make.upper()} {model.upper()} {year}"
        
        print(f"💾 CACHING: {len(compatible_products)} products for {vehicle_key}")
        
        # Store each product as a separate row for consistency with existing matrix
        for product in compatible_products:
            product_json = json.dumps(product)
            
            # Insert or update (upsert) the compatibility data
            cursor.execute("""
                INSERT INTO compatibility_matrix (vehicle_key, product_data, created_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (vehicle_key, product_data) 
                DO UPDATE SET created_at = NOW()
            """, (vehicle_key, product_json))
        
        conn.commit()
        print(f"✅ Cached {len(compatible_products)} products for {vehicle_key}")
        
    except Exception as e:
        print(f"❌ Error caching compatibility result: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'conn' in locals():
            conn.close()

def get_oems_for_vehicle_from_cache(vehicle_make, vehicle_model, vehicle_year):
    """
    Get all OEM numbers for a specific vehicle from the compatibility matrix cache
    Returns list of OEM numbers that are compatible with this vehicle
    """
    try:
        engine = create_engine(RAILWAY_DATABASE_URL)
        MatrixSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = MatrixSession()
        
        print(f"🔍 CACHE OEM LOOKUP: {vehicle_make} {vehicle_model} {vehicle_year}")
        
        # First try exact match
        compatible_entries = session.query(VehicleProductCompatibility.matched_oem).filter(
            VehicleProductCompatibility.vehicle_make == vehicle_make,
            VehicleProductCompatibility.vehicle_model == vehicle_model,
            VehicleProductCompatibility.vehicle_year == vehicle_year,
            VehicleProductCompatibility.is_compatible == True,
            VehicleProductCompatibility.matched_oem.isnot(None)
        ).distinct().all()
        
        # If no exact match, try fuzzy matching
        if not compatible_entries:
            print(f"🔍 No exact match found, trying fuzzy matching...")
            
            # Check what vehicles DO exist in cache
            existing_vehicles = session.query(
                VehicleProductCompatibility.vehicle_make,
                VehicleProductCompatibility.vehicle_model,
                VehicleProductCompatibility.vehicle_year
            ).distinct().limit(20).all()
            
            print(f"🔍 First 20 vehicles in cache:")
            for i, (make, model, year) in enumerate(existing_vehicles, 1):
                print(f"   {i}. {make} {model} {year}")
            
            # Try partial matches
            fuzzy_queries = [
                # Try without year
                session.query(VehicleProductCompatibility.matched_oem).filter(
                    VehicleProductCompatibility.vehicle_make == vehicle_make,
                    VehicleProductCompatibility.vehicle_model == vehicle_model,
                    VehicleProductCompatibility.is_compatible == True,
                    VehicleProductCompatibility.matched_oem.isnot(None)
                ),
                # Try with model contains
                session.query(VehicleProductCompatibility.matched_oem).filter(
                    VehicleProductCompatibility.vehicle_make == vehicle_make,
                    VehicleProductCompatibility.vehicle_model.contains(vehicle_model.split()[0]),
                    VehicleProductCompatibility.vehicle_year == vehicle_year,
                    VehicleProductCompatibility.is_compatible == True,
                    VehicleProductCompatibility.matched_oem.isnot(None)
                )
            ]
            
            for i, query in enumerate(fuzzy_queries, 1):
                try:
                    fuzzy_entries = query.distinct().all()
                    if fuzzy_entries:
                        print(f"✅ Fuzzy match {i} found {len(fuzzy_entries)} entries")
                        compatible_entries = fuzzy_entries
                        break
                except Exception as e:
                    print(f"❌ Fuzzy query {i} failed: {e}")
        
        # Extract OEM numbers from query results
        oem_numbers = [entry.matched_oem for entry in compatible_entries if entry.matched_oem]
        
        session.close()
        
        print(f"✅ CACHE OEM LOOKUP completed with {len(oem_numbers)} OEM numbers")
        if oem_numbers:
            print(f"🔍 First 5 OEMs: {oem_numbers[:5]}")
        else:
            print(f"❌ No OEM numbers found for {vehicle_make} {vehicle_model} {vehicle_year}")
        
        return oem_numbers
        
    except Exception as e:
        print(f"❌ Error in cache OEM lookup: {e}")
        import traceback
        traceback.print_exc()
        return []

def fast_compatibility_lookup(vehicle_make, vehicle_model, vehicle_year):
    """
    FAST: Lookup compatible products from pre-computed matrix
    This should be milliseconds instead of minutes!
    """
    try:
        engine = create_engine(RAILWAY_DATABASE_URL)
        MatrixSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = MatrixSession()
        
        print(f"🔍 FAST LOOKUP: {vehicle_make} {vehicle_model} {vehicle_year}")
        
        # Query pre-computed compatibility
        compatible_entries = session.query(VehicleProductCompatibility).filter(
            VehicleProductCompatibility.vehicle_make == vehicle_make,
            VehicleProductCompatibility.vehicle_model == vehicle_model,
            VehicleProductCompatibility.vehicle_year == vehicle_year,
            VehicleProductCompatibility.is_compatible == True
        ).all()
        
        print(f"⚡ Found {len(compatible_entries)} compatible products in matrix")
        
        # Get full product details
        compatible_products = []
        for entry in compatible_entries:
            # Get product details from Shopify table
            shopify_product = session.query(ShopifyProduct).filter(
                ShopifyProduct.id == entry.product_id
            ).first()
            
            if shopify_product:
                product_dict = {
                    'id': shopify_product.id,
                    'title': shopify_product.title,
                    'handle': shopify_product.handle,
                    'sku': shopify_product.sku,
                    'price': shopify_product.price,
                    'inventory_quantity': shopify_product.inventory_quantity,
                    'matched_oem': entry.matched_oem,
                    'manufacturer': entry.manufacturer_name,
                    'computed_at': entry.computed_at.isoformat() if entry.computed_at else None
                }
                compatible_products.append(product_dict)
        
        session.close()
        
        print(f"✅ FAST LOOKUP completed with {len(compatible_products)} products")
        return compatible_products
        
    except Exception as e:
        print(f"❌ Error in fast lookup: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    # Test the compatibility matrix system
    print("🧪 Testing Compatibility Matrix System...")
    
    # Step 1: Build matrix (slow, one-time process)
    print("\n🔨 Step 1: Building compatibility matrix...")
    success = build_compatibility_matrix()
    
    if success:
        # Step 2: Test fast lookup
        print("\n⚡ Step 2: Testing fast lookup...")
        start_time = time.time()
        
        compatible_products = fast_compatibility_lookup(
            'MERCEDES-BENZ', 'GLK 220 CDI 4MATIC', '2010'
        )
        
        lookup_time = time.time() - start_time
        print(f"⚡ Fast lookup completed in {lookup_time:.3f} seconds")
        
        # Check if MA01002 is found
        ma01002_found = any(p['id'] == 'MA01002' for p in compatible_products)
        print(f"🎯 MA01002 found in matrix: {'✅ YES' if ma01002_found else '❌ NO'}")
        
        if compatible_products:
            print(f"\n📦 Compatible products found:")
            for product in compatible_products:
                print(f"   - {product['id']}: {product['title']}")
    else:
        print("❌ Matrix building failed")
