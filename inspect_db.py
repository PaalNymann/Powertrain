#!/usr/bin/env python3
import sqlite3
import os

# Connect to the database
db_path = 'powertrain.db'
if not os.path.exists(db_path):
    print(f"Database file {db_path} not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== DATABASE INSPECTION ===\n")

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print(f"Tables in database: {[table[0] for table in tables]}\n")

# Check Shopify products
cursor.execute("SELECT COUNT(*) FROM shopify_products")
product_count = cursor.fetchone()[0]
print(f"Total Shopify products: {product_count}")

# Check metafields
cursor.execute("SELECT COUNT(*) FROM product_metafields")
metafield_count = cursor.fetchone()[0]
print(f"Total metafields: {metafield_count}")

# Check OEM index
cursor.execute("SELECT COUNT(*) FROM oem_index")
oem_count = cursor.fetchone()[0]
print(f"Total OEM index entries: {oem_count}\n")

# Show some sample metafields
print("=== SAMPLE METAFIELDS ===")
cursor.execute("""
    SELECT pm.namespace, pm.key, pm.value, p.title 
    FROM product_metafields pm 
    JOIN shopify_products p ON pm.product_id = p.id 
    WHERE pm.key IN ('original_nummer', 'tirsan_varenummer', 'odm_varenummer', 'ims_varenummer', 'welte_varenummer', 'bakkeren_varenummer')
    LIMIT 10
""")
metafields = cursor.fetchall()
for namespace, key, value, title in metafields:
    print(f"Product: {title[:50]}...")
    print(f"  {namespace}.{key}: {value}")
    print()

# Show some sample OEM index entries
print("=== SAMPLE OEM INDEX ENTRIES ===")
cursor.execute("""
    SELECT oi.oem_number, pm.key, p.title 
    FROM oem_index oi 
    JOIN product_metafields pm ON oi.metafield_id = pm.id 
    JOIN shopify_products p ON oi.product_id = p.id 
    LIMIT 10
""")
oem_entries = cursor.fetchall()
for oem_number, metafield_key, title in oem_entries:
    print(f"OEM: {oem_number} | Field: {metafield_key} | Product: {title[:50]}...")

conn.close() 