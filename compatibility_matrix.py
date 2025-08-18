#!/usr/bin/env python3
"""
Pre-Computed Compatibility Matrix System
Fast product search using pre-computed vehicle-product compatibility
"""

import time
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from database import SessionLocal, ProductMetafield, ShopifyProduct
from rapidapi_tecdoc import search_oem_in_tecdoc

# Railway database connection
RAILWAY_DATABASE_URL = 'postgresql://postgres:pmTNRdLNPAwZTYvtBFsqvfmjUOoNEuqM@shinkansen.proxy.rlwy.net:13074/railway'

Base = declarative_base()

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
