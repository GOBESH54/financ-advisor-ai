"""
Comprehensive System Test Script
Tests all major features: Statement Import, AI Forecasting, Business Intelligence
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5000/api"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_health():
    """Test basic API health"""
    print_section("1. HEALTH CHECK")
    try:
        response = requests.get(f"{BASE_URL}/test", timeout=5)
        print(f"✅ API Health: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ API Health Failed: {e}")
        return False

def test_statement_test_import():
    """Test database write capability"""
    print_section("2. DATABASE WRITE TEST")
    try:
        response = requests.post(f"{BASE_URL}/statement/test-import", timeout=10)
        result = response.json()
        if result.get('success'):
            print(f"✅ DB Write Test Passed: {result}")
            return True
        else:
            print(f"❌ DB Write Test Failed: {result}")
            return False
    except Exception as e:
        print(f"❌ DB Write Test Error: {e}")
        return False

def test_statement_import():
    """Test transaction import"""
    print_section("3. TRANSACTION IMPORT TEST")
    
    test_transactions = [
        {
            "date": (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            "description": "Test Salary Credit",
            "amount": 50000.0,
            "type": "credit",
            "category": "salary"
        },
        {
            "date": (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
            "description": "Test Grocery Shopping",
            "amount": 2500.0,
            "type": "debit",
            "category": "groceries"
        },
        {
            "date": (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
            "description": "Test Electricity Bill",
            "amount": 1800.0,
            "type": "debit",
            "category": "utilities"
        }
    ]
    
    try:
        response = requests.post(
            f"{BASE_URL}/statement/import",
            json={"transactions": test_transactions},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        result = response.json()
        
        if result.get('success'):
            print(f"✅ Import Success: {result.get('imported')} transactions imported")
            print(f"   Total Received: {result.get('total_received')}")
            if result.get('errors'):
                print(f"   ⚠️  Errors: {result.get('errors')}")
            return True
        else:
            print(f"❌ Import Failed: {result}")
            return False
    except Exception as e:
        print(f"❌ Import Error: {e}")
        return False

def test_dashboard():
    """Test dashboard endpoint"""
    print_section("4. DASHBOARD TEST")
    try:
        response = requests.get(f"{BASE_URL}/dashboard", timeout=10)
        result = response.json()
        
        print(f"✅ Dashboard Data Retrieved:")
        print(f"   Total Income: ₹{result.get('total_income', 0):,.2f}")
        print(f"   Total Expenses: ₹{result.get('total_expenses', 0):,.2f}")
        print(f"   Net Savings: ₹{result.get('net_savings', 0):,.2f}")
        print(f"   Income Count: {result.get('income_count', 0)}")
        print(f"   Expense Count: {result.get('expense_count', 0)}")
        return True
    except Exception as e:
        print(f"❌ Dashboard Error: {e}")
        return False

def test_lstm_forecasting():
    """Test LSTM forecasting"""
    print_section("5. AI FORECASTING TEST (LSTM)")
    try:
        response = requests.get(f"{BASE_URL}/forecast/lstm?periods=3", timeout=15)
        result = response.json()
        
        if 'forecast' in result:
            print(f"✅ LSTM Forecasting Working:")
            print(f"   Forecast Periods: {len(result['forecast'])}")
            for i, val in enumerate(result['forecast'], 1):
                print(f"   Month {i}: ₹{val:,.2f}")
            return True
        else:
            print(f"⚠️  LSTM Response: {result}")
            return False
    except Exception as e:
        print(f"❌ LSTM Forecasting Error: {e}")
        return False

def test_anomaly_detection():
    """Test anomaly detection"""
    print_section("6. ANOMALY DETECTION TEST")
    try:
        response = requests.get(f"{BASE_URL}/analyze/anomalies", timeout=15)
        result = response.json()
        
        if 'anomalies' in result:
            print(f"✅ Anomaly Detection Working:")
            print(f"   Total Transactions: {result.get('total_transactions', 0)}")
            print(f"   Anomalies Found: {result.get('anomaly_count', 0)}")
            print(f"   Anomaly %: {result.get('anomaly_percentage', 0):.2f}%")
            return True
        else:
            print(f"⚠️  Anomaly Detection Response: {result}")
            return False
    except Exception as e:
        print(f"❌ Anomaly Detection Error: {e}")
        return False

def test_budget_analysis():
    """Test budget analysis"""
    print_section("7. BUDGET ANALYSIS TEST")
    try:
        response = requests.get(f"{BASE_URL}/analyze/budget", timeout=15)
        result = response.json()
        
        if 'recommendations' in result or 'analysis' in result:
            print(f"✅ Budget Analysis Working:")
            print(f"   Analysis Keys: {list(result.keys())}")
            return True
        else:
            print(f"⚠️  Budget Analysis Response: {result}")
            return False
    except Exception as e:
        print(f"❌ Budget Analysis Error: {e}")
        return False

def test_investment_recommendations():
    """Test investment recommendations"""
    print_section("8. INVESTMENT RECOMMENDATIONS TEST")
    try:
        response = requests.get(f"{BASE_URL}/analyze/investments", timeout=15)
        result = response.json()
        
        if 'recommendations' in result or 'analysis' in result:
            print(f"✅ Investment Recommendations Working:")
            print(f"   Response Keys: {list(result.keys())}")
            return True
        else:
            print(f"⚠️  Investment Response: {result}")
            return False
    except Exception as e:
        print(f"❌ Investment Recommendations Error: {e}")
        return False

def run_all_tests():
    """Run all system tests"""
    print("\n" + "🚀 "*20)
    print("  PERSONAL FINANCE ADVISOR - SYSTEM TEST")
    print("🚀 "*20)
    
    results = {
        "Health Check": test_health(),
        "DB Write Test": test_statement_test_import(),
        "Transaction Import": test_statement_import(),
        "Dashboard": test_dashboard(),
        "LSTM Forecasting": test_lstm_forecasting(),
        "Anomaly Detection": test_anomaly_detection(),
        "Budget Analysis": test_budget_analysis(),
        "Investment Recommendations": test_investment_recommendations()
    }
    
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! System is fully operational.")
    elif passed >= total * 0.7:
        print("\n⚠️  Most tests passed. Some features may need attention.")
    else:
        print("\n❌ Multiple failures detected. Please check logs.")
    
    return results

if __name__ == "__main__":
    run_all_tests()
