import os
from datetime import timedelta

class Config:
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///finance_advisor.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': -1,
        'pool_pre_ping': True
    }
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-2024'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'dev-jwt-secret-change-in-production-2024'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # CORS
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5000"]
    
    # File paths
    UPLOAD_FOLDER = 'uploads'
    REPORTS_FOLDER = 'reports'
    MODELS_FOLDER = 'models'
    BACKUPS_FOLDER = 'backups'
    
    # Cache Configuration
    CACHE_TYPE = 'memcached' if os.environ.get('MEMCACHED_URL') else 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_MEMCACHED_SERVERS = [os.environ.get('MEMCACHED_URL', '127.0.0.1:11211')]
    
    # Celery Configuration
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # AI/ML Configuration
    USE_GPU = os.environ.get('USE_GPU', 'False').lower() == 'true'
    MAX_MEMORY_GB = int(os.environ.get('MAX_MEMORY_GB', '8'))
    LSTM_EPOCHS = int(os.environ.get('LSTM_EPOCHS', '50'))
    LSTM_BATCH_SIZE = int(os.environ.get('LSTM_BATCH_SIZE', '32'))
    
    # Indian Banking Configuration
    SUPPORTED_BANKS = [
        'HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'PNB', 'BOB', 'CANARA', 'IOB', 'YES'
    ]
    
    INDIAN_CATEGORIES = [
        'swiggy', 'zomato', 'dmart', 'bigbasket', 'irctc', 'uber', 'ola',
        'amazon', 'flipkart', 'myntra', 'paytm', 'phonepe', 'gpay',
        'petrol', 'grocery', 'medical', 'education', 'entertainment',
        'utilities', 'rent', 'emi', 'investment', 'insurance'
    ]
    
    UPI_KEYWORDS = [
        'UPI', 'PHONEPE', 'PAYTM', 'GOOGLEPAY', 'GPAY', 'BHIM', 'AMAZON PAY',
        'MOBIKWIK', 'FREECHARGE', 'AIRTEL MONEY', 'JIO MONEY'
    ]
    
    # Model parameters
    BUDGET_RULES = {
        'needs': 0.50,  # 50% for needs
        'wants': 0.30,  # 30% for wants
        'savings': 0.20  # 20% for savings
    }
    
    # Tax Configuration (Indian)
    TAX_SLABS_2024 = [
        (250000, 0.0),      # Up to 2.5L - 0%
        (500000, 0.05),     # 2.5L to 5L - 5%
        (750000, 0.10),     # 5L to 7.5L - 10%
        (1000000, 0.15),    # 7.5L to 10L - 15%
        (1250000, 0.20),    # 10L to 12.5L - 20%
        (1500000, 0.25),    # 12.5L to 15L - 25%
        (float('inf'), 0.30) # Above 15L - 30%
    ]
    
    # Performance Optimization
    PAGINATION_PER_PAGE = 50
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Security Features
    AUDIT_LOG_ENABLED = True
    ENCRYPTION_ENABLED = True
    SESSION_TIMEOUT = 30  # minutes
    
    # Third-party API Keys (set via environment variables)
    ALPHA_VANTAGE_API_KEY = os.environ.get('ALPHA_VANTAGE_API_KEY')
    ZERODHA_API_KEY = os.environ.get('ZERODHA_API_KEY')
    GROWW_API_KEY = os.environ.get('GROWW_API_KEY')
    
    # Feature Flags
    ENABLE_VOICE_COMMANDS = True
    ENABLE_OCR = True
    ENABLE_RECEIPT_SCANNING = True
    ENABLE_ANOMALY_DETECTION = True
    ENABLE_FRAUD_DETECTION = True
    ENABLE_LSTM_FORECASTING = True
    ENABLE_INVESTMENT_RECOMMENDATIONS = True
    
    # Mobile & PWA Configuration
    PWA_ENABLED = True
    OFFLINE_SYNC_ENABLED = True
    
    # Notification Configuration
    EMAIL_NOTIFICATIONS = os.environ.get('EMAIL_NOTIFICATIONS', 'False').lower() == 'true'
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
