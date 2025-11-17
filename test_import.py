#!/usr/bin/env python3
"""
Simple test script to verify the import functionality
"""

import requests
import json

# Test data
test_transactions = [
    {
        'date': '2024-01-15',
        'description': 'Test Salary Credit',
        'amount': 50000.0,
        'type': 'credit',
        'category': 'salary'
    },
    {
        'date': '2024-01-16',
        'description': 'Test Grocery Purchase',
        'amount': 2500.0,
        'type': 'debit',
        'category': 'groceries'
    }
]

def test_import_endpoint():
    """Test the import endpoint directly"""
    url = 'http://localhost:5000/api/statement/import'
    
    payload = {
        'transactions': test_transactions
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    try:
        print("Testing import endpoint...")
        print(f"URL: {url}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Import successful!")
            print(f"Imported: {result.get('imported', 0)} transactions")
            if result.get('errors'):
                print(f"Errors: {result['errors']}")
        else:
            print("❌ Import failed!")
            try:
                error_data = response.json()
                print(f"Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"Raw error: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure the backend server is running on http://localhost:5000")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_health_endpoint():
    """Test if the server is running"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ Backend server is running")
            return True
        else:
            print(f"❌ Backend server returned status {response.status_code}")
            return False
    except:
        print("❌ Backend server is not responding")
        return False

if __name__ == '__main__':
    print("=== Personal Finance Advisor Import Test ===")
    print()
    
    # Test server health first
    if test_health_endpoint():
        print()
        test_import_endpoint()
    else:
        print()
        print("Please start the backend server first by running:")
        print("cd backend && python app.py")