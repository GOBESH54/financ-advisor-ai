import pandas as pd
import re
from datetime import datetime
import logging
from pathlib import Path
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

class BankStatementParser:
    def __init__(self):
        # Common Indian bank patterns
        self.bank_patterns = {
            'HDFC': r'HDFC|HDFC BANK|HDFC Bank',
            'ICICI': r'ICICI|ICICI BANK|ICICI Bank',
            'SBI': r'STATE BANK|SBI|State Bank',
            'AXIS': r'AXIS|AXIS BANK|Axis Bank',
            'KOTAK': r'KOTAK|KOTAK MAHINDRA|Kotak Bank'
        }
        
        # Common transaction patterns
        self.txn_patterns = {
            'date': r'\d{2}[-/]\d{2}[-/]\d{2,4}|\d{2}[A-Za-z]{3,9}\d{0,2}(?:[\s,-]\d{2,4})?',
            'amount': r'[\d,]+(?:\.\d{2})?|\d+(?:\.\d{2})?',
            'description': r'[A-Za-z0-9\s\.\-\/,&]+',
            'ref': r'[A-Z0-9]{6,20}'
        }
        
        # Common transaction categories
        self.categories = {
            'food_dining': r'SWIGGY|ZOMATO|FOOD|RESTAURANT|EATERY|CAFE|MCDONALDS|PIZZA|BURGER',
            'groceries': r'BIG BAZAAR|MORE|DMART|RELIANCE FRESH|GROCERY|SUPERMARKET',
            'shopping': r'AMAZON|FLIPKART|MYNTRA|AJIO|SHOPPING|PURCHASE|BILLDESK',
            'transport': r'UBER|OLA|RAPIDO|METRO|BUS|TRAIN|IRCTC|FUEL|PETROL|DIESEL|BPCL|HPCL',
            'bills': r'ELECTRICITY|WATER|GAS|PHONE|MOBILE|RECHARGE|POSTPAID|PREPAID',
            'entertainment': r'NETFLIX|PRIME|HOTSTAR|ZEE5|MOVIE|CINEMA|THEATRE',
            'salary': r'SALARY|CREDIT INTEREST|INTEREST CREDITED|DIVIDEND',
            'transfer': r'IMPS|NEFT|RTGS|UPI|TRANSFER|TO SELF',
            'emi': r'EMI|LOAN|REPAYMENT',
            'investment': r'MUTUAL FUND|STOCK|EQUITY|INVEST|ICICIDIRECT|ZERODHA',
            'others': r'.*'  # Default category
        }

    def detect_bank(self, text: str) -> str:
        """Detect bank from text content"""
        text = str(text).upper()
        for bank, pattern in self.bank_patterns.items():
            if re.search(pattern, text):
                return bank
        return 'UNKNOWN'

    def parse_csv(self, filepath: str) -> List[Dict]:
        """Parse CSV bank statement"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(filepath, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                logger.error("Could not read CSV file with any encoding")
                return []
            
            # Clean column names
            df.columns = [str(col).strip().lower() for col in df.columns]
            
            # Detect bank from column names or data
            bank = self.detect_bank(' '.join(df.columns))
            
            # Map common column names
            date_col = next((col for col in df.columns if 'date' in col), None)
            desc_col = next((col for col in df.columns if 'desc' in col or 'narration' in col or 'particular' in col), None)
            debit_col = next((col for col in df.columns if 'debit' in col or 'withdrawal' in col or 'dr' == col.lower()), None)
            credit_col = next((col for col in df.columns if 'credit' in col or 'deposit' in col or 'cr' == col.lower()), None)
            
            # If no specific columns found, try to guess based on data
            if not all([date_col, desc_col, any([debit_col, credit_col])]):
                return self._guess_and_parse(df, bank)
            
            transactions = []
            for _, row in df.iterrows():
                try:
                    # Skip empty rows
                    if row.isnull().all():
                        continue
                        
                    # Get date
                    if date_col and date_col in row:
                        date = self._parse_date(str(row[date_col]))
                        if not date:
                            continue
                    else:
                        continue
                    
                    # Get description
                    description = str(row[desc_col]) if desc_col and desc_col in row else ''
                    
                    # Get amount and type
                    amount = 0
                    txn_type = 'debit'
                    
                    if debit_col and debit_col in row and pd.notna(row[debit_col]) and str(row[debit_col]).strip() not in ['', '0', '0.0', '0.00']:
                        amount = float(str(row[debit_col]).replace(',', ''))
                        txn_type = 'debit'
                    elif credit_col and credit_col in row and pd.notna(row[credit_col]) and str(row[credit_col]).strip() not in ['', '0', '0.0', '0.00']:
                        amount = float(str(row[credit_col]).replace(',', ''))
                        txn_type = 'credit'
                    else:
                        # If no amount found, skip
                        continue
                    
                    # Categorize transaction
                    category = self._categorize_transaction(description)
                    
                    transactions.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'description': description,
                        'amount': abs(amount),
                        'type': txn_type,
                        'category': category,
                        'bank': bank,
                        'formatted_date': date.strftime('%d/%m/%Y'),
                        'formatted_amount': f"₹{abs(amount):,.2f}",
                        'month': date.strftime('%Y-%m')
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing row {_}: {e}")
                    continue
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            return []
    
    def _guess_and_parse(self, df: pd.DataFrame, bank: str) -> List[Dict]:
        """Try to parse CSV when column names are not standard"""
        transactions = []
        
        for _, row in df.iterrows():
            try:
                # Skip empty rows
                if row.isnull().all():
                    continue
                
                # Try to find date in any column
                date = None
                description = ''
                amount = 0
                txn_type = 'debit'
                
                for col, value in row.items():
                    if pd.isna(value):
                        continue
                        
                    value_str = str(value).strip()
                    
                    # Check for date
                    if not date and self._parse_date(value_str):
                        date = self._parse_date(value_str)
                        continue
                    
                    # Check for amount
                    amount_match = re.search(r'[\d,]+\.?\d*', value_str.replace(',', ''))
                    if amount_match and not description:  # Only take first amount found
                        amount_str = amount_match.group()
                        try:
                            amount = float(amount_str)
                            # Guess type based on sign or column name
                            if '-' in value_str or 'dr' in str(col).lower():
                                txn_type = 'debit'
                            else:
                                txn_type = 'credit' if 'credit' in str(col).lower() else 'debit'
                        except (ValueError, TypeError):
                            pass
                        continue
                    
                    # Use first non-empty string as description
                    if not description and value_str and not value_str.replace('.', '').isdigit():
                        description = value_str
                
                if not date or not amount:
                    continue
                
                # Categorize transaction
                category = self._categorize_transaction(description)
                
                transactions.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'description': description,
                    'amount': abs(amount),
                    'type': txn_type,
                    'category': category,
                    'bank': bank,
                    'formatted_date': date.strftime('%d/%m/%Y'),
                    'formatted_amount': f"₹{abs(amount):,.2f}",
                    'month': date.strftime('%Y-%m')
                })
                
            except Exception as e:
                logger.error(f"Error in guess_and_parse for row {_}: {e}")
                continue
        
        return transactions
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from string with multiple formats"""
        if not date_str or str(date_str).lower() in ['nan', 'nat', 'none']:
            return None
            
        date_str = str(date_str).strip()
        
        # Common date formats in Indian bank statements
        date_formats = [
            '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d',
            '%d-%b-%Y', '%d-%b-%y',
            '%d %b %Y', '%d %B %Y',
            '%Y%m%d', '%d%m%Y',
            '%d/%m/%y', '%d-%m-%y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue
        
        return None
    
    def _categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        if not description:
            return 'others'
            
        desc_upper = description.upper()
        
        for category, pattern in self.categories.items():
            if re.search(pattern, desc_upper):
                return category
                
        return 'others'