import pandas as pd
import pdfplumber
import camelot
import re
import csv
import openpyxl
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import numpy as np
from pathlib import Path
import pytesseract
from PIL import Image
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedBankStatementParser:
    """Advanced parser for Indian bank statements supporting PDF, CSV, Excel, and image formats"""
    
    def __init__(self):
        # Enhanced Indian bank patterns with specific formats
        self.BANK_PATTERNS = {
            'HDFC': {
                'name': r'HDFC\s*BANK|hdfc\s*bank',
                'date_format': r'\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}',
                'amount_pattern': r'[₹\s]*[\d,]+\.?\d*',
                'transaction_pattern': r'(UPI|NEFT|RTGS|IMPS|ATM|POS|CHQ)',
                'columns': ['Date', 'Description', 'Chq/Ref Number', 'Value Date', 'Withdrawal', 'Deposit', 'Balance']
            },
            'ICICI': {
                'name': r'ICICI\s*BANK|icici\s*bank',
                'date_format': r'\d{2}/\d{2}/\d{4}',
                'amount_pattern': r'[₹\s]*[\d,]+\.?\d*',
                'transaction_pattern': r'(UPI|NEFT|RTGS|IMPS|ATM|POS|CHQ)',
                'columns': ['Date', 'Description', 'Cheque Number', 'Debit', 'Credit', 'Balance']
            },
            'SBI': {
                'name': r'STATE\s*BANK\s*OF\s*INDIA|SBI',
                'date_format': r'\d{2}\s\w{3}\s\d{4}|\d{2}/\d{2}/\d{4}',
                'amount_pattern': r'[₹\s]*[\d,]+\.?\d*',
                'transaction_pattern': r'(UPI|NEFT|RTGS|IMPS|ATM|POS|CHQ)',
                'columns': ['Txn Date', 'Value Date', 'Description', 'Ref No./Cheque No.', 'Debit', 'Credit', 'Balance']
            },
            'AXIS': {
                'name': r'AXIS\s*BANK|axis\s*bank',
                'date_format': r'\d{2}/\d{2}/\d{4}',
                'amount_pattern': r'[₹\s]*[\d,]+\.?\d*',
                'transaction_pattern': r'(UPI|NEFT|RTGS|IMPS|ATM|POS|CHQ)',
                'columns': ['Date', 'Description', 'Chq / Ref number', 'Debit', 'Credit', 'Balance']
            },
            'KOTAK': {
                'name': r'KOTAK\s*MAHINDRA\s*BANK|kotak',
                'date_format': r'\d{2}/\d{2}/\d{4}',
                'amount_pattern': r'[₹\s]*[\d,]+\.?\d*',
                'transaction_pattern': r'(UPI|NEFT|RTGS|IMPS|ATM|POS|CHQ)',
                'columns': ['Date', 'Description', 'Debit', 'Credit', 'Balance']
            }
        }
        
        # Common expense categories for auto-classification
        self.CATEGORY_PATTERNS = {
            'food_dining': r'SWIGGY|ZOMATO|DOMINOS|PIZZA|RESTAURANT|CAFE|HOTEL|FOOD|DINING',
            'groceries': r'BIGBASKET|GROFERS|DMart|RELIANCE|FRESH|GROCERY|SUPERMARKET|WALMART',
            'fuel': r'PETROL|DIESEL|FUEL|HP|BPCL|IOCL|SHELL|BHARAT\s*PETROLEUM',
            'utilities': r'ELECTRICITY|WATER|GAS|BROADBAND|INTERNET|MOBILE|TELECOM|AIRTEL|JIO|VI',
            'entertainment': r'NETFLIX|AMAZON\s*PRIME|HOTSTAR|SPOTIFY|BOOKMYSHOW|CINEMA|MOVIE',
            'transportation': r'UBER|OLA|METRO|BUS|RAILWAY|IRCTC|AUTO|TAXI|TRANSPORT',
            'shopping': r'AMAZON|FLIPKART|MYNTRA|SHOPPING|MALL|STORE|RETAIL',
            'medical': r'HOSPITAL|MEDICAL|PHARMACY|APOLLO|DOCTOR|HEALTH|MEDICINE',
            'education': r'SCHOOL|COLLEGE|UNIVERSITY|EDUCATION|COURSE|TRAINING|TUITION',
            'investment': r'MUTUAL\s*FUND|SIP|INSURANCE|INVESTMENT|ZERODHA|GROWW|UPSTOX',
            'transfer': r'TRANSFER|NEFT|RTGS|IMPS|UPI|PAYTM|PHONEPE|GPAY|WALLET',
            'salary': r'SALARY|SAL\s*CREDIT|PAYROLL|WAGES|INCOME',
            'bank_charges': r'CHARGES|FEE|PENALTY|INTEREST|MAINTENANCE|SERVICE',
            'cash_withdrawal': r'ATM\s*WDL|CASH\s*WITHDRAWAL|ATM|WITHDRAWAL',
            'others': r'.*'  # Catch-all pattern
        }
    
    def detect_bank(self, text: str) -> Optional[str]:
        """Detect bank from statement text"""
        text_upper = text.upper()
        for bank, pattern in self.BANK_PATTERNS.items():
            if re.search(pattern['name'], text_upper, re.IGNORECASE):
                logger.info(f"Detected bank: {bank}")
                return bank
        return None
    
    def parse_statement(self, file_path: str) -> Dict:
        """Main method to parse bank statement from various formats"""
        try:
            file_path = Path(file_path)
            extension = file_path.suffix.lower()
            
            logger.info(f"Parsing statement: {file_path.name}")
            
            if extension == '.pdf':
                return self._parse_pdf_statement(file_path)
            elif extension in ['.csv']:
                return self._parse_csv_statement(file_path)
            elif extension in ['.xlsx', '.xls']:
                return self._parse_excel_statement(file_path)
            elif extension in ['.jpg', '.jpeg', '.png', '.tiff']:
                return self._parse_image_statement(file_path)
            else:
                raise ValueError(f"Unsupported file format: {extension}")
                
        except Exception as e:
            logger.error(f"Error parsing statement: {e}")
            return {'error': str(e), 'transactions': []}
    
    def _parse_pdf_statement(self, file_path: Path) -> Dict:
        """Parse PDF bank statement using multiple methods"""
        try:
            # Method 1: Try pdfplumber first
            transactions = self._parse_pdf_with_pdfplumber(file_path)
            if transactions:
                return {'transactions': transactions, 'method': 'pdfplumber'}
            
            # Method 2: Try camelot for table extraction
            transactions = self._parse_pdf_with_camelot(file_path)
            if transactions:
                return {'transactions': transactions, 'method': 'camelot'}
            
            # Method 3: OCR as fallback
            transactions = self._parse_pdf_with_ocr(file_path)
            return {'transactions': transactions, 'method': 'ocr'}
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return {'error': str(e), 'transactions': []}
    
    def _parse_pdf_with_pdfplumber(self, file_path: Path) -> List[Dict]:
        """Parse PDF using pdfplumber"""
        transactions = []
        detected_bank = None
        
        with pdfplumber.open(file_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text
                    
                    # Detect bank from first page
                    if not detected_bank:
                        detected_bank = self.detect_bank(text)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:  # Has header and data
                            transactions.extend(self._process_table_data(table, detected_bank))
        
        # If no tables found, try regex parsing
        if not transactions and full_text:
            transactions = self._parse_text_with_regex(full_text, detected_bank)
        
        return self._clean_and_categorize_transactions(transactions)
    
    def _parse_pdf_with_camelot(self, file_path: Path) -> List[Dict]:
        """Parse PDF using camelot for better table extraction"""
        try:
            # Extract tables from PDF
            tables = camelot.read_pdf(str(file_path), pages='all', flavor='lattice')
            if not tables:
                tables = camelot.read_pdf(str(file_path), pages='all', flavor='stream')
            
            transactions = []
            detected_bank = None
            
            for table in tables:
                df = table.df
                if not df.empty and len(df.columns) >= 4:  # Minimum columns for transaction data
                    # Try to detect bank from table headers or content
                    if not detected_bank:
                        table_text = ' '.join(df.iloc[0].astype(str))
                        detected_bank = self.detect_bank(table_text)
                    
                    # Process table data
                    table_transactions = self._process_dataframe(df, detected_bank)
                    transactions.extend(table_transactions)
            
            return self._clean_and_categorize_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Camelot parsing error: {e}")
            return []
    
    def _parse_pdf_with_ocr(self, file_path: Path) -> List[Dict]:
        """Parse PDF using OCR as fallback"""
        try:
            # Convert PDF to images and OCR
            import fitz  # PyMuPDF
            
            doc = fitz.open(file_path)
            full_text = ""
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                # OCR the image
                text = pytesseract.image_to_string(img)
                full_text += text + "\n"
            
            doc.close()
            
            # Detect bank and parse
            detected_bank = self.detect_bank(full_text)
            transactions = self._parse_text_with_regex(full_text, detected_bank)
            
            return self._clean_and_categorize_transactions(transactions)
            
        except Exception as e:
            logger.error(f"OCR parsing error: {e}")
            return []
    
    def _parse_csv_statement(self, file_path: Path) -> Dict:
        """Parse CSV bank statement"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            df = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if df is None:
                raise ValueError("Could not read CSV file with any encoding")
            
            # Detect bank from column headers or data
            detected_bank = self.detect_bank(' '.join(df.columns.astype(str)))
            
            transactions = self._process_dataframe(df, detected_bank)
            return {
                'transactions': self._clean_and_categorize_transactions(transactions),
                'method': 'csv'
            }
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            return {'error': str(e), 'transactions': []}
    
    def _parse_excel_statement(self, file_path: Path) -> Dict:
        """Parse Excel bank statement"""
        try:
            # Read Excel file
            excel_file = pd.ExcelFile(file_path)
            
            # Try each sheet
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                if len(df) > 0 and len(df.columns) >= 4:
                    # Detect bank
                    detected_bank = self.detect_bank(' '.join(df.columns.astype(str)))
                    
                    transactions = self._process_dataframe(df, detected_bank)
                    if transactions:
                        return {
                            'transactions': self._clean_and_categorize_transactions(transactions),
                            'method': 'excel',
                            'sheet': sheet_name
                        }
            
            return {'error': 'No valid transaction data found in Excel file', 'transactions': []}
            
        except Exception as e:
            logger.error(f"Error parsing Excel: {e}")
            return {'error': str(e), 'transactions': []}
    
    def _parse_image_statement(self, file_path: Path) -> Dict:
        """Parse image bank statement using OCR"""
        try:
            # Load image and OCR
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            
            # Detect bank and parse
            detected_bank = self.detect_bank(text)
            transactions = self._parse_text_with_regex(text, detected_bank)
            
            return {
                'transactions': self._clean_and_categorize_transactions(transactions),
                'method': 'ocr_image'
            }
            
        except Exception as e:
            logger.error(f"Error parsing image: {e}")
            return {'error': str(e), 'transactions': []}
    
    def _process_table_data(self, table: List[List], bank: str) -> List[Dict]:
        """Process table data from PDF"""
        transactions = []
        
        if not table or len(table) < 2:
            return transactions
        
        # Find header row
        header_row = 0
        headers = [str(cell).strip() if cell else '' for cell in table[header_row]]
        
        # Process data rows
        for row_idx, row in enumerate(table[1:], 1):
            if len(row) >= 3:  # Minimum data for transaction
                transaction = self._extract_transaction_from_row(row, headers, bank)
                if transaction:
                    transactions.append(transaction)
        
        return transactions
    
    def _process_dataframe(self, df: pd.DataFrame, bank: str) -> List[Dict]:
        """Process pandas DataFrame"""
        transactions = []
        
        # Clean column names
        df.columns = [str(col).strip() for col in df.columns]
        
        # Skip empty rows
        df = df.dropna(how='all')
        
        for _, row in df.iterrows():
            transaction = self._extract_transaction_from_series(row, bank)
            if transaction:
                transactions.append(transaction)
        
        return transactions
    
    def _extract_transaction_from_row(self, row: List, headers: List[str], bank: str) -> Optional[Dict]:
        """Extract transaction from table row"""
        try:
            # Create row dict
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_dict[header] = str(row[i]).strip() if row[i] else ''
            
            return self._extract_transaction_from_dict(row_dict, bank)
            
        except Exception as e:
            logger.error(f"Error extracting transaction from row: {e}")
            return None
    
    def _extract_transaction_from_series(self, row: pd.Series, bank: str) -> Optional[Dict]:
        """Extract transaction from pandas Series"""
        try:
            row_dict = row.to_dict()
            return self._extract_transaction_from_dict(row_dict, bank)
            
        except Exception as e:
            logger.error(f"Error extracting transaction from series: {e}")
            return None
    
    def _extract_transaction_from_dict(self, row_dict: Dict, bank: str) -> Optional[Dict]:
        """Extract transaction from dictionary"""
        try:
            # Find date column
            date_value = None
            date_patterns = ['date', 'txn date', 'transaction date', 'value date']
            
            for pattern in date_patterns:
                for key, value in row_dict.items():
                    if pattern in key.lower() and value:
                        date_value = self._parse_date(str(value))
                        break
                if date_value:
                    break
            
            if not date_value:
                return None
            
            # Find description
            description = ""
            desc_patterns = ['description', 'particulars', 'narration', 'details']
            for pattern in desc_patterns:
                for key, value in row_dict.items():
                    if pattern in key.lower() and value:
                        description = str(value).strip()
                        break
                if description:
                    break
            
            # Find amounts (debit/credit or withdrawal/deposit)
            debit = self._extract_amount(row_dict, ['debit', 'withdrawal', 'dr'])
            credit = self._extract_amount(row_dict, ['credit', 'deposit', 'cr'])
            
            # Determine transaction type and amount
            if credit and credit > 0:
                transaction_type = 'credit'
                amount = credit
            elif debit and debit > 0:
                transaction_type = 'debit'
                amount = debit
            else:
                return None
            
            return {
                'date': date_value,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                'bank': bank,
                'raw_data': row_dict
            }
            
        except Exception as e:
            logger.error(f"Error extracting transaction from dict: {e}")
            return None
    
    def _extract_amount(self, row_dict: Dict, patterns: List[str]) -> Optional[float]:
        """Extract amount from row dictionary"""
        for pattern in patterns:
            for key, value in row_dict.items():
                if pattern in key.lower() and value:
                    try:
                        # Clean amount string
                        amount_str = str(value).replace(',', '').replace('₹', '').replace('-', '').strip()
                        if amount_str and amount_str.replace('.', '').isdigit():
                            return float(amount_str)
                    except (ValueError, TypeError):
                        continue
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from string"""
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d',
            '%d %b %Y', '%d-%b-%Y', '%d/%m/%y',
            '%m/%d/%Y', '%Y/%m/%d'
        ]
        
        date_str = date_str.strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _parse_text_with_regex(self, text: str, bank: str) -> List[Dict]:
        """Parse text using regex patterns"""
        transactions = []
        
        # Split text into lines and process
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for transaction patterns
            # Date pattern
            date_match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', line)
            if not date_match:
                continue
            
            date_str = date_match.group()
            date_obj = self._parse_date(date_str)
            
            if not date_obj:
                continue
            
            # Amount pattern
            amount_matches = re.findall(r'[₹\s]*[\d,]+\.?\d*', line)
            amounts = []
            
            for match in amount_matches:
                try:
                    clean_amount = match.replace(',', '').replace('₹', '').strip()
                    if clean_amount.replace('.', '').isdigit():
                        amounts.append(float(clean_amount))
                except ValueError:
                    continue
            
            if amounts:
                # Determine if debit or credit based on context
                transaction_type = 'debit'  # Default
                if any(word in line.upper() for word in ['CREDIT', 'DEPOSIT', 'CR']):
                    transaction_type = 'credit'
                
                transactions.append({
                    'date': date_obj,
                    'description': line,
                    'amount': max(amounts),  # Take largest amount
                    'type': transaction_type,
                    'bank': bank
                })
        
        return transactions
    
    def _clean_and_categorize_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Clean and categorize transactions"""
        cleaned_transactions = []
        
        for transaction in transactions:
            if not transaction or not transaction.get('date') or not transaction.get('amount'):
                continue
            
            # Auto-categorize based on description
            category = self._categorize_transaction(transaction['description'])
            transaction['category'] = category
            
            # Add additional fields
            transaction['month'] = transaction['date'].strftime('%Y-%m')
            transaction['formatted_date'] = transaction['date'].strftime('%d/%m/%Y')
            transaction['formatted_amount'] = f"₹{transaction['amount']:,.2f}"
            
            cleaned_transactions.append(transaction)
        
        # Sort by date
        cleaned_transactions.sort(key=lambda x: x['date'], reverse=True)
        
        return cleaned_transactions
    
    def _categorize_transaction(self, description: str) -> str:
        """Auto-categorize transaction based on description"""
        description_upper = description.upper()
        
        for category, pattern in self.CATEGORY_PATTERNS.items():
            if re.search(pattern, description_upper):
                return category
        
        return 'others'
    
    def get_statement_summary(self, transactions: List[Dict]) -> Dict:
        """Generate summary of parsed statement"""
        if not transactions:
            return {'error': 'No transactions found'}
        
        total_credits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        # Category-wise breakdown
        category_breakdown = {}
        for transaction in transactions:
            category = transaction.get('category', 'others')
            if category not in category_breakdown:
                category_breakdown[category] = {'count': 0, 'amount': 0}
            category_breakdown[category]['count'] += 1
            category_breakdown[category]['amount'] += transaction['amount']
        
        return {
            'total_transactions': len(transactions),
            'total_credits': total_credits,
            'total_debits': total_debits,
            'net_amount': total_credits - total_debits,
            'date_range': {
                'start': min(t['date'] for t in transactions).strftime('%d/%m/%Y'),
                'end': max(t['date'] for t in transactions).strftime('%d/%m/%Y')
            },
            'category_breakdown': category_breakdown,
            'banks': list(set(t.get('bank', 'Unknown') for t in transactions))
        }
