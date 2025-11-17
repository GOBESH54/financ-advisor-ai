"""
Gemini AI-powered PDF parser for complex bank statements
Uses Google's Gemini API to extract transaction data from PDFs
"""

import os
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    logger.warning("Google Generative AI not available. Install with: pip install google-generativeai")
    GEMINI_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class GeminiPDFParser:
    """AI-powered PDF parser using Google Gemini"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini parser
        
        Args:
            api_key: Google Gemini API key. If None, reads from environment variable GEMINI_API_KEY
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = None
        
        if GEMINI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                logger.info("✅ Gemini AI parser initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.model = None
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("Gemini AI not available - install google-generativeai")
            if not self.api_key:
                logger.warning("No Gemini API key found. Set GEMINI_API_KEY environment variable")
    
    def is_available(self) -> bool:
        """Check if Gemini parser is available"""
        return self.model is not None
    
    def parse_pdf(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parse bank statement PDF using Gemini AI
        
        Args:
            filepath: Path to PDF file
            
        Returns:
            List of transaction dictionaries
        """
        if not self.is_available():
            logger.warning("Gemini parser not available")
            return []
        
        try:
            logger.info(f"Using Gemini AI to parse PDF: {filepath}")
            
            # Extract text from PDF
            text = self._extract_text_from_pdf(filepath)
            
            if not text or len(text.strip()) < 50:
                logger.warning("Insufficient text extracted from PDF")
                return []
            
            # Use Gemini to extract transactions
            transactions = self._extract_with_gemini(text)
            
            logger.info(f"Gemini extracted {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error in Gemini PDF parsing: {e}")
            return []
    
    def _extract_text_from_pdf(self, filepath: str) -> str:
        """Extract text from PDF file"""
        if not PDF_AVAILABLE:
            return ""
        
        text = ""
        try:
            with open(filepath, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
        
        return text
    
    def _extract_with_gemini(self, text: str) -> List[Dict[str, Any]]:
        """Use Gemini AI to extract transaction data"""
        
        prompt = f"""
You are a bank statement parser. Extract ALL transactions from the following bank statement text.

For each transaction, extract:
1. Date (convert to YYYY-MM-DD format)
2. Description (the transaction details/narration)
3. Amount (as a positive number)
4. Type (either "credit" or "debit")
5. Category (choose from: salary, groceries, fuel, food_dining, utilities, medical, shopping, transfer, cash_withdrawal, loan, others)

IMPORTANT RULES:
- Extract EVERY transaction you find
- If amount appears in "Debit" column, type is "debit"
- If amount appears in "Credit" column, type is "credit"
- Balance amounts are NOT transactions - ignore them
- UPI transactions are usually "transfer" category
- Salary/income is "salary" category
- ATM withdrawals are "cash_withdrawal" category

Return ONLY a valid JSON array with this exact structure (no markdown, no explanation):
[
  {{
    "date": "YYYY-MM-DD",
    "description": "transaction description",
    "amount": 1234.56,
    "type": "credit",
    "category": "salary"
  }}
]

Bank Statement Text:
{text}

JSON Array:"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                # Remove ```json or ``` at start
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
                # Remove ``` at end
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse JSON
            transactions_raw = json.loads(response_text)
            
            # Validate and format transactions
            transactions = []
            for txn in transactions_raw:
                try:
                    # Validate required fields
                    if not all(k in txn for k in ['date', 'description', 'amount', 'type']):
                        logger.warning(f"Skipping transaction with missing fields: {txn}")
                        continue
                    
                    # Parse and validate date
                    try:
                        date_obj = datetime.strptime(txn['date'], '%Y-%m-%d')
                    except:
                        logger.warning(f"Invalid date format: {txn['date']}")
                        continue
                    
                    # Validate amount
                    try:
                        amount = float(txn['amount'])
                        if amount <= 0:
                            logger.warning(f"Invalid amount: {amount}")
                            continue
                    except:
                        logger.warning(f"Invalid amount format: {txn['amount']}")
                        continue
                    
                    # Validate type
                    if txn['type'] not in ['credit', 'debit']:
                        logger.warning(f"Invalid type: {txn['type']}")
                        continue
                    
                    # Format transaction
                    formatted_txn = {
                        'date': date_obj.strftime('%Y-%m-%d'),
                        'formatted_date': date_obj.strftime('%d %b %Y'),
                        'description': str(txn['description'])[:200],
                        'amount': amount,
                        'formatted_amount': f"₹{amount:,.2f}",
                        'type': txn['type'],
                        'category': txn.get('category', 'others'),
                        'bank': 'Extracted by AI'
                    }
                    
                    transactions.append(formatted_txn)
                    
                except Exception as e:
                    logger.warning(f"Error processing transaction: {e}")
                    continue
            
            return transactions
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")
            return []
    
    def parse_with_image(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parse bank statement PDF by sending it as an image to Gemini Vision
        This is more accurate for complex PDFs with tables
        
        Args:
            filepath: Path to PDF file
            
        Returns:
            List of transaction dictionaries
        """
        if not self.is_available():
            logger.warning("Gemini parser not available")
            return []
        
        try:
            logger.info(f"Using Gemini Vision to parse PDF: {filepath}")
            
            # Upload the PDF file
            uploaded_file = genai.upload_file(filepath)
            
            prompt = """
Analyze this bank statement PDF and extract ALL transactions.

For each transaction, provide:
1. Date (in YYYY-MM-DD format)
2. Description
3. Amount (positive number)
4. Type ("credit" or "debit")
5. Category (salary, groceries, fuel, food_dining, utilities, medical, shopping, transfer, cash_withdrawal, loan, or others)

Rules:
- Extract EVERY transaction from the statement
- Debit column = "debit" type
- Credit column = "credit" type
- Ignore balance amounts
- Be thorough and accurate

Return ONLY a JSON array (no markdown):
[{"date": "YYYY-MM-DD", "description": "...", "amount": 123.45, "type": "credit", "category": "salary"}]
"""
            
            response = self.model.generate_content([uploaded_file, prompt])
            response_text = response.text.strip()
            
            # Clean response
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1] if '\n' in response_text else response_text[3:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse and validate
            transactions_raw = json.loads(response_text)
            transactions = []
            
            for txn in transactions_raw:
                try:
                    if not all(k in txn for k in ['date', 'description', 'amount', 'type']):
                        continue
                    
                    date_obj = datetime.strptime(txn['date'], '%Y-%m-%d')
                    amount = float(txn['amount'])
                    
                    if amount <= 0 or txn['type'] not in ['credit', 'debit']:
                        continue
                    
                    formatted_txn = {
                        'date': date_obj.strftime('%Y-%m-%d'),
                        'formatted_date': date_obj.strftime('%d %b %Y'),
                        'description': str(txn['description'])[:200],
                        'amount': amount,
                        'formatted_amount': f"₹{amount:,.2f}",
                        'type': txn['type'],
                        'category': txn.get('category', 'others'),
                        'bank': 'Extracted by AI Vision'
                    }
                    
                    transactions.append(formatted_txn)
                    
                except Exception as e:
                    logger.warning(f"Error processing transaction: {e}")
                    continue
            
            # Clean up uploaded file
            try:
                genai.delete_file(uploaded_file.name)
            except:
                pass
            
            logger.info(f"Gemini Vision extracted {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error in Gemini Vision parsing: {e}")
            return []


# Convenience function for easy import
def parse_with_gemini(filepath: str, api_key: str = None, use_vision: bool = False) -> List[Dict[str, Any]]:
    """
    Parse bank statement PDF using Gemini AI
    
    Args:
        filepath: Path to PDF file
        api_key: Gemini API key (optional, reads from env if not provided)
        use_vision: If True, uses Gemini Vision (more accurate for complex PDFs)
        
    Returns:
        List of transaction dictionaries
    """
    parser = GeminiPDFParser(api_key)
    
    if use_vision:
        return parser.parse_with_image(filepath)
    else:
        return parser.parse_pdf(filepath)
