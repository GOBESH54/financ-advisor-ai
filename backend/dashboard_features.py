import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import json
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """Real-time notifications for budget alerts and bill reminders"""
    
    def __init__(self):
        self.notification_types = {
            'budget_alert': {'priority': 'high', 'icon': '⚠️'},
            'bill_reminder': {'priority': 'medium', 'icon': '📅'},
            'goal_milestone': {'priority': 'low', 'icon': '🎯'},
            'expense_spike': {'priority': 'high', 'icon': '📈'},
            'savings_low': {'priority': 'medium', 'icon': '💰'}
        }
    
    def generate_notifications(self, user_data: Dict) -> List[Dict]:
        """Generate all notifications for user"""
        notifications = []
        
        # Budget alerts
        notifications.extend(self._check_budget_alerts(user_data))
        
        # Bill reminders
        notifications.extend(self._check_bill_reminders(user_data))
        
        # Goal milestones
        notifications.extend(self._check_goal_milestones(user_data))
        
        # Expense spikes
        notifications.extend(self._check_expense_spikes(user_data))
        
        # Sort by priority and timestamp
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        notifications.sort(key=lambda n: (priority_order.get(n['priority'], 3), n['timestamp']), reverse=True)
        
        return notifications
    
    def _check_budget_alerts(self, user_data: Dict) -> List[Dict]:
        """Check for budget limit alerts"""
        alerts = []
        expenses = user_data.get('expenses', [])
        monthly_income = user_data.get('monthly_income', 0)
        
        if not expenses or not monthly_income:
            return alerts
        
        # Calculate current month expenses by category
        current_month = datetime.now().strftime('%Y-%m')
        current_expenses = [e for e in expenses if e['date'].startswith(current_month)]
        
        # Group by category
        category_totals = {}
        for expense in current_expenses:
            category = expense.get('category', 'other')
            category_totals[category] = category_totals.get(category, 0) + expense['amount']
        
        # Define budget limits (percentage of monthly income)
        budget_limits = {
            'groceries': 0.15,  # 15% of income
            'food_dining': 0.10,  # 10% of income
            'transportation': 0.15,  # 15% of income
            'utilities': 0.10,  # 10% of income
            'entertainment': 0.05,  # 5% of income
            'shopping': 0.10,  # 10% of income
            'other': 0.15  # 15% of income
        }
        
        # Check each category
        for category, spent in category_totals.items():
            limit = budget_limits.get(category, 0.15) * monthly_income
            
            if spent > limit * 0.8:  # Alert at 80% of limit
                severity = 'critical' if spent > limit else 'warning'
                
                alerts.append({
                    'id': f'budget_{category}_{current_month}',
                    'type': 'budget_alert',
                    'title': f'{category.title()} Budget Alert',
                    'message': f'You\'ve spent ₹{spent:,.0f} of ₹{limit:,.0f} budget ({spent/limit*100:.0f}%)',
                    'severity': severity,
                    'priority': 'high',
                    'icon': '⚠️',
                    'timestamp': datetime.now().isoformat(),
                    'category': category,
                    'action': 'reduce_spending'
                })
        
        return alerts
    
    def _check_bill_reminders(self, user_data: Dict) -> List[Dict]:
        """Check for upcoming bill due dates"""
        reminders = []
        debts = user_data.get('debts', [])
        
        today = datetime.now().date()
        
        for debt in debts:
            if debt.get('due_date'):
                due_date = datetime.strptime(debt['due_date'], '%Y-%m-%d').date()
                days_until_due = (due_date - today).days
                
                if 0 <= days_until_due <= 7:  # Due within a week
                    urgency = 'urgent' if days_until_due <= 2 else 'reminder'
                    
                    reminders.append({
                        'id': f'bill_{debt["name"]}_{debt["due_date"]}',
                        'type': 'bill_reminder',
                        'title': f'{debt["name"]} Payment Due',
                        'message': f'₹{debt["minimum_payment"]:,.0f} due in {days_until_due} days',
                        'severity': urgency,
                        'priority': 'medium',
                        'icon': '📅',
                        'timestamp': datetime.now().isoformat(),
                        'due_date': debt['due_date'],
                        'amount': debt['minimum_payment'],
                        'action': 'pay_bill'
                    })
        
        return reminders
    
    def _check_goal_milestones(self, user_data: Dict) -> List[Dict]:
        """Check for savings goal milestones"""
        milestones = []
        goals = user_data.get('savings_goals', [])
        
        for goal in goals:
            progress = (goal['current_amount'] / goal['target_amount']) * 100
            
            # Check for milestone achievements (25%, 50%, 75%, 90%)
            milestone_thresholds = [25, 50, 75, 90]
            
            for threshold in milestone_thresholds:
                if progress >= threshold and not goal.get(f'milestone_{threshold}_notified'):
                    milestones.append({
                        'id': f'goal_{goal["name"]}_{threshold}',
                        'type': 'goal_milestone',
                        'title': f'{goal["name"]} Milestone',
                        'message': f'Congratulations! You\'ve reached {threshold}% of your goal (₹{goal["current_amount"]:,.0f})',
                        'severity': 'achievement',
                        'priority': 'low',
                        'icon': '🎯',
                        'timestamp': datetime.now().isoformat(),
                        'progress': progress,
                        'action': 'view_goal'
                    })
        
        return milestones
    
    def _check_expense_spikes(self, user_data: Dict) -> List[Dict]:
        """Check for unusual expense spikes"""
        spikes = []
        expenses = user_data.get('expenses', [])
        
        if len(expenses) < 30:  # Need sufficient data
            return spikes
        
        # Calculate daily spending for last 30 days
        recent_expenses = [e for e in expenses if 
                          (datetime.now() - datetime.strptime(e['date'], '%Y-%m-%d')).days <= 30]
        
        daily_spending = {}
        for expense in recent_expenses:
            date = expense['date']
            daily_spending[date] = daily_spending.get(date, 0) + expense['amount']
        
        if len(daily_spending) < 7:
            return spikes
        
        amounts = list(daily_spending.values())
        avg_daily = np.mean(amounts)
        std_daily = np.std(amounts)
        
        # Check last 3 days for spikes
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            if date in daily_spending:
                amount = daily_spending[date]
                if amount > avg_daily + (2 * std_daily):  # 2 standard deviations above mean
                    spikes.append({
                        'id': f'spike_{date}',
                        'type': 'expense_spike',
                        'title': 'Unusual Spending Detected',
                        'message': f'You spent ₹{amount:,.0f} on {date}, which is {amount/avg_daily:.1f}x your daily average',
                        'severity': 'warning',
                        'priority': 'high',
                        'icon': '📈',
                        'timestamp': datetime.now().isoformat(),
                        'date': date,
                        'amount': amount,
                        'action': 'review_expenses'
                    })
        
        return spikes


class InteractiveCharts:
    """Interactive charts with drill-down capabilities"""
    
    def create_spending_analysis_chart(self, expenses_df: pd.DataFrame) -> str:
        """Create drill-down spending analysis chart"""
        if expenses_df.empty:
            return json.dumps({'error': 'No data available'})
        
        # Prepare data
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['month'] = expenses_df['date'].dt.to_period('M').astype(str)
        
        # Monthly totals by category
        monthly_category = expenses_df.groupby(['month', 'category'])['amount'].sum().reset_index()
        
        # Create sunburst chart for drill-down
        fig = go.Figure()
        
        # Add monthly bars
        monthly_totals = expenses_df.groupby('month')['amount'].sum().reset_index()
        
        fig.add_trace(go.Bar(
            x=monthly_totals['month'],
            y=monthly_totals['amount'],
            name='Monthly Total',
            marker_color='lightblue',
            hovertemplate='<b>%{x}</b><br>Total: ₹%{y:,.0f}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Monthly Spending Analysis (Click bars for category breakdown)',
            xaxis_title='Month',
            yaxis_title='Amount (₹)',
            template='plotly_white',
            hovermode='x unified'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def create_category_drill_down(self, expenses_df: pd.DataFrame, month: str = None) -> str:
        """Create category drill-down for specific month"""
        if expenses_df.empty:
            return json.dumps({'error': 'No data available'})
        
        # Filter by month if specified
        if month:
            expenses_df = expenses_df[expenses_df['date'].dt.to_period('M').astype(str) == month]
        
        # Category breakdown
        category_totals = expenses_df.groupby('category')['amount'].sum().reset_index()
        category_totals = category_totals.sort_values('amount', ascending=False)
        
        # Create pie chart with hover details
        fig = go.Figure(data=[go.Pie(
            labels=category_totals['category'],
            values=category_totals['amount'],
            hole=0.3,
            hovertemplate='<b>%{label}</b><br>Amount: ₹%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title=f'Expense Categories {f"for {month}" if month else ""}',
            template='plotly_white'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def create_trend_analysis(self, expenses_df: pd.DataFrame) -> str:
        """Create trend analysis with multiple metrics"""
        if expenses_df.empty:
            return json.dumps({'error': 'No data available'})
        
        # Prepare data
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['month'] = expenses_df['date'].dt.to_period('M')
        
        # Monthly trends
        monthly_data = expenses_df.groupby('month').agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        monthly_data.columns = ['month', 'total', 'avg_per_transaction', 'transaction_count']
        monthly_data['month_str'] = monthly_data['month'].astype(str)
        
        # Create subplots
        fig = go.Figure()
        
        # Total spending trend
        fig.add_trace(go.Scatter(
            x=monthly_data['month_str'],
            y=monthly_data['total'],
            mode='lines+markers',
            name='Total Spending',
            line=dict(color='red', width=3),
            hovertemplate='<b>%{x}</b><br>Total: ₹%{y:,.0f}<extra></extra>'
        ))
        
        # Transaction count trend
        fig.add_trace(go.Scatter(
            x=monthly_data['month_str'],
            y=monthly_data['transaction_count'],
            mode='lines+markers',
            name='Transaction Count',
            yaxis='y2',
            line=dict(color='blue', width=2),
            hovertemplate='<b>%{x}</b><br>Transactions: %{y}<extra></extra>'
        ))
        
        fig.update_layout(
            title='Spending Trends Analysis',
            xaxis_title='Month',
            yaxis=dict(title='Amount (₹)', side='left'),
            yaxis2=dict(title='Transaction Count', side='right', overlaying='y'),
            template='plotly_white',
            hovermode='x unified'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)


class GoalTracker:
    """Visual progress tracking for savings goals"""
    
    def create_goal_progress_chart(self, goals: List[Dict]) -> str:
        """Create visual progress bars for goals"""
        if not goals:
            return json.dumps({'error': 'No goals found'})
        
        # Prepare data
        goal_names = []
        progress_values = []
        target_amounts = []
        current_amounts = []
        
        for goal in goals:
            progress = (goal['current_amount'] / goal['target_amount']) * 100
            goal_names.append(goal['name'])
            progress_values.append(min(progress, 100))  # Cap at 100%
            target_amounts.append(goal['target_amount'])
            current_amounts.append(goal['current_amount'])
        
        # Create horizontal bar chart
        fig = go.Figure()
        
        # Progress bars
        fig.add_trace(go.Bar(
            y=goal_names,
            x=progress_values,
            orientation='h',
            marker=dict(
                color=progress_values,
                colorscale='RdYlGn',
                cmin=0,
                cmax=100
            ),
            text=[f'{p:.1f}%' for p in progress_values],
            textposition='inside',
            hovertemplate='<b>%{y}</b><br>Progress: %{x:.1f}%<br>Current: ₹%{customdata[0]:,.0f}<br>Target: ₹%{customdata[1]:,.0f}<extra></extra>',
            customdata=list(zip(current_amounts, target_amounts))
        ))
        
        fig.update_layout(
            title='Savings Goals Progress',
            xaxis_title='Progress (%)',
            yaxis_title='Goals',
            template='plotly_white',
            xaxis=dict(range=[0, 100]),
            height=max(400, len(goals) * 60)
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def calculate_goal_insights(self, goals: List[Dict], monthly_savings: float) -> Dict:
        """Calculate insights for goals"""
        insights = {
            'total_goals': len(goals),
            'completed_goals': 0,
            'total_target': 0,
            'total_current': 0,
            'projected_completion': {},
            'recommendations': []
        }
        
        for goal in goals:
            insights['total_target'] += goal['target_amount']
            insights['total_current'] += goal['current_amount']
            
            progress = goal['current_amount'] / goal['target_amount']
            if progress >= 1.0:
                insights['completed_goals'] += 1
            elif monthly_savings > 0:
                remaining = goal['target_amount'] - goal['current_amount']
                months_to_complete = remaining / monthly_savings
                insights['projected_completion'][goal['name']] = months_to_complete
        
        # Generate recommendations
        if monthly_savings <= 0:
            insights['recommendations'].append("Increase your monthly savings to achieve your goals faster")
        elif insights['total_current'] / insights['total_target'] < 0.5:
            insights['recommendations'].append("Consider prioritizing your most important goals")
        
        return insights


class ExpenseTrendAnalyzer:
    """Month-over-month expense trend analysis"""
    
    def analyze_trends(self, expenses_df: pd.DataFrame) -> Dict:
        """Analyze expense trends and patterns"""
        if expenses_df.empty:
            return {'error': 'No expense data available'}
        
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['month'] = expenses_df['date'].dt.to_period('M')
        
        # Monthly totals
        monthly_totals = expenses_df.groupby('month')['amount'].sum().reset_index()
        monthly_totals['month_str'] = monthly_totals['month'].astype(str)
        monthly_totals = monthly_totals.sort_values('month')
        
        if len(monthly_totals) < 2:
            return {'error': 'Need at least 2 months of data'}
        
        # Calculate month-over-month changes
        monthly_totals['mom_change'] = monthly_totals['amount'].pct_change() * 100
        monthly_totals['mom_absolute'] = monthly_totals['amount'].diff()
        
        # Category trends
        category_trends = expenses_df.groupby(['month', 'category'])['amount'].sum().reset_index()
        category_pivot = category_trends.pivot(index='month', columns='category', values='amount').fillna(0)
        category_changes = category_pivot.pct_change().iloc[-1] * 100  # Latest month changes
        
        # Identify patterns
        trends = {
            'overall_trend': 'increasing' if monthly_totals['mom_change'].iloc[-1] > 0 else 'decreasing',
            'avg_monthly_change': monthly_totals['mom_change'].mean(),
            'volatility': monthly_totals['mom_change'].std(),
            'total_last_month': monthly_totals['amount'].iloc[-1],
            'change_last_month': monthly_totals['mom_change'].iloc[-1],
            'category_changes': category_changes.to_dict(),
            'highest_increase_category': category_changes.idxmax() if not category_changes.empty else None,
            'highest_decrease_category': category_changes.idxmin() if not category_changes.empty else None
        }
        
        return trends
    
    def create_trend_chart(self, expenses_df: pd.DataFrame) -> str:
        """Create comprehensive trend visualization"""
        if expenses_df.empty:
            return json.dumps({'error': 'No data available'})
        
        # Prepare data
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['month'] = expenses_df['date'].dt.to_period('M')
        
        # Monthly totals and changes
        monthly_data = expenses_df.groupby('month')['amount'].sum().reset_index()
        monthly_data['month_str'] = monthly_data['month'].astype(str)
        monthly_data = monthly_data.sort_values('month')
        monthly_data['mom_change'] = monthly_data['amount'].pct_change() * 100
        
        # Create dual-axis chart
        fig = go.Figure()
        
        # Monthly spending
        fig.add_trace(go.Bar(
            x=monthly_data['month_str'],
            y=monthly_data['amount'],
            name='Monthly Spending',
            marker_color='lightblue',
            yaxis='y',
            hovertemplate='<b>%{x}</b><br>Amount: ₹%{y:,.0f}<extra></extra>'
        ))
        
        # Month-over-month change
        fig.add_trace(go.Scatter(
            x=monthly_data['month_str'],
            y=monthly_data['mom_change'],
            mode='lines+markers',
            name='MoM Change (%)',
            line=dict(color='red', width=2),
            yaxis='y2',
            hovertemplate='<b>%{x}</b><br>Change: %{y:.1f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title='Expense Trends Analysis',
            xaxis_title='Month',
            yaxis=dict(title='Amount (₹)', side='left'),
            yaxis2=dict(title='Month-over-Month Change (%)', side='right', overlaying='y'),
            template='plotly_white',
            hovermode='x unified'
        )
        
        return json.dumps(fig, cls=PlotlyJSONEncoder)
    
    def generate_insights(self, trends: Dict) -> List[str]:
        """Generate actionable insights from trends"""
        insights = []
        
        if trends.get('change_last_month', 0) > 10:
            insights.append(f"⚠️ Your expenses increased by {trends['change_last_month']:.1f}% last month")
        elif trends.get('change_last_month', 0) < -10:
            insights.append(f"✅ Great job! Your expenses decreased by {abs(trends['change_last_month']):.1f}% last month")
        
        if trends.get('volatility', 0) > 20:
            insights.append("📊 Your spending is quite volatile - consider creating a more consistent budget")
        
        highest_increase = trends.get('highest_increase_category')
        if highest_increase and trends['category_changes'][highest_increase] > 25:
            insights.append(f"📈 {highest_increase} expenses increased significantly - review this category")
        
        return insights
