#!/usr/bin/env python3
"""
Minimal sync script to get MA18002 into Shopify database
Uses only built-in Python modules and direct API calls
"""

import json
import urllib.request
import urllib.parse
import os

def sync_ma18002_via_api():
    """Sync MA18002 via direct API calls"""
    print("🔄 SYNCING MA18002 VIA DIRECT API CALLS")
    print("=" * 45)
    
    # Try different sync endpoints
    sync_urls = [
        "https://web-production-0809b.up.railway.app/sync/full",
        "https://sync-service-production.up.railway.app/sync/full",
        "http://localhost:8001/sync/full"
    ]
    
    for url in sync_urls:
        try:
            print(f"🔍 Trying sync endpoint: {url}")
            
            # Create POST request
            data = json.dumps({}).encode('utf-8')
            req = urllib.request.Request(
                url, 
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'MA18002-Sync-Script/1.0'
                },
                method='POST'
            )
            
            # Make request with timeout
            with urllib.request.urlopen(req, timeout=300) as response:
                result = response.read().decode('utf-8')
                print(f"✅ SUCCESS! Response from {url}:")
                print(result[:500] + "..." if len(result) > 500 else result)
                return True
                
        except urllib.error.HTTPError as e:
            print(f"❌ HTTP Error {e.code}: {e.reason}")
            if e.code == 404:
                print(f"   Endpoint not found: {url}")
            continue
            
        except urllib.error.URLError as e:
            print(f"❌ URL Error: {e.reason}")
            continue
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print(f"\\n❌ ALL SYNC ENDPOINTS FAILED")
    print(f"💡 ALTERNATIVE: Check if MA18002 is already in database")
    
    # Test if MA18002 is searchable
    print(f"\\n🔍 TESTING MA18002 SEARCHABILITY:")
    test_search_ma18002()
    
    return False

def test_search_ma18002():
    """Test if MA18002 is searchable via backend"""
    search_urls = [
        "https://web-production-0809b.up.railway.app/api/car_parts_search",
        "https://web-production-0809b.up.railway.app/test/ma18002"
    ]
    
    for url in search_urls:
        try:
            print(f"🔍 Testing search endpoint: {url}")
            
            if "car_parts_search" in url:
                # Test with ZT41818 (should find MA18002)
                data = json.dumps({"license_plate": "ZT41818"}).encode('utf-8')
                req = urllib.request.Request(
                    url, 
                    data=data,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
            else:
                # Test MA18002 endpoint
                req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = response.read().decode('utf-8')
                print(f"✅ Response from {url}:")
                
                # Parse JSON if possible
                try:
                    data = json.loads(result)
                    if "car_parts_search" in url:
                        parts_count = len(data.get('shopify_parts', []))
                        print(f"   Found {parts_count} parts for ZT41818")
                        
                        # Check if MA18002 is in results
                        for part in data.get('shopify_parts', []):
                            if 'MA18002' in part.get('title', '') or 'MA18002' in part.get('handle', ''):
                                print(f"   🎯 FOUND MA18002 in search results!")
                                return True
                        
                        if parts_count > 0:
                            print(f"   ❌ MA18002 NOT found in {parts_count} results")
                        else:
                            print(f"   ❌ No parts found for ZT41818")
                    else:
                        print(f"   MA18002 test result: {str(data)[:200]}...")
                        
                except json.JSONDecodeError:
                    print(f"   Raw response: {result[:200]}...")
                
        except Exception as e:
            print(f"❌ Search test failed: {e}")
    
    return False

def check_free_text_search():
    """Check if free text search works for MA18002 OEMs"""
    print(f"\\n🔍 TESTING FREE TEXT SEARCH:")
    print(f"   This simulates searching for '370008H310' in webshop")
    print(f"   Expected: Should return MA18002 if it exists in database")
    print(f"   Actual result from user: 'Ingen deler funnet'")
    print(f"   ✅ CONCLUSION: MA18002 is NOT in Shopify database")

if __name__ == "__main__":
    print("🎯 MA18002 SYNC ANALYSIS")
    print("=" * 25)
    
    # Check current status
    check_free_text_search()
    
    # Try to sync
    success = sync_ma18002_via_api()
    
    if success:
        print(f"\\n🎉 SYNC COMPLETED!")
        print(f"   MA18002 should now be searchable")
        print(f"   Try searching for '370008H310' in webshop")
    else:
        print(f"\\n💡 NEXT STEPS:")
        print(f"   1. Check Railway dashboard for sync service")
        print(f"   2. Run sync manually via Railway console")
        print(f"   3. Verify MA18002 exists in Rackbeat with correct metadata")
        print(f"   4. Debug sync filter logic for Mellomaksel products")
