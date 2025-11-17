from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from marshmallow import Schema, fields, ValidationError, validate
from flask_caching import Cache
from flask_migrate import Migrate
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    verify_jwt_in_request
)
from sqlalchemy import asc, desc
from werkzeug.utils import secure_filename

# Safe imports with fallback handling
try:
    from config import Config
    from models import db, User, Income, Expense, Debt, SavingsGoal, Investment, Budget
except ImportError as e:
    logger.error(f"Critical import error: {e}")
    raise

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=Config.CORS_ORIGINS)
cache = Cache(app, config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 300
})

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# Validation Schemas
class UserSchema(Schema):
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    age = fields.Int(required=False)
    risk_tolerance = fields.Str(validate=validate.OneOf(['low', 'medium', 'high']))

class IncomeSchema(Schema):
    source = fields.Str(required=True)
    amount = fields.Float(required=True)
    frequency = fields.Str(required=False, validate=validate.OneOf(['monthly', 'yearly', 'one-time']))
    date = fields.Date(required=False)

class ExpenseSchema(Schema):
    category = fields.Str(required=True)
    description = fields.Str(required=False, allow_none=True)
    amount = fields.Float(required=True)
    date = fields.Date(required=False)
    is_recurring = fields.Bool(required=False)
    frequency = fields.Str(required=False)

class DebtSchema(Schema):
    name = fields.Str(required=True)
    principal_amount = fields.Float(required=True)
    current_balance = fields.Float(required=True)
    interest_rate = fields.Float(required=True)
    minimum_payment = fields.Float(required=True)
    due_date = fields.Date(required=False, allow_none=True)

class SavingsGoalSchema(Schema):
    name = fields.Str(required=True)
    target_amount = fields.Float(required=True)
    current_amount = fields.Float(required=False)
    target_date = fields.Date(required=False, allow_none=True)
    priority = fields.Str(required=False)

user_schema = UserSchema()
income_schema = IncomeSchema()
expense_schema = ExpenseSchema()
debt_schema = DebtSchema()
savings_goal_schema = SavingsGoalSchema()

@app.errorhandler(ValidationError)
def handle_validation_error(err):
    return jsonify({'error': 'validation_error', 'messages': err.messages}), 422

# Pagination and sorting helpers
def get_pagination_params(max_per_page=100):
    page = request.args.get('page')
    per_page = request.args.get('per_page')
    try:
        page = int(page) if page is not None else None
        per_page = int(per_page) if per_page is not None else None
    except ValueError:
        page, per_page = None, None
    if page is not None and page < 1:
        page = 1
    if per_page is not None:
        per_page = max(1, min(per_page, max_per_page))
    return page, per_page

def apply_sorting(query, model, default_order, allowed_fields):
    sort = request.args.get('sort')
    if not sort:
        return query.order_by(default_order)
    direction = desc if sort.startswith('-') else asc
    field = sort.lstrip('+-')
    if field in allowed_fields and hasattr(model, field):
        return query.order_by(direction(getattr(model, field)))
    return query.order_by(default_order)

def set_pagination_headers(response, total, page, per_page):
    response.headers['X-Total-Count'] = total
    if page is not None:
        response.headers['X-Page'] = page
    if per_page is not None:
        response.headers['X-Per-Page'] = per_page
    return response

# Auth helpers
def get_current_user():
    # If anonymous access allowed, use first user as before
    if os.environ.get('ALLOW_ANON', '1') == '1':
        return User.query.first()
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid is None:
            return None
        return User.query.get(uid)
    except Exception:
        return None

def user_cache_key():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
    except Exception:
        uid = None
    base = request.full_path or request.path
    return f"{base}|u={uid or 'anon'}"

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'csv', 'pdf', 'xlsx', 'xls'}

# Create tables
with app.app_context():
    if os.environ.get('ALLOW_CREATE_ALL', '1') == '1':
        db.create_all()
        
        if not User.query.first():
            default_user = User(
                name='Default User',
                email='user@example.com',
                age=30,
                risk_tolerance='medium'
            )
            db.session.add(default_user)
            db.session.commit()

# User endpoints
@app.route('/api/user', methods=['GET'])
def get_user():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'age': user.age,
        'risk_tolerance': user.risk_tolerance
    })

@app.route('/api/user', methods=['POST', 'PUT'])
def update_user():
    data = user_schema.load(request.get_json(force=True))
    user = get_current_user()
    
    if not user:
        user = User()
        db.session.add(user)
    
    user.name = data.get('name', user.name)
    user.email = data.get('email', user.email)
    user.age = data.get('age', user.age)
    user.risk_tolerance = data.get('risk_tolerance', user.risk_tolerance)
    
    db.session.commit()
    return jsonify({'message': 'User updated successfully'})

# Auth endpoint (email only demo)
@app.route('/api/auth/login', methods=['POST'])
def login():
    payload = request.get_json(force=True) or {}
    email = payload.get('email')
    name = payload.get('name') or 'User'
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        # Simple creation flow for demo; in real apps, add password hashing
        user = User(name=name, email=email)
        db.session.add(user)
        db.session.commit()
    token = create_access_token(identity=user.id)
    return jsonify({'access_token': token, 'user': {
        'id': user.id, 'name': user.name, 'email': user.email,
        'age': user.age, 'risk_tolerance': user.risk_tolerance
    }})

# Income endpoints
@app.route('/api/income', methods=['GET'])
def get_income():
    user = get_current_user()
    query = Income.query.filter_by(user_id=user.id)
    query = apply_sorting(
        query,
        Income,
        desc(Income.created_at),
        ['date', 'amount', 'source', 'created_at', 'frequency']
    )
    total = query.count()
    page, per_page = get_pagination_params()
    if page and per_page:
        items = query.offset((page - 1) * per_page).limit(per_page).all()
    else:
        items = query.all()
    payload = [{
        'id': i.id,
        'source': i.source,
        'amount': i.amount,
        'frequency': i.frequency,
        'date': i.date.isoformat() if i.date else None
    } for i in items]
    resp = jsonify(payload)
    return set_pagination_headers(resp, total, page, per_page)

@app.route('/api/income', methods=['POST'])
def add_income():
    data = income_schema.load(request.get_json(force=True))
    user = get_current_user()
    
    income = Income(
        user_id=user.id,
        source=data['source'],
        amount=data['amount'],
        frequency=data.get('frequency', 'monthly'),
        date=data.get('date') or datetime.now().date()
    )
    
    db.session.add(income)
    db.session.commit()
    return jsonify({'message': 'Income added successfully', 'id': income.id})

# Expense endpoints
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    user = get_current_user()
    query = Expense.query.filter_by(user_id=user.id)
    query = apply_sorting(
        query,
        Expense,
        desc(Expense.created_at),
        ['date', 'amount', 'category', 'created_at', 'frequency']
    )
    total = query.count()
    page, per_page = get_pagination_params()
    if page and per_page:
        items = query.offset((page - 1) * per_page).limit(per_page).all()
    else:
        items = query.all()
    payload = [{
        'id': e.id,
        'category': e.category,
        'description': e.description,
        'amount': e.amount,
        'date': e.date.isoformat() if e.date else None,
        'is_recurring': e.is_recurring,
        'frequency': e.frequency
    } for e in items]
    resp = jsonify(payload)
    return set_pagination_headers(resp, total, page, per_page)

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = expense_schema.load(request.get_json(force=True))
    user = get_current_user()
    
    expense = Expense(
        user_id=user.id,
        category=data['category'],
        description=data.get('description', ''),
        amount=data['amount'],
        date=data.get('date') or datetime.now().date(),
        is_recurring=data.get('is_recurring', False),
        frequency=data.get('frequency', 'monthly')
    )
    
    db.session.add(expense)
    db.session.commit()
    return jsonify({'message': 'Expense added successfully', 'id': expense.id})

# Debt endpoints
@app.route('/api/debts', methods=['GET'])
def get_debts():
    user = get_current_user()
    query = Debt.query.filter_by(user_id=user.id)
    query = apply_sorting(
        query,
        Debt,
        desc(Debt.created_at),
        ['current_balance', 'interest_rate', 'minimum_payment', 'name', 'created_at', 'due_date']
    )
    total = query.count()
    page, per_page = get_pagination_params()
    if page and per_page:
        items = query.offset((page - 1) * per_page).limit(per_page).all()
    else:
        items = query.all()
    payload = [{
        'id': d.id,
        'name': d.name,
        'principal_amount': d.principal_amount,
        'current_balance': d.current_balance,
        'interest_rate': d.interest_rate,
        'minimum_payment': d.minimum_payment,
        'due_date': d.due_date.isoformat() if d.due_date else None
    } for d in items]
    resp = jsonify(payload)
    return set_pagination_headers(resp, total, page, per_page)

@app.route('/api/debts', methods=['POST'])
def add_debt():
    data = debt_schema.load(request.get_json(force=True))
    user = get_current_user()
    
    debt = Debt(
        user_id=user.id,
        name=data['name'],
        principal_amount=data['principal_amount'],
        current_balance=data['current_balance'],
        interest_rate=data['interest_rate'],
        minimum_payment=data['minimum_payment'],
        due_date=data.get('due_date')
    )
    
    db.session.add(debt)
    db.session.commit()
    return jsonify({'message': 'Debt added successfully', 'id': debt.id})

# Savings Goals endpoints
@app.route('/api/savings-goals', methods=['GET'])
def get_savings_goals():
    user = get_current_user()
    query = SavingsGoal.query.filter_by(user_id=user.id)
    query = apply_sorting(
        query,
        SavingsGoal,
        desc(SavingsGoal.created_at),
        ['target_amount', 'current_amount', 'name', 'created_at', 'priority', 'target_date']
    )
    total = query.count()
    page, per_page = get_pagination_params()
    if page and per_page:
        items = query.offset((page - 1) * per_page).limit(per_page).all()
    else:
        items = query.all()
    payload = [{
        'id': g.id,
        'name': g.name,
        'target_amount': g.target_amount,
        'current_amount': g.current_amount,
        'target_date': g.target_date.isoformat() if g.target_date else None,
        'priority': g.priority,
        'progress': (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0
    } for g in items]
    resp = jsonify(payload)
    return set_pagination_headers(resp, total, page, per_page)

@app.route('/api/savings-goals', methods=['POST'])
def add_savings_goal():
    data = savings_goal_schema.load(request.get_json(force=True))
    user = get_current_user()
    
    goal = SavingsGoal(
        user_id=user.id,
        name=data['name'],
        target_amount=data['target_amount'],
        current_amount=data.get('current_amount', 0),
        target_date=data.get('target_date'),
        priority=data.get('priority', 'medium')
    )
    
    db.session.add(goal)
    db.session.commit()
    return jsonify({'message': 'Savings goal added successfully', 'id': goal.id})

# Simple AI Analysis endpoints (without complex ML models)
@app.route('/api/analyze/budget', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def analyze_budget():
    user = get_current_user()
    
    # Get user's financial data
    incomes = Income.query.filter_by(user_id=user.id).all()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    debts = Debt.query.filter_by(user_id=user.id).all()
    
    # Calculate total monthly income
    total_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
    
    # Calculate total expenses
    total_expenses = sum([e.amount for e in expenses])
    
    # Calculate debt payments
    total_debt_payments = sum([d.minimum_payment for d in debts])
    
    # Simple 50/30/20 rule analysis
    needs_budget = total_income * 0.5
    wants_budget = total_income * 0.3
    savings_budget = total_income * 0.2
    
    # Categorize expenses (simplified)
    needs_expenses = sum([e.amount for e in expenses if e.category in ['utilities', 'groceries', 'rent', 'insurance']])
    wants_expenses = sum([e.amount for e in expenses if e.category in ['entertainment', 'dining', 'shopping']])
    
    analysis = {
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_debt_payments': total_debt_payments,
        'net_savings': total_income - total_expenses - total_debt_payments,
        'budget_analysis': {
            'needs': {
                'budget': needs_budget,
                'actual': needs_expenses,
                'status': 'good' if needs_expenses <= needs_budget else 'over_budget'
            },
            'wants': {
                'budget': wants_budget,
                'actual': wants_expenses,
                'status': 'good' if wants_expenses <= wants_budget else 'over_budget'
            },
            'savings': {
                'budget': savings_budget,
                'actual': total_income - total_expenses - total_debt_payments,
                'status': 'good' if (total_income - total_expenses - total_debt_payments) >= savings_budget else 'under_target'
            }
        },
        'recommendations': []
    }
    
    # Add simple recommendations
    if needs_expenses > needs_budget:
        analysis['recommendations'].append('Consider reducing essential expenses or increasing income')
    if wants_expenses > wants_budget:
        analysis['recommendations'].append('Reduce discretionary spending to stay within budget')
    if (total_income - total_expenses - total_debt_payments) < savings_budget:
        analysis['recommendations'].append('Increase savings rate to meet 20% target')
    
    return jsonify(analysis)

@app.route('/api/analyze/investments', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def analyze_investments():
    user = get_current_user()
    
    # Get user's financial profile
    incomes = Income.query.filter_by(user_id=user.id).all()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    debts = Debt.query.filter_by(user_id=user.id).all()
    
    total_income = sum([i.amount for i in incomes if i.frequency == 'monthly']) * 12
    total_expenses = sum([e.amount for e in expenses]) * 12
    total_debt = sum([d.current_balance for d in debts])
    
    # Simple investment recommendations based on age and risk tolerance
    age = user.age or 30
    risk_tolerance = user.risk_tolerance or 'medium'
    
    # Simple asset allocation based on age (100 - age rule)
    equity_percentage = max(100 - age, 20)  # Minimum 20% equity
    debt_percentage = min(age, 80)  # Maximum 80% debt
    
    # Adjust based on risk tolerance
    if risk_tolerance == 'high':
        equity_percentage = min(equity_percentage + 20, 90)
        debt_percentage = 100 - equity_percentage
    elif risk_tolerance == 'low':
        equity_percentage = max(equity_percentage - 20, 10)
        debt_percentage = 100 - equity_percentage
    
    available_investment = max((total_income - total_expenses) * 0.2, 0)
    
    recommendations = {
        'recommended_type': risk_tolerance,
        'allocation': {
            'equity': equity_percentage,
            'debt': debt_percentage,
            'gold': 10
        },
        'risk_score': risk_tolerance,
        'monthly_investment': available_investment / 12,
        'annual_investment': available_investment,
        'recommendations': [
            f'Based on your age ({age}), consider {equity_percentage}% equity allocation',
            f'Your risk tolerance is {risk_tolerance}, which suits this allocation',
            f'You can invest approximately ₹{available_investment/12:,.0f} per month'
        ]
    }
    
    return jsonify(recommendations)

# Dashboard summary endpoint
@app.route('/api/dashboard', methods=['GET'])
@cache.cached(timeout=60, key_prefix=user_cache_key)
def get_dashboard():
    user = get_current_user()
    
    # Get all financial data
    incomes = Income.query.filter_by(user_id=user.id).all()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    debts = Debt.query.filter_by(user_id=user.id).all()
    goals = SavingsGoal.query.filter_by(user_id=user.id).all()
    
    # Calculate summary statistics
    total_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
    total_expenses = sum([e.amount for e in expenses])
    total_debt = sum([d.current_balance for d in debts])
    total_savings = sum([g.current_amount for g in goals])
    
    # Get expense breakdown by category
    expense_categories = {}
    for expense in expenses:
        if expense.category not in expense_categories:
            expense_categories[expense.category] = 0
        expense_categories[expense.category] += expense.amount
    
    return jsonify({
        'summary': {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_savings': total_income - total_expenses,
            'total_debt': total_debt,
            'total_savings': total_savings,
            'debt_to_income': (total_debt / (total_income * 12)) if total_income > 0 else 0
        },
        'expense_breakdown': expense_categories,
        'recent_transactions': [
            {
                'type': 'income',
                'description': i.source,
                'amount': i.amount,
                'date': i.date.isoformat() if i.date else None
            } for i in sorted(incomes, key=lambda x: x.created_at, reverse=True)[:5]
        ] + [
            {
                'type': 'expense',
                'description': e.description or e.category,
                'amount': -e.amount,
                'date': e.date.isoformat() if e.date else None
            } for e in sorted(expenses, key=lambda x: x.created_at, reverse=True)[:5]
        ],
        'goals_progress': [
            {
                'name': g.name,
                'progress': (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0,
                'remaining': g.target_amount - g.current_amount
            } for g in goals
        ]
    })

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'version': 'simplified',
        'features': {
            'basic_crud': True,
            'simple_analytics': True,
            'budget_analysis': True,
            'investment_recommendations': True
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)