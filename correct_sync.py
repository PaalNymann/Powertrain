#!/usr/bin/env python3
"""
Correct sync script - only Drivaksel and Mellomaksel products with i_nettbutikk: ja
"""

import os
import sys
import subprocess

# Set environment variables for Railway database
os.environ['DATABASE_URL'] = 'postgresql://postgres:bNrAgtVDLbFWrqp@junction.proxy.rlwy.net:47292/railway'

def run_correct_sync():
    """Run sync with correct filters - only Drivaksel and Mellomaksel with i_nettbutikk: ja"""
    print("🚀 RUNNING CORRECT SYNC")
    print("=" * 50)
    print("✅ FILTERS:")
    print("   - Only group: Drivaksel OR Mellomaksel")
    print("   - Only i_nettbutikk: ja")
    print("   - NO stock filtering")
    print("   - Include ALL metafields (Original_nummer, Number, etc.)")
    print()
    
    # Run sync service with correct environment
    try:
        print("🔄 Starting sync service...")
        result = subprocess.run([
            'python', 'sync_service.py'
        ], capture_output=False, text=True, cwd='/Users/nyman/powertrain_system')
        
        if result.returncode == 0:
            print("\\n🎉 SYNC COMPLETED SUCCESSFULLY!")
        else:
            print(f"\\n❌ SYNC FAILED with return code: {result.returncode}")
            
    except Exception as e:
        print(f"❌ Error running sync: {e}")

if __name__ == "__main__":
    run_correct_sync()
