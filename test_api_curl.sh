#!/bin/bash

echo "🧪 TESTING API WITH CURL"
echo "=========================="

BASE_URL="https://web-production-0809b.up.railway.app/api/car_parts_search"

for PLATE in "YZ99554" "KH66644" "RJ62438"; do
    echo ""
    echo "🚗 Testing $PLATE:"
    echo "-------------------"
    
    URL="$BASE_URL?regnr=$PLATE"
    echo "🌐 Calling: $URL"
    
    # Use curl with timeout and show response
    RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" --max-time 30 "$URL")
    
    # Extract HTTP code
    HTTP_CODE=$(echo "$RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    
    # Extract JSON response
    JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    echo "📊 Status: $HTTP_CODE"
    
    if [ "$HTTP_CODE" = "200" ]; then
        # Try to extract parts count using basic text processing
        PARTS_COUNT=$(echo "$JSON_RESPONSE" | grep -o '"shopify_parts":\[[^]]*\]' | grep -o '\[.*\]' | grep -o ',' | wc -l)
        MESSAGE=$(echo "$JSON_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
        
        echo "🔍 Parts found: approximately $PARTS_COUNT"
        echo "💬 Message: $MESSAGE"
        
        if [ "$PARTS_COUNT" -eq 0 ]; then
            echo "❌ NO PARTS FOUND - This is the problem!"
        else
            echo "✅ Found parts"
        fi
    else
        echo "❌ HTTP Error: $HTTP_CODE"
        echo "📄 Response: ${JSON_RESPONSE:0:200}..."
    fi
done

echo ""
echo "🎯 SUMMARY:"
echo "If all three return 0 parts, the problem is likely:"
echo "1. Cache lookup failing for all vehicles"
echo "2. TecDoc fallback failing for all vehicles"
echo "3. Database connection issues"
echo "4. OEM matching logic completely broken"
