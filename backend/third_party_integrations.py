import sqlite3
import requests
import json
import re
import email
import imaplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import uuid
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

@dataclass
class MutualFundHolding:
    scheme_name: str
    folio_number: str
    units: float
    nav: float
    current_value: float
    invested_amount: float
    pnl: float
    pnl_percentage: float

@dataclass
class ExpenseRecord:
    amount: float
    category: str
    description: str
    date: str
    source_app: str
    transaction_id: str

class MutualFundIntegration:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
        self.platforms = {
            'groww': {
                'name': 'Groww',
                'api_url': 'https://api.groww.in',
                'auth_type': 'oauth'
            },
            'zerodha_coin': {
                'name': 'Zerodha Coin',
                'api_url': 'https://api.kite.trade',
                'auth_type': 'oauth'
            },
            'paytm_money': {
                'name': 'Paytm Money',
                'api_url': 'https://api.paytmmoney.com',
                'auth_type': 'oauth'
            }
        }
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mf_platforms (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform_name TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                last_sync TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mf_holdings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform_name TEXT NOT NULL,
                scheme_name TEXT NOT NULL,
                folio_number TEXT NOT NULL,
                units REAL NOT NULL,
                nav REAL NOT NULL,
                current_value REAL NOT NULL,
                invested_amount REAL NOT NULL,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mf_transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                platform_name TEXT NOT NULL,
                scheme_name TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                units REAL,
                nav REAL,
                transaction_date TEXT NOT NULL,
                order_id TEXT,
                status TEXT DEFAULT 'completed'
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def connect_platform(self, user_id: int, platform_name: str, credentials: Dict) -> Dict:
        """Connect to mutual fund platform"""
        try:
            # Mock OAuth connection
            access_token = f"{platform_name}_token_{uuid.uuid4().hex[:16]}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO mf_platforms 
                (user_id, platform_name, access_token, last_sync)
                VALUES (?, ?, ?, ?)
            ''', (user_id, platform_name, access_token, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'platform': platform_name,
                'message': f'{self.platforms[platform_name]["name"]} connected successfully'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def sync_holdings(self, user_id: int, platform_name: str) -> Dict:
        """Sync mutual fund holdings from platform"""
        try:
            # Mock API response
            mock_holdings = self._generate_mock_holdings(platform_name)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing holdings for this platform
            cursor.execute('''
                DELETE FROM mf_holdings 
                WHERE user_id = ? AND platform_name = ?
            ''', (user_id, platform_name))
            
            # Insert new holdings
            for holding in mock_holdings:
                cursor.execute('''
                    INSERT INTO mf_holdings 
                    (user_id, platform_name, scheme_name, folio_number, units, nav, current_value, invested_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, platform_name, holding['scheme_name'], holding['folio_number'],
                    holding['units'], holding['nav'], holding['current_value'], holding['invested_amount']
                ))
            
            # Update last sync
            cursor.execute('''
                UPDATE mf_platforms 
                SET last_sync = ? 
                WHERE user_id = ? AND platform_name = ?
            ''', (datetime.now().isoformat(), user_id, platform_name))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'holdings_synced': len(mock_holdings),
                'platform': platform_name
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_mock_holdings(self, platform_name: str) -> List[Dict]:
        """Generate mock mutual fund holdings"""
        schemes = [
            {'name': 'HDFC Equity Fund', 'nav': 45.67, 'units': 1000, 'invested': 40000},
            {'name': 'SBI Bluechip Fund', 'nav': 78.90, 'units': 500, 'invested': 35000},
            {'name': 'ICICI Prudential Balanced Fund', 'nav': 123.45, 'units': 300, 'invested': 30000}
        ]
        
        holdings = []
        for i, scheme in enumerate(schemes):
            current_value = scheme['units'] * scheme['nav']
            holdings.append({
                'scheme_name': scheme['name'],
                'folio_number': f"{platform_name.upper()}{12345 + i}",
                'units': scheme['units'],
                'nav': scheme['nav'],
                'current_value': current_value,
                'invested_amount': scheme['invested']
            })
        
        return holdings
    
    def get_consolidated_portfolio(self, user_id: int) -> Dict:
        """Get consolidated mutual fund portfolio"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT platform_name, scheme_name, folio_number, units, nav, current_value, invested_amount
            FROM mf_holdings 
            WHERE user_id = ?
        ''', (user_id,))
        
        holdings = cursor.fetchall()
        conn.close()
        
        portfolio = []
        total_invested = 0
        total_current = 0
        
        for holding in holdings:
            pnl = holding[5] - holding[6]  # current_value - invested_amount
            pnl_pct = (pnl / holding[6] * 100) if holding[6] > 0 else 0
            
            portfolio.append({
                'platform': holding[0],
                'scheme_name': holding[1],
                'folio_number': holding[2],
                'units': holding[3],
                'nav': holding[4],
                'current_value': holding[5],
                'invested_amount': holding[6],
                'pnl': pnl,
                'pnl_percentage': pnl_pct
            })
            
            total_invested += holding[6]
            total_current += holding[5]
        
        return {
            'holdings': portfolio,
            'summary': {
                'total_schemes': len(portfolio),
                'total_invested': total_invested,
                'total_current_value': total_current,
                'total_pnl': total_current - total_invested,
                'total_pnl_percentage': ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
            }
        }

class ExpenseAppIntegration:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
        self.supported_apps = {
            'splitwise': {'name': 'Splitwise', 'api_url': 'https://secure.splitwise.com/api/v3.0'},
            'walnut': {'name': 'Walnut', 'api_url': 'https://api.getwalnut.com'},
            'money_lover': {'name': 'Money Lover', 'api_url': 'https://api.moneylover.me'},
            'expense_manager': {'name': 'Expense Manager', 'api_url': 'https://api.expensemanager.com'}
        }
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expense_app_connections (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                app_name TEXT NOT NULL,
                access_token TEXT,
                last_sync TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS imported_expenses (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                source_app TEXT NOT NULL,
                original_id TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                expense_date TEXT NOT NULL,
                imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_app, original_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def connect_app(self, user_id: int, app_name: str, credentials: Dict) -> Dict:
        """Connect expense tracking app"""
        try:
            access_token = f"{app_name}_token_{uuid.uuid4().hex[:16]}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO expense_app_connections 
                (user_id, app_name, access_token, last_sync)
                VALUES (?, ?, ?, ?)
            ''', (user_id, app_name, access_token, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'app': app_name,
                'message': f'{self.supported_apps[app_name]["name"]} connected successfully'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def import_expenses(self, user_id: int, app_name: str, date_range: int = 30) -> Dict:
        """Import expenses from connected app"""
        try:
            # Mock API call to fetch expenses
            mock_expenses = self._generate_mock_expenses(app_name, date_range)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            imported_count = 0
            for expense in mock_expenses:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO imported_expenses 
                        (user_id, source_app, original_id, amount, category, description, expense_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, app_name, expense['id'], expense['amount'],
                        expense['category'], expense['description'], expense['date']
                    ))
                    
                    if cursor.rowcount > 0:
                        imported_count += 1
                        
                except sqlite3.IntegrityError:
                    continue
            
            # Update last sync
            cursor.execute('''
                UPDATE expense_app_connections 
                SET last_sync = ? 
                WHERE user_id = ? AND app_name = ?
            ''', (datetime.now().isoformat(), user_id, app_name))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'imported_count': imported_count,
                'app': app_name,
                'date_range': date_range
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_mock_expenses(self, app_name: str, days: int) -> List[Dict]:
        """Generate mock expenses from app"""
        categories = ['food', 'transportation', 'shopping', 'entertainment', 'utilities']
        expenses = []
        
        for i in range(10):  # Generate 10 mock expenses
            expense_date = datetime.now() - timedelta(days=i)
            expenses.append({
                'id': f"{app_name}_{uuid.uuid4().hex[:8]}",
                'amount': round(100 + (i * 50), 2),
                'category': categories[i % len(categories)],
                'description': f"Expense from {self.supported_apps[app_name]['name']} #{i+1}",
                'date': expense_date.isoformat()
            })
        
        return expenses
    
    def get_imported_summary(self, user_id: int) -> Dict:
        """Get summary of imported expenses"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT source_app, COUNT(*), SUM(amount), MAX(imported_at)
            FROM imported_expenses 
            WHERE user_id = ?
            GROUP BY source_app
        ''', (user_id,))
        
        summary = cursor.fetchall()
        
        cursor.execute('''
            SELECT category, SUM(amount), COUNT(*)
            FROM imported_expenses 
            WHERE user_id = ?
            GROUP BY category
            ORDER BY SUM(amount) DESC
        ''', (user_id,))
        
        categories = cursor.fetchall()
        conn.close()
        
        return {
            'apps': [{
                'app_name': s[0],
                'expense_count': s[1],
                'total_amount': s[2],
                'last_import': s[3]
            } for s in summary],
            'categories': [{
                'category': c[0],
                'total_amount': c[1],
                'expense_count': c[2]
            } for c in categories],
            'total_imported': sum(s[1] for s in summary),
            'total_amount': sum(s[2] for s in summary)
        }

class CalendarSync:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_reminders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                bill_name TEXT NOT NULL,
                due_date TEXT NOT NULL,
                amount REAL,
                category TEXT,
                reminder_days INTEGER DEFAULT 3,
                calendar_event_id TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_sync_settings (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                calendar_provider TEXT NOT NULL,
                access_token TEXT,
                calendar_id TEXT,
                sync_enabled BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_calendar_sync(self, user_id: int, provider: str, credentials: Dict) -> Dict:
        """Setup calendar synchronization"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO calendar_sync_settings 
                (user_id, calendar_provider, access_token, calendar_id)
                VALUES (?, ?, ?, ?)
            ''', (
                user_id, provider, credentials.get('access_token'),
                credentials.get('calendar_id', 'primary')
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'provider': provider,
                'message': f'{provider} calendar sync enabled'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def add_bill_reminder(self, user_id: int, bill_data: Dict) -> Dict:
        """Add bill due date reminder"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create calendar event (mock)
            event_id = f"bill_reminder_{uuid.uuid4().hex[:12]}"
            
            cursor.execute('''
                INSERT INTO calendar_reminders 
                (user_id, bill_name, due_date, amount, category, reminder_days, calendar_event_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, bill_data['bill_name'], bill_data['due_date'],
                bill_data.get('amount'), bill_data.get('category'),
                bill_data.get('reminder_days', 3), event_id
            ))
            
            reminder_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'reminder_id': reminder_id,
                'event_id': event_id,
                'message': f'Reminder set for {bill_data["bill_name"]}'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_upcoming_reminders(self, user_id: int, days_ahead: int = 7) -> List[Dict]:
        """Get upcoming bill reminders"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        future_date = (datetime.now() + timedelta(days=days_ahead)).isoformat()
        
        cursor.execute('''
            SELECT bill_name, due_date, amount, category, reminder_days
            FROM calendar_reminders 
            WHERE user_id = ? AND due_date <= ? AND status = 'active'
            ORDER BY due_date
        ''', (user_id, future_date))
        
        reminders = cursor.fetchall()
        conn.close()
        
        return [{
            'bill_name': r[0],
            'due_date': r[1],
            'amount': r[2],
            'category': r[3],
            'days_until_due': (datetime.fromisoformat(r[1]) - datetime.now()).days
        } for r in reminders]
    
    def sync_with_calendar(self, user_id: int) -> Dict:
        """Sync reminders with external calendar"""
        try:
            # Mock calendar API sync
            reminders = self.get_upcoming_reminders(user_id, 30)
            
            synced_events = []
            for reminder in reminders:
                # Mock creating/updating calendar event
                synced_events.append({
                    'bill_name': reminder['bill_name'],
                    'due_date': reminder['due_date'],
                    'status': 'synced'
                })
            
            return {
                'success': True,
                'synced_events': len(synced_events),
                'events': synced_events
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class EmailParser:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
        self.bank_patterns = {
            'hdfc': {
                'sender': 'alerts@hdfcbank.net',
                'amount_pattern': r'Rs\.?\s*([0-9,]+\.?[0-9]*)',
                'balance_pattern': r'Avl Bal:Rs\.?\s*([0-9,]+\.?[0-9]*)',
                'merchant_pattern': r'at\s+([A-Z\s]+)\s+on'
            },
            'sbi': {
                'sender': 'sbicard@sbi.co.in',
                'amount_pattern': r'INR\s*([0-9,]+\.?[0-9]*)',
                'balance_pattern': r'Available Balance.*?INR\s*([0-9,]+\.?[0-9]*)',
                'merchant_pattern': r'spent at\s+([A-Z\s]+)'
            },
            'icici': {
                'sender': 'credit-cards@icicibank.com',
                'amount_pattern': r'Rs\s*([0-9,]+\.?[0-9]*)',
                'balance_pattern': r'Available Limit.*?Rs\s*([0-9,]+\.?[0-9]*)',
                'merchant_pattern': r'Transaction at\s+([A-Z\s]+)'
            }
        }
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_accounts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                email_address TEXT NOT NULL,
                provider TEXT NOT NULL,
                access_token TEXT,
                last_sync TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parsed_transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                email_id TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                merchant_name TEXT,
                balance_after REAL,
                transaction_date TEXT NOT NULL,
                parsed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(email_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def setup_email_parsing(self, user_id: int, email_config: Dict) -> Dict:
        """Setup email parsing for transaction alerts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO email_accounts 
                (user_id, email_address, provider, access_token, last_sync)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id, email_config['email'], email_config['provider'],
                email_config.get('access_token'), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'email': email_config['email'],
                'message': 'Email parsing setup completed'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def parse_bank_emails(self, user_id: int, days_back: int = 7) -> Dict:
        """Parse bank transaction emails"""
        try:
            # Mock email parsing
            mock_emails = self._generate_mock_emails(days_back)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            parsed_count = 0
            for email_data in mock_emails:
                try:
                    parsed_txn = self._parse_transaction_email(email_data)
                    if parsed_txn:
                        cursor.execute('''
                            INSERT OR IGNORE INTO parsed_transactions 
                            (user_id, email_id, bank_name, amount, transaction_type, 
                             merchant_name, balance_after, transaction_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            user_id, parsed_txn['email_id'], parsed_txn['bank'],
                            parsed_txn['amount'], parsed_txn['type'],
                            parsed_txn['merchant'], parsed_txn['balance'], parsed_txn['date']
                        ))
                        
                        if cursor.rowcount > 0:
                            parsed_count += 1
                            
                except sqlite3.IntegrityError:
                    continue
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'parsed_count': parsed_count,
                'total_emails': len(mock_emails)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_mock_emails(self, days: int) -> List[Dict]:
        """Generate mock bank emails"""
        emails = []
        banks = ['hdfc', 'sbi', 'icici']
        
        for i in range(15):  # Generate 15 mock emails
            bank = banks[i % len(banks)]
            email_date = datetime.now() - timedelta(days=i//2)
            
            emails.append({
                'id': f"email_{uuid.uuid4().hex[:12]}",
                'sender': self.bank_patterns[bank]['sender'],
                'subject': f"Transaction Alert - {bank.upper()}",
                'body': self._generate_mock_email_body(bank, 1500 + (i * 100)),
                'date': email_date.isoformat(),
                'bank': bank
            })
        
        return emails
    
    def _generate_mock_email_body(self, bank: str, amount: float) -> str:
        """Generate mock email body"""
        if bank == 'hdfc':
            return f"Dear Customer, Rs.{amount:.2f} has been debited from your account at AMAZON INDIA on {datetime.now().strftime('%d-%m-%Y')}. Avl Bal:Rs.45,230.50"
        elif bank == 'sbi':
            return f"Transaction Alert: INR {amount:.2f} spent at GROCERY STORE on {datetime.now().strftime('%d/%m/%Y')}. Available Balance: INR 32,150.75"
        else:
            return f"ICICI Bank Alert: Rs {amount:.2f} Transaction at PETROL PUMP on {datetime.now().strftime('%d-%m-%Y')}. Available Limit: Rs 85,500.25"
    
    def _parse_transaction_email(self, email_data: Dict) -> Optional[Dict]:
        """Parse individual transaction email"""
        try:
            bank = email_data['bank']
            patterns = self.bank_patterns[bank]
            body = email_data['body']
            
            # Extract amount
            amount_match = re.search(patterns['amount_pattern'], body)
            if not amount_match:
                return None
            
            amount = float(amount_match.group(1).replace(',', ''))
            
            # Extract balance
            balance_match = re.search(patterns['balance_pattern'], body)
            balance = float(balance_match.group(1).replace(',', '')) if balance_match else None
            
            # Extract merchant
            merchant_match = re.search(patterns['merchant_pattern'], body)
            merchant = merchant_match.group(1).strip() if merchant_match else 'Unknown'
            
            return {
                'email_id': email_data['id'],
                'bank': bank.upper(),
                'amount': amount,
                'type': 'debit',
                'merchant': merchant,
                'balance': balance,
                'date': email_data['date']
            }
            
        except Exception as e:
            logging.error(f"Error parsing email: {e}")
            return None
    
    def get_parsed_transactions(self, user_id: int, days: int = 30) -> List[Dict]:
        """Get parsed transactions from emails"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT bank_name, amount, transaction_type, merchant_name, 
                   balance_after, transaction_date, parsed_at
            FROM parsed_transactions 
            WHERE user_id = ? AND transaction_date >= ?
            ORDER BY transaction_date DESC
        ''', (user_id, since_date))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return [{
            'bank': t[0],
            'amount': t[1],
            'type': t[2],
            'merchant': t[3],
            'balance_after': t[4],
            'transaction_date': t[5],
            'parsed_at': t[6]
        } for t in transactions]

class ThirdPartyIntegrationManager:
    def __init__(self, db_path: str):
        self.mutual_funds = MutualFundIntegration(db_path)
        self.expense_apps = ExpenseAppIntegration(db_path)
        self.calendar_sync = CalendarSync(db_path)
        self.email_parser = EmailParser(db_path)
        self.db_path = db_path
    
    def get_integrations_dashboard(self, user_id: int) -> Dict:
        """Get comprehensive integrations dashboard"""
        mf_portfolio = self.mutual_funds.get_consolidated_portfolio(user_id)
        expense_summary = self.expense_apps.get_imported_summary(user_id)
        upcoming_reminders = self.calendar_sync.get_upcoming_reminders(user_id)
        parsed_transactions = self.email_parser.get_parsed_transactions(user_id, 7)
        
        return {
            'mutual_funds': {
                'total_schemes': mf_portfolio['summary']['total_schemes'],
                'total_value': mf_portfolio['summary']['total_current_value'],
                'total_pnl': mf_portfolio['summary']['total_pnl'],
                'top_performers': sorted(mf_portfolio['holdings'], key=lambda x: x['pnl_percentage'], reverse=True)[:3]
            },
            'expense_imports': {
                'connected_apps': len(expense_summary['apps']),
                'total_imported': expense_summary['total_imported'],
                'total_amount': expense_summary['total_amount'],
                'top_categories': expense_summary['categories'][:3]
            },
            'calendar_reminders': {
                'upcoming_count': len(upcoming_reminders),
                'urgent_reminders': [r for r in upcoming_reminders if r['days_until_due'] <= 2],
                'next_due': upcoming_reminders[0] if upcoming_reminders else None
            },
            'email_parsing': {
                'recent_transactions': len(parsed_transactions),
                'total_amount': sum(t['amount'] for t in parsed_transactions),
                'banks_tracked': len(set(t['bank'] for t in parsed_transactions))
            }
        }
    
    def sync_all_integrations(self, user_id: int) -> Dict:
        """Sync all connected integrations"""
        results = {
            'mutual_funds': [],
            'expense_apps': [],
            'email_parsing': None,
            'calendar_sync': None
        }
        
        # Sync mutual fund platforms
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT platform_name FROM mf_platforms WHERE user_id = ? AND status = "active"', (user_id,))
        mf_platforms = cursor.fetchall()
        
        for platform in mf_platforms:
            result = self.mutual_funds.sync_holdings(user_id, platform[0])
            results['mutual_funds'].append({
                'platform': platform[0],
                'result': result
            })
        
        # Sync expense apps
        cursor.execute('SELECT app_name FROM expense_app_connections WHERE user_id = ? AND status = "active"', (user_id,))
        expense_apps = cursor.fetchall()
        
        for app in expense_apps:
            result = self.expense_apps.import_expenses(user_id, app[0])
            results['expense_apps'].append({
                'app': app[0],
                'result': result
            })
        
        conn.close()
        
        # Parse emails
        email_result = self.email_parser.parse_bank_emails(user_id)
        results['email_parsing'] = email_result
        
        # Sync calendar
        calendar_result = self.calendar_sync.sync_with_calendar(user_id)
        results['calendar_sync'] = calendar_result
        
        return {
            'success': True,
            'sync_results': results,
            'timestamp': datetime.now().isoformat()
        }