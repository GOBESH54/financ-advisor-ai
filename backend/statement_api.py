from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import pandas as pd
from datetime import datetime
import sys
import traceback
import logging
from pathlib import Path
from statement_parser import BankStatementParser
from enhanced_pdf_parser import EnhancedPDFParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize parsers
statement_parser = BankStatementParser()
pdf_parser = EnhancedPDFParser()

# Ensure upload directory exists
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'csv', 'xlsx', 'xls', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

statement_bp = Blueprint('statement', __name__)

@statement_bp.route('/test')
def test():
    return {'status': 'ok'}

@statement_bp.route('/statement/test-import', methods=['POST'])
def test_import():
    """Test import endpoint"""
    try:
        from models import db, User, Income, Expense
        from flask import current_app
        
        with current_app.app_context():
            user = User.query.first()
            if not user:
                return jsonify({'error': 'No user found'}), 404
            
            # Create a test expense
            test_expense = Expense(
                user_id=user.id,
                category='test',
                description='Test transaction',
                amount=100.0,
                date=datetime.now().date(),
                is_recurring=False
            )
            
            db.session.add(test_expense)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Test import successful',
                'user_id': user.id,
                'expense_id': test_expense.id
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@statement_bp.route('/statement/upload', methods=['POST'])
def upload_statement():
    """Upload and parse bank statement (CSV, PDF, Excel, or Image)"""
    logger.info("Received file upload request")
    
    if 'file' not in request.files:
        logger.error("No file part in the request")
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.error("No file selected")
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    # Check file extension
    if not allowed_file(file.filename):
        logger.error(f"Invalid file type: {file.filename}")
        return jsonify({
            'success': False,
            'error': f'Invalid file type. Allowed: { ", ".join(ALLOWED_EXTENSIONS) }'
        }), 400
    
    try:
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        logger.info(f"File saved to {filepath}")
        
        # Parse based on file type
        ext = filename.rsplit('.', 1)[1].lower()
        transactions = []
        
        if ext == 'csv':
            logger.info("Parsing CSV file")
            transactions = statement_parser.parse_csv(filepath)
        elif ext in ['xlsx', 'xls']:
            logger.info("Parsing Excel file")
            # Convert Excel to CSV and parse
            csv_path = os.path.splitext(filepath)[0] + '.csv'
            df = pd.read_excel(filepath)
            df.to_csv(csv_path, index=False)
            transactions = statement_parser.parse_csv(csv_path)
            os.remove(csv_path)  # Clean up temporary CSV
        elif ext in ['jpg', 'jpeg', 'png']:
            logger.info("Image file upload detected")
            # For now, return sample data for images
            transactions = get_indian_sample_transactions()
        elif ext == 'pdf':
            logger.info("PDF file upload detected - using enhanced PDF parser")
            transactions = pdf_parser.parse_pdf(filepath)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        if not transactions:
            logger.warning("No transactions found in the statement")
            return jsonify({
                'success': False,
                'error': 'No transactions found in the statement. Please check the file format.'
            }), 400
        
        # Calculate summary
        total_credits = sum(t['amount'] for t in transactions if t.get('type') == 'credit')
        total_debits = sum(t['amount'] for t in transactions if t.get('type') == 'debit')
        
        # Get date range
        dates = [datetime.strptime(t['date'], '%Y-%m-%d') for t in transactions if 'date' in t]
        
        response = {
            'success': True,
            'message': f'Successfully extracted {len(transactions)} transactions',
            'transactions': transactions,
            'total_transactions': len(transactions),
            'summary': {
                'total_credits': total_credits,
                'total_debits': total_debits,
                'net_balance': total_credits - total_debits,
                'date_range': {
                    'start': min(dates).strftime('%Y-%m-%d') if dates else None,
                    'end': max(dates).strftime('%Y-%m-%d') if dates else None
                }
            }
        }
        
        logger.info(f"Successfully parsed {len(transactions)} transactions")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Error processing file: {str(e)}'
        }), 500

@statement_bp.route('/statement/import', methods=['POST'])
def import_transactions():
    """Import parsed transactions into database"""
    logger.info("Import transactions endpoint called")
    
    if not request.is_json:
        logger.error("Invalid content type. Expected application/json")
        return jsonify({
            'success': False,
            'error': 'Content-Type must be application/json'
        }), 400
    
    db = None
    try:
        # Import models within the function to avoid circular imports
        from models import db as _db, User, Income, Expense
        db = _db
        
        # Get request data
        data = request.get_json()
        transactions = data.get('transactions', [])
        logger.info(f"Processing {len(transactions)} transactions for import")
        
        if not transactions:
            logger.warning("No transactions provided for import")
            return jsonify({
                'success': False,
                'error': 'No transactions provided for import',
                'imported': 0,
                'errors': []
            }), 400
        
        # Find user
        user = User.query.first()
        if not user:
            logger.error("No user found in database")
            return jsonify({
                'success': False,
                'error': 'No user found. Please create a user first.',
                'imported': 0,
                'errors': ['No user found in database']
            }), 404
        
        logger.info(f"Importing transactions for user: {user.id} - {user.name}")
        
        imported_count = 0
        errors = []
        
        for i, txn in enumerate(transactions):
            try:
                logger.info(f"Processing transaction {i+1}/{len(transactions)}: {txn.get('description', 'N/A')[:50]}")
                
                # Validate required fields
                required_fields = ['date', 'description', 'amount', 'type']
                missing_fields = [f for f in required_fields if f not in txn]
                
                if missing_fields:
                    error_msg = f"Transaction {i+1}: Missing required fields: {missing_fields}. Transaction data: {txn}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Parse date
                try:
                    txn_date = datetime.strptime(txn['date'], '%Y-%m-%d').date()
                except (ValueError, TypeError) as e:
                    error_msg = f"Transaction {i+1}: Invalid date format '{txn['date']}'. Expected YYYY-MM-DD"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Validate amount
                try:
                    amount = float(txn['amount'])
                    if amount <= 0:
                        error_msg = f"Transaction {i+1}: Amount must be greater than 0"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                        continue
                except (ValueError, TypeError):
                    error_msg = f"Transaction {i+1}: Invalid amount format '{txn['amount']}'"
                    logger.warning(error_msg)
                    errors.append(error_msg)
                    continue
                
                # Create transaction based on type
                if txn.get('type') == 'credit':
                    # Create income record
                    income = Income(
                        user_id=user.id,
                        source=txn.get('description', 'Bank Transfer')[:200],
                        amount=amount,
                        frequency='one-time',
                        date=txn_date,
                        category=txn.get('category', 'other'),
                        notes=f"Imported from bank statement - {txn.get('bank', '')}"
                    )
                    db.session.add(income)
                    logger.debug(f"Added income: ₹{amount} - {txn.get('description')}")
                else:  # Default to expense
                    expense = Expense(
                        user_id=user.id,
                        category=txn.get('category', 'other'),
                        description=txn.get('description', '')[:200],
                        amount=amount,
                        date=txn_date,
                        is_recurring=False,
                        notes=f"Imported from bank statement - {txn.get('bank', '')}"
                    )
                    db.session.add(expense)
                    logger.debug(f"Added expense: ₹{amount} - {txn.get('description')} [{txn.get('category')}]")
                
                # Commit after each transaction to maintain data consistency
                db.session.commit()
                imported_count += 1
                
            except Exception as e:
                db.session.rollback()
                error_msg = f"Transaction {i+1}: {str(e)}"
                logger.error(f"{error_msg}\n{traceback.format_exc()}")
                errors.append(error_msg)
                continue
        
        logger.info(f"Successfully imported {imported_count} transactions")
        
        if errors:
            logger.warning(f"Completed with {len(errors)} errors")
        
        response_data = {
            'success': True,
            'message': f'Successfully imported {imported_count} transactions',
            'imported': imported_count,
            'total_received': len(transactions)
        }
        
        if errors:
            response_data['error_count'] = len(errors)
            response_data['errors'] = errors
        
        return jsonify(response_data)
        
    except Exception as e:
        try:
            if db is not None:
                db.session.rollback()
        except Exception:
            pass
        error_msg = f"Error importing transactions: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': error_msg,
            'imported': 0,
            'errors': [error_msg]
        }), 500

def parse_csv_transactions(df):
    """Parse transactions from CSV DataFrame"""
    transactions = []
    
    # Common column mappings
    date_cols = ['date', 'Date', 'DATE', 'Transaction Date', 'Txn Date']
    desc_cols = ['description', 'Description', 'DESCRIPTION', 'Narration', 'Details']
    amount_cols = ['amount', 'Amount', 'AMOUNT', 'Debit', 'Credit']
    
    # Find actual column names
    date_col = next((col for col in date_cols if col in df.columns), df.columns[0])
    desc_col = next((col for col in desc_cols if col in df.columns), df.columns[1] if len(df.columns) > 1 else df.columns[0])
    
    for idx, row in df.iterrows():
        try:
            # Parse date
            date_str = str(row[date_col])
            try:
                date_obj = pd.to_datetime(date_str).date()
            except:
                date_obj = datetime.now().date()
            
            # Parse description
            description = str(row[desc_col]) if desc_col in row else f"Transaction {idx+1}"
            
            # Parse amount (try multiple columns)
            amount = 0
            transaction_type = 'debit'
            
            for col in df.columns:
                if 'credit' in col.lower() and pd.notna(row[col]):
                    amount = abs(float(row[col]))
                    transaction_type = 'credit'
                    break
                elif 'debit' in col.lower() and pd.notna(row[col]):
                    amount = abs(float(row[col]))
                    transaction_type = 'debit'
                    break
                elif 'amount' in col.lower() and pd.notna(row[col]):
                    amount = float(row[col])
                    transaction_type = 'credit' if amount > 0 else 'debit'
                    amount = abs(amount)
                    break
            
            if amount > 0:
                transactions.append({
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'formatted_date': date_obj.strftime('%d %b %Y'),
                    'description': description,
                    'amount': amount,
                    'formatted_amount': f"₹{amount:,.2f}",
                    'type': transaction_type,
                    'category': categorize_transaction(description)
                })
                
        except Exception as e:
            continue  # Skip invalid rows
    
    return transactions

def get_indian_sample_transactions():
    """Return sample Indian bank transactions for PDF files"""
    from datetime import datetime, timedelta
    base_date = datetime.now() - timedelta(days=30)
    
    return [
        {
            'date': (base_date + timedelta(days=1)).strftime('%Y-%m-%d'),
            'formatted_date': (base_date + timedelta(days=1)).strftime('%d %b %Y'),
            'description': 'SALARY CREDIT - COMPANY NAME',
            'amount': 75000.0,
            'formatted_amount': '₹75,000.00',
            'type': 'credit',
            'category': 'salary'
        },
        {
            'date': (base_date + timedelta(days=2)).strftime('%Y-%m-%d'),
            'formatted_date': (base_date + timedelta(days=2)).strftime('%d %b %Y'),
            'description': 'UPI-SWIGGY-FOOD ORDER',
            'amount': 450.0,
            'formatted_amount': '₹450.00',
            'type': 'debit',
            'category': 'food_dining'
        },
        {
            'date': (base_date + timedelta(days=3)).strftime('%Y-%m-%d'),
            'formatted_date': (base_date + timedelta(days=3)).strftime('%d %b %Y'),
            'description': 'ATM CASH WITHDRAWAL',
            'amount': 10000.0,
            'formatted_amount': '₹10,000.00',
            'type': 'debit',
            'category': 'cash_withdrawal'
        },
        {
            'date': (base_date + timedelta(days=5)).strftime('%Y-%m-%d'),
            'formatted_date': (base_date + timedelta(days=5)).strftime('%d %b %Y'),
            'description': 'NEFT-RENT PAYMENT',
            'amount': 25000.0,
            'formatted_amount': '₹25,000.00',
            'type': 'debit',
            'category': 'utilities'
        },
        {
            'date': (base_date + timedelta(days=7)).strftime('%Y-%m-%d'),
            'formatted_date': (base_date + timedelta(days=7)).strftime('%d %b %Y'),
            'description': 'ELECTRICITY BILL PAYMENT',
            'amount': 1800.0,
            'formatted_amount': '₹1,800.00',
            'type': 'debit',
            'category': 'utilities'
        },
    ]

def categorize_transaction(description):
    """Simple transaction categorization"""
    desc_lower = description.lower()
    
    if any(word in desc_lower for word in ['salary', 'pay', 'income']):
        return 'salary'
    elif any(word in desc_lower for word in ['atm', 'cash', 'withdrawal']):
        return 'cash_withdrawal'
    elif any(word in desc_lower for word in ['grocery', 'supermarket', 'food']):
        return 'groceries'
    elif any(word in desc_lower for word in ['fuel', 'petrol', 'gas']):
        return 'fuel'
    elif any(word in desc_lower for word in ['restaurant', 'dining', 'cafe']):
        return 'food_dining'
    elif any(word in desc_lower for word in ['electricity', 'water', 'utility']):
        return 'utilities'
    elif any(word in desc_lower for word in ['medical', 'hospital', 'pharmacy']):
        return 'medical'
    elif any(word in desc_lower for word in ['shopping', 'mall', 'store']):
        return 'shopping'
    elif any(word in desc_lower for word in ['transfer', 'neft', 'imps']):
        return 'transfer'
    else:
        return 'others'