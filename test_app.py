#!/usr/bin/env python3
import requests
import time
import subprocess
import sys
import os

def test_flask_app():
    """Test the Flask app endpoints"""
    
    # Start the Flask app in background
    print("Starting Flask app...")
    process = subprocess.Popen([sys.executable, 'app.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Wait for app to start
    time.sleep(5)
    
    try:
        # Test Statens Vegvesen endpoint
        print("Testing Statens Vegvesen endpoint...")
        response = requests.get("http://127.0.0.1:8000/api/statens_vegvesen?regnr=KH66644", timeout=10)
        print(f"SVV response: {response.status_code}")
        print(f"SVV content: {response.text[:200]}...")
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Kill the process
        process.terminate()
        process.wait()
        print("Flask app stopped.")

if __name__ == "__main__":
    test_flask_app() 