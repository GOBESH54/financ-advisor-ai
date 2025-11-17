import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import json
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from scipy import stats
import calendar

@dataclass
class SpendingPattern:
    category: str
    trend: str  # 'increasing', 'decreasing', 'stable'
    monthly_average: float
    variance: float
    anomalies: List[Dict]

@dataclass
class SeasonalInsight:
    period: str
    category: str
    seasonal_factor: float
    peak_months: List[str]
    spending_pattern: str

class SpendingPatternAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def analyze_spending_patterns(self, user_id: int, months: int = 12) -> Dict:
        """Analyze spending patterns and identify trends"""
        try:
            # Get expense data
            expenses_df = self._get_expense_data(user_id, months)
            
            if expenses_df.empty:
                return {'error': 'No expense data available'}
            
            # Analyze patterns by category
            patterns = {}
            for category in expenses_df['category'].unique():
                category_data = expenses_df[expenses_df['category'] == category]
                pattern = self._analyze_category_pattern(category_data)
                patterns[category] = pattern
            
            # Detect overall anomalies
            anomalies = self._detect_spending_anomalies(expenses_df)
            
            # Calculate spending velocity
            velocity = self._calculate_spending_velocity(expenses_df)
            
            return {
                'patterns': patterns,
                'anomalies': anomalies,
                'spending_velocity': velocity,
                'analysis_period': months,
                'total_categories': len(patterns),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_expense_data(self, user_id: int, months: int) -> pd.DataFrame:
        """Get expense data for analysis"""
        conn = sqlite3.connect(self.db_path)
        
        since_date = (datetime.now() - timedelta(days=months * 30)).isoformat()
        
        query = '''
            SELECT category, amount, date, description
            FROM expenses 
            WHERE user_id = ? AND date >= ?
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, conn, params=(user_id, since_date))
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M')
        
        return df
    
    def _analyze_category_pattern(self, category_data: pd.DataFrame) -> Dict:
        """Analyze spending pattern for a specific category"""
        # Group by month
        monthly_spending = category_data.groupby('month')['amount'].sum()
        
        if len(monthly_spending) < 3:
            return {
                'trend': 'insufficient_data',
                'monthly_average': category_data['amount'].mean(),
                'variance': category_data['amount'].var(),
                'anomalies': []
            }
        
        # Calculate trend
        months_numeric = range(len(monthly_spending))
        slope, _, r_value, p_value, _ = stats.linregress(months_numeric, monthly_spending.values)
        
        if p_value < 0.05:  # Significant trend
            trend = 'increasing' if slope > 0 else 'decreasing'
        else:
            trend = 'stable'
        
        # Detect anomalies using IQR method
        Q1 = monthly_spending.quantile(0.25)
        Q3 = monthly_spending.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        anomalies = []
        for month, amount in monthly_spending.items():
            if amount < lower_bound or amount > upper_bound:
                anomalies.append({
                    'month': str(month),
                    'amount': amount,
                    'type': 'high' if amount > upper_bound else 'low',
                    'deviation': abs(amount - monthly_spending.median())
                })
        
        return {
            'trend': trend,
            'trend_strength': abs(r_value),
            'monthly_average': monthly_spending.mean(),
            'variance': monthly_spending.var(),
            'anomalies': anomalies,
            'growth_rate': slope
        }
    
    def _detect_spending_anomalies(self, expenses_df: pd.DataFrame) -> List[Dict]:
        """Detect overall spending anomalies"""
        # Daily spending analysis
        daily_spending = expenses_df.groupby(expenses_df['date'].dt.date)['amount'].sum()
        
        # Use Z-score for anomaly detection
        z_scores = np.abs(stats.zscore(daily_spending))
        anomaly_threshold = 2.5
        
        anomalies = []
        for date, spending in daily_spending.items():
            z_score = z_scores[daily_spending.index.get_loc(date)]
            if z_score > anomaly_threshold:
                # Get transactions for this date
                date_transactions = expenses_df[expenses_df['date'].dt.date == date]
                
                anomalies.append({
                    'date': date.isoformat(),
                    'amount': spending,
                    'z_score': z_score,
                    'transactions': len(date_transactions),
                    'categories': date_transactions['category'].unique().tolist(),
                    'largest_transaction': date_transactions['amount'].max()
                })
        
        return sorted(anomalies, key=lambda x: x['z_score'], reverse=True)[:10]
    
    def _calculate_spending_velocity(self, expenses_df: pd.DataFrame) -> Dict:
        """Calculate spending velocity metrics"""
        if expenses_df.empty:
            return {}
        
        # Weekly spending
        weekly_spending = expenses_df.groupby(expenses_df['date'].dt.isocalendar().week)['amount'].sum()
        
        # Monthly spending
        monthly_spending = expenses_df.groupby(expenses_df['date'].dt.to_period('M'))['amount'].sum()
        
        return {
            'avg_daily_spending': expenses_df.groupby(expenses_df['date'].dt.date)['amount'].sum().mean(),
            'avg_weekly_spending': weekly_spending.mean(),
            'avg_monthly_spending': monthly_spending.mean(),
            'spending_consistency': 1 / (1 + monthly_spending.std()),  # Higher = more consistent
            'peak_spending_day': expenses_df.groupby(expenses_df['date'].dt.day_name())['amount'].sum().idxmax()
        }

class SeasonalAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.indian_festivals = {
            'diwali': {'months': [10, 11], 'categories': ['shopping', 'food', 'gifts']},
            'holi': {'months': [3], 'categories': ['food', 'entertainment']},
            'dussehra': {'months': [9, 10], 'categories': ['shopping', 'travel']},
            'eid': {'months': [4, 5, 6], 'categories': ['food', 'shopping', 'gifts']},
            'christmas': {'months': [12], 'categories': ['shopping', 'food', 'travel']},
            'new_year': {'months': [1, 12], 'categories': ['entertainment', 'travel']}
        }
    
    def analyze_seasonal_patterns(self, user_id: int, years: int = 2) -> Dict:
        """Analyze seasonal spending patterns"""
        try:
            # Get expense data
            expenses_df = self._get_seasonal_data(user_id, years)
            
            if expenses_df.empty:
                return {'error': 'No expense data available'}
            
            # Analyze monthly patterns
            monthly_patterns = self._analyze_monthly_patterns(expenses_df)
            
            # Analyze festival patterns
            festival_patterns = self._analyze_festival_patterns(expenses_df)
            
            # Seasonal decomposition
            seasonal_decomposition = self._seasonal_decomposition(expenses_df)
            
            return {
                'monthly_patterns': monthly_patterns,
                'festival_patterns': festival_patterns,
                'seasonal_decomposition': seasonal_decomposition,
                'analysis_period_years': years,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_seasonal_data(self, user_id: int, years: int) -> pd.DataFrame:
        """Get expense data for seasonal analysis"""
        conn = sqlite3.connect(self.db_path)
        
        since_date = (datetime.now() - timedelta(days=years * 365)).isoformat()
        
        query = '''
            SELECT category, amount, date
            FROM expenses 
            WHERE user_id = ? AND date >= ?
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, conn, params=(user_id, since_date))
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.month
            df['year'] = df['date'].dt.year
            df['month_name'] = df['date'].dt.month_name()
        
        return df
    
    def _analyze_monthly_patterns(self, expenses_df: pd.DataFrame) -> Dict:
        """Analyze spending patterns by month"""
        monthly_spending = expenses_df.groupby(['month', 'month_name'])['amount'].sum().reset_index()
        monthly_avg = monthly_spending.groupby(['month', 'month_name'])['amount'].mean().reset_index()
        
        # Calculate seasonal factors
        overall_avg = monthly_avg['amount'].mean()
        monthly_avg['seasonal_factor'] = monthly_avg['amount'] / overall_avg
        
        # Identify peak and low months
        peak_months = monthly_avg.nlargest(3, 'seasonal_factor')[['month_name', 'seasonal_factor']].to_dict('records')
        low_months = monthly_avg.nsmallest(3, 'seasonal_factor')[['month_name', 'seasonal_factor']].to_dict('records')
        
        return {
            'monthly_averages': monthly_avg.to_dict('records'),
            'peak_months': peak_months,
            'low_months': low_months,
            'seasonal_variance': monthly_avg['seasonal_factor'].var()
        }
    
    def _analyze_festival_patterns(self, expenses_df: pd.DataFrame) -> Dict:
        """Analyze spending patterns during festivals"""
        festival_analysis = {}
        
        for festival, info in self.indian_festivals.items():
            festival_months = info['months']
            relevant_categories = info['categories']
            
            # Filter data for festival months and categories
            festival_data = expenses_df[
                (expenses_df['month'].isin(festival_months)) &
                (expenses_df['category'].isin(relevant_categories))
            ]
            
            if not festival_data.empty:
                # Compare with non-festival spending
                non_festival_data = expenses_df[
                    (~expenses_df['month'].isin(festival_months)) &
                    (expenses_df['category'].isin(relevant_categories))
                ]
                
                festival_avg = festival_data.groupby('month')['amount'].sum().mean()
                non_festival_avg = non_festival_data.groupby('month')['amount'].sum().mean() if not non_festival_data.empty else 0
                
                uplift = ((festival_avg - non_festival_avg) / non_festival_avg * 100) if non_festival_avg > 0 else 0
                
                festival_analysis[festival] = {
                    'months': [calendar.month_name[m] for m in festival_months],
                    'categories': relevant_categories,
                    'avg_spending': festival_avg,
                    'uplift_percentage': uplift,
                    'total_transactions': len(festival_data)
                }
        
        return festival_analysis
    
    def _seasonal_decomposition(self, expenses_df: pd.DataFrame) -> Dict:
        """Perform seasonal decomposition of spending"""
        # Monthly total spending
        monthly_totals = expenses_df.groupby(expenses_df['date'].dt.to_period('M'))['amount'].sum()
        
        if len(monthly_totals) < 12:
            return {'error': 'Insufficient data for seasonal decomposition'}
        
        # Simple seasonal decomposition
        monthly_values = monthly_totals.values
        trend = np.convolve(monthly_values, np.ones(3)/3, mode='same')  # 3-month moving average
        
        # Calculate seasonal component
        seasonal = monthly_values - trend
        
        return {
            'trend': trend.tolist(),
            'seasonal': seasonal.tolist(),
            'periods': [str(p) for p in monthly_totals.index],
            'seasonality_strength': np.std(seasonal) / np.std(monthly_values)
        }

class PeerComparison:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def generate_peer_benchmarks(self, user_id: int) -> Dict:
        """Generate anonymous peer comparison benchmarks"""
        try:
            # Get user's financial profile
            user_profile = self._get_user_profile(user_id)
            
            if not user_profile:
                return {'error': 'User profile not available'}
            
            # Find similar users (anonymized)
            peer_group = self._find_peer_group(user_profile)
            
            # Generate benchmarks
            benchmarks = self._calculate_benchmarks(user_profile, peer_group)
            
            return {
                'user_profile': {
                    'income_bracket': user_profile['income_bracket'],
                    'age_group': user_profile['age_group'],
                    'spending_level': user_profile['spending_level']
                },
                'peer_group_size': len(peer_group),
                'benchmarks': benchmarks,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_user_profile(self, user_id: int) -> Optional[Dict]:
        """Get user's financial profile for peer matching"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user basic info
        cursor.execute('SELECT age FROM users WHERE id = ?', (user_id,))
        user_info = cursor.fetchone()
        
        if not user_info:
            conn.close()
            return None
        
        age = user_info[0] or 30
        
        # Get income data
        cursor.execute('''
            SELECT SUM(amount) FROM income 
            WHERE user_id = ? AND frequency = 'monthly'
        ''', (user_id,))
        
        monthly_income = cursor.fetchone()[0] or 0
        
        # Get expense data
        cursor.execute('''
            SELECT SUM(amount) FROM expenses 
            WHERE user_id = ? AND date >= ?
        ''', (user_id, (datetime.now() - timedelta(days=365)).isoformat()))
        
        annual_expenses = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Categorize user
        income_bracket = self._categorize_income(monthly_income * 12)
        age_group = self._categorize_age(age)
        spending_level = self._categorize_spending(annual_expenses)
        
        return {
            'user_id': user_id,
            'age': age,
            'age_group': age_group,
            'annual_income': monthly_income * 12,
            'income_bracket': income_bracket,
            'annual_expenses': annual_expenses,
            'spending_level': spending_level
        }
    
    def _categorize_income(self, annual_income: float) -> str:
        """Categorize income into brackets"""
        if annual_income < 300000:
            return 'low'
        elif annual_income < 800000:
            return 'middle'
        elif annual_income < 1500000:
            return 'upper_middle'
        else:
            return 'high'
    
    def _categorize_age(self, age: int) -> str:
        """Categorize age into groups"""
        if age < 25:
            return 'young'
        elif age < 35:
            return 'early_career'
        elif age < 50:
            return 'mid_career'
        else:
            return 'senior'
    
    def _categorize_spending(self, annual_spending: float) -> str:
        """Categorize spending level"""
        if annual_spending < 200000:
            return 'frugal'
        elif annual_spending < 500000:
            return 'moderate'
        elif annual_spending < 1000000:
            return 'high'
        else:
            return 'luxury'
    
    def _find_peer_group(self, user_profile: Dict) -> List[Dict]:
        """Find similar users for peer comparison (anonymized)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all users with similar profiles
        cursor.execute('''
            SELECT u.id, u.age,
                   COALESCE(SUM(i.amount), 0) * 12 as annual_income,
                   COALESCE(SUM(e.amount), 0) as annual_expenses
            FROM users u
            LEFT JOIN income i ON u.id = i.user_id AND i.frequency = 'monthly'
            LEFT JOIN expenses e ON u.id = e.user_id AND e.date >= ?
            WHERE u.id != ?
            GROUP BY u.id, u.age
        ''', ((datetime.now() - timedelta(days=365)).isoformat(), user_profile['user_id']))
        
        all_users = cursor.fetchall()
        conn.close()
        
        # Filter similar users
        peer_group = []
        for user_data in all_users:
            user_id, age, annual_income, annual_expenses = user_data
            
            if (self._categorize_income(annual_income) == user_profile['income_bracket'] and
                self._categorize_age(age or 30) == user_profile['age_group']):
                
                peer_group.append({
                    'age_group': self._categorize_age(age or 30),
                    'income_bracket': self._categorize_income(annual_income),
                    'annual_income': annual_income,
                    'annual_expenses': annual_expenses,
                    'spending_level': self._categorize_spending(annual_expenses)
                })
        
        return peer_group
    
    def _calculate_benchmarks(self, user_profile: Dict, peer_group: List[Dict]) -> Dict:
        """Calculate benchmark metrics"""
        if not peer_group:
            return {'error': 'No peer group found'}
        
        # Calculate peer statistics
        peer_incomes = [p['annual_income'] for p in peer_group]
        peer_expenses = [p['annual_expenses'] for p in peer_group]
        peer_savings_rates = [(p['annual_income'] - p['annual_expenses']) / p['annual_income'] * 100 
                             for p in peer_group if p['annual_income'] > 0]
        
        # User metrics
        user_savings_rate = ((user_profile['annual_income'] - user_profile['annual_expenses']) / 
                           user_profile['annual_income'] * 100) if user_profile['annual_income'] > 0 else 0
        
        return {
            'income': {
                'user': user_profile['annual_income'],
                'peer_median': np.median(peer_incomes),
                'peer_percentile': stats.percentileofscore(peer_incomes, user_profile['annual_income'])
            },
            'expenses': {
                'user': user_profile['annual_expenses'],
                'peer_median': np.median(peer_expenses),
                'peer_percentile': stats.percentileofscore(peer_expenses, user_profile['annual_expenses'])
            },
            'savings_rate': {
                'user': user_savings_rate,
                'peer_median': np.median(peer_savings_rates) if peer_savings_rates else 0,
                'peer_percentile': stats.percentileofscore(peer_savings_rates, user_savings_rate) if peer_savings_rates else 50
            }
        }

class FinancialHealthScorer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.weights = {
            'savings_rate': 0.25,
            'debt_to_income': 0.20,
            'emergency_fund': 0.15,
            'expense_stability': 0.15,
            'investment_diversification': 0.10,
            'budget_adherence': 0.10,
            'credit_utilization': 0.05
        }
    
    def calculate_financial_health_score(self, user_id: int) -> Dict:
        """Calculate comprehensive financial health score"""
        try:
            # Get user financial data
            financial_data = self._get_financial_data(user_id)
            
            if not financial_data:
                return {'error': 'Insufficient financial data'}
            
            # Calculate individual scores
            scores = {}
            scores['savings_rate'] = self._score_savings_rate(financial_data)
            scores['debt_to_income'] = self._score_debt_to_income(financial_data)
            scores['emergency_fund'] = self._score_emergency_fund(financial_data)
            scores['expense_stability'] = self._score_expense_stability(financial_data)
            scores['investment_diversification'] = self._score_investment_diversification(financial_data)
            scores['budget_adherence'] = self._score_budget_adherence(financial_data)
            scores['credit_utilization'] = self._score_credit_utilization(financial_data)
            
            # Calculate weighted overall score
            overall_score = sum(scores[metric] * self.weights[metric] for metric in scores)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(scores, financial_data)
            
            # Determine health category
            health_category = self._get_health_category(overall_score)
            
            return {
                'overall_score': round(overall_score, 1),
                'health_category': health_category,
                'individual_scores': scores,
                'recommendations': recommendations,
                'financial_summary': {
                    'monthly_income': financial_data['monthly_income'],
                    'monthly_expenses': financial_data['monthly_expenses'],
                    'savings_rate': financial_data['savings_rate'],
                    'debt_to_income_ratio': financial_data['debt_to_income_ratio']
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_financial_data(self, user_id: int) -> Optional[Dict]:
        """Get comprehensive financial data for scoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get income
        cursor.execute('''
            SELECT SUM(amount) FROM income 
            WHERE user_id = ? AND frequency = 'monthly'
        ''', (user_id,))
        monthly_income = cursor.fetchone()[0] or 0
        
        # Get expenses (last 12 months)
        cursor.execute('''
            SELECT SUM(amount) FROM expenses 
            WHERE user_id = ? AND date >= ?
        ''', (user_id, (datetime.now() - timedelta(days=365)).isoformat()))
        annual_expenses = cursor.fetchone()[0] or 0
        monthly_expenses = annual_expenses / 12
        
        # Get debts
        cursor.execute('''
            SELECT SUM(current_balance) FROM debts 
            WHERE user_id = ?
        ''', (user_id,))
        total_debt = cursor.fetchone()[0] or 0
        
        # Get savings goals
        cursor.execute('''
            SELECT SUM(current_amount) FROM savings_goals 
            WHERE user_id = ?
        ''', (user_id,))
        total_savings = cursor.fetchone()[0] or 0
        
        # Get expense variance (stability)
        cursor.execute('''
            SELECT amount, date FROM expenses 
            WHERE user_id = ? AND date >= ?
            ORDER BY date
        ''', (user_id, (datetime.now() - timedelta(days=365)).isoformat()))
        
        expenses_data = cursor.fetchall()
        
        conn.close()
        
        if monthly_income == 0:
            return None
        
        # Calculate metrics
        savings_rate = ((monthly_income - monthly_expenses) / monthly_income * 100) if monthly_income > 0 else 0
        debt_to_income_ratio = (total_debt / (monthly_income * 12) * 100) if monthly_income > 0 else 0
        
        # Calculate expense stability
        if expenses_data:
            df = pd.DataFrame(expenses_data, columns=['amount', 'date'])
            df['date'] = pd.to_datetime(df['date'])
            monthly_totals = df.groupby(df['date'].dt.to_period('M'))['amount'].sum()
            expense_cv = monthly_totals.std() / monthly_totals.mean() if monthly_totals.mean() > 0 else 1
        else:
            expense_cv = 1
        
        return {
            'monthly_income': monthly_income,
            'monthly_expenses': monthly_expenses,
            'annual_income': monthly_income * 12,
            'annual_expenses': annual_expenses,
            'total_debt': total_debt,
            'total_savings': total_savings,
            'savings_rate': savings_rate,
            'debt_to_income_ratio': debt_to_income_ratio,
            'expense_coefficient_variation': expense_cv,
            'emergency_fund_months': total_savings / monthly_expenses if monthly_expenses > 0 else 0
        }
    
    def _score_savings_rate(self, data: Dict) -> float:
        """Score savings rate (0-100)"""
        savings_rate = data['savings_rate']
        if savings_rate >= 30:
            return 100
        elif savings_rate >= 20:
            return 80
        elif savings_rate >= 10:
            return 60
        elif savings_rate >= 5:
            return 40
        else:
            return max(0, savings_rate * 8)  # Scale 0-5% to 0-40
    
    def _score_debt_to_income(self, data: Dict) -> float:
        """Score debt-to-income ratio (0-100, lower debt = higher score)"""
        debt_ratio = data['debt_to_income_ratio']
        if debt_ratio <= 10:
            return 100
        elif debt_ratio <= 20:
            return 80
        elif debt_ratio <= 36:
            return 60
        elif debt_ratio <= 50:
            return 40
        else:
            return max(0, 100 - debt_ratio)
    
    def _score_emergency_fund(self, data: Dict) -> float:
        """Score emergency fund adequacy (0-100)"""
        months = data['emergency_fund_months']
        if months >= 6:
            return 100
        elif months >= 3:
            return 80
        elif months >= 1:
            return 60
        else:
            return months * 60  # Scale 0-1 months to 0-60
    
    def _score_expense_stability(self, data: Dict) -> float:
        """Score expense stability (0-100, lower variation = higher score)"""
        cv = data['expense_coefficient_variation']
        if cv <= 0.1:
            return 100
        elif cv <= 0.2:
            return 80
        elif cv <= 0.3:
            return 60
        elif cv <= 0.5:
            return 40
        else:
            return max(0, 100 - cv * 100)
    
    def _score_investment_diversification(self, data: Dict) -> float:
        """Score investment diversification (simplified)"""
        # Simplified scoring based on savings
        if data['total_savings'] > data['monthly_income'] * 6:
            return 80
        elif data['total_savings'] > data['monthly_income'] * 3:
            return 60
        elif data['total_savings'] > data['monthly_income']:
            return 40
        else:
            return 20
    
    def _score_budget_adherence(self, data: Dict) -> float:
        """Score budget adherence (simplified)"""
        # Simplified scoring based on expense stability
        return self._score_expense_stability(data)
    
    def _score_credit_utilization(self, data: Dict) -> float:
        """Score credit utilization (simplified)"""
        # Simplified scoring - assume good if debt is low
        debt_ratio = data['debt_to_income_ratio']
        if debt_ratio <= 5:
            return 100
        elif debt_ratio <= 15:
            return 80
        elif debt_ratio <= 30:
            return 60
        else:
            return 40
    
    def _generate_recommendations(self, scores: Dict, data: Dict) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        if scores['savings_rate'] < 60:
            recommendations.append("Increase your savings rate to at least 20% of income")
        
        if scores['debt_to_income'] < 60:
            recommendations.append("Focus on reducing debt to improve financial health")
        
        if scores['emergency_fund'] < 60:
            recommendations.append("Build an emergency fund covering 3-6 months of expenses")
        
        if scores['expense_stability'] < 60:
            recommendations.append("Work on stabilizing monthly expenses through better budgeting")
        
        if scores['investment_diversification'] < 60:
            recommendations.append("Consider diversifying investments beyond savings accounts")
        
        return recommendations
    
    def _get_health_category(self, score: float) -> str:
        """Get health category based on score"""
        if score >= 80:
            return 'Excellent'
        elif score >= 70:
            return 'Good'
        elif score >= 60:
            return 'Fair'
        elif score >= 50:
            return 'Poor'
        else:
            return 'Critical'

class BusinessIntelligenceManager:
    def __init__(self, db_path: str):
        self.spending_analyzer = SpendingPatternAnalyzer(db_path)
        self.seasonal_analyzer = SeasonalAnalyzer(db_path)
        self.peer_comparison = PeerComparison(db_path)
        self.health_scorer = FinancialHealthScorer(db_path)
        self.db_path = db_path
    
    def generate_bi_dashboard(self, user_id: int) -> Dict:
        """Generate comprehensive business intelligence dashboard"""
        try:
            # Get all BI components
            spending_patterns = self.spending_analyzer.analyze_spending_patterns(user_id, 12)
            seasonal_analysis = self.seasonal_analyzer.analyze_seasonal_patterns(user_id, 2)
            peer_benchmarks = self.peer_comparison.generate_peer_benchmarks(user_id)
            health_score = self.health_scorer.calculate_financial_health_score(user_id)
            
            return {
                'spending_intelligence': {
                    'patterns_identified': len(spending_patterns.get('patterns', {})),
                    'anomalies_detected': len(spending_patterns.get('anomalies', [])),
                    'top_anomaly': spending_patterns.get('anomalies', [{}])[0] if spending_patterns.get('anomalies') else None
                },
                'seasonal_intelligence': {
                    'peak_spending_months': seasonal_analysis.get('monthly_patterns', {}).get('peak_months', [])[:3],
                    'festival_impact': len(seasonal_analysis.get('festival_patterns', {})),
                    'seasonality_strength': seasonal_analysis.get('seasonal_decomposition', {}).get('seasonality_strength', 0)
                },
                'peer_intelligence': {
                    'peer_group_size': peer_benchmarks.get('peer_group_size', 0),
                    'income_percentile': peer_benchmarks.get('benchmarks', {}).get('income', {}).get('peer_percentile', 50),
                    'savings_percentile': peer_benchmarks.get('benchmarks', {}).get('savings_rate', {}).get('peer_percentile', 50)
                },
                'financial_health': {
                    'overall_score': health_score.get('overall_score', 0),
                    'health_category': health_score.get('health_category', 'Unknown'),
                    'recommendations_count': len(health_score.get('recommendations', []))
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}