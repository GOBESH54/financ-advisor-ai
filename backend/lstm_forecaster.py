import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import logging
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
import joblib
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LSTMExpenseForecaster:
    """LSTM-based expense forecasting optimized for low-memory systems"""
    
    def __init__(self, lookback: int = 12, model_path: str = 'models/lstm_forecaster.h5'):
        """
        Initialize LSTM forecaster
        Args:
            lookback: Number of past months to use for prediction
            model_path: Path to save/load model
        """
        self.lookback = lookback
        self.model_path = model_path
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.is_trained = False
        
        # Create models directory
        os.makedirs('models', exist_ok=True)
        
        # Load existing model if available
        if os.path.exists(model_path):
            try:
                self.load_model()
            except Exception as e:
                logger.warning(f"Could not load existing model: {e}")
    
    def build_model(self, input_shape: Tuple[int, int]):
        """Build LSTM model architecture optimized for 8GB RAM"""
        model = Sequential([
            # First LSTM layer with reduced units for memory efficiency
            LSTM(32, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            
            # Second LSTM layer
            LSTM(16, return_sequences=False),
            Dropout(0.2),
            
            # Dense output layer
            Dense(8, activation='relu'),
            Dense(1)
        ])
        
        # Compile with Adam optimizer
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def prepare_data(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare time series data for LSTM training"""
        if len(data) < self.lookback + 1:
            raise ValueError(f"Need at least {self.lookback + 1} data points")
        
        # Reshape data
        data = data.reshape(-1, 1)
        
        # Scale data
        scaled_data = self.scaler.fit_transform(data)
        
        # Create sequences
        X, y = [], []
        for i in range(len(scaled_data) - self.lookback):
            X.append(scaled_data[i:i + self.lookback, 0])
            y.append(scaled_data[i + self.lookback, 0])
        
        X = np.array(X)
        y = np.array(y)
        
        # Reshape X for LSTM [samples, time steps, features]
        X = X.reshape(X.shape[0], X.shape[1], 1)
        
        return X, y
    
    def train(self, monthly_expenses: List[float], epochs: int = 50, batch_size: int = 8):
        """
        Train LSTM model on historical expenses
        Args:
            monthly_expenses: List of monthly expense amounts
            epochs: Number of training epochs
            batch_size: Batch size for training
        """
        if len(monthly_expenses) < self.lookback + 1:
            logger.warning(f"Not enough data to train LSTM (need {self.lookback + 1}, got {len(monthly_expenses)})")
            return False
        
        try:
            # Prepare data
            data = np.array(monthly_expenses)
            X, y = self.prepare_data(data)
            
            # Build model
            self.model = self.build_model(input_shape=(X.shape[1], 1))
            
            # Early stopping to prevent overfitting
            early_stop = EarlyStopping(
                monitor='loss',
                patience=10,
                restore_best_weights=True
            )
            
            # Train model
            logger.info("Training LSTM model...")
            self.model.fit(
                X, y,
                epochs=epochs,
                batch_size=batch_size,
                verbose=0,
                callbacks=[early_stop]
            )
            
            self.is_trained = True
            
            # Save model
            self.save_model()
            
            logger.info("LSTM model trained successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error training LSTM: {e}")
            return False
    
    def forecast(self, monthly_expenses: List[float], periods: int = 3) -> Dict:
        """
        Forecast future expenses
        Args:
            monthly_expenses: Historical monthly expenses
            periods: Number of months to forecast
        Returns:
            Dictionary with forecast data
        """
        if not self.is_trained:
            # Try to train on available data
            if len(monthly_expenses) >= self.lookback + 1:
                self.train(monthly_expenses)
            else:
                return self._fallback_forecast(monthly_expenses, periods)
        
        if not self.is_trained:
            return self._fallback_forecast(monthly_expenses, periods)
        
        try:
            # Prepare last lookback months
            data = np.array(monthly_expenses[-self.lookback:])
            data = data.reshape(-1, 1)
            scaled_data = self.scaler.transform(data)
            
            # Forecast iteratively
            forecasts = []
            current_sequence = scaled_data.copy()
            
            for _ in range(periods):
                # Reshape for prediction
                X = current_sequence.reshape(1, self.lookback, 1)
                
                # Predict next value
                pred_scaled = self.model.predict(X, verbose=0)
                pred = self.scaler.inverse_transform(pred_scaled)[0, 0]
                
                forecasts.append(float(pred))
                
                # Update sequence for next prediction
                current_sequence = np.append(current_sequence[1:], pred_scaled)
                current_sequence = current_sequence.reshape(-1, 1)
            
            # Calculate confidence intervals (simple approach)
            std = np.std(monthly_expenses[-12:]) if len(monthly_expenses) >= 12 else np.std(monthly_expenses)
            
            forecast_data = []
            for i, pred in enumerate(forecasts):
                forecast_data.append({
                    'month': i + 1,
                    'forecast': max(0, pred),  # Ensure non-negative
                    'lower_bound': max(0, pred - 1.96 * std),
                    'upper_bound': pred + 1.96 * std
                })
            
            return {
                'forecast': forecast_data,
                'total_projected': sum(forecasts),
                'average_monthly': np.mean(forecasts),
                'model_type': 'LSTM',
                'confidence': 0.95
            }
            
        except Exception as e:
            logger.error(f"Error forecasting with LSTM: {e}")
            return self._fallback_forecast(monthly_expenses, periods)
    
    def _fallback_forecast(self, monthly_expenses: List[float], periods: int) -> Dict:
        """Simple fallback forecast using moving average"""
        if len(monthly_expenses) == 0:
            return {
                'forecast': [],
                'total_projected': 0,
                'average_monthly': 0,
                'model_type': 'fallback',
                'confidence': 0.5
            }
        
        # Use last 3-6 months average
        recent = monthly_expenses[-6:] if len(monthly_expenses) >= 6 else monthly_expenses
        avg = np.mean(recent)
        std = np.std(recent)
        
        # Simple trend
        if len(recent) > 1:
            trend = (recent[-1] - recent[0]) / len(recent)
        else:
            trend = 0
        
        forecast_data = []
        for i in range(periods):
            pred = avg + trend * (i + 1)
            forecast_data.append({
                'month': i + 1,
                'forecast': max(0, pred),
                'lower_bound': max(0, pred - 1.96 * std),
                'upper_bound': pred + 1.96 * std
            })
        
        return {
            'forecast': forecast_data,
            'total_projected': sum([f['forecast'] for f in forecast_data]),
            'average_monthly': avg,
            'model_type': 'moving_average',
            'confidence': 0.7
        }
    
    def save_model(self):
        """Save model and scaler"""
        try:
            if self.model:
                self.model.save(self.model_path)
                joblib.dump(self.scaler, self.model_path.replace('.h5', '_scaler.pkl'))
                logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self):
        """Load model and scaler"""
        try:
            self.model = keras.models.load_model(self.model_path)
            self.scaler = joblib.load(self.model_path.replace('.h5', '_scaler.pkl'))
            self.is_trained = True
            logger.info(f"Model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise


def forecast_by_category(transactions: pd.DataFrame, periods: int = 3) -> Dict[str, Dict]:
    """
    Forecast expenses by category
    Args:
        transactions: DataFrame with transactions including 'category' and 'amount'
        periods: Number of months to forecast
    Returns:
        Dictionary mapping category to forecast data
    """
    forecasts = {}
    
    # Group by category
    for category in transactions['category'].unique():
        cat_txns = transactions[transactions['category'] == category]
        
        # Group by month
        cat_txns['date'] = pd.to_datetime(cat_txns['date'], errors='coerce')
        monthly = cat_txns.groupby(cat_txns['date'].dt.to_period('M'))['amount'].sum()
        
        if len(monthly) >= 3:
            # Forecast this category
            forecaster = LSTMExpenseForecaster(lookback=min(6, len(monthly) - 1))
            forecast = forecaster.forecast(monthly.values.tolist(), periods)
            forecasts[category] = forecast
    
    return forecasts
