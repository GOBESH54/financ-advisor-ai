import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from dataclasses import dataclass
import json
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import base64

@dataclass
class TaxDeduction:
    section: str
    description: str
    amount: float
    limit: float
    eligible_amount: float

@dataclass
class CashflowItem:
    category: str
    amount: float
    item_type: str  # 'inflow' or 'outflow'
    subcategory: str = ''

class TaxReportGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.tax_sections = {
            '80C': {'limit': 150000, 'description': 'Life Insurance, PPF, ELSS, etc.'},
            '80D': {'limit': 25000, 'description': 'Health Insurance Premium'},
            '80E': {'limit': None, 'description': 'Education Loan Interest'},
            '80G': {'limit': None, 'description': 'Donations'},
            '24B': {'limit': 200000, 'description': 'Home Loan Interest'},
            'HRA': {'limit': None, 'description': 'House Rent Allowance'}
        }
    
    def generate_itr_summary(self, user_id: int, financial_year: str) -> Dict:
        """Generate ITR-ready tax summary"""
        try:
            start_date = f"{int(financial_year.split('-')[0])}-04-01"
            end_date = f"{int(financial_year.split('-')[1])}-03-31"
            
            # Get income data
            income_data = self._get_income_data(user_id, start_date, end_date)
            
            # Get deduction data
            deductions = self._calculate_deductions(user_id, start_date, end_date)
            
            # Calculate tax liability
            tax_calculation = self._calculate_tax_liability(income_data, deductions)
            
            # Get capital gains
            capital_gains = self._get_capital_gains(user_id, start_date, end_date)
            
            return {
                'financial_year': financial_year,
                'income_summary': income_data,
                'deductions': deductions,
                'tax_calculation': tax_calculation,
                'capital_gains': capital_gains,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_income_data(self, user_id: int, start_date: str, end_date: str) -> Dict:
        """Get income data for tax calculation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT source, SUM(amount) as total_amount
            FROM income 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY source
        ''', (user_id, start_date, end_date))
        
        income_sources = cursor.fetchall()
        conn.close()
        
        # Categorize income
        salary_income = 0
        other_income = 0
        
        for source, amount in income_sources:
            if 'salary' in source.lower() or 'wage' in source.lower():
                salary_income += amount
            else:
                other_income += amount
        
        return {
            'salary_income': salary_income,
            'other_income': other_income,
            'total_income': salary_income + other_income,
            'income_sources': [{'source': s[0], 'amount': s[1]} for s in income_sources]
        }
    
    def _calculate_deductions(self, user_id: int, start_date: str, end_date: str) -> List[TaxDeduction]:
        """Calculate tax deductions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get expenses that qualify for deductions
        cursor.execute('''
            SELECT category, description, SUM(amount) as total_amount
            FROM expenses 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            AND category IN ('insurance', 'investment', 'education', 'medical', 'donation')
            GROUP BY category, description
        ''', (user_id, start_date, end_date))
        
        expense_data = cursor.fetchall()
        conn.close()
        
        deductions = []
        
        # Map expenses to tax sections
        section_80c = 0
        section_80d = 0
        section_80e = 0
        section_80g = 0
        
        for category, description, amount in expense_data:
            if category == 'insurance' and 'life' in description.lower():
                section_80c += amount
            elif category == 'investment' and any(term in description.lower() for term in ['ppf', 'elss', 'nsc']):
                section_80c += amount
            elif category == 'insurance' and 'health' in description.lower():
                section_80d += amount
            elif category == 'education' and 'loan' in description.lower():
                section_80e += amount
            elif category == 'donation':
                section_80g += amount
        
        # Create deduction objects
        if section_80c > 0:
            deductions.append(TaxDeduction(
                section='80C',
                description=self.tax_sections['80C']['description'],
                amount=section_80c,
                limit=self.tax_sections['80C']['limit'],
                eligible_amount=min(section_80c, self.tax_sections['80C']['limit'])
            ))
        
        if section_80d > 0:
            deductions.append(TaxDeduction(
                section='80D',
                description=self.tax_sections['80D']['description'],
                amount=section_80d,
                limit=self.tax_sections['80D']['limit'],
                eligible_amount=min(section_80d, self.tax_sections['80D']['limit'])
            ))
        
        if section_80e > 0:
            deductions.append(TaxDeduction(
                section='80E',
                description=self.tax_sections['80E']['description'],
                amount=section_80e,
                limit=0,  # No limit
                eligible_amount=section_80e
            ))
        
        if section_80g > 0:
            deductions.append(TaxDeduction(
                section='80G',
                description=self.tax_sections['80G']['description'],
                amount=section_80g,
                limit=0,  # No limit
                eligible_amount=section_80g
            ))
        
        return deductions
    
    def _calculate_tax_liability(self, income_data: Dict, deductions: List[TaxDeduction]) -> Dict:
        """Calculate tax liability"""
        gross_income = income_data['total_income']
        total_deductions = sum(d.eligible_amount for d in deductions)
        taxable_income = max(0, gross_income - total_deductions)
        
        # Tax slabs for FY 2023-24 (New Regime)
        tax = 0
        if taxable_income > 300000:
            if taxable_income <= 600000:
                tax += (taxable_income - 300000) * 0.05
            elif taxable_income <= 900000:
                tax += 300000 * 0.05 + (taxable_income - 600000) * 0.10
            elif taxable_income <= 1200000:
                tax += 300000 * 0.05 + 300000 * 0.10 + (taxable_income - 900000) * 0.15
            elif taxable_income <= 1500000:
                tax += 300000 * 0.05 + 300000 * 0.10 + 300000 * 0.15 + (taxable_income - 1200000) * 0.20
            else:
                tax += 300000 * 0.05 + 300000 * 0.10 + 300000 * 0.15 + 300000 * 0.20 + (taxable_income - 1500000) * 0.30
        
        # Add cess
        cess = tax * 0.04
        total_tax = tax + cess
        
        return {
            'gross_income': gross_income,
            'total_deductions': total_deductions,
            'taxable_income': taxable_income,
            'income_tax': tax,
            'cess': cess,
            'total_tax_liability': total_tax,
            'effective_tax_rate': (total_tax / gross_income * 100) if gross_income > 0 else 0
        }
    
    def _get_capital_gains(self, user_id: int, start_date: str, end_date: str) -> Dict:
        """Get capital gains data"""
        # Mock capital gains calculation
        return {
            'short_term_gains': 0,
            'long_term_gains': 0,
            'stcg_tax': 0,
            'ltcg_tax': 0,
            'total_cg_tax': 0
        }

class CashflowReportGenerator:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def generate_cashflow_statement(self, user_id: int, period: str, year: int, month: int = None) -> Dict:
        """Generate cashflow statement"""
        try:
            if period == 'monthly':
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{year + 1}-01-01"
                else:
                    end_date = f"{year}-{month + 1:02d}-01"
            elif period == 'quarterly':
                quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
                start_month, end_month = quarter_months[month]  # month represents quarter
                start_date = f"{year}-{start_month:02d}-01"
                if end_month == 12:
                    end_date = f"{year + 1}-01-01"
                else:
                    end_date = f"{year}-{end_month + 1:02d}-01"
            else:  # yearly
                start_date = f"{year}-01-01"
                end_date = f"{year + 1}-01-01"
            
            # Get operating cashflows
            operating_cf = self._get_operating_cashflow(user_id, start_date, end_date)
            
            # Get investing cashflows
            investing_cf = self._get_investing_cashflow(user_id, start_date, end_date)
            
            # Get financing cashflows
            financing_cf = self._get_financing_cashflow(user_id, start_date, end_date)
            
            # Calculate net cashflow
            net_cashflow = operating_cf['net'] + investing_cf['net'] + financing_cf['net']
            
            return {
                'period': period,
                'year': year,
                'month': month,
                'start_date': start_date,
                'end_date': end_date,
                'operating_activities': operating_cf,
                'investing_activities': investing_cf,
                'financing_activities': financing_cf,
                'net_cashflow': net_cashflow,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_operating_cashflow(self, user_id: int, start_date: str, end_date: str) -> Dict:
        """Get operating cashflow items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Income (cash inflows)
        cursor.execute('''
            SELECT SUM(amount) FROM income 
            WHERE user_id = ? AND date BETWEEN ? AND ?
        ''', (user_id, start_date, end_date))
        
        total_income = cursor.fetchone()[0] or 0
        
        # Operating expenses (cash outflows)
        cursor.execute('''
            SELECT category, SUM(amount) FROM expenses 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            AND category NOT IN ('investment', 'loan_payment')
            GROUP BY category
        ''', (user_id, start_date, end_date))
        
        expense_categories = cursor.fetchall()
        conn.close()
        
        total_expenses = sum(amount for _, amount in expense_categories)
        
        return {
            'cash_inflows': {
                'income': total_income,
                'total': total_income
            },
            'cash_outflows': {
                'expenses': [{'category': cat, 'amount': amt} for cat, amt in expense_categories],
                'total': total_expenses
            },
            'net': total_income - total_expenses
        }
    
    def _get_investing_cashflow(self, user_id: int, start_date: str, end_date: str) -> Dict:
        """Get investing cashflow items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Investment expenses
        cursor.execute('''
            SELECT SUM(amount) FROM expenses 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            AND category = 'investment'
        ''', (user_id, start_date, end_date))
        
        investments = cursor.fetchone()[0] or 0
        
        # Investment income (dividends, interest)
        cursor.execute('''
            SELECT SUM(amount) FROM income 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            AND source LIKE '%dividend%' OR source LIKE '%interest%'
        ''', (user_id, start_date, end_date))
        
        investment_income = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'cash_inflows': {
                'investment_income': investment_income,
                'total': investment_income
            },
            'cash_outflows': {
                'investments': investments,
                'total': investments
            },
            'net': investment_income - investments
        }
    
    def _get_financing_cashflow(self, user_id: int, start_date: str, end_date: str) -> Dict:
        """Get financing cashflow items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Loan payments
        cursor.execute('''
            SELECT SUM(amount) FROM expenses 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            AND category = 'loan_payment'
        ''', (user_id, start_date, end_date))
        
        loan_payments = cursor.fetchone()[0] or 0
        
        # New loans (if any)
        cursor.execute('''
            SELECT SUM(amount) FROM income 
            WHERE user_id = ? AND date BETWEEN ? AND ?
            AND source LIKE '%loan%'
        ''', (user_id, start_date, end_date))
        
        new_loans = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'cash_inflows': {
                'new_loans': new_loans,
                'total': new_loans
            },
            'cash_outflows': {
                'loan_payments': loan_payments,
                'total': loan_payments
            },
            'net': new_loans - loan_payments
        }

class NetWorthTracker:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                asset_name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                current_value REAL NOT NULL,
                purchase_value REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS liabilities (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                liability_name TEXT NOT NULL,
                liability_type TEXT NOT NULL,
                current_balance REAL NOT NULL,
                original_amount REAL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS net_worth_history (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                total_assets REAL NOT NULL,
                total_liabilities REAL NOT NULL,
                net_worth REAL NOT NULL,
                recorded_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_net_worth(self, user_id: int) -> Dict:
        """Calculate current net worth"""
        try:
            assets = self._get_assets(user_id)
            liabilities = self._get_liabilities(user_id)
            
            total_assets = sum(asset['current_value'] for asset in assets)
            total_liabilities = sum(liability['current_balance'] for liability in liabilities)
            net_worth = total_assets - total_liabilities
            
            # Record in history
            self._record_net_worth_history(user_id, total_assets, total_liabilities, net_worth)
            
            return {
                'assets': {
                    'items': assets,
                    'total': total_assets
                },
                'liabilities': {
                    'items': liabilities,
                    'total': total_liabilities
                },
                'net_worth': net_worth,
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_assets(self, user_id: int) -> List[Dict]:
        """Get user assets"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get saved assets
        cursor.execute('''
            SELECT asset_name, asset_type, current_value, purchase_value
            FROM assets WHERE user_id = ?
        ''', (user_id,))
        
        saved_assets = cursor.fetchall()
        
        # Get bank account balances
        cursor.execute('''
            SELECT bank_name, balance FROM bank_accounts 
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        bank_accounts = cursor.fetchall()
        
        # Get investment values
        cursor.execute('''
            SELECT scheme_name, current_value FROM mf_holdings 
            WHERE user_id = ?
        ''', (user_id,))
        
        investments = cursor.fetchall()
        
        conn.close()
        
        assets = []
        
        # Add saved assets
        for asset in saved_assets:
            assets.append({
                'name': asset[0],
                'type': asset[1],
                'current_value': asset[2],
                'purchase_value': asset[3] or 0
            })
        
        # Add bank accounts
        for account in bank_accounts:
            assets.append({
                'name': f"{account[0]} Account",
                'type': 'cash',
                'current_value': account[1],
                'purchase_value': account[1]
            })
        
        # Add investments
        for investment in investments:
            assets.append({
                'name': investment[0],
                'type': 'investment',
                'current_value': investment[1],
                'purchase_value': 0  # Would need invested amount
            })
        
        return assets
    
    def _get_liabilities(self, user_id: int) -> List[Dict]:
        """Get user liabilities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get saved liabilities
        cursor.execute('''
            SELECT liability_name, liability_type, current_balance, original_amount
            FROM liabilities WHERE user_id = ?
        ''', (user_id,))
        
        saved_liabilities = cursor.fetchall()
        
        # Get debts
        cursor.execute('''
            SELECT name, current_balance, principal_amount FROM debts 
            WHERE user_id = ?
        ''', (user_id,))
        
        debts = cursor.fetchall()
        
        conn.close()
        
        liabilities = []
        
        # Add saved liabilities
        for liability in saved_liabilities:
            liabilities.append({
                'name': liability[0],
                'type': liability[1],
                'current_balance': liability[2],
                'original_amount': liability[3] or 0
            })
        
        # Add debts
        for debt in debts:
            liabilities.append({
                'name': debt[0],
                'type': 'debt',
                'current_balance': debt[1],
                'original_amount': debt[2]
            })
        
        return liabilities
    
    def _record_net_worth_history(self, user_id: int, assets: float, liabilities: float, net_worth: float):
        """Record net worth in history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO net_worth_history (user_id, total_assets, total_liabilities, net_worth)
            VALUES (?, ?, ?, ?)
        ''', (user_id, assets, liabilities, net_worth))
        
        conn.commit()
        conn.close()
    
    def get_net_worth_trend(self, user_id: int, months: int = 12) -> Dict:
        """Get net worth trend over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=months * 30)).isoformat()
        
        cursor.execute('''
            SELECT total_assets, total_liabilities, net_worth, recorded_date
            FROM net_worth_history 
            WHERE user_id = ? AND recorded_date >= ?
            ORDER BY recorded_date
        ''', (user_id, since_date))
        
        history = cursor.fetchall()
        conn.close()
        
        if not history:
            return {'trend': [], 'growth': 0}
        
        trend_data = [{
            'assets': h[0],
            'liabilities': h[1],
            'net_worth': h[2],
            'date': h[3][:10]
        } for h in history]
        
        # Calculate growth
        if len(history) > 1:
            initial_nw = history[0][2]
            current_nw = history[-1][2]
            growth = ((current_nw - initial_nw) / initial_nw * 100) if initial_nw != 0 else 0
        else:
            growth = 0
        
        return {
            'trend': trend_data,
            'growth_percentage': growth,
            'period_months': months
        }

class ExpenseRatioAnalyzer:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.benchmarks = {
            'housing': {'ideal': 30, 'max': 40},
            'food': {'ideal': 15, 'max': 20},
            'transportation': {'ideal': 15, 'max': 20},
            'utilities': {'ideal': 8, 'max': 12},
            'entertainment': {'ideal': 5, 'max': 10},
            'healthcare': {'ideal': 5, 'max': 8},
            'savings': {'ideal': 20, 'min': 10}
        }
    
    def analyze_expense_ratios(self, user_id: int, period_months: int = 12) -> Dict:
        """Analyze expense ratios against benchmarks"""
        try:
            since_date = (datetime.now() - timedelta(days=period_months * 30)).isoformat()
            
            # Get income and expenses
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT SUM(amount) FROM income 
                WHERE user_id = ? AND date >= ?
            ''', (user_id, since_date))
            
            total_income = cursor.fetchone()[0] or 0
            
            cursor.execute('''
                SELECT category, SUM(amount) FROM expenses 
                WHERE user_id = ? AND date >= ?
                GROUP BY category
            ''', (user_id, since_date))
            
            expense_categories = cursor.fetchall()
            conn.close()
            
            if total_income == 0:
                return {'error': 'No income data available'}
            
            # Calculate ratios
            expense_ratios = {}
            total_expenses = 0
            
            for category, amount in expense_categories:
                ratio = (amount / total_income) * 100
                expense_ratios[category] = {
                    'amount': amount,
                    'percentage': ratio,
                    'benchmark': self.benchmarks.get(category, {'ideal': 10, 'max': 15}),
                    'status': self._get_ratio_status(category, ratio)
                }
                total_expenses += amount
            
            # Calculate savings ratio
            savings_amount = total_income - total_expenses
            savings_ratio = (savings_amount / total_income) * 100
            
            expense_ratios['savings'] = {
                'amount': savings_amount,
                'percentage': savings_ratio,
                'benchmark': self.benchmarks['savings'],
                'status': self._get_ratio_status('savings', savings_ratio)
            }
            
            # Overall analysis
            analysis = self._generate_analysis(expense_ratios, total_income)
            
            return {
                'period_months': period_months,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'expense_ratios': expense_ratios,
                'analysis': analysis,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_ratio_status(self, category: str, ratio: float) -> str:
        """Get status of expense ratio"""
        if category not in self.benchmarks:
            return 'unknown'
        
        benchmark = self.benchmarks[category]
        
        if category == 'savings':
            if ratio >= benchmark['ideal']:
                return 'excellent'
            elif ratio >= benchmark['min']:
                return 'good'
            else:
                return 'poor'
        else:
            if ratio <= benchmark['ideal']:
                return 'excellent'
            elif ratio <= benchmark['max']:
                return 'good'
            else:
                return 'high'
    
    def _generate_analysis(self, ratios: Dict, total_income: float) -> Dict:
        """Generate expense ratio analysis"""
        recommendations = []
        strengths = []
        concerns = []
        
        for category, data in ratios.items():
            status = data['status']
            percentage = data['percentage']
            
            if status == 'excellent':
                strengths.append(f"{category.title()}: {percentage:.1f}% (Excellent)")
            elif status == 'high' or status == 'poor':
                if category == 'savings':
                    concerns.append(f"Low savings rate: {percentage:.1f}%")
                    recommendations.append(f"Increase savings to at least 10% of income")
                else:
                    concerns.append(f"High {category} spending: {percentage:.1f}%")
                    recommendations.append(f"Reduce {category} expenses to under {data['benchmark']['max']}%")
        
        return {
            'strengths': strengths,
            'concerns': concerns,
            'recommendations': recommendations,
            'overall_score': self._calculate_overall_score(ratios)
        }
    
    def _calculate_overall_score(self, ratios: Dict) -> int:
        """Calculate overall financial health score"""
        score = 0
        total_categories = len(ratios)
        
        for category, data in ratios.items():
            status = data['status']
            if status == 'excellent':
                score += 100
            elif status == 'good':
                score += 75
            elif status == 'high' or status == 'poor':
                score += 25
        
        return int(score / total_categories) if total_categories > 0 else 0

class AdvancedReportsManager:
    def __init__(self, db_path: str):
        self.tax_reports = TaxReportGenerator(db_path)
        self.cashflow_reports = CashflowReportGenerator(db_path)
        self.net_worth_tracker = NetWorthTracker(db_path)
        self.expense_analyzer = ExpenseRatioAnalyzer(db_path)
        self.db_path = db_path
    
    def generate_comprehensive_report(self, user_id: int, report_type: str = 'annual') -> Dict:
        """Generate comprehensive financial report"""
        current_year = datetime.now().year
        
        report_data = {
            'report_type': report_type,
            'generated_for': f"User {user_id}",
            'generated_at': datetime.now().isoformat(),
            'year': current_year
        }
        
        try:
            # Tax summary
            tax_summary = self.tax_reports.generate_itr_summary(
                user_id, f"{current_year-1}-{current_year}"
            )
            report_data['tax_summary'] = tax_summary
            
            # Cashflow statement
            if report_type == 'monthly':
                cashflow = self.cashflow_reports.generate_cashflow_statement(
                    user_id, 'monthly', current_year, datetime.now().month
                )
            elif report_type == 'quarterly':
                quarter = (datetime.now().month - 1) // 3 + 1
                cashflow = self.cashflow_reports.generate_cashflow_statement(
                    user_id, 'quarterly', current_year, quarter
                )
            else:
                cashflow = self.cashflow_reports.generate_cashflow_statement(
                    user_id, 'yearly', current_year
                )
            report_data['cashflow_statement'] = cashflow
            
            # Net worth analysis
            net_worth = self.net_worth_tracker.calculate_net_worth(user_id)
            net_worth_trend = self.net_worth_tracker.get_net_worth_trend(user_id, 12)
            report_data['net_worth'] = {
                'current': net_worth,
                'trend': net_worth_trend
            }
            
            # Expense ratio analysis
            expense_analysis = self.expense_analyzer.analyze_expense_ratios(user_id, 12)
            report_data['expense_analysis'] = expense_analysis
            
            return report_data
            
        except Exception as e:
            report_data['error'] = str(e)
            return report_data
    
    def export_report_pdf(self, report_data: Dict) -> str:
        """Export report as PDF and return base64 string"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center
            )
            
            story.append(Paragraph("Financial Report", title_style))
            story.append(Spacer(1, 20))
            
            # Report info
            info_data = [
                ['Report Type:', report_data.get('report_type', 'N/A')],
                ['Generated At:', report_data.get('generated_at', 'N/A')[:19]],
                ['Year:', str(report_data.get('year', 'N/A'))]
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 3*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 20))
            
            # Net Worth Summary
            if 'net_worth' in report_data and 'current' in report_data['net_worth']:
                nw_data = report_data['net_worth']['current']
                if 'error' not in nw_data:
                    story.append(Paragraph("Net Worth Summary", styles['Heading2']))
                    
                    nw_summary = [
                        ['Total Assets:', f"₹{nw_data['assets']['total']:,.0f}"],
                        ['Total Liabilities:', f"₹{nw_data['liabilities']['total']:,.0f}"],
                        ['Net Worth:', f"₹{nw_data['net_worth']:,.0f}"]
                    ]
                    
                    nw_table = Table(nw_summary, colWidths=[2*inch, 2*inch])
                    nw_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, -1), colors.beige),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                    ]))
                    
                    story.append(nw_table)
                    story.append(Spacer(1, 20))
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            pdf_data = buffer.getvalue()
            buffer.close()
            
            # Return base64 encoded PDF
            return base64.b64encode(pdf_data).decode('utf-8')
            
        except Exception as e:
            return f"Error generating PDF: {str(e)}"