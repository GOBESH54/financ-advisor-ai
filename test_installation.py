#!/usr/bin/env python3
"""
Test script to verify Personal Finance Advisor installation
"""

import sys
import os
import importlib

def test_import(module_name, description):
    """Test if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description}")
        return True
    except ImportError as e:
        print(f"❌ {description} - {str(e)}")
        return False

def main():
    print("=" * 60)
    print("🔍 PERSONAL FINANCE ADVISOR - INSTALLATION TEST")
    print("=" * 60)
    
    # Test Python version
    python_version = sys.version_info
    if python_version.major == 3 and python_version.minor == 11:
        print(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
    else:
        print(f"⚠️ Python {python_version.major}.{python_version.minor}.{python_version.micro} (3.11 recommended)")
    
    print("\n📦 TESTING CORE DEPENDENCIES:")
    core_passed = 0
    core_tests = [
        ("flask", "Flask Web Framework"),
        ("pandas", "Data Processing"),
        ("numpy", "Numerical Computing"),
        ("matplotlib", "Data Visualization"),
        ("plotly", "Interactive Charts"),
        ("reportlab", "PDF Generation"),
        ("openpyxl", "Excel Processing"),
        ("PIL", "Image Processing (Pillow)"),
    ]
    
    for module, desc in core_tests:
        if test_import(module, desc):
            core_passed += 1
    
    print("\n🤖 TESTING AI/ML DEPENDENCIES:")
    ai_passed = 0
    ai_tests = [
        ("sklearn", "Machine Learning (scikit-learn)"),
        ("xgboost", "XGBoost"),
        ("tensorflow", "TensorFlow (Deep Learning)"),
        ("torch", "PyTorch (Deep Learning)"),
    ]
    
    for module, desc in ai_tests:
        if test_import(module, desc):
            ai_passed += 1
    
    print("\n🏦 TESTING BANKING DEPENDENCIES:")
    banking_passed = 0
    banking_tests = [
        ("PyPDF2", "PDF Processing"),
        ("pdfplumber", "Advanced PDF Parsing"),
    ]
    
    for module, desc in banking_tests:
        if test_import(module, desc):
            banking_passed += 1
    
    print("\n🔒 TESTING SECURITY DEPENDENCIES:")
    security_passed = 0
    security_tests = [
        ("cryptography", "Encryption & Security"),
    ]
    
    for module, desc in security_tests:
        if test_import(module, desc):
            security_passed += 1
    
    # Test database creation
    print("\n💾 TESTING DATABASE FUNCTIONALITY:")
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db = SQLAlchemy(app)
        
        with app.app_context():
            db.create_all()
            print("✅ Database Operations")
        database_ok = True
    except Exception as e:
        print(f"❌ Database Operations - {str(e)}")
        database_ok = False
    
    # Test backend imports
    print("\n🎯 TESTING BACKEND MODULES:")
    backend_passed = 0
    
    # Add backend to path
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    backend_tests = [
        ("models", "Database Models"),
        ("config", "Configuration"),
        ("report_generator", "Report Generator"),
        ("statement_parser", "Statement Parser"),
    ]
    
    for module, desc in backend_tests:
        if test_import(module, desc):
            backend_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INSTALLATION TEST SUMMARY")
    print("=" * 60)
    
    total_score = 0
    max_score = 0
    
    print(f"📦 Core Dependencies: {core_passed}/{len(core_tests)}")
    total_score += core_passed
    max_score += len(core_tests)
    
    print(f"🤖 AI/ML Dependencies: {ai_passed}/{len(ai_tests)}")
    total_score += ai_passed
    max_score += len(ai_tests)
    
    print(f"🏦 Banking Dependencies: {banking_passed}/{len(banking_tests)}")
    total_score += banking_passed
    max_score += len(banking_tests)
    
    print(f"🔒 Security Dependencies: {security_passed}/{len(security_tests)}")
    total_score += security_passed
    max_score += len(security_tests)
    
    print(f"💾 Database: {'✅' if database_ok else '❌'}")
    if database_ok:
        total_score += 1
    max_score += 1
    
    print(f"🎯 Backend Modules: {backend_passed}/{len(backend_tests)}")
    total_score += backend_passed
    max_score += len(backend_tests)
    
    percentage = (total_score / max_score) * 100
    print(f"\n🎯 OVERALL SCORE: {total_score}/{max_score} ({percentage:.1f}%)")
    
    if percentage >= 90:
        print("🎉 EXCELLENT! All major components are working.")
        status = "READY"
    elif percentage >= 70:
        print("✅ GOOD! Core features are working, some advanced features may be limited.")
        status = "FUNCTIONAL"
    elif percentage >= 50:
        print("⚠️ PARTIAL! Basic features should work, many advanced features unavailable.")
        status = "LIMITED"
    else:
        print("❌ POOR! Major issues detected. Please check installation.")
        status = "BROKEN"
    
    print(f"\n🚀 APPLICATION STATUS: {status}")
    
    if status in ["READY", "FUNCTIONAL"]:
        print("\n✨ You can start the application with:")
        print("   • LAUNCH_FINANCE_ADVISOR.bat (recommended)")
        print("   • start_optimized_fixed.bat")
    else:
        print("\n🔧 Please run setup_env_python311.bat to fix issues")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
