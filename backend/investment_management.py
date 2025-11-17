import requests
import sqlite3
from datetime import datetime, timedelta
import json
import pandas as pd
from typing import Dict, List, Tuple
import yfinance as yf
from dataclasses import dataclass
import logging

@dataclass
class Investment:
    symbol: str
    name: str
    quantity: float
    avg_price: float
    current_price: float
    investment_type: str  # 'stock', 'mutual_fund', 'etf'
    purchase_date: str
    
    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def invested_amount(self) -> float:
        return self.quantity * self.avg_price
    
    @property
    def pnl(self) -> float:
        return self.current_value - self.invested_amount
    
    @property
    def pnl_percentage(self) -> float:
        return (self.pnl / self.invested_amount) * 100 if self.invested_amount > 0 else 0

class PortfolioTracker:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investments (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity REAL NOT NULL,
                avg_price REAL NOT NULL,
                investment_type TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                user_id INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_real_time_price(self, symbol: str) -> float:
        """Get real-time price using yfinance"""
        try:
            # For Indian stocks, append .NS (NSE) or .BO (BSE)
            if not ('.' in symbol):
                symbol += '.NS'
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                price = float(data['Close'].iloc[-1])
                self.update_price_history(symbol, price)
                return price
        except Exception as e:
            logging.error(f"Error fetching price for {symbol}: {e}")
        
        return 0.0
    
    def update_price_history(self, symbol: str, price: float):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO price_history (symbol, price, timestamp)
            VALUES (?, ?, ?)
        ''', (symbol, price, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def add_investment(self, symbol: str, name: str, quantity: float, 
                      avg_price: float, investment_type: str, purchase_date: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO investments (symbol, name, quantity, avg_price, investment_type, purchase_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (symbol, name, quantity, avg_price, investment_type, purchase_date))
        conn.commit()
        conn.close()
    
    def get_portfolio(self) -> List[Investment]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM investments')
        rows = cursor.fetchall()
        conn.close()
        
        portfolio = []
        for row in rows:
            current_price = self.get_real_time_price(row[1])
            investment = Investment(
                symbol=row[1], name=row[2], quantity=row[3],
                avg_price=row[4], current_price=current_price,
                investment_type=row[5], purchase_date=row[6]
            )
            portfolio.append(investment)
        
        return portfolio
    
    def get_portfolio_summary(self) -> Dict:
        portfolio = self.get_portfolio()
        
        total_invested = sum(inv.invested_amount for inv in portfolio)
        total_current = sum(inv.current_value for inv in portfolio)
        total_pnl = total_current - total_invested
        
        return {
            'total_invested': total_invested,
            'total_current_value': total_current,
            'total_pnl': total_pnl,
            'total_pnl_percentage': (total_pnl / total_invested) * 100 if total_invested > 0 else 0,
            'investments_count': len(portfolio)
        }

class AssetAllocator:
    def __init__(self, portfolio_tracker: PortfolioTracker):
        self.portfolio_tracker = portfolio_tracker
    
    def get_current_allocation(self) -> Dict[str, float]:
        portfolio = self.portfolio_tracker.get_portfolio()
        total_value = sum(inv.current_value for inv in portfolio)
        
        allocation = {}
        for inv in portfolio:
            if inv.investment_type not in allocation:
                allocation[inv.investment_type] = 0
            allocation[inv.investment_type] += inv.current_value
        
        # Convert to percentages
        for asset_type in allocation:
            allocation[asset_type] = (allocation[asset_type] / total_value) * 100 if total_value > 0 else 0
        
        return allocation
    
    def get_target_allocation(self, age: int, risk_tolerance: str) -> Dict[str, float]:
        """Get target allocation based on age and risk tolerance"""
        equity_percentage = 100 - age  # Basic rule: 100 - age for equity
        
        if risk_tolerance == 'conservative':
            equity_percentage = max(20, equity_percentage - 20)
        elif risk_tolerance == 'aggressive':
            equity_percentage = min(90, equity_percentage + 20)
        
        return {
            'stock': equity_percentage * 0.7,  # 70% of equity in stocks
            'mutual_fund': equity_percentage * 0.3,  # 30% of equity in MF
            'etf': 100 - equity_percentage  # Rest in ETFs/bonds
        }
    
    def get_rebalancing_suggestions(self, age: int, risk_tolerance: str) -> List[Dict]:
        current = self.get_current_allocation()
        target = self.get_target_allocation(age, risk_tolerance)
        
        suggestions = []
        for asset_type, target_pct in target.items():
            current_pct = current.get(asset_type, 0)
            difference = target_pct - current_pct
            
            if abs(difference) > 5:  # Only suggest if difference > 5%
                action = 'increase' if difference > 0 else 'decrease'
                suggestions.append({
                    'asset_type': asset_type,
                    'current_percentage': current_pct,
                    'target_percentage': target_pct,
                    'action': action,
                    'difference': abs(difference)
                })
        
        return sorted(suggestions, key=lambda x: x['difference'], reverse=True)

class SIPManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sips (
                id INTEGER PRIMARY KEY,
                fund_name TEXT NOT NULL,
                amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT DEFAULT 'active',
                user_id INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sip_transactions (
                id INTEGER PRIMARY KEY,
                sip_id INTEGER,
                amount REAL NOT NULL,
                nav REAL NOT NULL,
                units REAL NOT NULL,
                transaction_date TEXT NOT NULL,
                FOREIGN KEY (sip_id) REFERENCES sips (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_sip(self, fund_name: str, amount: float, frequency: str, 
                start_date: str, end_date: str = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sips (fund_name, amount, frequency, start_date, end_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (fund_name, amount, frequency, start_date, end_date))
        conn.commit()
        conn.close()
    
    def get_active_sips(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sips WHERE status = "active"')
        rows = cursor.fetchall()
        conn.close()
        
        sips = []
        for row in rows:
            sip = {
                'id': row[0], 'fund_name': row[1], 'amount': row[2],
                'frequency': row[3], 'start_date': row[4], 'end_date': row[5],
                'status': row[6]
            }
            sips.append(sip)
        
        return sips
    
    def calculate_sip_returns(self, sip_id: int) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sip_transactions WHERE sip_id = ?', (sip_id,))
        transactions = cursor.fetchall()
        
        cursor.execute('SELECT * FROM sips WHERE id = ?', (sip_id,))
        sip_info = cursor.fetchone()
        
        conn.close()
        
        if not transactions or not sip_info:
            return {}
        
        total_invested = sum(t[2] for t in transactions)  # amount
        total_units = sum(t[4] for t in transactions)     # units
        
        # Get current NAV (simplified - would need real API)
        current_nav = 50.0  # Placeholder
        current_value = total_units * current_nav
        
        returns = current_value - total_invested
        returns_pct = (returns / total_invested) * 100 if total_invested > 0 else 0
        
        return {
            'sip_id': sip_id,
            'fund_name': sip_info[1],
            'total_invested': total_invested,
            'current_value': current_value,
            'returns': returns,
            'returns_percentage': returns_pct,
            'total_units': total_units
        }
    
    def optimize_sip_amount(self, current_amount: float, target_corpus: float, 
                           years: int, expected_return: float = 12.0) -> Dict:
        """Calculate optimal SIP amount for target corpus"""
        monthly_rate = expected_return / (12 * 100)
        months = years * 12
        
        # Future Value of Annuity formula
        fv_factor = ((1 + monthly_rate) ** months - 1) / monthly_rate
        required_sip = target_corpus / fv_factor
        
        return {
            'current_sip': current_amount,
            'required_sip': required_sip,
            'difference': required_sip - current_amount,
            'target_corpus': target_corpus,
            'projected_corpus': current_amount * fv_factor,
            'shortfall': max(0, target_corpus - (current_amount * fv_factor))
        }

class TaxLossHarvester:
    def __init__(self, portfolio_tracker: PortfolioTracker):
        self.portfolio_tracker = portfolio_tracker
    
    def identify_loss_opportunities(self, min_loss_percentage: float = 10.0) -> List[Dict]:
        portfolio = self.portfolio_tracker.get_portfolio()
        
        opportunities = []
        for inv in portfolio:
            if inv.pnl_percentage < -min_loss_percentage:
                # Calculate holding period
                purchase_date = datetime.fromisoformat(inv.purchase_date)
                holding_days = (datetime.now() - purchase_date).days
                
                tax_category = 'LTCG' if holding_days > 365 else 'STCG'
                
                opportunities.append({
                    'symbol': inv.symbol,
                    'name': inv.name,
                    'quantity': inv.quantity,
                    'current_loss': inv.pnl,
                    'loss_percentage': inv.pnl_percentage,
                    'holding_days': holding_days,
                    'tax_category': tax_category,
                    'potential_tax_benefit': abs(inv.pnl) * (0.15 if tax_category == 'STCG' else 0.10)
                })
        
        return sorted(opportunities, key=lambda x: x['potential_tax_benefit'], reverse=True)
    
    def calculate_capital_gains(self, year: int = None) -> Dict:
        if year is None:
            year = datetime.now().year
        
        portfolio = self.portfolio_tracker.get_portfolio()
        
        stcg = 0  # Short-term capital gains
        ltcg = 0  # Long-term capital gains
        
        for inv in portfolio:
            if inv.pnl > 0:  # Only gains
                purchase_date = datetime.fromisoformat(inv.purchase_date)
                if purchase_date.year == year:
                    holding_days = (datetime.now() - purchase_date).days
                    
                    if holding_days <= 365:
                        stcg += inv.pnl
                    else:
                        ltcg += inv.pnl
        
        # Tax calculations (Indian rates)
        stcg_tax = stcg * 0.15  # 15% for equity STCG
        ltcg_tax = max(0, (ltcg - 100000) * 0.10)  # 10% above 1L for equity LTCG
        
        return {
            'year': year,
            'stcg': stcg,
            'ltcg': ltcg,
            'stcg_tax': stcg_tax,
            'ltcg_tax': ltcg_tax,
            'total_tax': stcg_tax + ltcg_tax,
            'ltcg_exemption_used': min(ltcg, 100000)
        }

class InvestmentManager:
    def __init__(self, db_path: str):
        self.portfolio_tracker = PortfolioTracker(db_path)
        self.asset_allocator = AssetAllocator(self.portfolio_tracker)
        self.sip_manager = SIPManager(db_path)
        self.tax_harvester = TaxLossHarvester(self.portfolio_tracker)
    
    def get_investment_dashboard(self, age: int, risk_tolerance: str) -> Dict:
        portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
        current_allocation = self.asset_allocator.get_current_allocation()
        rebalancing_suggestions = self.asset_allocator.get_rebalancing_suggestions(age, risk_tolerance)
        active_sips = self.sip_manager.get_active_sips()
        tax_opportunities = self.tax_harvester.identify_loss_opportunities()
        capital_gains = self.tax_harvester.calculate_capital_gains()
        
        return {
            'portfolio_summary': portfolio_summary,
            'asset_allocation': {
                'current': current_allocation,
                'target': self.asset_allocator.get_target_allocation(age, risk_tolerance),
                'rebalancing_suggestions': rebalancing_suggestions
            },
            'sip_summary': {
                'active_sips_count': len(active_sips),
                'total_monthly_sip': sum(sip['amount'] for sip in active_sips),
                'active_sips': active_sips
            },
            'tax_planning': {
                'loss_opportunities': tax_opportunities[:5],  # Top 5
                'capital_gains': capital_gains,
                'potential_tax_savings': sum(opp['potential_tax_benefit'] for opp in tax_opportunities)
            }
        }