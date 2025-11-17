import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class SpendingPredictor:
    """Predict next month's expenses by category"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.categories = []
    
    def train(self, expenses_df: pd.DataFrame) -> Dict:
        """Train spending prediction models for each category"""
        if expenses_df.empty:
            return {'error': 'No data to train'}
        
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['month'] = expenses_df['date'].dt.to_period('M')
        
        # Group by month and category
        monthly_spending = expenses_df.groupby(['month', 'category'])['amount'].sum().reset_index()
        monthly_spending['month_num'] = monthly_spending['month'].dt.month
        monthly_spending['year'] = monthly_spending['month'].dt.year
        
        results = {}
        
        for category in monthly_spending['category'].unique():
            cat_data = monthly_spending[monthly_spending['category'] == category].copy()
            
            if len(cat_data) < 3:
                continue
            
            # Create features
            cat_data = cat_data.sort_values('month')
            cat_data['lag_1'] = cat_data['amount'].shift(1)
            cat_data['lag_2'] = cat_data['amount'].shift(2)
            cat_data['rolling_mean'] = cat_data['amount'].rolling(3, min_periods=1).mean()
            cat_data = cat_data.dropna()
            
            if len(cat_data) < 2:
                continue
            
            # Features and target
            features = ['month_num', 'lag_1', 'lag_2', 'rolling_mean']
            X = cat_data[features]
            y = cat_data['amount']
            
            # Train model
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            scaler = StandardScaler()
            
            X_scaled = scaler.fit_transform(X)
            model.fit(X_scaled, y)
            
            self.models[category] = model
            self.scalers[category] = scaler
            
            # Calculate accuracy
            y_pred = model.predict(X_scaled)
            mae = mean_absolute_error(y, y_pred)
            results[category] = {'mae': mae, 'samples': len(cat_data)}
        
        self.categories = list(self.models.keys())
        return results
    
    def predict_next_month(self, expenses_df: pd.DataFrame) -> Dict:
        """Predict next month's spending by category"""
        if not self.models:
            self.train(expenses_df)
        
        predictions = {}
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        
        for category in self.categories:
            cat_data = expenses_df[expenses_df['category'] == category].copy()
            
            if cat_data.empty:
                predictions[category] = 0
                continue
            
            # Get recent data
            cat_data = cat_data.sort_values('date')
            recent_amounts = cat_data['amount'].tail(3).tolist()
            
            # Pad if needed
            while len(recent_amounts) < 3:
                recent_amounts = [recent_amounts[0] if recent_amounts else 0] + recent_amounts
            
            next_month = datetime.now().month + 1
            if next_month > 12:
                next_month = 1
            
            # Create features
            features = [
                next_month,
                recent_amounts[-1],  # lag_1
                recent_amounts[-2],  # lag_2
                np.mean(recent_amounts)  # rolling_mean
            ]
            
            # Predict
            X = np.array(features).reshape(1, -1)
            X_scaled = self.scalers[category].transform(X)
            prediction = self.models[category].predict(X_scaled)[0]
            
            predictions[category] = max(0, prediction)
        
        return predictions

class BudgetOptimizer:
    """AI-suggested budget adjustments"""
    
    def __init__(self):
        self.optimal_ratios = {
            'groceries': 0.15,
            'food_dining': 0.08,
            'transportation': 0.12,
            'utilities': 0.10,
            'entertainment': 0.05,
            'shopping': 0.08,
            'healthcare': 0.05
        }
    
    def optimize_budget(self, income: float, expenses_df: pd.DataFrame) -> Dict:
        """Suggest budget optimizations"""
        if expenses_df.empty or income <= 0:
            return {'error': 'Invalid data'}
        
        # Current spending by category
        current_spending = expenses_df.groupby('category')['amount'].sum().to_dict()
        total_expenses = sum(current_spending.values())
        
        suggestions = []
        optimized_budget = {}
        
        for category, amount in current_spending.items():
            current_ratio = amount / income
            optimal_ratio = self.optimal_ratios.get(category, 0.05)
            optimal_amount = income * optimal_ratio
            
            optimized_budget[category] = optimal_amount
            
            if current_ratio > optimal_ratio * 1.2:  # 20% over optimal
                savings = amount - optimal_amount
                suggestions.append({
                    'category': category,
                    'type': 'reduce',
                    'current': amount,
                    'suggested': optimal_amount,
                    'savings': savings,
                    'message': f'Reduce {category} spending by ₹{savings:,.0f} ({current_ratio*100:.1f}% → {optimal_ratio*100:.1f}% of income)'
                })
        
        # Emergency fund suggestion
        emergency_fund = income * 6  # 6 months of income
        current_savings_rate = (income - total_expenses) / income
        
        if current_savings_rate < 0.20:  # Less than 20% savings
            suggestions.append({
                'category': 'savings',
                'type': 'increase',
                'current': income - total_expenses,
                'suggested': income * 0.20,
                'message': f'Increase savings rate to 20% (₹{income * 0.20:,.0f}/month)'
            })
        
        return {
            'suggestions': suggestions,
            'optimized_budget': optimized_budget,
            'potential_savings': sum(s.get('savings', 0) for s in suggestions if s['type'] == 'reduce'),
            'current_savings_rate': current_savings_rate * 100
        }

class FraudDetector:
    """Identify suspicious transactions"""
    
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def detect_fraud(self, transactions_df: pd.DataFrame) -> List[Dict]:
        """Detect suspicious transactions"""
        if transactions_df.empty or len(transactions_df) < 10:
            return []
        
        # Prepare features
        df = transactions_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['hour'] = df['date'].dt.hour
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Amount statistics
        df['amount_zscore'] = np.abs((df['amount'] - df['amount'].mean()) / df['amount'].std())
        
        # Time-based features
        df['days_since_last'] = df['date'].diff().dt.days.fillna(0)
        
        # Category encoding
        category_counts = df['category'].value_counts()
        df['category_frequency'] = df['category'].map(category_counts)
        
        features = ['amount', 'hour', 'day_of_week', 'is_weekend', 
                   'amount_zscore', 'days_since_last', 'category_frequency']
        
        X = df[features].fillna(0)
        
        # Train and predict
        if not self.is_trained:
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled)
            self.is_trained = True
        else:
            X_scaled = self.scaler.transform(X)
        
        anomaly_scores = self.model.decision_function(X_scaled)
        is_fraud = self.model.predict(X_scaled) == -1
        
        # Get suspicious transactions
        suspicious = []
        for idx, is_suspicious in enumerate(is_fraud):
            if is_suspicious:
                row = df.iloc[idx]
                reasons = []
                
                if row['amount_zscore'] > 2:
                    reasons.append('Unusually high amount')
                if row['hour'] < 6 or row['hour'] > 22:
                    reasons.append('Unusual time')
                if row['days_since_last'] > 30:
                    reasons.append('Long gap since last transaction')
                
                suspicious.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'description': row.get('description', ''),
                    'amount': row['amount'],
                    'category': row['category'],
                    'anomaly_score': anomaly_scores[idx],
                    'reasons': reasons or ['Statistical anomaly']
                })
        
        return sorted(suspicious, key=lambda x: x['anomaly_score'])

class CashflowForecaster:
    """6-month cashflow predictions"""
    
    def __init__(self):
        self.income_model = RandomForestRegressor(n_estimators=30, random_state=42)
        self.expense_model = RandomForestRegressor(n_estimators=30, random_state=42)
        self.scaler = StandardScaler()
    
    def forecast_cashflow(self, income_df: pd.DataFrame, expenses_df: pd.DataFrame, periods: int = 6) -> Dict:
        """Forecast cashflow for next 6 months"""
        
        # Prepare monthly data
        income_monthly = self._prepare_monthly_data(income_df, 'income')
        expense_monthly = self._prepare_monthly_data(expenses_df, 'expense')
        
        if len(income_monthly) < 3 or len(expense_monthly) < 3:
            return self._simple_forecast(income_df, expenses_df, periods)
        
        # Forecast income and expenses
        income_forecast = self._forecast_series(income_monthly['amount'], periods)
        expense_forecast = self._forecast_series(expense_monthly['amount'], periods)
        
        # Calculate cashflow
        cashflow_forecast = []
        cumulative_cashflow = 0
        
        for i in range(periods):
            monthly_income = income_forecast[i]
            monthly_expense = expense_forecast[i]
            net_cashflow = monthly_income - monthly_expense
            cumulative_cashflow += net_cashflow
            
            forecast_date = datetime.now() + timedelta(days=30 * (i + 1))
            
            cashflow_forecast.append({
                'month': forecast_date.strftime('%Y-%m'),
                'income': monthly_income,
                'expenses': monthly_expense,
                'net_cashflow': net_cashflow,
                'cumulative_cashflow': cumulative_cashflow
            })
        
        # Analysis
        avg_monthly_cashflow = np.mean([cf['net_cashflow'] for cf in cashflow_forecast])
        months_to_break_even = None
        
        if avg_monthly_cashflow < 0:
            current_balance = 0  # Assume starting balance
            for i, cf in enumerate(cashflow_forecast):
                current_balance += cf['net_cashflow']
                if current_balance < 0:
                    months_to_break_even = i + 1
                    break
        
        return {
            'forecast': cashflow_forecast,
            'summary': {
                'avg_monthly_income': np.mean([cf['income'] for cf in cashflow_forecast]),
                'avg_monthly_expenses': np.mean([cf['expenses'] for cf in cashflow_forecast]),
                'avg_monthly_cashflow': avg_monthly_cashflow,
                'total_cashflow_6m': sum([cf['net_cashflow'] for cf in cashflow_forecast]),
                'months_to_break_even': months_to_break_even
            }
        }
    
    def _prepare_monthly_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """Prepare monthly aggregated data"""
        if df.empty:
            return pd.DataFrame()
        
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.to_period('M')
        
        monthly = df.groupby('month')['amount'].sum().reset_index()
        monthly['month_num'] = monthly['month'].dt.month
        monthly['trend'] = range(len(monthly))
        
        return monthly
    
    def _forecast_series(self, series: pd.Series, periods: int) -> List[float]:
        """Forecast time series using simple trend"""
        if len(series) < 3:
            return [series.mean()] * periods
        
        # Simple linear trend
        x = np.arange(len(series))
        y = series.values
        
        # Fit linear regression
        slope = np.polyfit(x, y, 1)[0]
        last_value = y[-1]
        
        forecast = []
        for i in range(1, periods + 1):
            predicted = last_value + (slope * i)
            # Add some seasonality (simple)
            seasonal_factor = 1 + 0.1 * np.sin(2 * np.pi * i / 12)
            forecast.append(max(0, predicted * seasonal_factor))
        
        return forecast
    
    def _simple_forecast(self, income_df: pd.DataFrame, expenses_df: pd.DataFrame, periods: int) -> Dict:
        """Simple forecast when insufficient data"""
        avg_income = income_df['amount'].mean() if not income_df.empty else 0
        avg_expense = expenses_df['amount'].mean() if not expenses_df.empty else 0
        
        forecast = []
        cumulative = 0
        
        for i in range(periods):
            net = avg_income - avg_expense
            cumulative += net
            forecast_date = datetime.now() + timedelta(days=30 * (i + 1))
            
            forecast.append({
                'month': forecast_date.strftime('%Y-%m'),
                'income': avg_income,
                'expenses': avg_expense,
                'net_cashflow': net,
                'cumulative_cashflow': cumulative
            })
        
        return {
            'forecast': forecast,
            'summary': {
                'avg_monthly_income': avg_income,
                'avg_monthly_expenses': avg_expense,
                'avg_monthly_cashflow': avg_income - avg_expense,
                'total_cashflow_6m': (avg_income - avg_expense) * periods,
                'months_to_break_even': None
            }
        }