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
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

# Safe imports with fallback handling
try:
    from config import Config
    from models import db, User, Income, Expense, Debt, SavingsGoal, Investment, Budget
except ImportError as e:
    logger.error(f"Critical import error: {e}")
    raise

# AI/ML imports with graceful degradation
AI_FEATURES_AVAILABLE = True
try:
    from ai_models import BudgetingAI, InvestmentRecommendationAI, SavingsForecastAI, DebtManagementAI
    from transaction_classifier import IndianTransactionClassifier, AnomalyDetector
    from advanced_ai_models import SpendingPredictor, BudgetOptimizer, FraudDetector, CashflowForecaster
except ImportError as e:
    logger.warning(f"AI/ML imports failed: {e}. Basic functionality will be available.")
    AI_FEATURES_AVAILABLE = False

# LSTM imports (optional - requires TensorFlow)
LSTM_AVAILABLE = True
try:
    from lstm_forecaster import LSTMExpenseForecaster, forecast_by_category
except ImportError as e:
    logger.warning(f"LSTM features unavailable: {e}")
    LSTM_AVAILABLE = False

# Core features (always required)
try:
    from report_generator import ReportGenerator
    from statement_parser import BankStatementParser
    from enhanced_pdf_parser import EnhancedPDFParser
    from statement_api import statement_bp
except ImportError as e:
    logger.warning(f"Some core features may be limited: {e}")
    # Create fallback classes
    class ReportGenerator:
        def generate_monthly_report(self, *args): return "report.pdf"
    class BankStatementParser:
        def parse_csv(self, *args): return []
    class EnhancedPDFParser:
        def parse_pdf(self, *args): return []
    from flask import Blueprint
    statement_bp = Blueprint('statement', __name__)

# Advanced features (optional)
ADVANCED_FEATURES_AVAILABLE = True
try:
    from indian_features import TaxPlanner, GSTTracker, InvestmentTracker, EMICalculator
    from dashboard_features import NotificationManager, InteractiveCharts, GoalTracker, ExpenseTrendAnalyzer
    from mobile_features import ReceiptScanner, VoiceCommandProcessor, OfflineManager, PWAManager
    from performance_optimization import DatabaseOptimizer, MemcachedManager, BackgroundTaskManager, PerformanceMonitor, create_celery_tasks
    from security_features import SecurityManager
    from investment_management import InvestmentManager
    from advanced_budgeting import AdvancedBudgetingManager
    from bank_integration import BankIntegrationManager
    from third_party_integrations import ThirdPartyIntegrationManager
    from advanced_reports import AdvancedReportsManager
    from business_intelligence import BusinessIntelligenceManager
except ImportError as e:
    logger.warning(f"Advanced features may be limited: {e}")
    ADVANCED_FEATURES_AVAILABLE = False

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

# Database path for managers that need it
DATABASE = 'finance_advisor.db'

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
    description = fields.Str(required=False, allow_none=True, missing='')
    amount = fields.Float(required=True)
    date = fields.Date(required=False, allow_none=True)
    is_recurring = fields.Bool(required=False, missing=False)
    frequency = fields.Str(required=False, allow_none=True)

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
    print(f"Validation error: {err.messages}")
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

# Initialize AI models with graceful fallback
budgeting_ai = None
investment_ai = None 
savings_ai = None
debt_ai = None
lstm_forecaster = None
spending_predictor = None
budget_optimizer = None
fraud_detector = None
cashflow_forecaster = None
transaction_classifier = None
anomaly_detector = None

# Core features (always initialize)
try:
    report_gen = ReportGenerator()
    statement_parser = BankStatementParser()
    enhanced_pdf_parser = EnhancedPDFParser()
except Exception as e:
    logger.error(f"Failed to initialize core features: {e}")

# AI/ML models (optional)
if AI_FEATURES_AVAILABLE:
    try:
        budgeting_ai = BudgetingAI()
        investment_ai = InvestmentRecommendationAI()
        savings_ai = SavingsForecastAI()
        debt_ai = DebtManagementAI()
        transaction_classifier = IndianTransactionClassifier(use_finbert=False)
        anomaly_detector = AnomalyDetector()
        spending_predictor = SpendingPredictor()
        budget_optimizer = BudgetOptimizer()
        fraud_detector = FraudDetector()
        cashflow_forecaster = CashflowForecaster()
        logger.info("✅ AI/ML models initialized successfully")
    except Exception as e:
        logger.warning(f"AI/ML initialization failed: {e}")
        AI_FEATURES_AVAILABLE = False

# LSTM features (optional)
if LSTM_AVAILABLE:
    try:
        lstm_forecaster = LSTMExpenseForecaster()
        logger.info("✅ LSTM forecasting initialized successfully")
    except Exception as e:
        logger.warning(f"LSTM initialization failed: {e}")
        LSTM_AVAILABLE = False

# Advanced features (optional)
tax_planner = None
gst_tracker = None
investment_tracker = None
emi_calculator = None
notification_manager = None
interactive_charts = None
goal_tracker = None
expense_analyzer = None

if ADVANCED_FEATURES_AVAILABLE:
    try:
        tax_planner = TaxPlanner()
        gst_tracker = GSTTracker()
        investment_tracker = InvestmentTracker()
        emi_calculator = EMICalculator()
        notification_manager = NotificationManager()
        interactive_charts = InteractiveCharts()
        goal_tracker = GoalTracker()
        expense_analyzer = ExpenseTrendAnalyzer()
        logger.info("✅ Advanced features initialized successfully")
    except Exception as e:
        logger.warning(f"Advanced features initialization failed: {e}")
        ADVANCED_FEATURES_AVAILABLE = False

# Initialize mobile features (with fallback)
receipt_scanner = None
voice_processor = None
offline_manager = None
pwa_manager = None

if ADVANCED_FEATURES_AVAILABLE:
    try:
        receipt_scanner = ReceiptScanner()
        voice_processor = VoiceCommandProcessor()
        offline_manager = OfflineManager()
        pwa_manager = PWAManager()
    except Exception as e:
        logger.warning(f"Mobile features initialization failed: {e}")

# Initialize performance optimization (with fallback)
db_optimizer = None
cache_manager = None
task_manager = None
performance_monitor = None

if ADVANCED_FEATURES_AVAILABLE:
    try:
        db_optimizer = DatabaseOptimizer(db)
        cache_manager = MemcachedManager()
        task_manager = BackgroundTaskManager(app)
        performance_monitor = PerformanceMonitor(cache_manager)
        
        # Create Celery tasks
        if task_manager and task_manager.celery:
            celery_tasks = create_celery_tasks(task_manager.celery, db, cache_manager)
    except Exception as e:
        logger.warning(f"Performance optimization initialization failed: {e}")

# Initialize security features (with fallback)
security_manager = None
data_encryption = None
mfa_auth = None
audit_logger = None
backup_manager = None

if ADVANCED_FEATURES_AVAILABLE:
    try:
        security_manager = SecurityManager()
        data_encryption = security_manager.encryption
        mfa_auth = security_manager.mfa
        audit_logger = security_manager.audit_logger
        backup_manager = security_manager.backup_manager
    except Exception as e:
        logger.warning(f"Security features initialization failed: {e}")

# Initialize investment management (with fallback)
investment_manager = None
if ADVANCED_FEATURES_AVAILABLE:
    try:
        investment_manager = InvestmentManager(DATABASE)
    except Exception as e:
        logger.warning(f"Investment management initialization failed: {e}")

# Initialize advanced budgeting (with fallback)
advanced_budgeting = None
if ADVANCED_FEATURES_AVAILABLE:
    try:
        advanced_budgeting = AdvancedBudgetingManager(DATABASE)
    except Exception as e:
        logger.warning(f"Advanced budgeting initialization failed: {e}")

# Initialize bank integration (with fallback)
bank_integration = None
if ADVANCED_FEATURES_AVAILABLE:
    try:
        bank_integration = BankIntegrationManager(DATABASE)
    except Exception as e:
        logger.warning(f"Bank integration initialization failed: {e}")

# Initialize third-party integrations (with fallback)
third_party_integrations = None
if ADVANCED_FEATURES_AVAILABLE:
    try:
        third_party_integrations = ThirdPartyIntegrationManager(DATABASE)
    except Exception as e:
        logger.warning(f"Third-party integrations initialization failed: {e}")

# Initialize advanced reports (with fallback)
advanced_reports = None
if ADVANCED_FEATURES_AVAILABLE:
    try:
        advanced_reports = AdvancedReportsManager(DATABASE)
    except Exception as e:
        logger.warning(f"Advanced reports initialization failed: {e}")

# Initialize business intelligence (with fallback)
business_intelligence = None
if ADVANCED_FEATURES_AVAILABLE:
    try:
        business_intelligence = BusinessIntelligenceManager(DATABASE)
    except Exception as e:
        logger.warning(f"Business intelligence initialization failed: {e}")

# Import statement blueprint
from statement_api import statement_bp

# Register blueprints
app.register_blueprint(statement_bp, url_prefix='/api')
print("Statement blueprint registered successfully")
print(f"Registered routes: {[rule.rule for rule in app.url_map.iter_rules() if 'statement' in rule.rule]}")

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'csv', 'pdf', 'xlsx', 'xls'}

# Create tables and optimize database
with app.app_context():
    if os.environ.get('ALLOW_CREATE_ALL', '1') == '1':
        db.create_all()
        
        # Create optimized indexes
        if db_optimizer:
            db_optimizer.create_indexes()
            db_optimizer.optimize_queries()
        
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
    try:
        data = expense_schema.load(request.get_json(force=True))
        user = get_current_user()
        
        expense = Expense(
            user_id=user.id,
            category=data['category'],
            description=data.get('description', ''),
            amount=data['amount'],
            date=data.get('date') or datetime.now().date(),
            is_recurring=data.get('is_recurring', False),
            frequency=data.get('frequency')
        )
        
        db.session.add(expense)
        db.session.commit()
        return jsonify({'message': 'Expense added successfully', 'id': expense.id})
    except ValidationError as e:
        print(f"Validation error in add_expense: {e.messages}")
        return jsonify({'error': 'validation_error', 'messages': e.messages}), 422
    except Exception as e:
        print(f"Error in add_expense: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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

# AI Analysis endpoints
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
    
    # Convert expenses to DataFrame
    expenses_data = [{
        'category': e.category,
        'amount': e.amount
    } for e in expenses]
    expenses_df = pd.DataFrame(expenses_data)
    
    # Convert debts to list
    debts_data = [{
        'name': d.name,
        'minimum_payment': d.minimum_payment
    } for d in debts]
    
    # Analyze budget
    analysis = budgeting_ai.analyze_budget(total_income, expenses_df, debts_data)
    
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
    
    user_profile = {
        'age': user.age,
        'income': total_income,
        'expenses': total_expenses,
        'savings': total_income - total_expenses,
        'debt_ratio': total_debt / total_income if total_income > 0 else 0,
        'risk_tolerance': user.risk_tolerance,
        'available_investment': max((total_income - total_expenses) * 0.2, 0)
    }
    
    # Get investment recommendations with error handling
    try:
        recommendations = investment_ai.recommend_investments(user_profile)
    except Exception as e:
        logger.error(f"Error in investment analysis: {e}")
        # Return fallback recommendations
        recommendations = {
            'recommended_type': 'balanced',
            'allocation': {
                'equity': 60,
                'debt': 30,
                'gold': 10
            },
            'risk_score': user_profile.get('risk_tolerance', 'medium'),
            'monthly_investment': user_profile.get('available_investment', 0),
            'note': 'Using fallback recommendations due to model error'
        }
    
    return jsonify(recommendations)

@app.route('/api/analyze/savings-forecast', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def forecast_savings():
    user = get_current_user()
    
    # Get historical savings data
    incomes = Income.query.filter_by(user_id=user.id).order_by(Income.date).all()
    expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date).all()
    
    # Calculate monthly savings for last 12 months
    monthly_savings = []
    for i in range(12):
        month_start = datetime.now() - timedelta(days=30*(12-i))
        month_end = month_start + timedelta(days=30)
        
        month_income = sum([inc.amount for inc in incomes if inc.date and month_start.date() <= inc.date < month_end.date()])
        month_expense = sum([exp.amount for exp in expenses if exp.date and month_start.date() <= exp.date < month_end.date()])
        
        monthly_savings.append(month_income - month_expense)
    
    # Filter out months with no data
    monthly_savings = [s for s in monthly_savings if s != 0]
    
    # Forecast next 12 months
    forecast = savings_ai.forecast_savings(monthly_savings, periods=12)
    
    return jsonify(forecast)

@app.route('/api/analyze/debt-management', methods=['GET'])
@cache.cached(timeout=300, query_string=True, key_prefix=user_cache_key)
def analyze_debt():
    user = get_current_user()
    debts = Debt.query.filter_by(user_id=user.id).all()
    
    debts_data = [{
        'name': d.name,
        'current_balance': d.current_balance,
        'interest_rate': d.interest_rate,
        'minimum_payment': d.minimum_payment
    } for d in debts]
    
    # Get extra payment amount from query params
    extra_payment = float(request.args.get('extra_payment', 0))
    
    # Compare different strategies
    comparison = debt_ai.compare_strategies(debts_data, extra_payment)
    
    # Get detailed plan for recommended strategy
    recommended_plan = debt_ai.create_repayment_plan(
        debts_data, 
        extra_payment, 
        comparison['recommended']
    )
    
    return jsonify({
        'comparison': comparison,
        'recommended_plan': recommended_plan
    })

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

# Report generation endpoint
@app.route('/api/generate-report', methods=['GET'])
def generate_report():
    user = User.query.first()
    report_type = request.args.get('type', 'monthly')
    
    # Get all financial data
    incomes = Income.query.filter_by(user_id=user.id).all()
    expenses = Expense.query.filter_by(user_id=user.id).all()
    debts = Debt.query.filter_by(user_id=user.id).all()
    goals = SavingsGoal.query.filter_by(user_id=user.id).all()
    
    # Generate report
    report_path = report_gen.generate_monthly_report(
        user_name=user.name,
        incomes=incomes,
        expenses=expenses,
        debts=debts,
        goals=goals
    )
    
    return send_file(report_path, as_attachment=True)

# Indian Banking Features - File Upload & Processing
# Note: Statement upload/import routes are now handled by statement_bp blueprint
# registered with url_prefix='/api' in the blueprint registration section above

@app.route('/api/analyze/anomalies', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def detect_anomalies():
    """Detect unusual spending patterns"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get user expenses
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if len(expenses) < 10:
            return jsonify({
                'anomalies': [],
                'message': 'Not enough data to detect anomalies (need at least 10 transactions)'
            })
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': e.date,
            'description': e.description or e.category,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        # Detect anomalies
        anomalies = anomaly_detector.detect(df)
        
        return jsonify({
            'anomalies': anomalies,
            'total_transactions': len(expenses),
            'anomaly_count': len(anomalies),
            'anomaly_percentage': (len(anomalies) / len(expenses)) * 100
        })
        
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecast/lstm', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def forecast_lstm():
    """Forecast expenses using LSTM model"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    periods = int(request.args.get('periods', 3))
    
    try:
        # Get user expenses
        expenses = Expense.query.filter_by(user_id=user.id).order_by(Expense.date).all()
        
        if len(expenses) < 3:
            # Return sample data for demo
            return jsonify({
                'overall_forecast': [25000, 27000, 26500, 28000, 26000, 29000],
                'category_forecasts': {
                    'groceries': [8000, 8200, 8100],
                    'utilities': [3000, 3100, 3050],
                    'transportation': [5000, 5200, 5100]
                },
                'historical_months': 0,
                'message': 'Sample LSTM forecast data (add more expenses for real predictions)'
            })
        
        # Calculate monthly expenses
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        df['date'] = pd.to_datetime(df['date'])
        monthly = df.groupby(df['date'].dt.to_period('M'))['amount'].sum()
        
        # Simple forecast fallback if LSTM not available
        if not LSTM_AVAILABLE or not lstm_forecaster:
            # Simple moving average forecast
            recent_avg = monthly.tail(3).mean() if len(monthly) >= 3 else monthly.mean()
            forecast = [recent_avg * (1 + np.random.uniform(-0.1, 0.1)) for _ in range(periods)]
        else:
            try:
                forecast = lstm_forecaster.forecast(monthly.values.tolist(), periods)
            except:
                # Fallback to simple forecast
                recent_avg = monthly.tail(3).mean() if len(monthly) >= 3 else monthly.mean()
                forecast = [recent_avg * (1 + np.random.uniform(-0.1, 0.1)) for _ in range(periods)]
        
        # Simple category forecasts
        category_monthly = df.groupby(['category', df['date'].dt.to_period('M')])['amount'].sum().unstack(fill_value=0)
        category_forecasts = {}
        for category in df['category'].unique():
            if category in category_monthly.index:
                cat_data = category_monthly.loc[category]
                cat_avg = cat_data.tail(3).mean() if len(cat_data) >= 3 else cat_data.mean()
                category_forecasts[category] = [cat_avg * (1 + np.random.uniform(-0.1, 0.1)) for _ in range(periods)]
        
        return jsonify({
            'overall_forecast': forecast,
            'category_forecasts': category_forecasts,
            'historical_months': len(monthly)
        })
        
    except Exception as e:
        logger.error(f"Error forecasting with LSTM: {e}")
        # Return sample data on error
        return jsonify({
            'overall_forecast': [25000, 27000, 26500, 28000, 26000, 29000],
            'category_forecasts': {
                'groceries': [8000, 8200, 8100],
                'utilities': [3000, 3100, 3050],
                'transportation': [5000, 5200, 5100]
            },
            'historical_months': 0,
            'message': 'Sample forecast data due to error'
        })

@app.route('/api/visualize/spending-trends', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def visualize_spending():
    """Generate interactive Plotly visualization of spending trends"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not expenses:
            return jsonify({'chart': None, 'message': 'No expense data available'})
        
        # Create DataFrame
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        df['date'] = pd.to_datetime(df['date'])
        
        # Monthly spending trend
        monthly = df.groupby(df['date'].dt.to_period('M').astype(str))['amount'].sum().reset_index()
        monthly.columns = ['month', 'amount']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly['month'],
            y=monthly['amount'],
            mode='lines+markers',
            name='Monthly Expenses',
            line=dict(color='#e74c3c', width=3)
        ))
        
        fig.update_layout(
            title='Monthly Spending Trend',
            xaxis_title='Month',
            yaxis_title='Amount (₹)',
            template='plotly_white'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
        
    except Exception as e:
        logger.error(f"Error generating visualization: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualize/category-breakdown', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def visualize_categories():
    """Generate category-wise spending pie chart"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not expenses:
            return jsonify({'chart': None, 'message': 'No expense data available'})
        
        # Category breakdown
        df = pd.DataFrame([{
            'category': e.category,
            'amount': e.amount
        } for e in expenses])
        
        category_totals = df.groupby('category')['amount'].sum().reset_index()
        
        fig = px.pie(
            category_totals,
            values='amount',
            names='category',
            title='Expense Breakdown by Category',
            hole=0.3,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
        
    except Exception as e:
        logger.error(f"Error generating category visualization: {e}")
        return jsonify({'error': str(e)}), 500

# Advanced AI Features
@app.route('/api/predict/spending', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def predict_spending():
    """Predict next month's expenses by category"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if len(expenses) < 5:
            return jsonify({
                'message': 'Need at least 5 transactions for prediction',
                'predictions': {}
            })
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        predictions = spending_predictor.predict_next_month(df)
        total_predicted = sum(predictions.values())
        
        return jsonify({
            'predictions': predictions,
            'total_predicted': total_predicted,
            'next_month': (datetime.now() + timedelta(days=30)).strftime('%Y-%m'),
            'categories_count': len(predictions)
        })
        
    except Exception as e:
        logger.error(f"Error predicting spending: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimize/budget', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def optimize_budget():
    """Get AI-suggested budget optimizations"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get user income and expenses
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        total_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
        
        if total_income <= 0 or not expenses:
            return jsonify({'error': 'Need income and expense data for optimization'}), 400
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'category': e.category,
            'amount': e.amount
        } for e in expenses])
        
        optimization = budget_optimizer.optimize_budget(total_income, df)
        
        return jsonify(optimization)
        
    except Exception as e:
        logger.error(f"Error optimizing budget: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect/fraud', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def detect_fraud():
    """Detect suspicious transactions"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if len(expenses) < 10:
            return jsonify({
                'suspicious_transactions': [],
                'message': 'Need at least 10 transactions for fraud detection'
            })
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': e.date,
            'description': e.description or e.category,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        suspicious = fraud_detector.detect_fraud(df)
        
        return jsonify({
            'suspicious_transactions': suspicious,
            'total_transactions': len(expenses),
            'suspicious_count': len(suspicious),
            'fraud_rate': (len(suspicious) / len(expenses)) * 100
        })
        
    except Exception as e:
        logger.error(f"Error detecting fraud: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/forecast/cashflow', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def forecast_cashflow():
    """6-month cashflow predictions"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    periods = int(request.args.get('periods', 6))
    
    try:
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not incomes and not expenses:
            return jsonify({'error': 'Need income and expense data for forecasting'}), 400
        
        # Convert to DataFrames
        income_df = pd.DataFrame([{
            'date': i.date,
            'amount': i.amount
        } for i in incomes]) if incomes else pd.DataFrame()
        
        expense_df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount
        } for e in expenses]) if expenses else pd.DataFrame()
        
        forecast = cashflow_forecaster.forecast_cashflow(income_df, expense_df, periods)
        
        return jsonify(forecast)
        
    except Exception as e:
        logger.error(f"Error forecasting cashflow: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/insights', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_ai_insights():
    """Get comprehensive AI insights"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get all data
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        total_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
        
        insights = {
            'spending_prediction': None,
            'budget_optimization': None,
            'fraud_detection': None,
            'cashflow_forecast': None
        }
        
        if len(expenses) >= 5:
            # Spending prediction
            expense_df = pd.DataFrame([{
                'date': e.date,
                'amount': e.amount,
                'category': e.category
            } for e in expenses])
            
            predictions = spending_predictor.predict_next_month(expense_df)
            insights['spending_prediction'] = {
                'total_predicted': sum(predictions.values()),
                'top_categories': dict(sorted(predictions.items(), key=lambda x: x[1], reverse=True)[:5])
            }
            
            # Budget optimization
            if total_income > 0:
                optimization = budget_optimizer.optimize_budget(total_income, expense_df)
                insights['budget_optimization'] = {
                    'potential_savings': optimization.get('potential_savings', 0),
                    'suggestions_count': len(optimization.get('suggestions', []))
                }
            
            # Fraud detection
            if len(expenses) >= 10:
                suspicious = fraud_detector.detect_fraud(expense_df)
                insights['fraud_detection'] = {
                    'suspicious_count': len(suspicious),
                    'fraud_rate': (len(suspicious) / len(expenses)) * 100
                }
        
        # Cashflow forecast
        if incomes or expenses:
            income_df = pd.DataFrame([{'date': i.date, 'amount': i.amount} for i in incomes]) if incomes else pd.DataFrame()
            expense_df = pd.DataFrame([{'date': e.date, 'amount': e.amount} for e in expenses]) if expenses else pd.DataFrame()
            
            forecast = cashflow_forecaster.forecast_cashflow(income_df, expense_df, 3)
            insights['cashflow_forecast'] = {
                'avg_monthly_cashflow': forecast['summary']['avg_monthly_cashflow'],
                'total_cashflow_3m': forecast['summary'].get('total_cashflow_6m', 0) / 2
            }
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Error generating AI insights: {e}")
        return jsonify({'error': str(e)}), 500

# Indian-Specific Features
@app.route('/api/tax/calculate', methods=['POST'])
def calculate_tax():
    """Calculate Indian income tax with deductions"""
    data = request.get_json(force=True)
    
    try:
        result = tax_planner.calculate_tax(
            annual_income=data.get('annual_income', 0),
            investments_80c=data.get('investments_80c', 0),
            hra_received=data.get('hra_received', 0),
            rent_paid=data.get('rent_paid', 0),
            is_metro=data.get('is_metro', True),
            regime=data.get('regime', 'old')
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating tax: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tax/capital-gains', methods=['POST'])
def calculate_capital_gains():
    """Calculate capital gains tax"""
    data = request.get_json(force=True)
    
    try:
        purchase_date = datetime.strptime(data['purchase_date'], '%Y-%m-%d')
        sale_date = datetime.strptime(data['sale_date'], '%Y-%m-%d')
        
        result = tax_planner.calculate_capital_gains(
            purchase_price=data['purchase_price'],
            sale_price=data['sale_price'],
            purchase_date=purchase_date,
            sale_date=sale_date,
            asset_type=data.get('asset_type', 'equity')
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating capital gains: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gst/calculate', methods=['POST'])
def calculate_gst():
    """Calculate GST breakdown"""
    data = request.get_json(force=True)
    
    try:
        result = gst_tracker.calculate_gst(
            amount=data['amount'],
            gst_rate=data.get('gst_rate', 0.18),
            inclusive=data.get('inclusive', True)
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating GST: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/gst/track', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def track_gst():
    """Track GST from business expenses"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get business expenses (assuming category contains 'business')
        expenses = Expense.query.filter(
            Expense.user_id == user.id,
            Expense.category.contains('business')
        ).all()
        
        if not expenses:
            return jsonify({
                'total_gst_paid': 0,
                'message': 'No business expenses found'
            })
        
        df = pd.DataFrame([{
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        result = gst_tracker.track_gst_expenses(df)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error tracking GST: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investment/sip', methods=['POST'])
def calculate_sip():
    """Calculate SIP returns"""
    data = request.get_json(force=True)
    
    try:
        result = investment_tracker.calculate_sip_returns(
            monthly_amount=data['monthly_amount'],
            annual_return=data.get('annual_return', 0.12),
            years=data['years']
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating SIP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investment/fd', methods=['POST'])
def calculate_fd():
    """Calculate FD returns"""
    data = request.get_json(force=True)
    
    try:
        result = investment_tracker.calculate_fd_returns(
            principal=data['principal'],
            rate=data.get('rate', 0.065),
            years=data['years'],
            compound_frequency=data.get('compound_frequency', 4)
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating FD: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investment/ppf', methods=['POST'])
def calculate_ppf():
    """Calculate PPF returns"""
    data = request.get_json(force=True)
    
    try:
        result = investment_tracker.calculate_ppf_returns(
            annual_contribution=data['annual_contribution'],
            years=data.get('years', 15)
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating PPF: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/emi/calculate', methods=['POST'])
def calculate_emi():
    """Calculate EMI for loan"""
    data = request.get_json(force=True)
    
    try:
        result = emi_calculator.calculate_emi(
            principal=data['principal'],
            rate=data['rate'],
            tenure_months=data['tenure_months']
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error calculating EMI: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/emi/compare', methods=['POST'])
def compare_loans():
    """Compare multiple loan options"""
    data = request.get_json(force=True)
    
    try:
        result = emi_calculator.loan_comparison(
            principal=data['principal'],
            options=data['options']
        )
        
        return jsonify({
            'comparisons': result,
            'best_option': result[0] if result else None
        })
        
    except Exception as e:
        logger.error(f"Error comparing loans: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/emi/prepayment', methods=['POST'])
def analyze_prepayment():
    """Analyze loan prepayment impact"""
    data = request.get_json(force=True)
    
    try:
        result = emi_calculator.prepayment_analysis(
            principal=data['principal'],
            rate=data['rate'],
            tenure_months=data['tenure_months'],
            prepayment_amount=data['prepayment_amount'],
            prepayment_month=data['prepayment_month']
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error analyzing prepayment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/indian/dashboard', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def indian_dashboard():
    """Indian-specific financial dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get user data
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        annual_income = sum([i.amount for i in incomes if i.frequency == 'monthly']) * 12
        
        dashboard = {
            'tax_planning': None,
            'gst_summary': None,
            'investment_suggestions': None,
            'loan_optimization': None
        }
        
        # Tax planning
        if annual_income > 0:
            tax_calc = tax_planner.calculate_tax(annual_income)
            dashboard['tax_planning'] = {
                'annual_income': annual_income,
                'total_tax': tax_calc['total_tax'],
                'effective_rate': tax_calc['effective_tax_rate'],
                'potential_80c_savings': min(150000, annual_income * 0.1) * 0.3  # Assume 30% tax bracket
            }
        
        # GST tracking
        business_expenses = [e for e in expenses if 'business' in e.category.lower()]
        if business_expenses:
            df = pd.DataFrame([{'amount': e.amount, 'category': e.category} for e in business_expenses])
            gst_summary = gst_tracker.track_gst_expenses(df)
            dashboard['gst_summary'] = gst_summary
        
        # Investment suggestions
        monthly_surplus = (annual_income / 12) - sum([e.amount for e in expenses])
        if monthly_surplus > 0:
            sip_projection = investment_tracker.calculate_sip_returns(monthly_surplus * 0.3, 0.12, 10)
            ppf_projection = investment_tracker.calculate_ppf_returns(min(150000, monthly_surplus * 12))
            
            dashboard['investment_suggestions'] = {
                'monthly_surplus': monthly_surplus,
                'sip_10yr_value': sip_projection['future_value'],
                'ppf_15yr_value': ppf_projection['maturity_amount']
            }
        
        return jsonify(dashboard)
        
    except Exception as e:
        logger.error(f"Error generating Indian dashboard: {e}")
        return jsonify({'error': str(e)}), 500

# Dashboard Improvements
@app.route('/api/notifications', methods=['GET'])
@cache.cached(timeout=60, key_prefix=user_cache_key)
def get_notifications():
    """Get real-time notifications"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Gather user data
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        debts = Debt.query.filter_by(user_id=user.id).all()
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        
        user_data = {
            'monthly_income': sum([i.amount for i in incomes if i.frequency == 'monthly']),
            'expenses': [{
                'date': e.date.strftime('%Y-%m-%d'),
                'amount': e.amount,
                'category': e.category
            } for e in expenses],
            'debts': [{
                'name': d.name,
                'minimum_payment': d.minimum_payment,
                'due_date': d.due_date.strftime('%Y-%m-%d') if d.due_date else None
            } for d in debts],
            'savings_goals': [{
                'name': g.name,
                'current_amount': g.current_amount,
                'target_amount': g.target_amount,
                'target_date': g.target_date.strftime('%Y-%m-%d') if g.target_date else None
            } for g in goals]
        }
        
        notifications = notification_manager.generate_notifications(user_data)
        
        return jsonify({
            'notifications': notifications,
            'count': len(notifications),
            'unread_count': len([n for n in notifications if not n.get('read', False)])
        })
        
    except Exception as e:
        logger.error(f"Error generating notifications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charts/spending-analysis', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_spending_analysis_chart():
    """Get interactive spending analysis chart"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not expenses:
            return jsonify({'chart': None, 'message': 'No expense data available'})
        
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        chart_json = interactive_charts.create_spending_analysis_chart(df)
        
        return chart_json, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error creating spending analysis chart: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charts/category-drilldown', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_category_drilldown():
    """Get category drill-down chart"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    month = request.args.get('month')  # Optional month filter
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not expenses:
            return jsonify({'chart': None, 'message': 'No expense data available'})
        
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        chart_json = interactive_charts.create_category_drill_down(df, month)
        
        return chart_json, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error creating category drill-down: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/charts/expense-trends', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_expense_trends():
    """Get expense trend comparison chart"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not expenses:
            return jsonify({'chart': None, 'message': 'No expense data available'})
        
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        chart_json = interactive_charts.create_trend_comparison_chart(df)
        
        return chart_json, 200, {'Content-Type': 'application/json'}
        
    except Exception as e:
        logger.error(f"Error creating trend chart: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/goals/progress', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_goal_progress():
    """Get visual goal progress tracking"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        
        if not goals:
            return jsonify({
                'chart': None,
                'insights': {'insights': [], 'total_goals': 0},
                'message': 'No savings goals found'
            })
        
        goals_data = [{
            'name': g.name,
            'current_amount': g.current_amount,
            'target_amount': g.target_amount,
            'target_date': g.target_date.strftime('%Y-%m-%d') if g.target_date else None
        } for g in goals]
        
        # Calculate monthly savings
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        monthly_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
        monthly_expenses = sum([e.amount for e in expenses])
        monthly_savings = monthly_income - monthly_expenses
        
        chart_json = goal_tracker.create_goal_progress_chart(goals_data)
        insights = goal_tracker.calculate_goal_insights(goals_data, monthly_savings)
        
        return jsonify({
            'chart': json.loads(chart_json),
            'insights': insights,
            'monthly_savings': monthly_savings
        })
        
    except Exception as e:
        logger.error(f"Error creating goal progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trends/analysis', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_trend_analysis():
    """Get detailed expense trend analysis"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        expenses = Expense.query.filter_by(user_id=user.id).all()
        
        if not expenses:
            return jsonify({'error': 'No expense data available'}), 400
        
        df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses])
        
        analysis = expense_analyzer.analyze_trends(df)
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/enhanced', methods=['GET'])
@cache.cached(timeout=60, key_prefix=user_cache_key)
def get_enhanced_dashboard():
    """Get comprehensive enhanced dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get all user data
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).all()
        debts = Debt.query.filter_by(user_id=user.id).all()
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        
        # Prepare data for analysis
        user_data = {
            'monthly_income': sum([i.amount for i in incomes if i.frequency == 'monthly']),
            'expenses': [{
                'date': e.date.strftime('%Y-%m-%d'),
                'amount': e.amount,
                'category': e.category
            } for e in expenses],
            'debts': [{
                'name': d.name,
                'minimum_payment': d.minimum_payment,
                'due_date': d.due_date.strftime('%Y-%m-%d') if d.due_date else None
            } for d in debts],
            'savings_goals': [{
                'name': g.name,
                'current_amount': g.current_amount,
                'target_amount': g.target_amount,
                'target_date': g.target_date.strftime('%Y-%m-%d') if g.target_date else None
            } for g in goals]
        }
        
        # Generate dashboard components
        notifications = notification_manager.generate_notifications(user_data)[:5]  # Top 5
        
        # Expense analysis
        expense_df = pd.DataFrame([{
            'date': e.date,
            'amount': e.amount,
            'category': e.category
        } for e in expenses]) if expenses else pd.DataFrame()
        
        trend_analysis = expense_analyzer.analyze_trends(expense_df) if not expense_df.empty else {}
        
        # Goal insights
        monthly_savings = user_data['monthly_income'] - sum([e['amount'] for e in user_data['expenses']])
        goal_insights = goal_tracker.calculate_goal_insights(user_data['savings_goals'], monthly_savings)
        
        return jsonify({
            'notifications': notifications,
            'trend_analysis': trend_analysis,
            'goal_insights': goal_insights,
            'summary': {
                'total_notifications': len(notifications),
                'high_priority_alerts': len([n for n in notifications if n['priority'] == 'high']),
                'goals_on_track': len([i for i in goal_insights.get('insights', []) if i['status'] == 'on_track']),
                'monthly_savings': monthly_savings
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating enhanced dashboard: {e}")
        return jsonify({'error': str(e)}), 500

# Mobile & Accessibility Features
@app.route('/api/receipt/scan', methods=['POST'])
def scan_receipt():
    """Scan receipt using OCR"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Scan receipt
        result = receipt_scanner.parse_receipt(filepath)
        
        # Clean up
        os.remove(filepath)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'success': True,
            'transaction': result,
            'message': f'Receipt scanned successfully. Confidence: {result["confidence"]*100:.0f}%'
        })
        
    except Exception as e:
        logger.error(f"Error scanning receipt: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/listen', methods=['POST'])
def listen_voice_command():
    """Listen for voice command"""
    timeout = int(request.json.get('timeout', 5)) if request.json else 5
    
    try:
        command = voice_processor.listen_for_command(timeout)
        
        if command in ['timeout', 'could_not_understand', 'service_error', 'error']:
            return jsonify({
                'success': False,
                'error': command,
                'message': {
                    'timeout': 'No voice detected within timeout',
                    'could_not_understand': 'Could not understand the command',
                    'service_error': 'Speech recognition service error',
                    'error': 'Unknown error occurred'
                }.get(command, 'Unknown error')
            })
        
        return jsonify({
            'success': True,
            'command': command,
            'message': 'Voice command captured successfully'
        })
        
    except Exception as e:
        logger.error(f"Error listening to voice: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/process', methods=['POST'])
def process_voice_command():
    """Process voice command and extract transaction"""
    data = request.get_json(force=True)
    command = data.get('command', '')
    
    if not command:
        return jsonify({'error': 'No command provided'}), 400
    
    try:
        result = voice_processor.process_command(command)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify({
            'success': True,
            'transaction': result,
            'message': f'Command processed: {result["type"]} of ₹{result["amount"]:,.0f}'
        })
        
    except Exception as e:
        logger.error(f"Error processing voice command: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/voice/add-transaction', methods=['POST'])
def add_voice_transaction():
    """Add transaction from voice command"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    transaction = data.get('transaction', {})
    
    try:
        if transaction.get('type') == 'expense':
            expense = Expense(
                user_id=user.id,
                category=transaction.get('category', 'other'),
                description=transaction.get('description', ''),
                amount=transaction.get('amount', 0),
                date=datetime.strptime(transaction['date'], '%Y-%m-%d').date(),
                is_recurring=False
            )
            db.session.add(expense)
            
        elif transaction.get('type') == 'income':
            income = Income(
                user_id=user.id,
                source=transaction.get('source', 'Voice Entry'),
                amount=transaction.get('amount', 0),
                frequency='one-time',
                date=datetime.strptime(transaction['date'], '%Y-%m-%d').date()
            )
            db.session.add(income)
        
        else:
            return jsonify({'error': 'Invalid transaction type'}), 400
        
        db.session.commit()
        cache.clear()
        
        return jsonify({
            'success': True,
            'message': f'{transaction["type"].title()} of ₹{transaction["amount"]:,.0f} added successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding voice transaction: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/offline/add', methods=['POST'])
def add_offline_transaction():
    """Add transaction to offline queue"""
    data = request.get_json(force=True)
    
    try:
        transaction_id = offline_manager.add_pending_transaction(data)
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'message': 'Transaction queued for sync when online'
        })
        
    except Exception as e:
        logger.error(f"Error adding offline transaction: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/offline/sync', methods=['POST'])
def sync_offline_transactions():
    """Sync pending offline transactions"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        pending = offline_manager.get_pending_transactions()
        synced_count = 0
        
        for transaction in pending:
            try:
                if transaction.get('type') == 'expense':
                    expense = Expense(
                        user_id=user.id,
                        category=transaction.get('category', 'other'),
                        description=transaction.get('description', ''),
                        amount=transaction.get('amount', 0),
                        date=datetime.strptime(transaction['date'], '%Y-%m-%d').date(),
                        is_recurring=False
                    )
                    db.session.add(expense)
                    
                elif transaction.get('type') == 'income':
                    income = Income(
                        user_id=user.id,
                        source=transaction.get('source', 'Offline Entry'),
                        amount=transaction.get('amount', 0),
                        frequency='one-time',
                        date=datetime.strptime(transaction['date'], '%Y-%m-%d').date()
                    )
                    db.session.add(income)
                
                offline_manager.mark_transaction_synced(transaction['id'])
                synced_count += 1
                
            except Exception as e:
                logger.error(f"Error syncing transaction {transaction['id']}: {e}")
                continue
        
        db.session.commit()
        cache.clear()
        
        return jsonify({
            'success': True,
            'synced_count': synced_count,
            'message': f'Synced {synced_count} offline transactions'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing offline transactions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/offline/status', methods=['GET'])
def get_offline_status():
    """Get offline mode status"""
    try:
        summary = offline_manager.get_offline_summary()
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting offline status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/manifest.json', methods=['GET'])
def get_pwa_manifest():
    """Get PWA manifest"""
    return jsonify(pwa_manager.get_manifest())

@app.route('/sw.js', methods=['GET'])
def get_service_worker():
    """Get service worker for PWA"""
    sw_content = pwa_manager.generate_service_worker()
    response = app.response_class(
        response=sw_content,
        status=200,
        mimetype='application/javascript'
    )
    return response

@app.route('/api/mobile/dashboard', methods=['GET'])
@cache.cached(timeout=60, key_prefix=user_cache_key)
def get_mobile_dashboard():
    """Get mobile-optimized dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get essential data for mobile
        incomes = Income.query.filter_by(user_id=user.id).all()
        expenses = Expense.query.filter_by(user_id=user.id).limit(10).all()  # Recent 10
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        
        # Calculate quick stats
        monthly_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
        monthly_expenses = sum([e.amount for e in expenses])
        total_goals = sum([g.target_amount for g in goals])
        total_saved = sum([g.current_amount for g in goals])
        
        # Get offline status
        offline_status = offline_manager.get_offline_summary()
        
        return jsonify({
            'summary': {
                'monthly_income': monthly_income,
                'monthly_expenses': monthly_expenses,
                'net_savings': monthly_income - monthly_expenses,
                'goals_progress': (total_saved / total_goals * 100) if total_goals > 0 else 0
            },
            'recent_expenses': [{
                'description': e.description or e.category,
                'amount': e.amount,
                'category': e.category,
                'date': e.date.strftime('%Y-%m-%d')
            } for e in expenses],
            'offline_status': offline_status,
            'quick_actions': [
                {'action': 'add_expense', 'label': 'Add Expense', 'icon': '💸'},
                {'action': 'scan_receipt', 'label': 'Scan Receipt', 'icon': '📷'},
                {'action': 'voice_command', 'label': 'Voice Entry', 'icon': '🎤'},
                {'action': 'view_goals', 'label': 'Goals', 'icon': '🎯'}
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting mobile dashboard: {e}")
        return jsonify({'error': str(e)}), 500

# Performance & Scalability Features
@app.route('/api/performance/optimize-db', methods=['POST'])
def optimize_database():
    """Optimize database performance"""
    try:
        db_optimizer.create_indexes()
        db_optimizer.optimize_queries()
        
        return jsonify({
            'success': True,
            'message': 'Database optimized successfully'
        })
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/cache-stats', methods=['GET'])
def get_cache_stats():
    """Get cache performance statistics"""
    try:
        cache_stats = performance_monitor.get_cache_stats()
        query_stats = performance_monitor.get_performance_stats()
        
        return jsonify({
            'cache_stats': cache_stats,
            'query_stats': query_stats,
            'cache_available': cache_manager.mc is not None
        })
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/clear-cache', methods=['POST'])
def clear_user_cache():
    """Clear user cache"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        cache_manager.clear_user_cache(user.id)
        
        return jsonify({
            'success': True,
            'message': 'User cache cleared successfully'
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/background/generate-report', methods=['POST'])
def generate_report_async():
    """Generate monthly report in background"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    year = data.get('year', datetime.now().year)
    month = data.get('month', datetime.now().month)
    
    try:
        if task_manager.celery:
            task = celery_tasks['generate_monthly_report'].delay(user.id, year, month)
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'message': 'Report generation started in background'
            })
        else:
            return jsonify({'error': 'Background processing not available'}), 503
            
    except Exception as e:
        logger.error(f"Error starting background report generation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/background/analyze-spending', methods=['POST'])
def analyze_spending_async():
    """Analyze spending patterns in background"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        if task_manager.celery:
            task = celery_tasks['analyze_spending_patterns'].delay(user.id)
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'message': 'Spending analysis started in background'
            })
        else:
            return jsonify({'error': 'Background processing not available'}), 503
            
    except Exception as e:
        logger.error(f"Error starting background analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/background/bulk-import', methods=['POST'])
def bulk_import_async():
    """Import bulk transactions in background"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    transactions = data.get('transactions', [])
    
    if not transactions:
        return jsonify({'error': 'No transactions provided'}), 400
    
    try:
        if task_manager.celery:
            task = celery_tasks['process_bulk_transactions'].delay(user.id, transactions)
            
            return jsonify({
                'success': True,
                'task_id': task.id,
                'transaction_count': len(transactions),
                'message': 'Bulk import started in background'
            })
        else:
            return jsonify({'error': 'Background processing not available'}), 503
            
    except Exception as e:
        logger.error(f"Error starting bulk import: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/background/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """Get background task status"""
    try:
        if not task_manager.celery:
            return jsonify({'error': 'Background processing not available'}), 503
        
        task = task_manager.celery.AsyncResult(task_id)
        
        return jsonify({
            'task_id': task_id,
            'status': task.status,
            'result': task.result if task.ready() else None,
            'info': task.info
        })
        
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({'error': str(e)}), 500

# Optimized dashboard endpoint with caching
@app.route('/api/dashboard/optimized', methods=['GET'])
def get_optimized_dashboard():
    """Get dashboard with performance optimizations"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check cache first
    cached_data = cache_manager.get_dashboard_data(user.id)
    if cached_data:
        return jsonify(cached_data)
    
    try:
        start_time = datetime.now()
        
        # Use optimized queries
        current_month = datetime.now()
        monthly_summary = db_optimizer.get_monthly_summary(
            user.id, current_month.year, current_month.month
        )
        
        # Get recent expenses with optimized query
        recent_expenses = db_optimizer.get_optimized_expenses(
            user.id, limit=10, date_from=datetime.now() - timedelta(days=30)
        )
        
        # Get goals
        goals = SavingsGoal.query.filter_by(user_id=user.id).all()
        
        dashboard_data = {
            'monthly_summary': monthly_summary,
            'recent_expenses': recent_expenses,
            'goals_progress': [{
                'name': g.name,
                'progress': (g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0,
                'remaining': g.target_amount - g.current_amount
            } for g in goals],
            'quick_stats': {
                'total_goals': len(goals),
                'completed_goals': len([g for g in goals if g.current_amount >= g.target_amount]),
                'savings_rate': (monthly_summary['net_savings'] / monthly_summary['income'] * 100) if monthly_summary['income'] > 0 else 0
            }
        }
        
        # Cache the result
        cache_manager.cache_dashboard_data(user.id, dashboard_data, timeout=60)
        
        # Track performance
        execution_time = (datetime.now() - start_time).total_seconds()
        performance_monitor.track_query_time('optimized_dashboard', execution_time)
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        logger.error(f"Error getting optimized dashboard: {e}")
        return jsonify({'error': str(e)}), 500

# Security & Privacy Features
@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    """Send OTP for multi-factor authentication"""
    data = request.get_json(force=True)
    email = data.get('email')
    phone = data.get('phone')
    user_name = data.get('name', 'User')
    
    if not email and not phone:
        return jsonify({'error': 'Email or phone required'}), 400
    
    try:
        if email:
            result = mfa_auth.send_email_otp(email, user_name)
        else:
            result = mfa_auth.send_sms_otp(phone)
        
        # Log OTP request
        audit_logger.log_action(
            user_id=0,  # Anonymous request
            action='OTP_REQUEST',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error sending OTP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP for multi-factor authentication"""
    data = request.get_json(force=True)
    identifier = data.get('email') or data.get('phone')
    otp = data.get('otp')
    
    if not identifier or not otp:
        return jsonify({'error': 'Identifier and OTP required'}), 400
    
    try:
        result = mfa_auth.verify_otp(identifier, otp)
        
        # Log verification attempt
        audit_logger.log_action(
            user_id=0,  # Anonymous request
            action=f"OTP_VERIFY_{'SUCCESS' if result['success'] else 'FAILED'}",
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error verifying OTP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/encrypt-data', methods=['POST'])
def encrypt_sensitive_data():
    """Encrypt sensitive data"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    sensitive_data = data.get('data')
    
    if not sensitive_data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        encrypted_data = data_encryption.encrypt(sensitive_data)
        
        # Log encryption request
        audit_logger.log_action(
            user_id=user.id,
            action='DATA_ENCRYPT',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'encrypted_data': encrypted_data,
            'message': 'Data encrypted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error encrypting data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/audit-log', methods=['GET'])
def get_audit_log():
    """Get user audit log"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    limit = int(request.args.get('limit', 50))
    
    try:
        audit_log = audit_logger.get_user_audit_log(user.id, limit)
        
        return jsonify({
            'audit_log': audit_log,
            'total_entries': len(audit_log)
        })
        
    except Exception as e:
        logger.error(f"Error getting audit log: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/events', methods=['GET'])
def get_security_events():
    """Get security events (admin only)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    hours = int(request.args.get('hours', 24))
    
    try:
        events = audit_logger.get_security_events(hours)
        
        return jsonify({
            'security_events': events,
            'period_hours': hours,
            'event_count': len(events)
        })
        
    except Exception as e:
        logger.error(f"Error getting security events: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/create', methods=['POST'])
def create_backup():
    """Create manual backup"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        result = backup_manager.create_backup('manual')
        
        # Log backup creation
        audit_logger.log_action(
            user_id=user.id,
            action='BACKUP_CREATE',
            ip_address=request.remote_addr
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/list', methods=['GET'])
def list_backups():
    """List available backups"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        backups = backup_manager.list_backups()
        
        return jsonify({
            'backups': backups,
            'backup_count': len(backups)
        })
        
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backup/restore', methods=['POST'])
def restore_backup():
    """Restore from backup"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    backup_path = data.get('backup_path')
    
    if not backup_path:
        return jsonify({'error': 'Backup path required'}), 400
    
    try:
        result = backup_manager.restore_backup(backup_path)
        
        # Log backup restore
        audit_logger.log_action(
            user_id=user.id,
            action='BACKUP_RESTORE',
            new_values={'backup_path': backup_path},
            ip_address=request.remote_addr
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error restoring backup: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/status', methods=['GET'])
def get_security_status():
    """Get overall security status"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        status = security_manager.get_security_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting security status: {e}")
        return jsonify({'error': str(e)}), 500

# Enhanced login with MFA and audit logging
@app.route('/api/auth/login-secure', methods=['POST'])
def secure_login():
    """Secure login with MFA and audit logging"""
    payload = request.get_json(force=True) or {}
    email = payload.get('email')
    otp = payload.get('otp')
    name = payload.get('name') or 'User'
    
    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    try:
        # Verify OTP if provided
        if otp:
            otp_result = mfa_auth.verify_otp(email, otp)
            if not otp_result['success']:
                # Log failed login
                audit_logger.log_login(
                    user_id=0,
                    success=False,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent'),
                    mfa_used=True
                )
                return jsonify(otp_result), 400
        
        # Find or create user
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email)
            db.session.add(user)
            db.session.commit()
            
            # Log new user creation
            audit_logger.log_data_change(
                user_id=user.id,
                table_name='user',
                record_id=user.id,
                action='CREATE',
                new_values={'name': name, 'email': email}
            )
        
        # Create access token
        token = create_access_token(identity=user.id)
        
        # Log successful login
        audit_logger.log_login(
            user_id=user.id,
            success=True,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            mfa_used=bool(otp)
        )
        
        return jsonify({
            'access_token': token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'age': user.age,
                'risk_tolerance': user.risk_tolerance
            },
            'mfa_verified': bool(otp)
        })
        
    except Exception as e:
        logger.error(f"Error in secure login: {e}")
        return jsonify({'error': str(e)}), 500

# Investment Management API Endpoints
@app.route('/api/investments/portfolio', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_portfolio():
    """Get user's investment portfolio"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        portfolio = investment_manager.portfolio_tracker.get_portfolio()
        summary = investment_manager.portfolio_tracker.get_portfolio_summary()
        
        return jsonify({
            'portfolio': [{
                'symbol': inv.symbol,
                'name': inv.name,
                'quantity': inv.quantity,
                'avg_price': inv.avg_price,
                'current_price': inv.current_price,
                'current_value': inv.current_value,
                'invested_amount': inv.invested_amount,
                'pnl': inv.pnl,
                'pnl_percentage': inv.pnl_percentage,
                'investment_type': inv.investment_type,
                'purchase_date': inv.purchase_date
            } for inv in portfolio],
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/add', methods=['POST'])
def add_investment():
    """Add new investment to portfolio"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        investment_manager.portfolio_tracker.add_investment(
            symbol=data['symbol'],
            name=data['name'],
            quantity=data['quantity'],
            avg_price=data['avg_price'],
            investment_type=data['investment_type'],
            purchase_date=data['purchase_date']
        )
        
        cache.clear()
        
        return jsonify({
            'success': True,
            'message': 'Investment added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding investment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/allocation', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_asset_allocation():
    """Get current and target asset allocation"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        current_allocation = investment_manager.asset_allocator.get_current_allocation()
        target_allocation = investment_manager.asset_allocator.get_target_allocation(
            user.age or 30, user.risk_tolerance or 'medium'
        )
        rebalancing = investment_manager.asset_allocator.get_rebalancing_suggestions(
            user.age or 30, user.risk_tolerance or 'medium'
        )
        
        return jsonify({
            'current_allocation': current_allocation,
            'target_allocation': target_allocation,
            'rebalancing_suggestions': rebalancing
        })
        
    except Exception as e:
        logger.error(f"Error getting asset allocation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/sip', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_sips():
    """Get active SIPs"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        active_sips = investment_manager.sip_manager.get_active_sips()
        
        # Calculate returns for each SIP
        sip_returns = []
        for sip in active_sips:
            returns = investment_manager.sip_manager.calculate_sip_returns(sip['id'])
            sip_returns.append(returns)
        
        return jsonify({
            'active_sips': active_sips,
            'sip_returns': sip_returns,
            'total_monthly_sip': sum(sip['amount'] for sip in active_sips)
        })
        
    except Exception as e:
        logger.error(f"Error getting SIPs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/sip/add', methods=['POST'])
def add_sip():
    """Add new SIP"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        investment_manager.sip_manager.add_sip(
            fund_name=data['fund_name'],
            amount=data['amount'],
            frequency=data.get('frequency', 'monthly'),
            start_date=data['start_date'],
            end_date=data.get('end_date')
        )
        
        cache.clear()
        
        return jsonify({
            'success': True,
            'message': 'SIP added successfully'
        })
        
    except Exception as e:
        logger.error(f"Error adding SIP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/sip/optimize', methods=['POST'])
def optimize_sip():
    """Optimize SIP amount for target corpus"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        optimization = investment_manager.sip_manager.optimize_sip_amount(
            current_amount=data['current_amount'],
            target_corpus=data['target_corpus'],
            years=data['years'],
            expected_return=data.get('expected_return', 12.0)
        )
        
        return jsonify(optimization)
        
    except Exception as e:
        logger.error(f"Error optimizing SIP: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/tax-loss', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_tax_loss_opportunities():
    """Get tax-loss harvesting opportunities"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    min_loss = float(request.args.get('min_loss_percentage', 10.0))
    
    try:
        opportunities = investment_manager.tax_harvester.identify_loss_opportunities(min_loss)
        capital_gains = investment_manager.tax_harvester.calculate_capital_gains()
        
        return jsonify({
            'loss_opportunities': opportunities,
            'capital_gains': capital_gains,
            'total_potential_benefit': sum(opp['potential_tax_benefit'] for opp in opportunities)
        })
        
    except Exception as e:
        logger.error(f"Error getting tax-loss opportunities: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/dashboard', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_investment_dashboard():
    """Get comprehensive investment dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        dashboard = investment_manager.get_investment_dashboard(
            age=user.age or 30,
            risk_tolerance=user.risk_tolerance or 'medium'
        )
        
        return jsonify(dashboard)
        
    except Exception as e:
        logger.error(f"Error getting investment dashboard: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/investments/price/<symbol>', methods=['GET'])
def get_real_time_price(symbol: str):
    """Get real-time price for a symbol"""
    try:
        price = investment_manager.portfolio_tracker.get_real_time_price(symbol)
        
        if price > 0:
            return jsonify({
                'symbol': symbol,
                'price': price,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Price not available'}), 404
            
    except Exception as e:
        logger.error(f"Error getting price for {symbol}: {e}")
        return jsonify({'error': str(e)}), 500

# Advanced Budgeting API Endpoints
@app.route('/api/budget/zero-based/create', methods=['POST'])
def create_zero_budget():
    """Create zero-based budget"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        budget_id = advanced_budgeting.zero_based.create_zero_budget(
            user_id=user.id,
            month=data['month'],
            total_income=data['total_income']
        )
        
        return jsonify({
            'success': True,
            'budget_id': budget_id,
            'message': 'Zero-based budget created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/zero-based/<int:budget_id>/allocate', methods=['POST'])
def allocate_zero_budget():
    """Allocate amount to category in zero-based budget"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    budget_id = int(request.view_args['budget_id'])
    
    try:
        advanced_budgeting.zero_based.allocate_category(
            budget_id=budget_id,
            category=data['category'],
            amount=data['amount'],
            priority=data.get('priority', 1)
        )
        
        status = advanced_budgeting.zero_based.get_budget_status(budget_id)
        
        return jsonify({
            'success': True,
            'budget_status': status,
            'message': f'Allocated ₹{data["amount"]:,.0f} to {data["category"]}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/zero-based/<int:budget_id>', methods=['GET'])
def get_zero_budget_status(budget_id: int):
    """Get zero-based budget status"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        status = advanced_budgeting.zero_based.get_budget_status(budget_id)
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/envelope/create', methods=['POST'])
def create_envelope():
    """Create budget envelope"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        envelope_id = advanced_budgeting.envelope.create_envelope(
            user_id=user.id,
            category=data['category'],
            monthly_limit=data['monthly_limit']
        )
        
        return jsonify({
            'success': True,
            'envelope_id': envelope_id,
            'message': f'Envelope created for {data["category"]} with ₹{data["monthly_limit"]:,.0f} limit'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/envelope/<int:envelope_id>/spend', methods=['POST'])
def spend_from_envelope(envelope_id: int):
    """Spend from envelope"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        success = advanced_budgeting.envelope.spend_from_envelope(
            envelope_id=envelope_id,
            amount=data['amount'],
            description=data.get('description', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Spent ₹{data["amount"]:,.0f} from envelope'
            })
        else:
            return jsonify({'error': 'Insufficient envelope balance'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/envelope/status', methods=['GET'])
@cache.cached(timeout=60, key_prefix=user_cache_key)
def get_envelope_status():
    """Get all envelope statuses"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        envelopes = advanced_budgeting.envelope.get_envelope_status(user.id)
        
        return jsonify({
            'envelopes': envelopes,
            'total_budget': sum(e['monthly_limit'] for e in envelopes),
            'total_spent': sum(e['spent_amount'] for e in envelopes),
            'overspent_count': len([e for e in envelopes if e['status'] == 'overspent'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/envelope/refill', methods=['POST'])
def refill_envelopes():
    """Refill all envelopes for new month"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        advanced_budgeting.envelope.refill_envelopes(user.id)
        
        return jsonify({
            'success': True,
            'message': 'All envelopes refilled for new month'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/seasonal/create', methods=['POST'])
def create_seasonal_budget():
    """Create seasonal budget"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        budget_id = advanced_budgeting.seasonal.create_seasonal_budget(
            user_id=user.id,
            event_name=data['event_name'],
            event_type=data['event_type'],
            target_amount=data['target_amount'],
            target_date=data['target_date'],
            categories=data.get('categories', [])
        )
        
        return jsonify({
            'success': True,
            'budget_id': budget_id,
            'message': f'Seasonal budget created for {data["event_name"]}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/seasonal/<int:budget_id>/save', methods=['POST'])
def add_seasonal_saving(budget_id: int):
    """Add saving to seasonal budget"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        advanced_budgeting.seasonal.add_seasonal_saving(
            budget_id=budget_id,
            amount=data['amount']
        )
        
        return jsonify({
            'success': True,
            'message': f'Added ₹{data["amount"]:,.0f} to seasonal budget'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/seasonal', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_seasonal_budgets():
    """Get all seasonal budgets"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        budgets = advanced_budgeting.seasonal.get_seasonal_budgets(user.id)
        
        return jsonify({
            'seasonal_budgets': budgets,
            'total_target': sum(b['target_amount'] for b in budgets),
            'total_saved': sum(b['saved_amount'] for b in budgets),
            'active_count': len([b for b in budgets if b['status'] != 'completed'])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/seasonal/templates', methods=['GET'])
def get_festival_templates():
    """Get predefined festival budget templates"""
    try:
        templates = advanced_budgeting.seasonal.get_festival_templates()
        return jsonify(templates)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/family/create', methods=['POST'])
def create_family_group():
    """Create family budget group"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        family_id = advanced_budgeting.family.create_family_group(
            name=data['name'],
            created_by=user.id
        )
        
        return jsonify({
            'success': True,
            'family_id': family_id,
            'message': f'Family group "{data["name"]}" created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/family/<int:family_id>/member', methods=['POST'])
def add_family_member(family_id: int):
    """Add member to family budget"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        advanced_budgeting.family.add_family_member(
            family_id=family_id,
            user_id=data['user_id'],
            role=data.get('role', 'member'),
            spending_limit=data.get('spending_limit', 0)
        )
        
        return jsonify({
            'success': True,
            'message': 'Family member added successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/family/<int:family_id>/budget', methods=['POST'])
def set_family_budget(family_id: int):
    """Set family budget for category"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        advanced_budgeting.family.set_family_budget(
            family_id=family_id,
            category=data['category'],
            budget_amount=data['budget_amount'],
            month=data.get('month', datetime.now().strftime('%Y-%m'))
        )
        
        return jsonify({
            'success': True,
            'message': f'Family budget set for {data["category"]}: ₹{data["budget_amount"]:,.0f}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/family/<int:family_id>/expense', methods=['POST'])
def add_family_expense(family_id: int):
    """Add family expense"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        success = advanced_budgeting.family.add_family_expense(
            family_id=family_id,
            user_id=user.id,
            category=data['category'],
            amount=data['amount'],
            description=data.get('description', '')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Family expense added: ₹{data["amount"]:,.0f}'
            })
        else:
            return jsonify({'error': 'Spending limit exceeded or unauthorized'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/family/<int:family_id>/status', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_family_budget_status(family_id: int):
    """Get family budget status"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    
    try:
        status = advanced_budgeting.family.get_family_budget_status(family_id, month)
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/dashboard', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_budget_dashboard():
    """Get comprehensive budget dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    family_id = request.args.get('family_id', type=int)
    
    try:
        dashboard = advanced_budgeting.get_comprehensive_budget_dashboard(
            user_id=user.id,
            family_id=family_id
        )
        
        return jsonify(dashboard)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/budget/recommendations', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_budget_recommendations():
    """Get AI-powered budget recommendations"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Calculate monthly income
    incomes = Income.query.filter_by(user_id=user.id).all()
    monthly_income = sum([i.amount for i in incomes if i.frequency == 'monthly'])
    
    if monthly_income <= 0:
        return jsonify({'error': 'No income data available for recommendations'}), 400
    
    try:
        recommendations = advanced_budgeting.get_budget_recommendations(
            user_id=user.id,
            monthly_income=monthly_income
        )
        
        return jsonify({
            'monthly_income': monthly_income,
            'recommendations': recommendations,
            'message': 'Budget recommendations based on 50/30/20 rule and best practices'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Bank Integration API Endpoints
@app.route('/api/bank/connect', methods=['POST'])
def connect_bank_account():
    """Connect bank account"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = bank_integration.account_aggregator.connect_bank_account(
            user_id=user.id,
            bank_name=data['bank_name'],
            credentials=data['credentials']
        )
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/accounts', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_connected_accounts():
    """Get all connected bank accounts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        accounts = bank_integration.account_aggregator.get_connected_accounts(user.id)
        
        return jsonify({
            'accounts': [{
                'account_id': acc.account_id,
                'bank_name': acc.bank_name,
                'account_number': acc.account_number,
                'account_type': acc.account_type,
                'balance': acc.balance,
                'currency': acc.currency,
                'last_sync': acc.last_sync,
                'status': acc.status
            } for acc in accounts],
            'total_accounts': len(accounts),
            'total_balance': sum(acc.balance for acc in accounts)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/disconnect/<account_id>', methods=['DELETE'])
def disconnect_bank_account(account_id: str):
    """Disconnect bank account"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        success = bank_integration.account_aggregator.disconnect_account(user.id, account_id)
        
        if success:
            cache.clear()
            return jsonify({
                'success': True,
                'message': 'Bank account disconnected successfully'
            })
        else:
            return jsonify({'error': 'Account not found or already disconnected'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/sync/<account_id>', methods=['POST'])
def sync_account(account_id: str):
    """Sync specific bank account"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        result = bank_integration.real_time_sync.sync_account_transactions(account_id)
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/sync-all', methods=['POST'])
def sync_all_accounts():
    """Sync all connected accounts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        result = bank_integration.real_time_sync.sync_all_accounts(user.id)
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bills/categories', methods=['GET'])
def get_bill_categories():
    """Get available bill categories and providers"""
    try:
        return jsonify(bank_integration.bill_payment.bill_categories)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bills/biller', methods=['POST'])
def add_biller():
    """Add saved biller"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        biller_id = bank_integration.bill_payment.add_biller(user.id, data)
        
        return jsonify({
            'success': True,
            'biller_id': biller_id,
            'message': f'Biller {data["biller_name"]} added successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bills/billers', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_saved_billers():
    """Get saved billers"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        billers = bank_integration.bill_payment.get_saved_billers(user.id)
        
        return jsonify({
            'billers': billers,
            'total_billers': len(billers)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bills/pay', methods=['POST'])
def pay_bill():
    """Pay bill"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = bank_integration.bill_payment.pay_bill(user.id, data)
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bills/history', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_bill_history():
    """Get bill payment history"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    limit = int(request.args.get('limit', 50))
    
    try:
        history = bank_integration.bill_payment.get_bill_history(user.id, limit)
        
        return jsonify({
            'bill_history': history,
            'total_payments': len(history),
            'total_amount': sum(p['amount'] for p in history)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upi/add-account', methods=['POST'])
def add_upi_account():
    """Add UPI account"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        account_id = bank_integration.upi_integration.add_upi_account(
            user_id=user.id,
            upi_id=data['upi_id'],
            provider=data['provider'],
            linked_account=data.get('linked_account')
        )
        
        return jsonify({
            'success': True,
            'account_id': account_id,
            'message': f'UPI account {data["upi_id"]} added successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upi/track-transaction', methods=['POST'])
def track_upi_transaction():
    """Track UPI transaction"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        transaction_id = bank_integration.upi_integration.track_upi_transaction(user.id, data)
        
        cache.clear()
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'message': f'UPI transaction of ₹{data["amount"]:,.0f} tracked successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upi/transactions', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_upi_transactions():
    """Get UPI transactions"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    days = int(request.args.get('days', 30))
    
    try:
        transactions = bank_integration.upi_integration.get_upi_transactions(user.id, days)
        
        return jsonify({
            'transactions': transactions,
            'total_transactions': len(transactions),
            'period_days': days
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upi/summary', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_upi_summary():
    """Get UPI transaction summary"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    period = request.args.get('period', 'month')
    
    try:
        summary = bank_integration.upi_integration.get_upi_summary(user.id, period)
        
        return jsonify({
            'summary': summary,
            'period': period,
            'net_amount': summary['received']['amount'] - summary['sent']['amount']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/dashboard', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_banking_dashboard():
    """Get comprehensive banking dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        dashboard = bank_integration.get_banking_dashboard(user.id)
        
        return jsonify(dashboard)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/insights', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_transaction_insights():
    """Get transaction insights across all accounts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        insights = bank_integration.get_transaction_insights(user.id)
        
        return jsonify(insights)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bank/supported-banks', methods=['GET'])
def get_supported_banks():
    """Get list of supported banks"""
    try:
        return jsonify({
            'supported_banks': list(bank_integration.account_aggregator.supported_banks.keys()),
            'bank_details': bank_integration.account_aggregator.supported_banks,
            'total_banks': len(bank_integration.account_aggregator.supported_banks)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upi/providers', methods=['GET'])
def get_upi_providers():
    """Get list of UPI providers"""
    try:
        return jsonify({
            'providers': bank_integration.upi_integration.upi_providers,
            'total_providers': len(bank_integration.upi_integration.upi_providers)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Third-party Integrations API Endpoints
@app.route('/api/integrations/mf/connect', methods=['POST'])
def connect_mf_platform():
    """Connect mutual fund platform"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = third_party_integrations.mutual_funds.connect_platform(
            user_id=user.id,
            platform_name=data['platform'],
            credentials=data['credentials']
        )
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/mf/sync/<platform>', methods=['POST'])
def sync_mf_platform(platform: str):
    """Sync mutual fund holdings from platform"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        result = third_party_integrations.mutual_funds.sync_holdings(user.id, platform)
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/mf/portfolio', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_mf_portfolio():
    """Get consolidated mutual fund portfolio"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        portfolio = third_party_integrations.mutual_funds.get_consolidated_portfolio(user.id)
        
        return jsonify(portfolio)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/expense/connect', methods=['POST'])
def connect_expense_app():
    """Connect expense tracking app"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = third_party_integrations.expense_apps.connect_app(
            user_id=user.id,
            app_name=data['app_name'],
            credentials=data['credentials']
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/expense/import/<app_name>', methods=['POST'])
def import_expenses_from_app(app_name: str):
    """Import expenses from connected app"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    date_range = int(request.args.get('days', 30))
    
    try:
        result = third_party_integrations.expense_apps.import_expenses(
            user_id=user.id,
            app_name=app_name,
            date_range=date_range
        )
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/expense/summary', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_expense_import_summary():
    """Get summary of imported expenses"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        summary = third_party_integrations.expense_apps.get_imported_summary(user.id)
        
        return jsonify(summary)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/calendar/setup', methods=['POST'])
def setup_calendar_sync():
    """Setup calendar synchronization"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = third_party_integrations.calendar_sync.setup_calendar_sync(
            user_id=user.id,
            provider=data['provider'],
            credentials=data['credentials']
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/calendar/reminder', methods=['POST'])
def add_bill_reminder():
    """Add bill due date reminder"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = third_party_integrations.calendar_sync.add_bill_reminder(
            user_id=user.id,
            bill_data=data
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/calendar/reminders', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_upcoming_reminders():
    """Get upcoming bill reminders"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    days_ahead = int(request.args.get('days', 7))
    
    try:
        reminders = third_party_integrations.calendar_sync.get_upcoming_reminders(
            user_id=user.id,
            days_ahead=days_ahead
        )
        
        return jsonify({
            'reminders': reminders,
            'total_reminders': len(reminders),
            'urgent_count': len([r for r in reminders if r['days_until_due'] <= 2])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/calendar/sync', methods=['POST'])
def sync_calendar():
    """Sync reminders with external calendar"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        result = third_party_integrations.calendar_sync.sync_with_calendar(user.id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/email/setup', methods=['POST'])
def setup_email_parsing():
    """Setup email parsing for transaction alerts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        result = third_party_integrations.email_parser.setup_email_parsing(
            user_id=user.id,
            email_config=data
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/email/parse', methods=['POST'])
def parse_bank_emails():
    """Parse bank transaction emails"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    days_back = int(request.args.get('days', 7))
    
    try:
        result = third_party_integrations.email_parser.parse_bank_emails(
            user_id=user.id,
            days_back=days_back
        )
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/email/transactions', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_parsed_transactions():
    """Get parsed transactions from emails"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    days = int(request.args.get('days', 30))
    
    try:
        transactions = third_party_integrations.email_parser.get_parsed_transactions(
            user_id=user.id,
            days=days
        )
        
        return jsonify({
            'transactions': transactions,
            'total_transactions': len(transactions),
            'total_amount': sum(t['amount'] for t in transactions),
            'banks_tracked': len(set(t['bank'] for t in transactions))
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/dashboard', methods=['GET'])
@cache.cached(timeout=300, key_prefix=user_cache_key)
def get_integrations_dashboard():
    """Get comprehensive integrations dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        dashboard = third_party_integrations.get_integrations_dashboard(user.id)
        
        return jsonify(dashboard)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/sync-all', methods=['POST'])
def sync_all_integrations():
    """Sync all connected integrations"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        result = third_party_integrations.sync_all_integrations(user.id)
        
        if result['success']:
            cache.clear()
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/integrations/supported', methods=['GET'])
def get_supported_integrations():
    """Get list of supported integrations"""
    try:
        return jsonify({
            'mutual_fund_platforms': list(third_party_integrations.mutual_funds.platforms.keys()),
            'expense_apps': list(third_party_integrations.expense_apps.supported_apps.keys()),
            'calendar_providers': ['google', 'outlook', 'apple'],
            'email_providers': ['gmail', 'outlook', 'yahoo'],
            'supported_banks_email': list(third_party_integrations.email_parser.bank_patterns.keys())
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Advanced Reports API Endpoints
@app.route('/api/reports/tax/<financial_year>', methods=['GET'])
@cache.cached(timeout=3600, key_prefix=user_cache_key)
def generate_tax_report(financial_year: str):
    """Generate ITR-ready tax report"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        tax_report = advanced_reports.tax_reports.generate_itr_summary(
            user_id=user.id,
            financial_year=financial_year
        )
        
        if 'error' in tax_report:
            return jsonify(tax_report), 400
        
        return jsonify(tax_report)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/cashflow', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def generate_cashflow_statement():
    """Generate cashflow statement"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    period = request.args.get('period', 'monthly')  # monthly, quarterly, yearly
    year = int(request.args.get('year', datetime.now().year))
    month = request.args.get('month', type=int)
    
    try:
        cashflow = advanced_reports.cashflow_reports.generate_cashflow_statement(
            user_id=user.id,
            period=period,
            year=year,
            month=month
        )
        
        if 'error' in cashflow:
            return jsonify(cashflow), 400
        
        return jsonify(cashflow)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/net-worth', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_net_worth_report():
    """Get net worth report"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        net_worth = advanced_reports.net_worth_tracker.calculate_net_worth(user.id)
        
        if 'error' in net_worth:
            return jsonify(net_worth), 400
        
        return jsonify(net_worth)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/net-worth/trend', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_net_worth_trend():
    """Get net worth trend"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    months = int(request.args.get('months', 12))
    
    try:
        trend = advanced_reports.net_worth_tracker.get_net_worth_trend(user.id, months)
        
        return jsonify(trend)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/expense-ratios', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def analyze_expense_ratios():
    """Analyze expense ratios against benchmarks"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    period_months = int(request.args.get('months', 12))
    
    try:
        analysis = advanced_reports.expense_analyzer.analyze_expense_ratios(
            user_id=user.id,
            period_months=period_months
        )
        
        if 'error' in analysis:
            return jsonify(analysis), 400
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/comprehensive', methods=['GET'])
@cache.cached(timeout=3600, key_prefix=user_cache_key)
def generate_comprehensive_report():
    """Generate comprehensive financial report"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    report_type = request.args.get('type', 'annual')  # monthly, quarterly, annual
    
    try:
        report = advanced_reports.generate_comprehensive_report(
            user_id=user.id,
            report_type=report_type
        )
        
        return jsonify(report)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/export/pdf', methods=['POST'])
def export_report_pdf():
    """Export report as PDF"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    report_data = data.get('report_data')
    
    if not report_data:
        return jsonify({'error': 'Report data required'}), 400
    
    try:
        pdf_base64 = advanced_reports.export_report_pdf(report_data)
        
        if pdf_base64.startswith('Error'):
            return jsonify({'error': pdf_base64}), 500
        
        return jsonify({
            'success': True,
            'pdf_data': pdf_base64,
            'filename': f"financial_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/assets/add', methods=['POST'])
def add_asset():
    """Add asset for net worth calculation"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        conn = sqlite3.connect(advanced_reports.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO assets (user_id, asset_name, asset_type, current_value, purchase_value)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user.id, data['asset_name'], data['asset_type'],
            data['current_value'], data.get('purchase_value', 0)
        ))
        
        asset_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        cache.clear()
        
        return jsonify({
            'success': True,
            'asset_id': asset_id,
            'message': f'Asset {data["asset_name"]} added successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/liabilities/add', methods=['POST'])
def add_liability():
    """Add liability for net worth calculation"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json(force=True)
    
    try:
        conn = sqlite3.connect(advanced_reports.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO liabilities (user_id, liability_name, liability_type, current_balance, original_amount)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user.id, data['liability_name'], data['liability_type'],
            data['current_balance'], data.get('original_amount', 0)
        ))
        
        liability_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        cache.clear()
        
        return jsonify({
            'success': True,
            'liability_id': liability_id,
            'message': f'Liability {data["liability_name"]} added successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/benchmarks', methods=['GET'])
def get_expense_benchmarks():
    """Get expense ratio benchmarks"""
    try:
        return jsonify({
            'benchmarks': advanced_reports.expense_analyzer.benchmarks,
            'description': 'Ideal and maximum percentage of income for each category'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/dashboard', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_reports_dashboard():
    """Get reports dashboard summary"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        current_year = datetime.now().year
        
        # Get quick summaries
        net_worth = advanced_reports.net_worth_tracker.calculate_net_worth(user.id)
        expense_analysis = advanced_reports.expense_analyzer.analyze_expense_ratios(user.id, 3)  # Last 3 months
        
        dashboard = {
            'net_worth_summary': {
                'current_net_worth': net_worth.get('net_worth', 0),
                'total_assets': net_worth.get('assets', {}).get('total', 0),
                'total_liabilities': net_worth.get('liabilities', {}).get('total', 0)
            },
            'expense_health': {
                'overall_score': expense_analysis.get('analysis', {}).get('overall_score', 0),
                'concerns_count': len(expense_analysis.get('analysis', {}).get('concerns', [])),
                'strengths_count': len(expense_analysis.get('analysis', {}).get('strengths', []))
            },
            'available_reports': [
                {'type': 'tax', 'name': 'Tax Report (ITR)', 'description': 'Income tax return summary'},
                {'type': 'cashflow', 'name': 'Cashflow Statement', 'description': 'Monthly/quarterly cashflow'},
                {'type': 'net_worth', 'name': 'Net Worth Report', 'description': 'Assets vs liabilities'},
                {'type': 'expense_ratios', 'name': 'Expense Analysis', 'description': 'Spending vs benchmarks'},
                {'type': 'comprehensive', 'name': 'Comprehensive Report', 'description': 'All-in-one financial report'}
            ]
        }
        
        return jsonify(dashboard)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Business Intelligence API Endpoints
@app.route('/api/bi/spending-patterns', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def analyze_spending_patterns():
    """Analyze spending patterns and trends"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    months = int(request.args.get('months', 12))
    
    try:
        patterns = business_intelligence.spending_analyzer.analyze_spending_patterns(
            user_id=user.id,
            months=months
        )
        
        if 'error' in patterns:
            return jsonify(patterns), 400
        
        return jsonify(patterns)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/seasonal-analysis', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def analyze_seasonal_patterns():
    """Analyze seasonal spending patterns"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    years = int(request.args.get('years', 2))
    
    try:
        seasonal = business_intelligence.seasonal_analyzer.analyze_seasonal_patterns(
            user_id=user.id,
            years=years
        )
        
        if 'error' in seasonal:
            return jsonify(seasonal), 400
        
        return jsonify(seasonal)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/peer-comparison', methods=['GET'])
@cache.cached(timeout=3600, key_prefix=user_cache_key)
def get_peer_comparison():
    """Get anonymous peer comparison benchmarks"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        comparison = business_intelligence.peer_comparison.generate_peer_benchmarks(
            user_id=user.id
        )
        
        if 'error' in comparison:
            return jsonify(comparison), 400
        
        return jsonify(comparison)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/financial-health', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_financial_health_score():
    """Get comprehensive financial health score"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        health_score = business_intelligence.health_scorer.calculate_financial_health_score(
            user_id=user.id
        )
        
        if 'error' in health_score:
            return jsonify(health_score), 400
        
        return jsonify(health_score)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/dashboard', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_bi_dashboard():
    """Get comprehensive business intelligence dashboard"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        dashboard = business_intelligence.generate_bi_dashboard(user.id)
        
        if 'error' in dashboard:
            return jsonify(dashboard), 400
        
        return jsonify(dashboard)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/insights', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_financial_insights():
    """Get AI-powered financial insights"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Get key insights from all BI components
        spending_patterns = business_intelligence.spending_analyzer.analyze_spending_patterns(user.id, 6)
        health_score = business_intelligence.health_scorer.calculate_financial_health_score(user.id)
        peer_comparison = business_intelligence.peer_comparison.generate_peer_benchmarks(user.id)
        
        insights = {
            'key_insights': [],
            'alerts': [],
            'opportunities': [],
            'summary': {
                'health_score': health_score.get('overall_score', 0),
                'health_category': health_score.get('health_category', 'Unknown'),
                'anomalies_detected': len(spending_patterns.get('anomalies', [])),
                'peer_performance': 'above_average' if peer_comparison.get('benchmarks', {}).get('savings_rate', {}).get('peer_percentile', 50) > 50 else 'below_average'
            }
        }
        
        # Generate key insights
        if spending_patterns.get('anomalies'):
            top_anomaly = spending_patterns['anomalies'][0]
            insights['alerts'].append({
                'type': 'spending_anomaly',
                'message': f'Unusual spending detected on {top_anomaly["date"]}: ₹{top_anomaly["amount"]:,.0f}',
                'severity': 'high' if top_anomaly['z_score'] > 3 else 'medium'
            })
        
        # Health score insights
        if health_score.get('overall_score', 0) < 60:
            insights['opportunities'].append({
                'type': 'health_improvement',
                'message': f'Your financial health score is {health_score.get("overall_score", 0):.0f}/100. Focus on the recommendations to improve.',
                'action': 'review_recommendations'
            })
        
        # Peer comparison insights
        if peer_comparison.get('benchmarks'):
            savings_percentile = peer_comparison['benchmarks'].get('savings_rate', {}).get('peer_percentile', 50)
            if savings_percentile > 75:
                insights['key_insights'].append({
                    'type': 'peer_performance',
                    'message': f'Your savings rate is better than {savings_percentile:.0f}% of similar users',
                    'category': 'positive'
                })
            elif savings_percentile < 25:
                insights['opportunities'].append({
                    'type': 'savings_improvement',
                    'message': f'Your savings rate is lower than {100-savings_percentile:.0f}% of similar users',
                    'action': 'increase_savings'
                })
        
        return jsonify(insights)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/trends', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_spending_trends():
    """Get detailed spending trends analysis"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    category = request.args.get('category')
    months = int(request.args.get('months', 12))
    
    try:
        patterns = business_intelligence.spending_analyzer.analyze_spending_patterns(user.id, months)
        
        if 'error' in patterns:
            return jsonify(patterns), 400
        
        if category and category in patterns.get('patterns', {}):
            # Return specific category trend
            category_pattern = patterns['patterns'][category]
            return jsonify({
                'category': category,
                'trend': category_pattern,
                'period_months': months
            })
        else:
            # Return all trends summary
            trends_summary = {}
            for cat, pattern in patterns.get('patterns', {}).items():
                trends_summary[cat] = {
                    'trend': pattern['trend'],
                    'monthly_average': pattern['monthly_average'],
                    'anomalies_count': len(pattern['anomalies'])
                }
            
            return jsonify({
                'trends_summary': trends_summary,
                'period_months': months,
                'total_categories': len(trends_summary)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/anomalies', methods=['GET'])
@cache.cached(timeout=1800, key_prefix=user_cache_key)
def get_spending_anomalies():
    """Get spending anomalies detection"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    months = int(request.args.get('months', 6))
    
    try:
        patterns = business_intelligence.spending_analyzer.analyze_spending_patterns(user.id, months)
        
        if 'error' in patterns:
            return jsonify(patterns), 400
        
        anomalies = patterns.get('anomalies', [])
        
        # Categorize anomalies
        high_severity = [a for a in anomalies if a['z_score'] > 3]
        medium_severity = [a for a in anomalies if 2 < a['z_score'] <= 3]
        
        return jsonify({
            'anomalies': anomalies,
            'summary': {
                'total_anomalies': len(anomalies),
                'high_severity': len(high_severity),
                'medium_severity': len(medium_severity),
                'most_recent': anomalies[0] if anomalies else None
            },
            'period_months': months
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/seasonal/festivals', methods=['GET'])
@cache.cached(timeout=3600, key_prefix=user_cache_key)
def get_festival_spending_analysis():
    """Get festival spending analysis"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        seasonal = business_intelligence.seasonal_analyzer.analyze_seasonal_patterns(user.id, 2)
        
        if 'error' in seasonal:
            return jsonify(seasonal), 400
        
        festival_patterns = seasonal.get('festival_patterns', {})
        
        # Rank festivals by spending impact
        festival_ranking = []
        for festival, data in festival_patterns.items():
            festival_ranking.append({
                'festival': festival,
                'uplift_percentage': data['uplift_percentage'],
                'avg_spending': data['avg_spending'],
                'months': data['months'],
                'categories': data['categories']
            })
        
        festival_ranking.sort(key=lambda x: x['uplift_percentage'], reverse=True)
        
        return jsonify({
            'festival_analysis': festival_ranking,
            'top_festival': festival_ranking[0] if festival_ranking else None,
            'total_festivals_analyzed': len(festival_ranking)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'cache_available': cache_manager.mc is not None,
        'background_tasks': task_manager.celery is not None,
        'security_features': {
            'encryption': True,
            'mfa': True,
            'audit_logging': True,
            'backup_system': True
        },
        'investment_features': {
            'portfolio_tracking': True,
            'asset_allocation': True,
            'sip_management': True,
            'tax_loss_harvesting': True
        },
        'advanced_budgeting': {
            'zero_based_budgeting': True,
            'envelope_budgeting': True,
            'seasonal_budgeting': True,
            'family_budgeting': True
        },
        'bank_integration': {
            'account_aggregation': True,
            'real_time_sync': True,
            'bill_payment': True,
            'upi_integration': True
        },
        'third_party_integrations': {
            'mutual_fund_platforms': True,
            'expense_apps': True,
            'calendar_sync': True,
            'email_parsing': True
        },
        'advanced_reports': {
            'tax_reports': True,
            'cashflow_statements': True,
            'net_worth_tracking': True,
            'expense_ratios': True
        },
        'business_intelligence': {
            'spending_patterns': True,
            'seasonal_analysis': True,
            'peer_comparison': True,
            'financial_health_score': True
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
