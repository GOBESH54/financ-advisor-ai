import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from statsmodels.tsa.arima.model import ARIMA
import joblib
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class BudgetingAI:
    """Rule-based budgeting system with 50/30/20 rule and custom adjustments"""
    
    def __init__(self):
        self.rules = {
            'needs': 0.50,
            'wants': 0.30,
            'savings': 0.20
        }
        
    def analyze_budget(self, income, expenses_df, debts=None):
        """Analyze current budget and provide recommendations"""
        total_income = income
        
        # Categorize expenses
        expense_categories = {
            'needs': ['housing', 'utilities', 'groceries', 'insurance', 'healthcare', 'transportation'],
            'wants': ['entertainment', 'dining', 'shopping', 'hobbies', 'travel'],
            'savings': ['savings', 'investments', 'retirement']
        }
        
        categorized_expenses = {'needs': 0, 'wants': 0, 'savings': 0, 'debt': 0}
        
        if not expenses_df.empty:
            for _, expense in expenses_df.iterrows():
                category = expense.get('category', '').lower()
                for key, values in expense_categories.items():
                    if any(cat in category for cat in values):
                        categorized_expenses[key] += expense['amount']
                        break
                else:
                    categorized_expenses['wants'] += expense['amount']
        
        # Add debt payments
        if debts:
            for debt in debts:
                categorized_expenses['debt'] += debt.get('minimum_payment', 0)
        
        # Calculate recommended budget
        recommended_budget = {
            'needs': total_income * self.rules['needs'],
            'wants': total_income * self.rules['wants'],
            'savings': total_income * self.rules['savings']
        }
        
        # Adjust for debt
        if categorized_expenses['debt'] > 0:
            debt_ratio = categorized_expenses['debt'] / total_income
            if debt_ratio > 0.20:
                # High debt - reduce wants and increase debt payment
                recommended_budget['wants'] *= 0.7
                recommended_budget['debt'] = categorized_expenses['debt']
            else:
                recommended_budget['debt'] = categorized_expenses['debt']
                recommended_budget['savings'] -= categorized_expenses['debt'] * 0.5
        
        # Generate recommendations
        recommendations = []
        
        for category in ['needs', 'wants', 'savings']:
            if category in categorized_expenses:
                actual = categorized_expenses[category]
                recommended = recommended_budget[category]
                
                if actual > recommended * 1.1:
                    recommendations.append({
                        'category': category,
                        'issue': 'overspending',
                        'actual': actual,
                        'recommended': recommended,
                        'action': f'Reduce {category} spending by ${actual - recommended:.2f}'
                    })
                elif actual < recommended * 0.9 and category == 'savings':
                    recommendations.append({
                        'category': category,
                        'issue': 'undersaving',
                        'actual': actual,
                        'recommended': recommended,
                        'action': f'Increase savings by ${recommended - actual:.2f}'
                    })
        
        return {
            'current_allocation': categorized_expenses,
            'recommended_allocation': recommended_budget,
            'recommendations': recommendations,
            'budget_health_score': self._calculate_health_score(categorized_expenses, recommended_budget)
        }
    
    def _calculate_health_score(self, actual, recommended):
        """Calculate budget health score (0-100)"""
        score = 100
        
        for category in ['needs', 'wants', 'savings']:
            if category in actual and category in recommended:
                diff_ratio = abs(actual[category] - recommended[category]) / max(recommended[category], 1)
                score -= min(diff_ratio * 20, 30)
        
        return max(score, 0)

class InvestmentRecommendationAI:
    """AI model for investment recommendations using Random Forest and XGBoost"""
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.investment_types = {
            'low': {'stocks': 20, 'bonds': 70, 'cash': 10},
            'medium': {'stocks': 60, 'bonds': 30, 'cash': 10},
            'high': {'stocks': 80, 'bonds': 15, 'cash': 5}
        }
        
    def train_model(self, training_data=None):
        """Train investment recommendation model"""
        # Generate synthetic training data if none provided
        if training_data is None:
            training_data = self._generate_synthetic_data()
        
        X = training_data[['age', 'income', 'expenses', 'savings', 'debt_ratio', 'risk_score']]
        y = training_data['investment_type']
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Random Forest model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_scaled, y)
        
        # Save model
        os.makedirs('models', exist_ok=True)
        joblib.dump(self.model, 'models/investment_model.pkl')
        joblib.dump(self.scaler, 'models/investment_scaler.pkl')
        
        return True
    
    def _generate_synthetic_data(self):
        """Generate synthetic training data"""
        np.random.seed(42)
        n_samples = 1000
        
        data = []
        for _ in range(n_samples):
            age = np.random.randint(25, 65)
            income = np.random.uniform(30000, 200000)
            expenses = income * np.random.uniform(0.5, 0.9)
            savings = income - expenses
            debt_ratio = np.random.uniform(0, 0.5)
            risk_score = np.random.randint(1, 11)
            
            # Determine investment type based on features
            if age > 50 or risk_score < 4:
                investment_type = 'conservative'
            elif risk_score > 7 and age < 40:
                investment_type = 'aggressive'
            else:
                investment_type = 'moderate'
            
            data.append({
                'age': age,
                'income': income,
                'expenses': expenses,
                'savings': savings,
                'debt_ratio': debt_ratio,
                'risk_score': risk_score,
                'investment_type': investment_type
            })
        
        return pd.DataFrame(data)
    
    def recommend_investments(self, user_profile):
        """Generate investment recommendations"""
        # Load or train model
        if self.model is None:
            if os.path.exists('models/investment_model.pkl'):
                self.model = joblib.load('models/investment_model.pkl')
                self.scaler = joblib.load('models/investment_scaler.pkl')
            else:
                self.train_model()
        
        # Prepare features
        features = pd.DataFrame([{
            'age': user_profile.get('age', 30),
            'income': user_profile.get('income', 50000),
            'expenses': user_profile.get('expenses', 35000),
            'savings': user_profile.get('savings', 15000),
            'debt_ratio': user_profile.get('debt_ratio', 0.2),
            'risk_score': self._map_risk_tolerance(user_profile.get('risk_tolerance', 'medium'))
        }])
        
        # Scale and predict
        features_scaled = self.scaler.transform(features)
        investment_type = self.model.predict(features_scaled)[0]
        confidence = max(self.model.predict_proba(features_scaled)[0])
        
        # Get allocation based on risk tolerance
        risk_level = user_profile.get('risk_tolerance', 'medium')
        allocation = self.investment_types.get(risk_level, self.investment_types['medium'])
        
        # Generate specific recommendations
        recommendations = self._generate_specific_recommendations(
            investment_type, 
            allocation, 
            user_profile
        )
        
        return {
            'investment_type': investment_type,
            'confidence': confidence,
            'allocation': allocation,
            'recommendations': recommendations
        }
    
    def _map_risk_tolerance(self, risk_tolerance):
        """Map risk tolerance to numeric score"""
        mapping = {'low': 3, 'medium': 6, 'high': 9}
        return mapping.get(risk_tolerance, 5)
    
    def _generate_specific_recommendations(self, investment_type, allocation, user_profile):
        """Generate specific investment recommendations"""
        recommendations = []
        
        total_investment = user_profile.get('available_investment', 10000)
        
        if allocation['stocks'] > 0:
            stock_amount = total_investment * (allocation['stocks'] / 100)
            recommendations.append({
                'type': 'stocks',
                'allocation_percentage': allocation['stocks'],
                'amount': stock_amount,
                'specific': 'Consider index funds (S&P 500, Total Market) for diversification'
            })
        
        if allocation['bonds'] > 0:
            bond_amount = total_investment * (allocation['bonds'] / 100)
            recommendations.append({
                'type': 'bonds',
                'allocation_percentage': allocation['bonds'],
                'amount': bond_amount,
                'specific': 'Mix of government and corporate bonds for stability'
            })
        
        if allocation['cash'] > 0:
            cash_amount = total_investment * (allocation['cash'] / 100)
            recommendations.append({
                'type': 'cash/emergency',
                'allocation_percentage': allocation['cash'],
                'amount': cash_amount,
                'specific': 'High-yield savings account for emergency fund'
            })
        
        return recommendations

class SavingsForecastAI:
    """Time series forecasting for savings prediction"""
    
    def __init__(self):
        self.model = None
        
    def forecast_savings(self, historical_data, periods=12):
        """Forecast future savings using ARIMA model"""
        if len(historical_data) < 3:
            # Not enough data for ARIMA, use simple projection
            return self._simple_projection(historical_data, periods)
        
        try:
            # Prepare data
            savings_series = pd.Series(historical_data)
            
            # Fit ARIMA model
            model = ARIMA(savings_series, order=(1, 1, 1))
            self.model = model.fit()
            
            # Generate forecast
            forecast = self.model.forecast(steps=periods)
            
            # Calculate confidence intervals
            forecast_df = pd.DataFrame({
                'forecast': forecast,
                'lower_bound': forecast * 0.9,  # 10% margin
                'upper_bound': forecast * 1.1
            })
            
            return {
                'forecast': forecast_df.to_dict('records'),
                'total_projected': float(forecast.sum()),
                'average_monthly': float(forecast.mean()),
                'model_type': 'ARIMA'
            }
            
        except Exception as e:
            # Fallback to simple projection
            return self._simple_projection(historical_data, periods)
    
    def _simple_projection(self, historical_data, periods):
        """Simple linear projection for limited data"""
        if len(historical_data) == 0:
            return {
                'forecast': [],
                'total_projected': 0,
                'average_monthly': 0,
                'model_type': 'none'
            }
        
        avg_savings = np.mean(historical_data)
        trend = 0
        
        if len(historical_data) > 1:
            # Calculate simple trend
            trend = (historical_data[-1] - historical_data[0]) / len(historical_data)
        
        forecast = []
        for i in range(periods):
            projected = avg_savings + (trend * i)
            forecast.append({
                'forecast': projected,
                'lower_bound': projected * 0.9,
                'upper_bound': projected * 1.1
            })
        
        return {
            'forecast': forecast,
            'total_projected': sum([f['forecast'] for f in forecast]),
            'average_monthly': avg_savings,
            'model_type': 'linear_projection'
        }

class DebtManagementAI:
    """AI for debt repayment strategies and planning"""
    
    def __init__(self):
        self.strategies = ['avalanche', 'snowball', 'hybrid']
        
    def create_repayment_plan(self, debts, extra_payment=0, strategy='avalanche'):
        """Create debt repayment plan"""
        if not debts:
            return {'plan': [], 'total_interest': 0, 'payoff_months': 0}
        
        debts_df = pd.DataFrame(debts)
        
        # Sort debts based on strategy
        if strategy == 'avalanche':
            # Highest interest rate first
            debts_df = debts_df.sort_values('interest_rate', ascending=False)
        elif strategy == 'snowball':
            # Lowest balance first
            debts_df = debts_df.sort_values('current_balance')
        else:  # hybrid
            # Balance between rate and balance
            debts_df['priority'] = debts_df['interest_rate'] * 0.7 + (1 / debts_df['current_balance']) * 0.3
            debts_df = debts_df.sort_values('priority', ascending=False)
        
        repayment_plan = []
        total_interest = 0
        
        for _, debt in debts_df.iterrows():
            plan = self._calculate_payoff(
                debt['current_balance'],
                debt['interest_rate'],
                debt['minimum_payment'] + extra_payment,
                debt['name']
            )
            repayment_plan.append(plan)
            total_interest += plan['total_interest']
            
            # After paying off one debt, add its payment to extra_payment
            extra_payment += debt['minimum_payment']
        
        return {
            'strategy': strategy,
            'plan': repayment_plan,
            'total_interest': total_interest,
            'total_months': max([p['payoff_months'] for p in repayment_plan] if repayment_plan else [0])
        }
    
    def _calculate_payoff(self, balance, rate, payment, name):
        """Calculate debt payoff timeline"""
        monthly_rate = rate / 100 / 12
        remaining_balance = balance
        months = 0
        total_interest = 0
        
        while remaining_balance > 0 and months < 360:  # Max 30 years
            interest_charge = remaining_balance * monthly_rate
            principal_payment = payment - interest_charge
            
            if principal_payment <= 0:
                # Payment doesn't cover interest
                break
            
            remaining_balance -= principal_payment
            total_interest += interest_charge
            months += 1
            
            if remaining_balance < payment:
                # Last payment
                total_interest += remaining_balance * monthly_rate
                remaining_balance = 0
                months += 1
        
        return {
            'debt_name': name,
            'original_balance': balance,
            'monthly_payment': payment,
            'payoff_months': months,
            'total_interest': total_interest,
            'total_paid': balance + total_interest
        }
    
    def compare_strategies(self, debts, extra_payment=0):
        """Compare different debt repayment strategies"""
        results = {}
        
        for strategy in self.strategies:
            plan = self.create_repayment_plan(debts, extra_payment, strategy)
            results[strategy] = {
                'total_interest': plan['total_interest'],
                'payoff_months': plan['total_months'],
                'monthly_payment': sum([d['minimum_payment'] for d in debts]) + extra_payment
            }
        
        # Find best strategy
        best_strategy = min(results.keys(), key=lambda x: results[x]['total_interest'])
        
        return {
            'strategies': results,
            'recommended': best_strategy,
            'savings': results['avalanche']['total_interest'] - results['snowball']['total_interest'] if 'avalanche' in results and 'snowball' in results else 0
        }
