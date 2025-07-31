#!/usr/bin/env python3
"""
Clean API tokens from files before deployment
"""

import re
import os

def clean_file(file_path, patterns):
    """Clean sensitive data from a file"""
    try:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            return
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Cleaned {file_path}")
        else:
            print(f"ℹ️  No changes needed for {file_path}")
            
    except Exception as e:
        print(f"❌ Error cleaning {file_path}: {e}")

def main():
    # Patterns to clean (regex pattern, replacement)
    patterns = [
        # Shopify tokens
        (r'shpat_[a-zA-Z0-9]+', 'your_shopify_token_here'),
        # Rackbeat tokens
        (r'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9\.[a-zA-Z0-9\-_\.]+', 'your_rackbeat_token_here'),
        # SVV API keys
        (r'936b8481-8c71-49ab-832d-10944c9b6728', 'your_svv_api_key_here'),
    ]
    
    # Files to clean - all files that might contain secrets
    files_to_clean = [
        'RAILWAY_DEPLOYMENT.md',
        'README.md', 
        'SYSTEM_OVERVIEW.md',
        'simple_sync.py',
        'update_existing_products.py',
        '.env',
        'DEVELOPMENT_LOG.md',
        'test_metafields.py',
        'test_single_product.py'
    ]
    
    print("🧹 Cleaning API tokens from files...")
    
    for file_path in files_to_clean:
        clean_file(file_path, patterns)
    
    print("✅ All files cleaned!")

if __name__ == "__main__":
    main() 