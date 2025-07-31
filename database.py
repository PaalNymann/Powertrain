import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Database configuration for Railway
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create engine
engine = create_engine(DATABASE_URL or 'sqlite:///powertrain.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class ShopifyProduct(Base):
    __tablename__ = "shopify_products"
    
    id = Column(Integer, primary_key=True, index=True)
    shopify_id = Column(String, unique=True, index=True)
    title = Column(String)
    handle = Column(String)
    sku = Column(String)
    price = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    metafields = relationship("ProductMetafield", back_populates="product")
    oem_entries = relationship("OemIndex", back_populates="product")

class ProductMetafield(Base):
    __tablename__ = "product_metafields"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("shopify_products.id"))
    namespace = Column(String)
    key = Column(String)
    value = Column(Text)
    
    product = relationship("ShopifyProduct", back_populates="metafields")
    oem_entries = relationship("OemIndex", back_populates="metafield")

class OemIndex(Base):
    __tablename__ = "oem_index"
    
    id = Column(Integer, primary_key=True, index=True)
    oem_number = Column(String, index=True)
    product_id = Column(Integer, ForeignKey("shopify_products.id"))
    metafield_id = Column(Integer, ForeignKey("product_metafields.id"))
    
    product = relationship("ShopifyProduct", back_populates="oem_entries")
    metafield = relationship("ProductMetafield", back_populates="oem_entries")

# Database functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def search_products_by_oem(oem_number):
    """Fast database search for products by part number in correct metafields"""
    db = SessionLocal()
    try:
        # Remove spaces from OEM number to match database format
        clean_oem = oem_number.replace(" ", "")
        
        # Search directly in metafields - ONLY the specified fields, NOT the "number" field
        results = db.query(ProductMetafield).filter(
            ProductMetafield.key.in_(['original_nummer', 'tirsan_varenummer', 'odm_varenummer', 'ims_varenummer', 'welte_varenummer', 'bakkeren_varenummer']),
            ProductMetafield.value.ilike(f"%{clean_oem}%")
        ).all()
        
        products = []
        for result in results:
            product = result.product
            products.append({
                "id": product.shopify_id,
                "title": product.title,
                "handle": product.handle,
                "sku": product.sku,
                "price": product.price,
                "matching_part_number": oem_number,
                "metafield_key": result.key,
                "metafield_value": result.value
            })
        
        return products
    finally:
        db.close()

def update_shopify_cache(products_data):
    """Update Shopify products cache"""
    db = SessionLocal()
    try:
        # Clear existing data
        db.query(OemIndex).delete()
        db.query(ProductMetafield).delete()
        db.query(ShopifyProduct).delete()
        
        for product_data in products_data:
            # Create product
            product = ShopifyProduct(
                shopify_id=str(product_data.get('id')),
                title=product_data.get('title', ''),
                handle=product_data.get('handle', ''),
                sku=product_data.get('variants', [{}])[0].get('sku', ''),
                price=float(product_data.get('variants', [{}])[0].get('price', 0)),
                updated_at=datetime.utcnow()
            )
            db.add(product)
            db.flush()  # Get the product ID
            
            # Add metafields
            for metafield_data in product_data.get('metafields', []):
                metafield = ProductMetafield(
                    product_id=product.id,
                    namespace=metafield_data.get('namespace', ''),
                    key=metafield_data.get('key', ''),
                    value=metafield_data.get('value', '')
                )
                db.add(metafield)
                db.flush()
                
                # Index part numbers in metafield value - ONLY for the specified metafields
                # DO NOT index the "number" field as it contains fictive internal numbers
                if metafield.key in ['original_nummer', 'tirsan_varenummer', 'odm_varenummer', 'ims_varenummer', 'welte_varenummer', 'bakkeren_varenummer']:
                    value = metafield.value.upper()
                    # Extract part numbers (alphanumeric, 6-15 chars)
                    import re
                    part_matches = re.findall(r'\b[A-Z0-9]{6,15}\b', value)
                    
                    for part in part_matches:
                        oem_entry = OemIndex(
                            oem_number=part,
                            product_id=product.id,
                            metafield_id=metafield.id
                        )
                        db.add(oem_entry)
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        print(f"Database update error: {e}")
        return False
    finally:
        db.close()

def get_cache_stats():
    """Get database cache statistics"""
    db = SessionLocal()
    try:
        product_count = db.query(ShopifyProduct).count()
        metafield_count = db.query(ProductMetafield).count()
        oem_count = db.query(OemIndex).count()
        
        return {
            "products": product_count,
            "metafields": metafield_count,
            "oem_entries": oem_count
        }
    finally:
        db.close() 