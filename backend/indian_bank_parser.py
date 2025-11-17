"""
Specialized parser for Indian Bank statements
Handles the specific format used by Indian Bank
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class IndianBankParser:
    """Parser specifically for Indian Bank statement format"""
    
    def __init__(self):
        self.date_pattern = r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})'
        
    def parse_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse Indian Bank statement text"""
        transactions = []
        
        # Split into lines
        lines = text.split('\n')
        
        # Find the start of transaction data (after "ACCOUNT ACTIVITY")
        in_transactions = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if 'ACCOUNT ACTIVITY' in line.upper():
                in_transactions = True
                continue
            
            if not in_transactions or not line:
                continue
            
            # Skip header line
            if 'Date' in line and 'Transaction Details' in line:
                continue
            
            # Try to parse transaction
            transaction = self._parse_transaction_line(line, lines, i)
            if transaction:
                transactions.append(transaction)
        
        logger.info(f"Indian Bank Parser: Extracted {len(transactions)} transactions")
        return transactions
    
    def _parse_transaction_line(self, line: str, all_lines: List[str], line_idx: int) -> Dict[str, Any]:
        """Parse a single transaction line"""
        
        # Extract date
        date_match = re.search(self.date_pattern, line)
        if not date_match:
            return None
        
        date_str = date_match.group(1)
        
        try:
            date_obj = datetime.strptime(date_str, '%d %b %Y')
        except:
            return None
        
        # Extract amounts (look for INR followed by numbers)
        amounts = []
        inr_pattern = r'INR\s+([\d,]+\.?\d*)'
        for match in re.finditer(inr_pattern, line):
            try:
                amount = float(match.group(1).replace(',', ''))
                if amount > 0:
                    amounts.append(amount)
            except:
                continue
        
        if not amounts:
            return None
        
        # Determine transaction type
        # In Indian Bank format: Date | Description | Debits | Credits | Balance
        # Look for the "-" or "+" signs or position
        is_credit = False
        is_debit = False
        
        # Split by INR to analyze structure
        parts = re.split(r'INR', line)
        
        # If we have 3 INR amounts: Debit, Credit, Balance
        if len(amounts) == 3:
            debit_amount = amounts[0]
            credit_amount = amounts[1]
            
            if debit_amount > 0 and credit_amount == 0:
                is_debit = True
                transaction_amount = debit_amount
            elif credit_amount > 0 and debit_amount == 0:
                is_credit = True
                transaction_amount = credit_amount
            else:
                # Use the non-zero one
                transaction_amount = debit_amount if debit_amount > 0 else credit_amount
                is_debit = debit_amount > 0
                is_credit = credit_amount > 0
        
        # If we have 2 INR amounts: Transaction and Balance
        elif len(amounts) == 2:
            transaction_amount = amounts[0]
            # Check if there's a "-" before the first INR (indicates debit)
            first_inr_pos = line.find('INR')
            before_inr = line[:first_inr_pos]
            
            if '-' in before_inr:
                is_debit = True
            elif '+' in before_inr:
                is_credit = True
            else:
                # Look at the description for clues
                desc_lower = line.lower()
                if any(word in desc_lower for word in ['upi', 'payment', 'debit', 'withdrawal']):
                    is_debit = True
                else:
                    is_credit = True
        
        # If only 1 amount, it's likely the balance - skip
        elif len(amounts) == 1:
            return None
        else:
            transaction_amount = amounts[0]
            is_debit = True  # Default
        
        # Extract description (everything between date and first INR)
        desc_start = date_match.end()
        first_inr_pos = line.find('INR', desc_start)
        
        if first_inr_pos > desc_start:
            description = line[desc_start:first_inr_pos].strip()
        else:
            description = "Transaction"
        
        # Clean up description
        description = re.sub(r'[-+\s]+$', '', description).strip()
        
        if not description or len(description) < 3:
            description = "Bank Transaction"
        
        # Categorize
        category = self._categorize(description)
        
        txn_type = 'credit' if is_credit else 'debit'
        
        return {
            'date': date_obj.strftime('%Y-%m-%d'),
            'formatted_date': date_obj.strftime('%d %b %Y'),
            'description': description[:200],
            'amount': transaction_amount,
            'formatted_amount': f"₹{transaction_amount:,.2f}",
            'type': txn_type,
            'category': category,
            'bank': 'Indian Bank'
        }
    
    def _categorize(self, description: str) -> str:
        """Categorize transaction based on description"""
        desc_lower = description.lower()
        
        # UPI transactions
        if 'upi' in desc_lower:
            if any(word in desc_lower for word in ['swiggy', 'zomato', 'food']):
                return 'food_dining'
            elif any(word in desc_lower for word in ['amazon', 'flipkart', 'shopping']):
                return 'shopping'
            else:
                return 'transfer'
        
        # Common categories
        if any(word in desc_lower for word in ['salary', 'pay', 'income']):
            return 'salary'
        elif any(word in desc_lower for word in ['atm', 'cash', 'withdrawal']):
            return 'cash_withdrawal'
        elif any(word in desc_lower for word in ['grocery', 'supermarket']):
            return 'groceries'
        elif any(word in desc_lower for word in ['fuel', 'petrol', 'gas']):
            return 'fuel'
        elif any(word in desc_lower for word in ['electricity', 'water', 'utility', 'bill', 'rent']):
            return 'utilities'
        elif any(word in desc_lower for word in ['medical', 'hospital', 'pharmacy']):
            return 'medical'
        elif any(word in desc_lower for word in ['transfer', 'neft', 'imps', 'rtgs']):
            return 'transfer'
        else:
            return 'others'
