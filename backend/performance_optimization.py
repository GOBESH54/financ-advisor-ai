from sqlalchemy import Index, text
from flask_sqlalchemy import SQLAlchemy
import memcache
from celery import Celery
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import pickle

logger = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Database optimization with indexing and query optimization"""
    
    def __init__(self, db: SQLAlchemy):
        self.db = db
    
    def create_indexes(self):
        """Create optimized indexes for better query performance"""
        try:
            # User-based queries (most common)
            self.db.engine.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_income_user_date 
                ON income (user_id, date DESC);
            """))
            
            self.db.engine.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_expense_user_date 
                ON expense (user_id, date DESC);
            """))
            
            self.db.engine.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_expense_user_category 
                ON expense (user_id, category);
            """))
            
            # Date range queries
            self.db.engine.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_expense_date_amount 
                ON expense (date, amount);
            """))
            
            # Debt management queries
            self.db.engine.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_debt_user_due_date 
                ON debt (user_id, due_date);
            """))
            
            # Goals tracking
            self.db.engine.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_savings_goal_user_target_date 
                ON savings_goal (user_id, target_date);
            """))
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def optimize_queries(self):
        """Optimize common query patterns"""
        try:
            # Analyze tables for better query planning
            tables = ['user', 'income', 'expense', 'debt', 'savings_goal']
            
            for table in tables:
                self.db.engine.execute(text(f"ANALYZE {table};"))
            
            logger.info("Database tables analyzed for optimization")
            
        except Exception as e:
            logger.error(f"Error optimizing queries: {e}")
    
    def get_optimized_expenses(self, user_id: int, limit: int = 100, 
                              category: str = None, date_from: datetime = None) -> List:
        """Optimized expense query with proper indexing"""
        
        query = text("""
            SELECT id, category, description, amount, date, is_recurring, frequency
            FROM expense 
            WHERE user_id = :user_id
            AND (:category IS NULL OR category = :category)
            AND (:date_from IS NULL OR date >= :date_from)
            ORDER BY date DESC 
            LIMIT :limit
        """)
        
        result = self.db.engine.execute(query, {
            'user_id': user_id,
            'category': category,
            'date_from': date_from,
            'limit': limit
        })
        
        return [dict(row) for row in result]
    
    def get_monthly_summary(self, user_id: int, year: int, month: int) -> Dict:
        """Optimized monthly summary query"""
        
        query = text("""
            SELECT 
                'income' as type,
                SUM(amount) as total,
                COUNT(*) as count
            FROM income 
            WHERE user_id = :user_id 
            AND EXTRACT(YEAR FROM date) = :year 
            AND EXTRACT(MONTH FROM date) = :month
            
            UNION ALL
            
            SELECT 
                'expense' as type,
                SUM(amount) as total,
                COUNT(*) as count
            FROM expense 
            WHERE user_id = :user_id 
            AND EXTRACT(YEAR FROM date) = :year 
            AND EXTRACT(MONTH FROM date) = :month
        """)
        
        result = self.db.engine.execute(query, {
            'user_id': user_id,
            'year': year,
            'month': month
        })
        
        summary = {'income': 0, 'expense': 0, 'income_count': 0, 'expense_count': 0}
        
        for row in result:
            if row['type'] == 'income':
                summary['income'] = float(row['total'] or 0)
                summary['income_count'] = row['count']
            else:
                summary['expense'] = float(row['total'] or 0)
                summary['expense_count'] = row['count']
        
        summary['net_savings'] = summary['income'] - summary['expense']
        return summary

class MemcachedManager:
    """Memcached caching layer (Windows-compatible Redis alternative)"""
    
    def __init__(self, servers=['127.0.0.1:11211']):
        self.mc = None
        self.default_timeout = 300  # 5 minutes
        self.fallback_cache = {}  # In-memory fallback
        
        try:
            import memcache
            self.mc = memcache.Client(servers, debug=0)
            # Test connection
            test_key = 'memcached_test'
            self.mc.set(test_key, 'test_value', time=1)
            if self.mc.get(test_key) == 'test_value':
                self.mc.delete(test_key)
                logger.info("Memcached client initialized and connected")
            else:
                raise Exception("Memcached server not responding")
        except ImportError:
            logger.warning("python-memcached not installed, using fallback cache")
            self.mc = None
        except Exception as e:
            logger.warning(f"Memcached server not available: {e}. Using fallback cache.")
            self.mc = None
    
    def get(self, key: str):
        """Get value from cache"""
        if self.mc:
            try:
                return self.mc.get(key)
            except Exception as e:
                logger.error(f"Memcached get error: {e}")
                # Fall back to in-memory cache
        
        # Fallback to in-memory cache
        return self.fallback_cache.get(key)
    
    def set(self, key: str, value, timeout: int = None):
        """Set value in cache"""
        timeout = timeout or self.default_timeout
        
        if self.mc:
            try:
                return self.mc.set(key, value, time=timeout)
            except Exception as e:
                logger.error(f"Memcached set error: {e}")
                # Fall back to in-memory cache
        
        # Fallback to in-memory cache with expiration tracking
        expiry_time = datetime.now() + timedelta(seconds=timeout)
        self.fallback_cache[key] = {'value': value, 'expires': expiry_time}
        return True
    
    def delete(self, key: str):
        """Delete key from cache"""
        deleted = False
        
        if self.mc:
            try:
                deleted = self.mc.delete(key)
            except Exception as e:
                logger.error(f"Memcached delete error: {e}")
        
        # Also delete from fallback cache
        if key in self.fallback_cache:
            del self.fallback_cache[key]
            deleted = True
            
        return deleted
    
    def clear_user_cache(self, user_id: int):
        """Clear all cache entries for a user"""
        patterns = [
            f'dashboard_{user_id}',
            f'expenses_{user_id}',
            f'income_{user_id}',
            f'goals_{user_id}',
            f'notifications_{user_id}',
            f'trends_{user_id}'
        ]
        
        for pattern in patterns:
            self.delete(pattern)
            
        # Clean expired entries from fallback cache
        self._cleanup_expired_cache()
    
    def cache_dashboard_data(self, user_id: int, data: Dict, timeout: int = 60):
        """Cache dashboard data with short timeout"""
        key = f'dashboard_{user_id}'
        return self.set(key, data, timeout)
    
    def get_dashboard_data(self, user_id: int) -> Optional[Dict]:
        """Get cached dashboard data"""
        key = f'dashboard_{user_id}'
        return self.get(key)
    
    def cache_query_result(self, query_key: str, result, timeout: int = 300):
        """Cache query result"""
        return self.set(query_key, result, timeout)
    
    def get_query_result(self, query_key: str):
        """Get cached query result"""
        return self.get(query_key)
    
    def _cleanup_expired_cache(self):
        """Clean up expired entries from fallback cache"""
        current_time = datetime.now()
        expired_keys = []
        
        for key, data in self.fallback_cache.items():
            if isinstance(data, dict) and 'expires' in data:
                if current_time > data['expires']:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del self.fallback_cache[key]
    
    def get_cache_stats(self):
        """Get cache statistics"""
        stats = {
            'backend': 'memcached' if self.mc else 'fallback',
            'fallback_entries': len(self.fallback_cache)
        }
        
        if self.mc:
            try:
                mc_stats = self.mc.get_stats()
                stats['memcached_stats'] = mc_stats
            except Exception as e:
                stats['memcached_error'] = str(e)
                
        return stats

class BackgroundTaskManager:
    """Background processing with Celery"""
    
    def __init__(self, app=None):
        self.celery = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Celery with Flask app"""
        # Try memcached backend first, fallback to in-memory
        try:
            # Test if memcached is available
            import memcache
            mc = memcache.Client(['127.0.0.1:11211'], debug=0)
            mc.set('celery_test', 'test_value', time=1)
            if mc.get('celery_test') == 'test_value':
                mc.delete('celery_test')
                backend = 'cache+memcached://127.0.0.1:11211/'
                logger.info("Using memcached backend for Celery")
            else:
                raise Exception("Memcached not responding")
        except Exception as e:
            logger.warning(f"Memcached not available for Celery: {e}. Using memory backend.")
            backend = 'cache+memory://'
        
        self.celery = Celery(
            app.import_name,
            backend=backend,
            broker='memory://'  # In-memory broker for Windows compatibility
        )
        
        # Configure Celery
        self.celery.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='Asia/Kolkata',
            enable_utc=True,
            task_routes={
                'finance.heavy_analysis': {'queue': 'heavy'},
                'finance.report_generation': {'queue': 'reports'},
                'finance.notification_processing': {'queue': 'notifications'}
            }
        )
        
        # Update task base classes to be Flask-aware
        class ContextTask(self.celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        self.celery.Task = ContextTask
        return self.celery

# Celery tasks
def create_celery_tasks(celery_app, db, cache_manager):
    """Create Celery background tasks"""
    
    @celery_app.task(name='finance.generate_monthly_report')
    def generate_monthly_report(user_id: int, year: int, month: int):
        """Generate monthly financial report in background"""
        try:
            from models import User, Income, Expense, Debt, SavingsGoal
            from report_generator import ReportGenerator
            
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}
            
            # Get data for the month
            incomes = Income.query.filter(
                Income.user_id == user_id,
                Income.date >= datetime(year, month, 1),
                Income.date < datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
            ).all()
            
            expenses = Expense.query.filter(
                Expense.user_id == user_id,
                Expense.date >= datetime(year, month, 1),
                Expense.date < datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
            ).all()
            
            # Generate report
            report_gen = ReportGenerator()
            report_path = report_gen.generate_monthly_report(
                user_name=user.name,
                incomes=incomes,
                expenses=expenses,
                debts=[],
                goals=[]
            )
            
            return {'success': True, 'report_path': report_path}
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {'error': str(e)}
    
    @celery_app.task(name='finance.analyze_spending_patterns')
    def analyze_spending_patterns(user_id: int):
        """Analyze user spending patterns in background"""
        try:
            from models import Expense
            from advanced_ai_models import SpendingPredictor
            
            expenses = Expense.query.filter_by(user_id=user_id).all()
            
            if len(expenses) < 10:
                return {'error': 'Insufficient data for analysis'}
            
            # Convert to DataFrame
            import pandas as pd
            df = pd.DataFrame([{
                'date': e.date,
                'amount': e.amount,
                'category': e.category
            } for e in expenses])
            
            # Analyze patterns
            predictor = SpendingPredictor()
            predictions = predictor.predict_next_month(df)
            
            # Cache results
            cache_key = f'spending_analysis_{user_id}'
            cache_manager.cache_query_result(cache_key, {
                'predictions': predictions,
                'analysis_date': datetime.now().isoformat(),
                'total_predicted': sum(predictions.values())
            }, timeout=3600)  # Cache for 1 hour
            
            return {'success': True, 'predictions': predictions}
            
        except Exception as e:
            logger.error(f"Error analyzing spending patterns: {e}")
            return {'error': str(e)}
    
    @celery_app.task(name='finance.process_bulk_transactions')
    def process_bulk_transactions(user_id: int, transactions: List[Dict]):
        """Process bulk transaction import in background"""
        try:
            from models import Income, Expense
            
            processed_count = 0
            
            for txn in transactions:
                try:
                    if txn.get('type') == 'expense':
                        expense = Expense(
                            user_id=user_id,
                            category=txn.get('category', 'other'),
                            description=txn.get('description', ''),
                            amount=txn.get('amount', 0),
                            date=datetime.strptime(txn['date'], '%Y-%m-%d').date(),
                            is_recurring=False
                        )
                        db.session.add(expense)
                        
                    elif txn.get('type') == 'income':
                        income = Income(
                            user_id=user_id,
                            source=txn.get('source', 'Bulk Import'),
                            amount=txn.get('amount', 0),
                            frequency='one-time',
                            date=datetime.strptime(txn['date'], '%Y-%m-%d').date()
                        )
                        db.session.add(income)
                    
                    processed_count += 1
                    
                except Exception as txn_error:
                    logger.error(f"Error processing transaction: {txn_error}")
                    continue
            
            db.session.commit()
            
            # Clear user cache after bulk import
            cache_manager.clear_user_cache(user_id)
            
            return {'success': True, 'processed': processed_count}
            
        except Exception as e:
            logger.error(f"Error processing bulk transactions: {e}")
            return {'error': str(e)}
    
    @celery_app.task(name='finance.send_notifications')
    def send_notifications(user_id: int, notification_type: str):
        """Send notifications in background"""
        try:
            from dashboard_features import NotificationManager
            from models import User, Income, Expense, Debt, SavingsGoal
            
            user = User.query.get(user_id)
            if not user:
                return {'error': 'User not found'}
            
            # Get user data
            incomes = Income.query.filter_by(user_id=user_id).all()
            expenses = Expense.query.filter_by(user_id=user_id).all()
            debts = Debt.query.filter_by(user_id=user_id).all()
            goals = SavingsGoal.query.filter_by(user_id=user_id).all()
            
            user_data = {
                'monthly_income': sum([i.amount for i in incomes if i.frequency == 'monthly']),
                'expenses': [{
                    'date': e.date.strftime('%Y-%m-%d'),
                    'amount': e.amount,
                    'category': e.category
                } for e in expenses],
                'debts': [{
                    'amount': d.amount,
                    'due_date': d.due_date.strftime('%Y-%m-%d') if d.due_date else None
                } for d in debts],
                'goals': [{
                    'name': g.name,
                    'target_amount': g.target_amount,
                    'current_amount': g.current_amount
                } for g in goals]
            }
            
            # Generate notifications
            notification_manager = NotificationManager()
            notifications = notification_manager.generate_notifications(user_data)
            
            # Cache notifications
            cache_key = f'notifications_{user_id}'
            cache_manager.set(cache_key, notifications, timeout=300)
            
            return {'success': True, 'notifications': notifications}
            
        except Exception as e:
            logger.error(f"Error processing notifications: {e}")
            return {'error': str(e)}
    
    return {
        'generate_monthly_report': generate_monthly_report,
        'analyze_spending_patterns': analyze_spending_patterns,
        'process_bulk_transactions': process_bulk_transactions,
        'send_notifications': send_notifications
    }

class PerformanceMonitor:
    """Monitor application performance"""
    
    def __init__(self, cache_manager: MemcachedManager):
        self.cache_manager = cache_manager
        self.metrics = {}
    
    def track_query_time(self, query_name: str, execution_time: float):
        """Track query execution time"""
        if query_name not in self.metrics:
            self.metrics[query_name] = []
        
        self.metrics[query_name].append({
            'time': execution_time,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 100 measurements
        if len(self.metrics[query_name]) > 100:
            self.metrics[query_name] = self.metrics[query_name][-100:]
    
    def get_performance_stats(self) -> Dict:
        """Get performance statistics"""
        stats = {}
        
        for query_name, measurements in self.metrics.items():
            if measurements:
                times = [m['time'] for m in measurements]
                stats[query_name] = {
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times),
                    'count': len(times)
                }
        
        return stats
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache_manager.get_cache_stats()