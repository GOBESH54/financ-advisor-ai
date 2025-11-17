import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import calendar

@dataclass
class BudgetAllocation:
    category: str
    allocated_amount: float
    spent_amount: float
    remaining_amount: float
    percentage_used: float

class ZeroBasedBudgeting:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS zero_based_budgets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                total_income REAL NOT NULL,
                allocated_amount REAL NOT NULL,
                unallocated_amount REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_allocations (
                id INTEGER PRIMARY KEY,
                budget_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                allocated_amount REAL NOT NULL,
                priority INTEGER DEFAULT 1,
                FOREIGN KEY (budget_id) REFERENCES zero_based_budgets (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_zero_budget(self, user_id: int, month: str, total_income: float) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO zero_based_budgets (user_id, month, total_income, allocated_amount, unallocated_amount)
            VALUES (?, ?, ?, 0, ?)
        ''', (user_id, month, total_income, total_income))
        
        budget_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return budget_id
    
    def allocate_category(self, budget_id: int, category: str, amount: float, priority: int = 1):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Add allocation
        cursor.execute('''
            INSERT OR REPLACE INTO budget_allocations (budget_id, category, allocated_amount, priority)
            VALUES (?, ?, ?, ?)
        ''', (budget_id, category, amount, priority))
        
        # Update budget totals
        cursor.execute('SELECT SUM(allocated_amount) FROM budget_allocations WHERE budget_id = ?', (budget_id,))
        total_allocated = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT total_income FROM zero_based_budgets WHERE id = ?', (budget_id,))
        total_income = cursor.fetchone()[0]
        
        unallocated = total_income - total_allocated
        
        cursor.execute('''
            UPDATE zero_based_budgets 
            SET allocated_amount = ?, unallocated_amount = ?
            WHERE id = ?
        ''', (total_allocated, unallocated, budget_id))
        
        conn.commit()
        conn.close()
    
    def get_budget_status(self, budget_id: int) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM zero_based_budgets WHERE id = ?', (budget_id,))
        budget = cursor.fetchone()
        
        cursor.execute('''
            SELECT category, allocated_amount, priority 
            FROM budget_allocations 
            WHERE budget_id = ? 
            ORDER BY priority
        ''', (budget_id,))
        allocations = cursor.fetchall()
        
        conn.close()
        
        return {
            'budget_id': budget_id,
            'month': budget[2],
            'total_income': budget[3],
            'allocated_amount': budget[4],
            'unallocated_amount': budget[5],
            'is_balanced': budget[5] == 0,
            'allocations': [{'category': a[0], 'amount': a[1], 'priority': a[2]} for a in allocations]
        }

class EnvelopeBudgeting:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS envelopes (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                current_balance REAL NOT NULL,
                spent_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS envelope_transactions (
                id INTEGER PRIMARY KEY,
                envelope_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                transaction_date TEXT NOT NULL,
                FOREIGN KEY (envelope_id) REFERENCES envelopes (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_envelope(self, user_id: int, category: str, monthly_limit: float):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO envelopes (user_id, category, monthly_limit, current_balance)
            VALUES (?, ?, ?, ?)
        ''', (user_id, category, monthly_limit, monthly_limit))
        
        envelope_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return envelope_id
    
    def spend_from_envelope(self, envelope_id: int, amount: float, description: str = '') -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT current_balance FROM envelopes WHERE id = ?', (envelope_id,))
        balance = cursor.fetchone()[0]
        
        if balance >= amount:
            # Record transaction
            cursor.execute('''
                INSERT INTO envelope_transactions (envelope_id, amount, description, transaction_date)
                VALUES (?, ?, ?, ?)
            ''', (envelope_id, amount, description, datetime.now().isoformat()))
            
            # Update envelope
            cursor.execute('''
                UPDATE envelopes 
                SET current_balance = current_balance - ?, spent_amount = spent_amount + ?
                WHERE id = ?
            ''', (amount, amount, envelope_id))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def refill_envelopes(self, user_id: int):
        """Refill all envelopes at month start"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE envelopes 
            SET current_balance = monthly_limit, spent_amount = 0
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_envelope_status(self, user_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, category, monthly_limit, current_balance, spent_amount
            FROM envelopes 
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        envelopes = cursor.fetchall()
        conn.close()
        
        return [{
            'id': e[0],
            'category': e[1],
            'monthly_limit': e[2],
            'current_balance': e[3],
            'spent_amount': e[4],
            'percentage_used': (e[4] / e[2] * 100) if e[2] > 0 else 0,
            'status': 'overspent' if e[3] < 0 else 'warning' if e[3] < e[2] * 0.2 else 'good'
        } for e in envelopes]

class SeasonalBudgeting:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seasonal_budgets (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                event_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                target_amount REAL NOT NULL,
                saved_amount REAL DEFAULT 0,
                target_date TEXT NOT NULL,
                monthly_saving_required REAL NOT NULL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seasonal_categories (
                id INTEGER PRIMARY KEY,
                budget_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                estimated_amount REAL NOT NULL,
                FOREIGN KEY (budget_id) REFERENCES seasonal_budgets (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_seasonal_budget(self, user_id: int, event_name: str, event_type: str, 
                             target_amount: float, target_date: str, categories: List[Dict]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate monthly saving required
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        months_remaining = max(1, (target_dt.year - datetime.now().year) * 12 + target_dt.month - datetime.now().month)
        monthly_required = target_amount / months_remaining
        
        cursor.execute('''
            INSERT INTO seasonal_budgets 
            (user_id, event_name, event_type, target_amount, target_date, monthly_saving_required)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, event_name, event_type, target_amount, target_date, monthly_required))
        
        budget_id = cursor.lastrowid
        
        # Add categories
        for cat in categories:
            cursor.execute('''
                INSERT INTO seasonal_categories (budget_id, category, estimated_amount)
                VALUES (?, ?, ?)
            ''', (budget_id, cat['category'], cat['amount']))
        
        conn.commit()
        conn.close()
        
        return budget_id
    
    def add_seasonal_saving(self, budget_id: int, amount: float):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE seasonal_budgets 
            SET saved_amount = saved_amount + ?
            WHERE id = ?
        ''', (amount, budget_id))
        
        conn.commit()
        conn.close()
    
    def get_seasonal_budgets(self, user_id: int) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, event_name, event_type, target_amount, saved_amount, 
                   target_date, monthly_saving_required
            FROM seasonal_budgets 
            WHERE user_id = ? AND status = 'active'
        ''', (user_id,))
        
        budgets = cursor.fetchall()
        
        result = []
        for budget in budgets:
            budget_id = budget[0]
            
            # Get categories
            cursor.execute('''
                SELECT category, estimated_amount 
                FROM seasonal_categories 
                WHERE budget_id = ?
            ''', (budget_id,))
            categories = cursor.fetchall()
            
            # Calculate progress
            progress = (budget[4] / budget[3] * 100) if budget[3] > 0 else 0
            
            # Calculate days remaining
            target_date = datetime.strptime(budget[5], '%Y-%m-%d')
            days_remaining = (target_date - datetime.now()).days
            
            result.append({
                'id': budget_id,
                'event_name': budget[1],
                'event_type': budget[2],
                'target_amount': budget[3],
                'saved_amount': budget[4],
                'progress_percentage': progress,
                'target_date': budget[5],
                'days_remaining': days_remaining,
                'monthly_saving_required': budget[6],
                'categories': [{'category': c[0], 'amount': c[1]} for c in categories],
                'status': 'completed' if progress >= 100 else 'on_track' if progress >= 80 else 'behind'
            })
        
        conn.close()
        return result
    
    def get_festival_templates(self) -> Dict[str, List[Dict]]:
        """Predefined festival budget templates"""
        return {
            'diwali': [
                {'category': 'Decorations', 'amount': 5000},
                {'category': 'Gifts', 'amount': 15000},
                {'category': 'Sweets & Food', 'amount': 8000},
                {'category': 'Clothes', 'amount': 12000},
                {'category': 'Fireworks', 'amount': 3000}
            ],
            'wedding': [
                {'category': 'Venue', 'amount': 200000},
                {'category': 'Catering', 'amount': 150000},
                {'category': 'Photography', 'amount': 50000},
                {'category': 'Decorations', 'amount': 75000},
                {'category': 'Clothes & Jewelry', 'amount': 100000}
            ],
            'vacation': [
                {'category': 'Transportation', 'amount': 25000},
                {'category': 'Accommodation', 'amount': 40000},
                {'category': 'Food & Dining', 'amount': 15000},
                {'category': 'Activities', 'amount': 10000},
                {'category': 'Shopping', 'amount': 8000}
            ]
        }

class FamilyBudgeting:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family_groups (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family_members (
                id INTEGER PRIMARY KEY,
                family_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT DEFAULT 'member',
                spending_limit REAL DEFAULT 0,
                FOREIGN KEY (family_id) REFERENCES family_groups (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family_budgets (
                id INTEGER PRIMARY KEY,
                family_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                total_budget REAL NOT NULL,
                spent_amount REAL DEFAULT 0,
                month TEXT NOT NULL,
                FOREIGN KEY (family_id) REFERENCES family_groups (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS family_expenses (
                id INTEGER PRIMARY KEY,
                family_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                expense_date TEXT NOT NULL,
                approved BOOLEAN DEFAULT 1,
                FOREIGN KEY (family_id) REFERENCES family_groups (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_family_group(self, name: str, created_by: int) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO family_groups (name, created_by)
            VALUES (?, ?)
        ''', (name, created_by))
        
        family_id = cursor.lastrowid
        
        # Add creator as admin
        cursor.execute('''
            INSERT INTO family_members (family_id, user_id, role)
            VALUES (?, ?, 'admin')
        ''', (family_id, created_by))
        
        conn.commit()
        conn.close()
        
        return family_id
    
    def add_family_member(self, family_id: int, user_id: int, role: str = 'member', spending_limit: float = 0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO family_members (family_id, user_id, role, spending_limit)
            VALUES (?, ?, ?, ?)
        ''', (family_id, user_id, role, spending_limit))
        
        conn.commit()
        conn.close()
    
    def set_family_budget(self, family_id: int, category: str, budget_amount: float, month: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO family_budgets (family_id, category, total_budget, month)
            VALUES (?, ?, ?, ?)
        ''', (family_id, category, budget_amount, month))
        
        conn.commit()
        conn.close()
    
    def add_family_expense(self, family_id: int, user_id: int, category: str, 
                          amount: float, description: str = '') -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check user's spending limit
        cursor.execute('''
            SELECT spending_limit FROM family_members 
            WHERE family_id = ? AND user_id = ?
        ''', (family_id, user_id))
        
        member = cursor.fetchone()
        if not member:
            conn.close()
            return False
        
        spending_limit = member[0]
        
        # Check current month spending
        current_month = datetime.now().strftime('%Y-%m')
        cursor.execute('''
            SELECT SUM(amount) FROM family_expenses 
            WHERE family_id = ? AND user_id = ? AND expense_date LIKE ?
        ''', (family_id, user_id, f"{current_month}%"))
        
        current_spending = cursor.fetchone()[0] or 0
        
        if spending_limit > 0 and (current_spending + amount) > spending_limit:
            conn.close()
            return False
        
        # Add expense
        cursor.execute('''
            INSERT INTO family_expenses (family_id, user_id, category, amount, description, expense_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (family_id, user_id, category, amount, description, datetime.now().isoformat()))
        
        # Update family budget
        cursor.execute('''
            UPDATE family_budgets 
            SET spent_amount = spent_amount + ?
            WHERE family_id = ? AND category = ? AND month = ?
        ''', (amount, family_id, category, current_month))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_family_budget_status(self, family_id: int, month: str = None) -> Dict:
        if not month:
            month = datetime.now().strftime('%Y-%m')
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get family info
        cursor.execute('SELECT name FROM family_groups WHERE id = ?', (family_id,))
        family_name = cursor.fetchone()[0]
        
        # Get budget status
        cursor.execute('''
            SELECT category, total_budget, spent_amount
            FROM family_budgets 
            WHERE family_id = ? AND month = ?
        ''', (family_id, month))
        
        budgets = cursor.fetchall()
        
        # Get member spending
        cursor.execute('''
            SELECT fm.user_id, fm.role, fm.spending_limit,
                   COALESCE(SUM(fe.amount), 0) as spent
            FROM family_members fm
            LEFT JOIN family_expenses fe ON fm.user_id = fe.user_id 
                AND fe.family_id = ? AND fe.expense_date LIKE ?
            WHERE fm.family_id = ?
            GROUP BY fm.user_id, fm.role, fm.spending_limit
        ''', (family_id, f"{month}%", family_id))
        
        members = cursor.fetchall()
        
        conn.close()
        
        return {
            'family_name': family_name,
            'month': month,
            'budgets': [{
                'category': b[0],
                'total_budget': b[1],
                'spent_amount': b[2],
                'remaining': b[1] - b[2],
                'percentage_used': (b[2] / b[1] * 100) if b[1] > 0 else 0
            } for b in budgets],
            'members': [{
                'user_id': m[0],
                'role': m[1],
                'spending_limit': m[2],
                'spent_amount': m[3],
                'remaining_limit': m[2] - m[3] if m[2] > 0 else 0
            } for m in members],
            'total_budget': sum(b[1] for b in budgets),
            'total_spent': sum(b[2] for b in budgets)
        }

class AdvancedBudgetingManager:
    def __init__(self, db_path: str):
        self.zero_based = ZeroBasedBudgeting(db_path)
        self.envelope = EnvelopeBudgeting(db_path)
        self.seasonal = SeasonalBudgeting(db_path)
        self.family = FamilyBudgeting(db_path)
    
    def get_comprehensive_budget_dashboard(self, user_id: int, family_id: int = None) -> Dict:
        current_month = datetime.now().strftime('%Y-%m')
        
        dashboard = {
            'zero_based_budget': None,
            'envelope_status': self.envelope.get_envelope_status(user_id),
            'seasonal_budgets': self.seasonal.get_seasonal_budgets(user_id),
            'family_budget': None
        }
        
        if family_id:
            dashboard['family_budget'] = self.family.get_family_budget_status(family_id, current_month)
        
        return dashboard
    
    def get_budget_recommendations(self, user_id: int, monthly_income: float) -> Dict:
        """AI-powered budget recommendations"""
        recommendations = {
            'zero_based_allocation': {
                'needs': monthly_income * 0.5,
                'wants': monthly_income * 0.3,
                'savings': monthly_income * 0.2
            },
            'envelope_suggestions': [
                {'category': 'Groceries', 'amount': monthly_income * 0.15},
                {'category': 'Transportation', 'amount': monthly_income * 0.10},
                {'category': 'Entertainment', 'amount': monthly_income * 0.05},
                {'category': 'Utilities', 'amount': monthly_income * 0.08},
                {'category': 'Healthcare', 'amount': monthly_income * 0.05}
            ],
            'seasonal_planning': {
                'emergency_fund': monthly_income * 6,
                'annual_festivals': monthly_income * 2,
                'vacation_fund': monthly_income * 1.5
            }
        }
        
        return recommendations