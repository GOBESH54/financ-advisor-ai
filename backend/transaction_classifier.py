import os
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
import logging
import re
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sklearn.ensemble import IsolationForest
import joblib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndianTransactionClassifier:
    """Classify transactions using FinBERT and rule-based logic for Indian context"""
    
    # Indian-specific expense categories
    INDIAN_CATEGORIES = {
        'groceries': ['grocery', 'supermarket', 'kirana', 'bigbasket', 'grofers', 'blinkit', 'zepto', 'dmart', 'reliance fresh', 'more', 'spencer'],
        'food_dining': ['swiggy', 'zomato', 'restaurant', 'cafe', 'food', 'pizza', 'burger', 'biryani', 'dominos', 'mcdonald', 'kfc', 'subway'],
        'transportation': ['uber', 'ola', 'rapido', 'petrol', 'diesel', 'fuel', 'parking', 'metro', 'bus', 'auto', 'cab', 'taxi'],
        'utilities': ['electricity', 'water', 'gas', 'lpg', 'cylinder', 'power', 'bescom', 'mseb', 'bsnl', 'jio', 'airtel', 'vodafone', 'vi'],
        'emi': ['emi', 'loan', 'equated', 'monthly installment', 'home loan', 'car loan', 'personal loan', 'bajaj finserv'],
        'rent': ['rent', 'house rent', 'apartment', 'flat', 'maintenance', 'society'],
        'insurance': ['insurance', 'premium', 'lic', 'hdfc life', 'sbi life', 'icici pru', 'policy'],
        'healthcare': ['hospital', 'pharmacy', 'medicine', 'doctor', 'clinic', 'apollo', 'fortis', 'max', 'practo', 'netmeds', '1mg', 'pharmeasy'],
        'education': ['school', 'college', 'university', 'tuition', 'course', 'exam', 'fees', 'byju', 'unacademy', 'upgrad'],
        'entertainment': ['movie', 'theatre', 'pvr', 'inox', 'netflix', 'amazon prime', 'hotstar', 'spotify', 'youtube', 'gaming'],
        'shopping': ['amazon', 'flipkart', 'myntra', 'ajio', 'meesho', 'shopping', 'mall', 'clothing', 'fashion'],
        'investment': ['sip', 'mutual fund', 'mf', 'zerodha', 'groww', 'upstox', 'stock', 'shares', 'demat', 'trading'],
        'travel': ['flight', 'hotel', 'booking', 'makemytrip', 'goibibo', 'cleartrip', 'oyo', 'airbnb', 'irctc', 'train'],
        'telecom': ['mobile', 'recharge', 'prepaid', 'postpaid', 'broadband', 'internet', 'jio', 'airtel', 'vi', 'bsnl'],
        'salary': ['salary', 'payroll', 'wages', 'income', 'transfer from'],
        'transfer': ['upi', 'neft', 'rtgs', 'imps', 'transfer to', 'sent to'],
        'withdrawal': ['atm', 'cash withdrawal', 'withdraw'],
        'other': []
    }
    
    def __init__(self, use_finbert: bool = False):
        """
        Initialize classifier
        Args:
            use_finbert: Use FinBERT (requires GPU/memory). Falls back to rule-based if False.
        """
        self.use_finbert = use_finbert
        self.model = None
        self.tokenizer = None
        
        # Check if GPU is available
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Using device: {self.device}")
        
        if use_finbert:
            try:
                self._load_finbert()
            except Exception as e:
                logger.warning(f"Failed to load FinBERT, falling back to rule-based: {e}")
                self.use_finbert = False
    
    def _load_finbert(self):
        """Load FinBERT model for transaction classification"""
        try:
            # Use lightweight FinBERT or distilbert for lower memory
            model_name = "distilbert-base-uncased"  # Smaller alternative
            
            logger.info(f"Loading model: {model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=len(self.INDIAN_CATEGORIES)
            )
            
            # Move to GPU if available
            if self.device == 'cuda':
                self.model = self.model.half()  # Use FP16 for memory efficiency
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("FinBERT loaded successfully")
        except Exception as e:
            logger.error(f"Error loading FinBERT: {e}")
            raise
    
    def classify(self, description: str, amount: float = 0, payment_method: str = '') -> str:
        """
        Classify transaction into category
        Args:
            description: Transaction description
            amount: Transaction amount
            payment_method: Payment method (UPI, NEFT, etc.)
        Returns:
            Category name
        """
        if self.use_finbert and self.model:
            return self._classify_with_finbert(description)
        else:
            return self._classify_rule_based(description, amount, payment_method)
    
    def _classify_with_finbert(self, description: str) -> str:
        """Classify using FinBERT model"""
        try:
            # Tokenize
            inputs = self.tokenizer(
                description,
                return_tensors="pt",
                truncation=True,
                max_length=128,
                padding=True
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=-1).item()
            
            # Map to category
            categories = list(self.INDIAN_CATEGORIES.keys())
            return categories[predicted_class] if predicted_class < len(categories) else 'other'
            
        except Exception as e:
            logger.warning(f"FinBERT classification failed: {e}")
            return self._classify_rule_based(description, 0, '')
    
    def _classify_rule_based(self, description: str, amount: float = 0, payment_method: str = '') -> str:
        """Rule-based classification using keywords"""
        description_lower = description.lower()
        
        # Check each category's keywords
        for category, keywords in self.INDIAN_CATEGORIES.items():
            for keyword in keywords:
                if keyword in description_lower:
                    return category
        
        # Additional heuristics
        if payment_method == 'EMI':
            return 'emi'
        
        if amount > 10000 and any(word in description_lower for word in ['transfer', 'to']):
            return 'transfer'
        
        if amount > 5000 and amount < 50000:
            # Likely rent or EMI
            if 'monthly' in description_lower or 'rent' in description_lower:
                return 'rent'
        
        return 'other'
    
    def batch_classify(self, transactions: List[Dict]) -> List[Dict]:
        """Classify multiple transactions"""
        for txn in transactions:
            category = self.classify(
                txn.get('description', ''),
                txn.get('amount', 0),
                txn.get('payment_method', '')
            )
            txn['category'] = category
        
        return transactions


class AnomalyDetector:
    """Detect unusual spending patterns using Isolation Forest"""
    
    def __init__(self):
        self.model = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        self.is_fitted = False
        self.scaler_mean = None
        self.scaler_std = None
    
    def fit(self, transactions: pd.DataFrame):
        """Train anomaly detector on historical transactions"""
        if len(transactions) < 10:
            logger.warning("Not enough transactions to train anomaly detector")
            return
        
        features = self._extract_features(transactions)
        
        if features is None or len(features) == 0:
            return
        
        # Normalize
        self.scaler_mean = features.mean()
        self.scaler_std = features.std()
        features_scaled = (features - self.scaler_mean) / (self.scaler_std + 1e-8)
        
        # Fit model
        self.model.fit(features_scaled)
        self.is_fitted = True
        logger.info("Anomaly detector trained")
    
    def detect(self, transactions: pd.DataFrame) -> List[Dict]:
        """Detect anomalies in transactions"""
        if not self.is_fitted:
            self.fit(transactions)
        
        if not self.is_fitted:
            return []
        
        features = self._extract_features(transactions)
        
        if features is None or len(features) == 0:
            return []
        
        # Normalize
        features_scaled = (features - self.scaler_mean) / (self.scaler_std + 1e-8)
        
        # Predict
        predictions = self.model.predict(features_scaled)
        scores = self.model.score_samples(features_scaled)
        
        # Find anomalies
        anomalies = []
        for idx, (pred, score) in enumerate(zip(predictions, scores)):
            if pred == -1:  # Anomaly
                anomalies.append({
                    'transaction_index': idx,
                    'anomaly_score': float(score),
                    'description': transactions.iloc[idx].get('description', ''),
                    'amount': float(transactions.iloc[idx].get('amount', 0)),
                    'date': str(transactions.iloc[idx].get('date', '')),
                    'reason': self._explain_anomaly(transactions.iloc[idx], score)
                })
        
        return anomalies
    
    def _extract_features(self, transactions: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Extract features for anomaly detection"""
        if transactions.empty:
            return None
        
        features = pd.DataFrame()
        
        # Amount-based features
        features['amount'] = transactions['amount'].astype(float)
        features['log_amount'] = np.log1p(features['amount'])
        
        # Time-based features
        if 'date' in transactions.columns:
            dates = pd.to_datetime(transactions['date'], errors='coerce')
            features['day_of_week'] = dates.dt.dayofweek
            features['day_of_month'] = dates.dt.day
            features['hour'] = dates.dt.hour if hasattr(dates.dt, 'hour') else 12
        else:
            features['day_of_week'] = 0
            features['day_of_month'] = 15
            features['hour'] = 12
        
        # Category-based features (if available)
        if 'category' in transactions.columns:
            # One-hot encode top categories
            top_cats = transactions['category'].value_counts().head(5).index
            for cat in top_cats:
                features[f'cat_{cat}'] = (transactions['category'] == cat).astype(int)
        
        return features.fillna(0)
    
    def _explain_anomaly(self, transaction: pd.Series, score: float) -> str:
        """Explain why transaction is anomalous"""
        amount = transaction.get('amount', 0)
        
        if amount > 50000:
            return f"Unusually large amount: ₹{amount:,.2f}"
        
        if score < -0.5:
            return "Transaction pattern significantly different from usual behavior"
        
        return "Unusual spending pattern detected"
