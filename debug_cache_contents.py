#!/usr/bin/env python3
"""
Debug what's actually in the compatibility matrix cache
"""

def debug_cache_contents():
    """Check what vehicle data exists in compatibility matrix"""
    
    print("🔍 DEBUGGING COMPATIBILITY MATRIX CONTENTS")
    print("=" * 50)
    
    # Test vehicles we expect
    expected_vehicles = [
        ("YZ99554", "MERCEDES-BENZ", "GLK", "2010"),
        ("KH66644", "VOLKSWAGEN", "TIGUAN", "2009"), 
        ("RJ62438", "VOLVO", "V70", "2012")
    ]
    
    print("🎯 EXPECTED VEHICLES:")
    for plate, make, model, year in expected_vehicles:
        print(f"   {plate}: {make} {model} {year}")
    
    print(f"\n🔍 CACHE LOOKUP VARIATIONS TO TEST:")
    
    for plate, make, model, year in expected_vehicles:
        print(f"\n🚗 {plate} ({make} {model} {year}):")
        print("-" * 40)
        
        # Different key formats to try
        variations = [
            f"{make} {model} {year}",
            f"{make.upper()} {model.upper()} {year}",
            f"{make} {model}",
            f"{model} {year}",
            f"{model}",
            f"{make} {model.split()[0]} {year}",  # First word of model only
            f"{make} {model.split()[0]}",  # Make + first word of model
        ]
        
        for i, variation in enumerate(variations, 1):
            print(f"   {i}. '{variation}'")
    
    print(f"\n💡 DEBUGGING STRATEGY:")
    print("1. Check if ANY of these variations exist in compatibility_matrix table")
    print("2. Check what vehicle_make/model/year combinations DO exist")
    print("3. Check if OEM numbers are correctly stored for existing entries")
    print("4. Verify why Vito/Sprinter parts appear for GLK (wrong OEM match?)")
    
    print(f"\n🚨 CRITICAL QUESTIONS:")
    print("❓ Does compatibility_matrix have entries for these exact vehicles?")
    print("❓ Are the vehicle_make/model/year fields normalized consistently?") 
    print("❓ Do the matched_oem fields contain the correct OEM numbers?")
    print("❓ Why are Vito/Sprinter OEMs matching GLK searches?")

if __name__ == "__main__":
    debug_cache_contents()
