#!/usr/bin/env python3
"""
Initialize database for Personal Finance Advisor
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from flask import Flask
    print("✅ Flask imported")
    
    # Basic app config
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_advisor.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Try to import models
    try:
        from models import db
        print("✅ Models imported")
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            print("✅ Database initialized successfully")
            
    except ImportError as e:
        print(f"⚠️ Models not available: {e}")
        print("Creating basic database structure...")
        
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy()
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            print("✅ Basic database created")
            
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    print("Database will be created at runtime")

print("🎯 Ready to start application")
