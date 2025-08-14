#!/usr/bin/env python3
"""
TecDoc Database Synchronization Script

This script fetches canonical TecDoc data (brands, categories, etc.) and updates
the database to enable robust, automated vehicle parts lookup and matching.

Usage:
    python3 tecdoc_database_sync.py
"""

import os
import sys
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# TecDoc API configuration
TECDOC_API_KEY = os.getenv('TECDOC_API_KEY')
TECDOC_BASE_URL = 'https://api.apify.com/v2/acts/making-data-meaningful~tecdoc/run-sync-get-dataset-items'

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')

class TecDocDatabaseSync:
    def __init__(self):
        self.api_key = TECDOC_API_KEY
        self.base_url = TECDOC_BASE_URL
        self.db_url = DATABASE_URL
        self.conn = None
        
        if not self.api_key:
            raise ValueError("TECDOC_API_KEY environment variable is required")
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    def connect_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            print("✅ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            sys.exit(1)
    
    def call_tecdoc_api(self, params):
        """Make API call to TecDoc via Apify"""
        try:
            url = f"{self.base_url}?token={self.api_key}"
            response = requests.post(url, json=params, timeout=60)
            
            if response.status_code not in [200, 201]:
                print(f"❌ TecDoc API error {response.status_code}: {response.text}")
                return None
            
            data = response.json()
            # Extract from array wrapper if needed
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return data
            
        except Exception as e:
            print(f"❌ TecDoc API call failed: {e}")
            return None
    
    def create_tecdoc_tables(self):
        """Create tables for TecDoc reference data"""
        try:
            cursor = self.conn.cursor()
            
            # TecDoc Manufacturers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tecdoc_manufacturers (
                    manufacturer_id INTEGER PRIMARY KEY,
                    brand VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # TecDoc Vehicle Types table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tecdoc_vehicle_types (
                    type_id INTEGER PRIMARY KEY,
                    type_name VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # TecDoc Product Categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tecdoc_product_categories (
                    category_id INTEGER PRIMARY KEY,
                    category_name VARCHAR(255) NOT NULL,
                    parent_category_id INTEGER,
                    level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # TecDoc Countries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tecdoc_countries (
                    country_id INTEGER PRIMARY KEY,
                    country_name VARCHAR(255) NOT NULL,
                    country_code VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # TecDoc Languages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tecdoc_languages (
                    lang_id INTEGER PRIMARY KEY,
                    language_name VARCHAR(255) NOT NULL,
                    language_code VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            print("✅ TecDoc reference tables created/verified")
            
        except Exception as e:
            print(f"❌ Failed to create TecDoc tables: {e}")
            self.conn.rollback()
            raise
    
    def sync_languages(self):
        """Fetch and sync all TecDoc languages"""
        print("🔄 Syncing TecDoc languages...")
        
        data = self.call_tecdoc_api({
            "selectPageType": "get-all-languages"
        })
        
        if not data or 'languages' not in data:
            print("❌ No languages data received from TecDoc")
            return
        
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM tecdoc_languages")
        
        # Insert new data (skip records with null IDs)
        for lang in data['languages']:
            lang_id = lang.get('langId')
            if lang_id is not None:  # Skip records with null IDs
                cursor.execute("""
                    INSERT INTO tecdoc_languages (lang_id, language_name, language_code)
                    VALUES (%s, %s, %s)
                """, (
                    lang_id,
                    lang.get('languageName', ''),
                    lang.get('languageCode', '')
                ))
        
        self.conn.commit()
        print(f"✅ Synced {len(data['languages'])} languages")
    
    def sync_countries(self):
        """Fetch and sync all TecDoc countries"""
        print("🔄 Syncing TecDoc countries...")
        
        data = self.call_tecdoc_api({
            "selectPageType": "get-all-countries"
        })
        
        if not data or 'countries' not in data:
            print("❌ No countries data received from TecDoc")
            return
        
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM tecdoc_countries")
        
        # Insert new data (skip records with null IDs)
        for country in data['countries']:
            country_id = country.get('countryId')
            if country_id is not None:  # Skip records with null IDs
                cursor.execute("""
                    INSERT INTO tecdoc_countries (country_id, country_name, country_code)
                    VALUES (%s, %s, %s)
                """, (
                    country_id,
                    country.get('countryName', ''),
                    country.get('countryCode', '')
                ))
        
        self.conn.commit()
        print(f"✅ Synced {len(data['countries'])} countries")
    
    def sync_vehicle_types(self):
        """Fetch and sync all TecDoc vehicle types"""
        print("🔄 Syncing TecDoc vehicle types...")
        
        data = self.call_tecdoc_api({
            "selectPageType": "get-vehicle-types"
        })
        
        if not data or 'vehicleTypes' not in data:
            print("❌ No vehicle types data received from TecDoc")
            return
        
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM tecdoc_vehicle_types")
        
        # Insert new data (skip records with null IDs)
        for vtype in data['vehicleTypes']:
            type_id = vtype.get('typeId')
            if type_id is not None:  # Skip records with null IDs
                cursor.execute("""
                    INSERT INTO tecdoc_vehicle_types (type_id, type_name)
                    VALUES (%s, %s)
                """, (
                    type_id,
                    vtype.get('typeName', '')
                ))
        
        self.conn.commit()
        print(f"✅ Synced {len(data['vehicleTypes'])} vehicle types")
    
    def sync_manufacturers(self):
        """Fetch and sync all TecDoc manufacturers"""
        print("🔄 Syncing TecDoc manufacturers...")
        
        data = self.call_tecdoc_api({
            "selectPageType": "get-manufacturers-by-type-id-lang-id-country-id",
            "langId": 4,  # English
            "countryId": 62,  # Germany
            "typeId": 1  # Automobile
        })
        
        if not data or 'manufacturers' not in data:
            print("❌ No manufacturers data received from TecDoc")
            return
        
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM tecdoc_manufacturers")
        
        # Insert new data (skip records with null IDs)
        for mfr in data['manufacturers']:
            manufacturer_id = mfr.get('manufacturerId')
            if manufacturer_id is not None:  # Skip records with null IDs
                cursor.execute("""
                    INSERT INTO tecdoc_manufacturers (manufacturer_id, brand)
                    VALUES (%s, %s)
                """, (
                    manufacturer_id,
                    mfr.get('brand', '')
                ))
        
        self.conn.commit()
        print(f"✅ Synced {len(data['manufacturers'])} manufacturers")
    
    def sync_product_categories(self):
        """Fetch and sync TecDoc product categories for major manufacturers"""
        print("🔄 Syncing TecDoc product categories...")
        
        cursor = self.conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM tecdoc_product_categories")
        
        # Get some major manufacturers to fetch categories
        major_manufacturers = [120, 121, 184]  # VOLVO, VW, BMW
        
        all_categories = {}
        
        for mfr_id in major_manufacturers:
            print(f"📡 Fetching categories for manufacturer {mfr_id}...")
            
            # We need a vehicle ID to get categories, so let's get some models first
            models_data = self.call_tecdoc_api({
                "selectPageType": "get-models",
                "langId": 4,
                "countryId": 62,
                "typeId": 1,
                "manufacturerId": mfr_id
            })
            
            if not models_data or 'models' not in models_data or not models_data['models']:
                continue
            
            # Get first model
            first_model = models_data['models'][0]
            model_id = first_model.get('modelId')
            
            if not model_id:
                continue
            
            # Get vehicle engine types for this model
            engines_data = self.call_tecdoc_api({
                "selectPageType": "get-all-vehicle-engine-types",
                "langId": 4,
                "countryId": 62,
                "typeId": 1,
                "manufacturerId": mfr_id,
                "modelId": model_id
            })
            
            if not engines_data or 'vehicles' not in engines_data or not engines_data['vehicles']:
                continue
            
            # Get first vehicle
            first_vehicle = engines_data['vehicles'][0]
            vehicle_id = first_vehicle.get('vehicleId')
            
            if not vehicle_id:
                continue
            
            # Now get categories for this vehicle
            categories_data = self.call_tecdoc_api({
                "selectPageType": "get-categories-v1",
                "langId": 4,
                "countryId": 62,
                "typeId": 1,
                "manufacturerId": mfr_id,
                "vehicleId": vehicle_id
            })
            
            if categories_data and 'categories' in categories_data:
                for cat in categories_data['categories']:
                    cat_id = cat.get('categoryId')
                    if cat_id and cat_id not in all_categories:
                        all_categories[cat_id] = cat
        
        # Insert unique categories (skip records with null IDs)
        for cat_id, cat_data in all_categories.items():
            if cat_id is not None:  # Skip records with null IDs
                cursor.execute("""
                    INSERT INTO tecdoc_product_categories (category_id, category_name, level)
                    VALUES (%s, %s, %s)
                """, (
                    cat_id,
                    cat_data.get('categoryName', ''),
                    1
                ))
        
        self.conn.commit()
        print(f"✅ Synced {len(all_categories)} product categories")
    
    def create_lookup_functions(self):
        """Create database functions for TecDoc lookups"""
        try:
            cursor = self.conn.cursor()
            
            # Function to find manufacturer ID by brand name
            cursor.execute("""
                CREATE OR REPLACE FUNCTION find_tecdoc_manufacturer(brand_name TEXT)
                RETURNS INTEGER AS $$
                DECLARE
                    result INTEGER;
                BEGIN
                    SELECT manufacturer_id INTO result
                    FROM tecdoc_manufacturers
                    WHERE UPPER(brand) = UPPER(brand_name)
                    LIMIT 1;
                    
                    RETURN result;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            # Function to find category ID by category name
            cursor.execute("""
                CREATE OR REPLACE FUNCTION find_tecdoc_category(category_name TEXT)
                RETURNS INTEGER AS $$
                DECLARE
                    result INTEGER;
                BEGIN
                    SELECT category_id INTO result
                    FROM tecdoc_product_categories
                    WHERE UPPER(category_name) LIKE '%' || UPPER(category_name) || '%'
                    LIMIT 1;
                    
                    RETURN result;
                END;
                $$ LANGUAGE plpgsql;
            """)
            
            self.conn.commit()
            print("✅ Created TecDoc lookup functions")
            
        except Exception as e:
            print(f"❌ Failed to create lookup functions: {e}")
            self.conn.rollback()
            raise
    
    def run_full_sync(self):
        """Run complete TecDoc database synchronization"""
        print("🚀 Starting TecDoc database synchronization...")
        print(f"📅 Started at: {datetime.now()}")
        
        try:
            self.connect_database()
            self.create_tecdoc_tables()
            
            # Sync reference data
            self.sync_languages()
            self.sync_countries()
            self.sync_vehicle_types()
            self.sync_manufacturers()
            self.sync_product_categories()
            
            # Create lookup functions
            self.create_lookup_functions()
            
            print("✅ TecDoc database synchronization completed successfully!")
            print(f"📅 Completed at: {datetime.now()}")
            
        except Exception as e:
            print(f"❌ Synchronization failed: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()

def main():
    """Main function"""
    try:
        sync = TecDocDatabaseSync()
        sync.run_full_sync()
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
