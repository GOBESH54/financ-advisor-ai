import cv2
import pytesseract
import numpy as np
from PIL import Image
import re
from datetime import datetime
from typing import Dict, List, Optional
import logging
import speech_recognition as sr
import json

logger = logging.getLogger(__name__)

class ReceiptScanner:
    """OCR-based receipt scanning for bill processing"""
    
    def __init__(self):
        # Common Indian merchant patterns
        self.merchant_patterns = {
            'dmart': r'D[\s\-]*MART|AVENUE SUPERMARTS',
            'bigbasket': r'BIG[\s\-]*BASKET|SUPERMARKET GROCERY',
            'reliance': r'RELIANCE[\s\-]*FRESH|RELIANCE[\s\-]*DIGITAL',
            'more': r'MORE[\s\-]*SUPERMARKET|ADITYA BIRLA',
            'swiggy': r'SWIGGY|BUNDL TECHNOLOGIES',
            'zomato': r'ZOMATO|ZOMATO MEDIA',
            'uber': r'UBER|UBER INDIA',
            'ola': r'OLA|ANI TECHNOLOGIES',
            'amazon': r'AMAZON|AMAZON PAY',
            'flipkart': r'FLIPKART|FLIPKART INTERNET',
            'paytm': r'PAYTM|ONE97 COMMUNICATIONS',
            'phonepe': r'PHONEPE|PHONEPE PVT',
            'gpay': r'GOOGLE PAY|GPAY|GOOGLE INDIA'
        }
        
        self.amount_patterns = [
            r'TOTAL[:\s]*₹?[\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'AMOUNT[:\s]*₹?[\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'₹[\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'RS[:\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'INR[:\s]*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        ]
        
        self.date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(\d{1,2}\s+\w{3}\s+\d{2,4})',
            r'(\d{2,4}[/-]\d{1,2}[/-]\d{1,2})'
        ]
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy"""
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError("Could not read image")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply threshold to get binary image
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Morphological operations to clean up
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return processed
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return None
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from receipt image using OCR"""
        try:
            # Preprocess image
            processed_img = self.preprocess_image(image_path)
            if processed_img is None:
                return ""
            
            # Configure Tesseract for better accuracy
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz₹.,/:-\s'
            
            # Extract text
            text = pytesseract.image_to_string(processed_img, config=custom_config, lang='eng')
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def parse_receipt(self, image_path: str) -> Dict:
        """Parse receipt and extract transaction details"""
        try:
            # Extract text from image
            text = self.extract_text_from_image(image_path)
            if not text:
                return {'error': 'Could not extract text from image'}
            
            # Clean text
            text = text.upper().replace('\n', ' ').replace('\t', ' ')
            
            # Extract merchant
            merchant = self._extract_merchant(text)
            
            # Extract amount
            amount = self._extract_amount(text)
            
            # Extract date
            date = self._extract_date(text)
            
            # Determine category based on merchant
            category = self._categorize_merchant(merchant)
            
            # Extract additional details
            details = {
                'merchant': merchant,
                'amount': amount,
                'date': date,
                'category': category,
                'raw_text': text[:500],  # First 500 chars for debugging
                'confidence': self._calculate_confidence(merchant, amount, date)
            }
            
            return details
            
        except Exception as e:
            logger.error(f"Error parsing receipt: {e}")
            return {'error': str(e)}
    
    def _extract_merchant(self, text: str) -> str:
        """Extract merchant name from text"""
        for merchant, pattern in self.merchant_patterns.items():
            if re.search(pattern, text):
                return merchant.title()
        
        # Try to extract from common positions
        lines = text.split()
        if lines:
            # Often merchant name is in first few words
            for i in range(min(5, len(lines))):
                word = lines[i]
                if len(word) > 3 and word.isalpha():
                    return word.title()
        
        return "Unknown Merchant"
    
    def _extract_amount(self, text: str) -> float:
        """Extract amount from text"""
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Get the largest amount (likely the total)
                amounts = []
                for match in matches:
                    try:
                        # Remove commas and convert to float
                        amount = float(match.replace(',', ''))
                        amounts.append(amount)
                    except ValueError:
                        continue
                
                if amounts:
                    return max(amounts)
        
        return 0.0
    
    def _extract_date(self, text: str) -> str:
        """Extract date from text"""
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                date_str = matches[0]
                # Try to parse and standardize date
                try:
                    # Handle different date formats
                    if '/' in date_str:
                        parts = date_str.split('/')
                    elif '-' in date_str:
                        parts = date_str.split('-')
                    else:
                        continue
                    
                    if len(parts) == 3:
                        # Assume DD/MM/YYYY or MM/DD/YYYY
                        day, month, year = parts
                        if len(year) == 2:
                            year = '20' + year
                        
                        # Create date object to validate
                        date_obj = datetime(int(year), int(month), int(day))
                        return date_obj.strftime('%Y-%m-%d')
                        
                except (ValueError, IndexError):
                    continue
        
        # Default to today if no date found
        return datetime.now().strftime('%Y-%m-%d')
    
    def _categorize_merchant(self, merchant: str) -> str:
        """Categorize transaction based on merchant"""
        merchant_lower = merchant.lower()
        
        category_mapping = {
            'groceries': ['dmart', 'bigbasket', 'reliance', 'more', 'supermarket', 'grocery'],
            'food_dining': ['swiggy', 'zomato', 'restaurant', 'cafe', 'hotel'],
            'transportation': ['uber', 'ola', 'taxi', 'auto', 'petrol', 'fuel'],
            'shopping': ['amazon', 'flipkart', 'myntra', 'ajio', 'mall'],
            'utilities': ['paytm', 'phonepe', 'gpay', 'recharge', 'bill']
        }
        
        for category, keywords in category_mapping.items():
            if any(keyword in merchant_lower for keyword in keywords):
                return category
        
        return 'other'
    
    def _calculate_confidence(self, merchant: str, amount: float, date: str) -> float:
        """Calculate confidence score for extracted data"""
        confidence = 0.0
        
        # Merchant confidence
        if merchant != "Unknown Merchant":
            confidence += 0.4
        
        # Amount confidence
        if amount > 0:
            confidence += 0.4
        
        # Date confidence
        if date != datetime.now().strftime('%Y-%m-%d'):
            confidence += 0.2
        
        return min(confidence, 1.0)

class VoiceCommandProcessor:
    """Voice command processing for expense entry"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Command patterns
        self.expense_patterns = [
            r'add expense of (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*for\s+(.+)',
            r'spent (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*on\s+(.+)',
            r'expense (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*(.+)',
            r'paid (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*for\s+(.+)'
        ]
        
        self.income_patterns = [
            r'add income of (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*from\s+(.+)',
            r'received (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*from\s+(.+)',
            r'income (?:rs|rupees|₹)?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:rs|rupees|₹)?\s*(.+)'
        ]
        
        # Category mapping for voice commands
        self.category_mapping = {
            'grocery': 'groceries', 'groceries': 'groceries', 'food': 'groceries',
            'restaurant': 'food_dining', 'dining': 'food_dining', 'lunch': 'food_dining', 'dinner': 'food_dining',
            'transport': 'transportation', 'taxi': 'transportation', 'uber': 'transportation', 'ola': 'transportation',
            'fuel': 'transportation', 'petrol': 'transportation', 'diesel': 'transportation',
            'electricity': 'utilities', 'water': 'utilities', 'gas': 'utilities', 'internet': 'utilities',
            'mobile': 'utilities', 'phone': 'utilities', 'recharge': 'utilities',
            'movie': 'entertainment', 'cinema': 'entertainment', 'netflix': 'entertainment',
            'shopping': 'shopping', 'clothes': 'shopping', 'amazon': 'shopping', 'flipkart': 'shopping',
            'medical': 'healthcare', 'doctor': 'healthcare', 'medicine': 'healthcare', 'hospital': 'healthcare'
        }
    
    def listen_for_command(self, timeout: int = 5) -> str:
        """Listen for voice command"""
        try:
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Listen for command
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
                
                # Recognize speech
                command = self.recognizer.recognize_google(audio, language='en-IN')
                return command.lower()
                
        except sr.WaitTimeoutError:
            return "timeout"
        except sr.UnknownValueError:
            return "could_not_understand"
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return "service_error"
        except Exception as e:
            logger.error(f"Voice command error: {e}")
            return "error"
    
    def process_command(self, command: str) -> Dict:
        """Process voice command and extract transaction details"""
        try:
            command = command.strip().lower()
            
            # Try expense patterns
            for pattern in self.expense_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    description = match.group(2).strip()
                    
                    return {
                        'type': 'expense',
                        'amount': float(amount_str),
                        'description': description,
                        'category': self._categorize_description(description),
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'confidence': 0.9,
                        'raw_command': command
                    }
            
            # Try income patterns
            for pattern in self.income_patterns:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(',', '')
                    source = match.group(2).strip()
                    
                    return {
                        'type': 'income',
                        'amount': float(amount_str),
                        'source': source,
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'confidence': 0.9,
                        'raw_command': command
                    }
            
            return {
                'error': 'Could not parse command',
                'raw_command': command,
                'suggestions': [
                    'Try: "Add expense of 500 rupees for groceries"',
                    'Try: "Spent 200 on lunch"',
                    'Try: "Add income of 50000 from salary"'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            return {'error': str(e), 'raw_command': command}
    
    def _categorize_description(self, description: str) -> str:
        """Categorize expense based on description"""
        description_lower = description.lower()
        
        for keyword, category in self.category_mapping.items():
            if keyword in description_lower:
                return category
        
        return 'other'

class OfflineManager:
    """Offline mode functionality"""
    
    def __init__(self, storage_path: str = 'offline_data.json'):
        self.storage_path = storage_path
        self.offline_data = self._load_offline_data()
    
    def _load_offline_data(self) -> Dict:
        """Load offline data from storage"""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'pending_transactions': [],
                'cached_data': {},
                'last_sync': None
            }
    
    def _save_offline_data(self):
        """Save offline data to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.offline_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving offline data: {e}")
    
    def add_pending_transaction(self, transaction: Dict) -> str:
        """Add transaction to offline queue"""
        transaction_id = f"offline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.offline_data['pending_transactions'])}"
        
        transaction.update({
            'id': transaction_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        })
        
        self.offline_data['pending_transactions'].append(transaction)
        self._save_offline_data()
        
        return transaction_id
    
    def get_pending_transactions(self) -> List[Dict]:
        """Get all pending transactions"""
        return self.offline_data['pending_transactions']
    
    def mark_transaction_synced(self, transaction_id: str):
        """Mark transaction as synced"""
        for txn in self.offline_data['pending_transactions']:
            if txn['id'] == transaction_id:
                txn['status'] = 'synced'
                break
        
        # Remove synced transactions
        self.offline_data['pending_transactions'] = [
            txn for txn in self.offline_data['pending_transactions'] 
            if txn['status'] != 'synced'
        ]
        
        self._save_offline_data()
    
    def cache_data(self, key: str, data: Dict):
        """Cache data for offline access"""
        self.offline_data['cached_data'][key] = {
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self._save_offline_data()
    
    def get_cached_data(self, key: str, max_age_hours: int = 24) -> Optional[Dict]:
        """Get cached data if not too old"""
        if key not in self.offline_data['cached_data']:
            return None
        
        cached_item = self.offline_data['cached_data'][key]
        cached_time = datetime.fromisoformat(cached_item['timestamp'])
        
        if (datetime.now() - cached_time).total_seconds() > max_age_hours * 3600:
            return None
        
        return cached_item['data']
    
    def get_offline_summary(self) -> Dict:
        """Get summary of offline data"""
        return {
            'pending_transactions': len(self.offline_data['pending_transactions']),
            'cached_items': len(self.offline_data['cached_data']),
            'last_sync': self.offline_data.get('last_sync'),
            'storage_size_kb': self._get_storage_size()
        }
    
    def _get_storage_size(self) -> float:
        """Get storage file size in KB"""
        try:
            import os
            return os.path.getsize(self.storage_path) / 1024
        except:
            return 0.0

class PWAManager:
    """Progressive Web App functionality"""
    
    def __init__(self):
        self.manifest = {
            "name": "Personal Finance Advisor",
            "short_name": "FinanceApp",
            "description": "AI-powered personal finance management",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#2563eb",
            "orientation": "portrait-primary",
            "icons": [
                {
                    "src": "/static/icons/icon-72x72.png",
                    "sizes": "72x72",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-96x96.png",
                    "sizes": "96x96",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-128x128.png",
                    "sizes": "128x128",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-144x144.png",
                    "sizes": "144x144",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-152x152.png",
                    "sizes": "152x152",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-384x384.png",
                    "sizes": "384x384",
                    "type": "image/png"
                },
                {
                    "src": "/static/icons/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png"
                }
            ]
        }
    
    def get_manifest(self) -> Dict:
        """Get PWA manifest"""
        return self.manifest
    
    def generate_service_worker(self) -> str:
        """Generate service worker for offline functionality"""
        return '''
const CACHE_NAME = 'finance-app-v1';
const urlsToCache = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
  '/static/icons/icon-192x192.png',
  '/api/dashboard',
  '/api/expenses',
  '/api/income'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      }
    )
  );
});

self.addEventListener('sync', event => {
  if (event.tag === 'background-sync') {
    event.waitUntil(syncPendingTransactions());
  }
});

async function syncPendingTransactions() {
  try {
    const response = await fetch('/api/sync/offline');
    if (response.ok) {
      console.log('Offline transactions synced');
    }
  } catch (error) {
    console.error('Sync failed:', error);
  }
}
'''