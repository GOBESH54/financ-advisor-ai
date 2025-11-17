import sqlite3
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import hashlib
import uuid
import logging

@dataclass
class BankAccount:
    account_id: str
    bank_name: str
    account_number: str
    account_type: str
    balance: float
    currency: str
    last_sync: str
    status: str

@dataclass
class Transaction:
    transaction_id: str
    account_id: str
    amount: float
    transaction_type: str
    description: str
    category: str
    date: str
    balance_after: float
    reference_number: str

class AccountAggregator:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
        self.supported_banks = {
            'SBI': {'api_url': 'https://api.sbi.co.in', 'auth_type': 'oauth'},
            'HDFC': {'api_url': 'https://api.hdfcbank.com', 'auth_type': 'oauth'},
            'ICICI': {'api_url': 'https://api.icicibank.com', 'auth_type': 'oauth'},
            'AXIS': {'api_url': 'https://api.axisbank.com', 'auth_type': 'oauth'},
            'KOTAK': {'api_url': 'https://api.kotak.com', 'auth_type': 'oauth'},
            'PNB': {'api_url': 'https://api.pnb.co.in', 'auth_type': 'oauth'}
        }
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                account_id TEXT UNIQUE NOT NULL,
                bank_name TEXT NOT NULL,
                account_number TEXT NOT NULL,
                account_type TEXT NOT NULL,
                balance REAL NOT NULL,
                currency TEXT DEFAULT 'INR',
                last_sync TEXT,
                status TEXT DEFAULT 'active',
                access_token TEXT,
                refresh_token TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_transactions (
                id INTEGER PRIMARY KEY,
                account_id TEXT NOT NULL,
                transaction_id TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT,
                category TEXT,
                transaction_date TEXT NOT NULL,
                balance_after REAL,
                reference_number TEXT,
                sync_status TEXT DEFAULT 'synced',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def connect_bank_account(self, user_id: int, bank_name: str, credentials: Dict) -> Dict:
        """Connect bank account using OAuth or credentials"""
        try:
            # Simulate bank API connection
            account_id = f"{bank_name}_{user_id}_{uuid.uuid4().hex[:8]}"
            
            # Mock API response
            account_data = {
                'account_id': account_id,
                'account_number': f"****{credentials.get('account_number', '1234')[-4:]}",
                'account_type': credentials.get('account_type', 'savings'),
                'balance': 50000.0,  # Mock balance
                'currency': 'INR'
            }
            
            # Store account
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bank_accounts 
                (user_id, account_id, bank_name, account_number, account_type, balance, last_sync, access_token)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, account_id, bank_name, account_data['account_number'],
                account_data['account_type'], account_data['balance'],
                datetime.now().isoformat(), credentials.get('access_token', 'mock_token')
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'account_id': account_id,
                'message': f'{bank_name} account connected successfully'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_connected_accounts(self, user_id: int) -> List[BankAccount]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT account_id, bank_name, account_number, account_type, 
                   balance, currency, last_sync, status
            FROM bank_accounts 
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        accounts = cursor.fetchall()
        conn.close()
        
        return [BankAccount(*account) for account in accounts]
    
    def disconnect_account(self, user_id: int, account_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE bank_accounts 
            SET status = 'disconnected' 
            WHERE user_id = ? AND account_id = ?
        ''', (user_id, account_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success

class RealTimeSync:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.sync_interval = 300  # 5 minutes
    
    def sync_account_transactions(self, account_id: str) -> Dict:
        """Sync transactions from bank API"""
        try:
            # Mock API call to fetch transactions
            mock_transactions = self._generate_mock_transactions(account_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            new_transactions = 0
            for txn in mock_transactions:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO bank_transactions 
                        (account_id, transaction_id, amount, transaction_type, description, 
                         category, transaction_date, balance_after, reference_number)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        account_id, txn['transaction_id'], txn['amount'],
                        txn['type'], txn['description'], txn['category'],
                        txn['date'], txn['balance_after'], txn['reference']
                    ))
                    
                    if cursor.rowcount > 0:
                        new_transactions += 1
                        
                except sqlite3.IntegrityError:
                    continue
            
            # Update last sync time
            cursor.execute('''
                UPDATE bank_accounts 
                SET last_sync = ?, balance = ?
                WHERE account_id = ?
            ''', (datetime.now().isoformat(), mock_transactions[-1]['balance_after'], account_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'new_transactions': new_transactions,
                'last_sync': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_mock_transactions(self, account_id: str) -> List[Dict]:
        """Generate mock transactions for testing"""
        transactions = []
        balance = 50000.0
        
        mock_data = [
            {'amount': -2500, 'type': 'debit', 'desc': 'ATM Withdrawal', 'cat': 'cash'},
            {'amount': -1200, 'type': 'debit', 'desc': 'Grocery Store', 'cat': 'food'},
            {'amount': 25000, 'type': 'credit', 'desc': 'Salary Credit', 'cat': 'income'},
            {'amount': -800, 'type': 'debit', 'desc': 'Fuel Payment', 'cat': 'transportation'},
            {'amount': -3500, 'type': 'debit', 'desc': 'Online Shopping', 'cat': 'shopping'}
        ]
        
        for i, data in enumerate(mock_data):
            balance += data['amount']
            transactions.append({
                'transaction_id': f"TXN_{account_id}_{i}_{uuid.uuid4().hex[:8]}",
                'amount': data['amount'],
                'type': data['type'],
                'description': data['desc'],
                'category': data['cat'],
                'date': (datetime.now() - timedelta(days=i)).isoformat(),
                'balance_after': balance,
                'reference': f"REF{uuid.uuid4().hex[:10].upper()}"
            })
        
        return transactions
    
    def sync_all_accounts(self, user_id: int) -> Dict:
        """Sync all connected accounts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT account_id FROM bank_accounts 
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        accounts = cursor.fetchall()
        conn.close()
        
        results = []
        total_new = 0
        
        for account in accounts:
            result = self.sync_account_transactions(account[0])
            results.append({
                'account_id': account[0],
                'result': result
            })
            if result['success']:
                total_new += result['new_transactions']
        
        return {
            'success': True,
            'accounts_synced': len(accounts),
            'total_new_transactions': total_new,
            'results': results
        }

class BillPayment:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
        self.bill_categories = {
            'electricity': {'name': 'Electricity', 'providers': ['BESCOM', 'MSEDCL', 'TNEB']},
            'gas': {'name': 'Gas', 'providers': ['Indane', 'Bharat Gas', 'HP Gas']},
            'water': {'name': 'Water', 'providers': ['BWSSB', 'Mumbai Water', 'Delhi Jal Board']},
            'mobile': {'name': 'Mobile', 'providers': ['Airtel', 'Jio', 'Vi', 'BSNL']},
            'internet': {'name': 'Internet', 'providers': ['Airtel Fiber', 'Jio Fiber', 'ACT']},
            'dth': {'name': 'DTH', 'providers': ['Tata Sky', 'Dish TV', 'Airtel Digital TV']},
            'insurance': {'name': 'Insurance', 'providers': ['LIC', 'HDFC Life', 'ICICI Prudential']}
        }
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_billers (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                biller_name TEXT NOT NULL,
                category TEXT NOT NULL,
                account_number TEXT NOT NULL,
                provider TEXT NOT NULL,
                nickname TEXT,
                auto_pay BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bill_payments (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                biller_id INTEGER,
                account_id TEXT NOT NULL,
                amount REAL NOT NULL,
                bill_category TEXT NOT NULL,
                provider TEXT NOT NULL,
                bill_number TEXT,
                payment_status TEXT DEFAULT 'pending',
                transaction_id TEXT,
                payment_date TEXT NOT NULL,
                due_date TEXT,
                FOREIGN KEY (biller_id) REFERENCES saved_billers (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_biller(self, user_id: int, biller_data: Dict) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO saved_billers 
            (user_id, biller_name, category, account_number, provider, nickname, auto_pay)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, biller_data['biller_name'], biller_data['category'],
            biller_data['account_number'], biller_data['provider'],
            biller_data.get('nickname', ''), biller_data.get('auto_pay', False)
        ))
        
        biller_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return biller_id
    
    def get_saved_billers(self, user_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, biller_name, category, account_number, provider, nickname, auto_pay
            FROM saved_billers 
            WHERE user_id = ?
        ''', (user_id,))
        
        billers = cursor.fetchall()
        conn.close()
        
        return [{
            'id': b[0], 'biller_name': b[1], 'category': b[2],
            'account_number': b[3], 'provider': b[4], 'nickname': b[5], 'auto_pay': bool(b[6])
        } for b in billers]
    
    def pay_bill(self, user_id: int, payment_data: Dict) -> Dict:
        """Process bill payment"""
        try:
            # Validate account balance
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT balance FROM bank_accounts 
                WHERE user_id = ? AND account_id = ? AND status = 'active'
            ''', (user_id, payment_data['account_id']))
            
            account = cursor.fetchone()
            if not account or account[0] < payment_data['amount']:
                return {'success': False, 'error': 'Insufficient balance'}
            
            # Generate transaction ID
            transaction_id = f"BILL_{uuid.uuid4().hex[:12].upper()}"
            
            # Record payment
            cursor.execute('''
                INSERT INTO bill_payments 
                (user_id, biller_id, account_id, amount, bill_category, provider, 
                 bill_number, payment_status, transaction_id, payment_date, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?)
            ''', (
                user_id, payment_data.get('biller_id'), payment_data['account_id'],
                payment_data['amount'], payment_data['category'], payment_data['provider'],
                payment_data.get('bill_number', ''), transaction_id,
                datetime.now().isoformat(), payment_data.get('due_date')
            ))
            
            # Update account balance
            cursor.execute('''
                UPDATE bank_accounts 
                SET balance = balance - ? 
                WHERE account_id = ?
            ''', (payment_data['amount'], payment_data['account_id']))
            
            # Add transaction record
            cursor.execute('''
                INSERT INTO bank_transactions 
                (account_id, transaction_id, amount, transaction_type, description, 
                 category, transaction_date, reference_number)
                VALUES (?, ?, ?, 'debit', ?, 'bills', ?, ?)
            ''', (
                payment_data['account_id'], transaction_id, -payment_data['amount'],
                f"Bill Payment - {payment_data['provider']}", datetime.now().isoformat(), transaction_id
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'message': f'Bill payment of ₹{payment_data["amount"]:,.0f} successful'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_bill_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT amount, bill_category, provider, payment_status, 
                   transaction_id, payment_date, due_date
            FROM bill_payments 
            WHERE user_id = ? 
            ORDER BY payment_date DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        payments = cursor.fetchall()
        conn.close()
        
        return [{
            'amount': p[0], 'category': p[1], 'provider': p[2],
            'status': p[3], 'transaction_id': p[4], 'payment_date': p[5], 'due_date': p[6]
        } for p in payments]

class UPIIntegration:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
        self.upi_providers = ['PhonePe', 'Google Pay', 'Paytm', 'BHIM', 'Amazon Pay']
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upi_accounts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                upi_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                linked_account TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upi_transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                upi_id TEXT NOT NULL,
                transaction_id TEXT UNIQUE NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                counterparty_upi TEXT,
                counterparty_name TEXT,
                description TEXT,
                status TEXT DEFAULT 'completed',
                transaction_date TEXT NOT NULL,
                reference_number TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_upi_account(self, user_id: int, upi_id: str, provider: str, linked_account: str = None) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO upi_accounts (user_id, upi_id, provider, linked_account)
            VALUES (?, ?, ?, ?)
        ''', (user_id, upi_id, provider, linked_account))
        
        account_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return account_id
    
    def track_upi_transaction(self, user_id: int, transaction_data: Dict) -> str:
        """Track UPI transaction"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        transaction_id = f"UPI_{uuid.uuid4().hex[:12].upper()}"
        
        cursor.execute('''
            INSERT INTO upi_transactions 
            (user_id, upi_id, transaction_id, amount, transaction_type, 
             counterparty_upi, counterparty_name, description, transaction_date, reference_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id, transaction_data['upi_id'], transaction_id,
            transaction_data['amount'], transaction_data['type'],
            transaction_data.get('counterparty_upi', ''), transaction_data.get('counterparty_name', ''),
            transaction_data.get('description', ''), datetime.now().isoformat(),
            transaction_data.get('reference_number', transaction_id)
        ))
        
        conn.commit()
        conn.close()
        
        return transaction_id
    
    def get_upi_transactions(self, user_id: int, days: int = 30) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT transaction_id, upi_id, amount, transaction_type, 
                   counterparty_upi, counterparty_name, description, 
                   status, transaction_date, reference_number
            FROM upi_transactions 
            WHERE user_id = ? AND transaction_date >= ?
            ORDER BY transaction_date DESC
        ''', (user_id, since_date))
        
        transactions = cursor.fetchall()
        conn.close()
        
        return [{
            'transaction_id': t[0], 'upi_id': t[1], 'amount': t[2], 'type': t[3],
            'counterparty_upi': t[4], 'counterparty_name': t[5], 'description': t[6],
            'status': t[7], 'date': t[8], 'reference': t[9]
        } for t in transactions]
    
    def get_upi_summary(self, user_id: int, period: str = 'month') -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if period == 'month':
            since_date = (datetime.now() - timedelta(days=30)).isoformat()
        else:
            since_date = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute('''
            SELECT transaction_type, COUNT(*), SUM(amount)
            FROM upi_transactions 
            WHERE user_id = ? AND transaction_date >= ?
            GROUP BY transaction_type
        ''', (user_id, since_date))
        
        summary = cursor.fetchall()
        conn.close()
        
        result = {'sent': {'count': 0, 'amount': 0}, 'received': {'count': 0, 'amount': 0}}
        
        for s in summary:
            if s[0] == 'sent':
                result['sent'] = {'count': s[1], 'amount': abs(s[2])}
            elif s[0] == 'received':
                result['received'] = {'count': s[1], 'amount': s[2]}
        
        return result

class BankIntegrationManager:
    def __init__(self, db_path: str):
        self.account_aggregator = AccountAggregator(db_path)
        self.real_time_sync = RealTimeSync(db_path)
        self.bill_payment = BillPayment(db_path)
        self.upi_integration = UPIIntegration(db_path)
        self.db_path = db_path
    
    def get_banking_dashboard(self, user_id: int) -> Dict:
        """Get comprehensive banking dashboard"""
        connected_accounts = self.account_aggregator.get_connected_accounts(user_id)
        recent_bills = self.bill_payment.get_bill_history(user_id, 10)
        upi_summary = self.upi_integration.get_upi_summary(user_id)
        recent_upi = self.upi_integration.get_upi_transactions(user_id, 7)
        
        total_balance = sum(acc.balance for acc in connected_accounts)
        
        return {
            'accounts_summary': {
                'total_accounts': len(connected_accounts),
                'total_balance': total_balance,
                'accounts': [{
                    'account_id': acc.account_id,
                    'bank_name': acc.bank_name,
                    'account_number': acc.account_number,
                    'balance': acc.balance,
                    'last_sync': acc.last_sync
                } for acc in connected_accounts]
            },
            'recent_bills': recent_bills,
            'upi_summary': upi_summary,
            'recent_upi_transactions': recent_upi[:5],
            'quick_actions': [
                {'action': 'sync_accounts', 'label': 'Sync All Accounts'},
                {'action': 'pay_bill', 'label': 'Pay Bills'},
                {'action': 'view_upi', 'label': 'UPI Transactions'},
                {'action': 'add_account', 'label': 'Connect Account'}
            ]
        }
    
    def get_transaction_insights(self, user_id: int) -> Dict:
        """Get transaction insights across all accounts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bank transactions
        cursor.execute('''
            SELECT category, SUM(ABS(amount)) as total, COUNT(*) as count
            FROM bank_transactions bt
            JOIN bank_accounts ba ON bt.account_id = ba.account_id
            WHERE ba.user_id = ? AND bt.transaction_date >= ?
            GROUP BY category
            ORDER BY total DESC
        ''', (user_id, (datetime.now() - timedelta(days=30)).isoformat()))
        
        bank_categories = cursor.fetchall()
        
        # UPI transactions
        cursor.execute('''
            SELECT 'UPI' as category, SUM(ABS(amount)) as total, COUNT(*) as count
            FROM upi_transactions
            WHERE user_id = ? AND transaction_date >= ?
        ''', (user_id, (datetime.now() - timedelta(days=30)).isoformat()))
        
        upi_total = cursor.fetchone()
        
        # Bill payments
        cursor.execute('''
            SELECT bill_category, SUM(amount) as total, COUNT(*) as count
            FROM bill_payments
            WHERE user_id = ? AND payment_date >= ?
            GROUP BY bill_category
        ''', (user_id, (datetime.now() - timedelta(days=30)).isoformat()))
        
        bill_categories = cursor.fetchall()
        
        conn.close()
        
        return {
            'bank_spending': [{'category': c[0], 'amount': c[1], 'count': c[2]} for c in bank_categories],
            'upi_spending': {'amount': upi_total[1] if upi_total[1] else 0, 'count': upi_total[2] if upi_total[2] else 0},
            'bill_payments': [{'category': c[0], 'amount': c[1], 'count': c[2]} for c in bill_categories],
            'total_transactions': sum(c[2] for c in bank_categories) + (upi_total[2] if upi_total[2] else 0) + sum(c[2] for c in bill_categories)
        }