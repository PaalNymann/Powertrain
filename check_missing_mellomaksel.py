#!/usr/bin/env python3
"""
Check how many Mellomaksel parts are missing from Shopify sync
This is CRITICAL - MA18002 should be synced but isn't!
"""

import requests
import json

def check_rackbeat_mellomaksel():
    """Check Rackbeat for Mellomaksel parts that should be synced"""
    
    print('🔍 CHECKING RACKBEAT FOR MELLOMAKSEL PARTS...')
    print('=' * 60)
    
    # Rackbeat API credentials
    rackbeat_url = "https://app.rackbeat.com/api/products"
    rackbeat_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiNzk2NzJkMzc4ZGJkMzI4YzY4YWY4YzU4ZGU4YjU3NzJlNzNkNzJlMzQ5MzY0NzI0MzY4ZGJkZGJkNjFmNzUzNjY3ZGY5YzI3ZjI4ZGZkNzciLCJpYXQiOjE3MjQyNTU1NjkuNzI5NzYsIm5iZiI6MTcyNDI1NTU2OS43Mjk3NjMsImV4cCI6MTc1NTc5MTU2OS43MjU5NzQsInN1YiI6IjEwNzMzIiwic2NvcGVzIjpbXX0.dVgJhWNJBhKGxCOKJMKEhYJKJHGFDSAQWERTYUIOP"
    
    headers = {
        'Authorization': f'Bearer {rackbeat_token}',
        'Accept': 'application/json'
    }
    
    try:
        # Get all products from Rackbeat
        print('📡 Fetching products from Rackbeat...')
        response = requests.get(rackbeat_url, headers=headers)
        
        if response.status_code != 200:
            print(f'❌ Rackbeat API error: {response.status_code}')
            return
        
        data = response.json()
        products = data.get('data', [])
        
        print(f'✅ Found {len(products)} total products in Rackbeat')
        
        # Filter for Mellomaksel parts that should be synced
        mellomaksel_parts = []
        ma18002_found = False
        
        for product in products:
            # Check if it's Mellomaksel group
            group = product.get('group', '')
            if group != 'Mellomaksel':
                continue
            
            # Check if it has i_nettbutikk = ja
            custom_fields = product.get('custom_fields', [])
            i_nettbutikk = None
            
            for field in custom_fields:
                if field.get('slug') == 'i-nettbutikk':
                    i_nettbutikk = field.get('value')
                    break
            
            if i_nettbutikk != 'ja':
                continue
            
            # Check if it's on stock
            available_quantity = product.get('available_quantity', 0)
            if available_quantity <= 0:
                continue
            
            # This part should be synced!
            mellomaksel_parts.append(product)
            
            # Check specifically for MA18002
            number = product.get('number', '')
            if number == 'MA18002':
                ma18002_found = True
                print(f'✅ FOUND MA18002 IN RACKBEAT:')
                print(f'   Number: {number}')
                print(f'   Name: {product.get("name", "")}')
                print(f'   Group: {group}')
                print(f'   i_nettbutikk: {i_nettbutikk}')
                print(f'   Stock: {available_quantity}')
                print(f'   Price: {product.get("sales_price", 0)}')
        
        print(f'\n📊 MELLOMAKSEL SYNC STATUS:')
        print(f'   Total Mellomaksel parts that SHOULD be synced: {len(mellomaksel_parts)}')
        print(f'   MA18002 found in Rackbeat: {"✅ YES" if ma18002_found else "❌ NO"}')
        
        if not ma18002_found:
            print(f'\n❌ CRITICAL: MA18002 NOT FOUND IN RACKBEAT!')
            print(f'   This means the part number or metadata is wrong!')
        
        # Show first 10 parts that should be synced
        print(f'\n📋 FIRST 10 MELLOMAKSEL PARTS THAT SHOULD BE SYNCED:')
        for i, part in enumerate(mellomaksel_parts[:10]):
            print(f'   {i+1}. {part.get("number", "")} - {part.get("name", "")}')
        
        if len(mellomaksel_parts) > 10:
            print(f'   ... and {len(mellomaksel_parts) - 10} more')
        
    except Exception as e:
        print(f'❌ Error checking Rackbeat: {e}')

if __name__ == '__main__':
    check_rackbeat_mellomaksel()
