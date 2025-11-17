"""
Free PDF Parser for Bank Statements
Uses Tesseract OCR + Regex for offline PDF parsing
"""

import re
import logging
import tempfile
import io
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Check for required libraries
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    import numpy as np
    
    TESSERACT_AVAILABLE = True
except ImportError:
    logger.warning("Tesseract OCR not available. Install with: pip install pytesseract pdf2image pillow numpy")
    TESSERACT_AVAILABLE = False

class FreePDFParser:
    """Free PDF parser using Tesseract OCR and regex"""
    
    def __init__(self):
        """Initialize the free PDF parser"""
        self.date_patterns = [
            # Indian format: DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
            r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})',
            # Text month: 10 Oct 2025 or 10-Oct-2025
            r'(\d{1,2})[- ](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[- ](\d{4})',
            # YYYY/MM/DD
            r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
        ]
        
        # Common bank keywords for transaction lines
        self.bank_keywords = [
            'UPI', 'NEFT', 'IMPS', 'RTGS', 'ATM', 'CASH', 'TRF', 'TRANSFER',
            'CREDIT', 'DEBIT', 'BAL', 'B/F', 'BALANCE', 'WITHDRAWAL', 'DEPOSIT'
        ]
        
        # Common transaction descriptions
        self.txn_keywords = {
            'UPI': 'UPI',
            'NEFT': 'NEFT',
            'IMPS': 'IMPS',
            'RTGS': 'RTGS',
            'ATM': 'ATM',
            'CASH': 'Cash',
            'SALARY': 'Salary',
            'REFUND': 'Refund',
            'INTEREST': 'Interest',
            'BILL': 'Bill Payment',
            'RENT': 'Rent',
            'GROCERY': 'Grocery',
            'FUEL': 'Fuel',
            'MEDICAL': 'Medical',
            'SHOPPING': 'Shopping'
        }
        
        # Compile regex patterns
        self.amount_pattern = re.compile(r'[₹$]?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        self.clean_pattern = re.compile(r'\s+')
        
        # Check Tesseract installation
        self.tesseract_installed = self._check_tesseract()
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is installed and accessible"""
        if not TESSERACT_AVAILABLE:
            return False
            
        try:
            # Try to get Tesseract version
            pytesseract.get_tesseract_version()
            return True
        except (pytesseract.TesseractNotFoundError, Exception) as e:
            logger.warning(f"Tesseract not found: {e}")
            return False
    
    def _extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using Tesseract OCR"""
        if not self.tesseract_installed:
            logger.error("Tesseract not available for PDF text extraction")
            return ""
            
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            # Extract text from each page
            full_text = []
            for i, image in enumerate(images):
                # Convert to grayscale for better OCR
                image = image.convert('L')
                
                # Use Tesseract to do OCR on the image
                text = pytesseract.image_to_string(image, lang='eng')
                full_text.append(text)
                
                # Clean up
                del image
                
            return '\n'.join(full_text)
            
        except Exception as e:
            logger.error(f"Error extracting text with Tesseract: {e}")
            return ""
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str or not date_str.strip():
            return None
            
        date_str = date_str.strip()
        
        # Try different date formats
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',  # DD/MM/YYYY
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',  # DD/MM/YY
            '%Y/%m/%d', '%Y-%m-%d',              # YYYY/MM/DD
            '%d %b %Y', '%d-%b-%Y',              # 10 Oct 2025
            '%b %d, %Y', '%B %d, %Y'             # Oct 10, 2025
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
                
        return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
            
        # Replace multiple spaces with single space
        text = self.clean_pattern.sub(' ', text)
        
        # Remove special characters except basic punctuation
        text = re.sub(r'[^\w\s.,₹$/-]', ' ', text)
        
        return text.strip()
    
    def _extract_transaction_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Extract transaction from a single line of text"""
        if not line or len(line.strip()) < 10:  # Skip very short lines
            return None
            
        # Clean the line
        line = self._clean_text(line)
        
        # Skip lines that don't look like transactions
        if not any(keyword in line.upper() for keyword in self.bank_keywords):
            return None
        
        # Try to find a date in the line
        date_match = None
        for pattern in self.date_patterns:
            match = re.search(pattern, line)
            if match:
                date_match = match.group(0)
                # Remove date from line for further processing
                line = line.replace(date_match, '').strip()
                break
        
        # If no date found, skip this line
        if not date_match:
            return None
            
        # Parse the date
        date_str = self._parse_date(date_match)
        if not date_str:
            return None
        
        # Extract amount (look for the last number in the line)
        amounts = self.amount_pattern.findall(line)
        if not amounts:
            return None
            
        # Get the last amount (usually the transaction amount)
        amount_str = amounts[-1].replace(',', '')
        
        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            return None
            
        # Determine transaction type (credit/debit)
        txn_type = 'debit'  # Default to debit
        line_upper = line.upper()
        
        # Check for credit indicators
        if any(word in line_upper for word in ['CREDIT', 'CR', 'DEPOSIT', 'CREDITED']):
            txn_type = 'credit'
        # Check for debit indicators
        elif any(word in line_upper for word in ['DEBIT', 'DR', 'WITHDRAWAL', 'DEBITED']):
            txn_type = 'debit'
        
        # If amount is in description, remove it
        for amt in amounts:
            line = line.replace(amt, '').strip()
        
        # Clean up description
        description = line.strip()
        if not description:
            description = 'Bank Transaction'
        
        # Categorize transaction
        category = self._categorize_transaction(description)
        
        # Format amount with 2 decimal places
        formatted_amount = f"₹{amount:,.2f}"
        
        # Format date for display
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d %b %Y')
        except:
            formatted_date = date_str
        
        return {
            'date': date_str,
            'formatted_date': formatted_date,
            'description': description[:200],
            'amount': amount,
            'formatted_amount': formatted_amount,
            'type': txn_type,
            'category': category,
            'bank': 'Extracted by OCR'
        }
    
    def _categorize_transaction(self, description: str) -> str:
        """Categorize transaction based on description"""
        if not description:
            return 'others'
            
        desc_upper = description.upper()
        
        # Check for common transaction types
        if any(word in desc_upper for word in ['SALARY', 'PAYMENT RECEIVED', 'CREDIT']):
            return 'salary'
        elif 'UPI' in desc_upper:
            if any(word in desc_upper for word in ['FOOD', 'SWIGGY', 'ZOMATO', 'EAT']):
                return 'food_dining'
            return 'transfer'
        elif any(word in desc_upper for word in ['NEFT', 'IMPS', 'RTGS']):
            return 'transfer'
        elif 'ATM' in desc_upper or 'CASH' in desc_upper:
            return 'cash_withdrawal'
        elif any(word in desc_upper for word in ['GROCERY', 'SUPERMARKET', 'BIGBAZAAR']):
            return 'groceries'
        elif any(word in desc_upper for word in ['FUEL', 'PETROL', 'DIESEL', 'BPCL', 'HPCL', 'IOCL']):
            return 'fuel'
        elif any(word in desc_upper for word in ['ELECTRICITY', 'WATER', 'GAS', 'BILL', 'RENT']):
            return 'utilities'
        elif any(word in desc_upper for word in ['MEDICAL', 'HOSPITAL', 'PHARMACY']):
            return 'medical'
        elif any(word in desc_upper for word in ['SHOPPING', 'AMAZON', 'FLIPKART', 'MYNTRA']):
            return 'shopping'
        else:
            return 'others'
    
    def parse_pdf(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parse bank statement PDF and extract transactions
        
        Args:
            filepath: Path to the PDF file
            
        Returns:
            List of transaction dictionaries
        """
        if not self.tesseract_installed:
            logger.error("Tesseract OCR is not available")
            return []
            
        try:
            logger.info(f"Extracting text from PDF using Tesseract: {filepath}")
            
            # Extract text from PDF
            text = self._extract_text_from_pdf(filepath)
            
            if not text or len(text.strip()) < 100:  # At least 100 chars to be useful
                logger.warning("Insufficient text extracted from PDF")
                return []
                
            logger.info(f"Extracted {len(text)} characters from PDF")
            
            # Split into lines and process each line
            lines = text.split('\n')
            transactions = []
            
            for line in lines:
                try:
                    txn = self._extract_transaction_line(line)
                    if txn:
                        transactions.append(txn)
                except Exception as e:
                    logger.warning(f"Error processing line: {e}")
                    continue
            
            logger.info(f"Extracted {len(transactions)} transactions from PDF")
            return transactions
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            return []


def parse_with_free_ocr(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Convenience function to parse PDF using free OCR
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        List of transaction dictionaries
    """
    if not TESSERACT_AVAILABLE:
        logger.error("Tesseract OCR not available. Install with: pip install pytesseract pdf2image")
        return []
        
    parser = FreePDFParser()
    return parser.parse_pdf(pdf_path)
