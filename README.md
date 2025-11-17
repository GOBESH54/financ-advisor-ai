# 💰 Personal Finance Advisor AI System

A comprehensive, AI-powered personal finance management system with advanced machine learning capabilities, real-time analytics, and intelligent forecasting.

## 🚀 Features

### Core Financial Management
- **📊 Dashboard**: Real-time financial health monitoring with visual insights
- **💰 Income & Expense Tracking**: Detailed transaction management with categorization
- **📈 Budget Analysis**: Smart budgeting based on the 50/30/20 rule with AI recommendations
- **🎯 Savings Goals**: Goal tracking with progress monitoring and forecasting
- **💳 Debt Management**: Strategic debt repayment planning (Avalanche, Snowball, Hybrid)
- **📄 Reports**: Comprehensive PDF report generation

### 🧠 Advanced AI Features
- **LSTM Forecasting**: Deep learning expense predictions using TensorFlow
- **Spending Prediction**: ML-based category-wise spending forecasts
- **Cashflow Forecasting**: 6-month income/expense predictions with ARIMA models
- **Anomaly Detection**: Unusual spending pattern identification
- **Business Intelligence**: Advanced analytics with trend analysis
- **Investment Recommendations**: Random Forest & XGBoost portfolio optimization

### 🏦 Banking Integration
- **Bank Statement Upload**: CSV/PDF/Excel statement parsing
- **Transaction Classification**: AI-powered transaction categorization
- **Real-time Sync**: Automatic transaction import
- **Multi-bank Support**: Support for major Indian banks

### 🔒 Security & Privacy
- **Local Storage**: All data stored locally using SQLite
- **Data Encryption**: Advanced security features
- **Audit Logging**: Complete activity tracking
- **Backup System**: Automated data backup

## 📋 Prerequisites

- **Python 3.11+**
- **Node.js 16+** and npm
- **Windows OS** (for .bat scripts)

## 🛠️ Quick Setup

1. **Clone/Download** the project
2. **Run the setup**:
   ```bash
   start_app.bat
   ```

This automatically:
- ✅ Starts Flask backend on http://localhost:5000
- ✅ Starts React frontend on http://localhost:3000
- ✅ Opens your browser to the application

## 📱 Using the Application

### Initial Setup
1. Application creates a default user automatically
2. Navigate to **Settings** to update your profile
3. Set your risk tolerance for investment recommendations

### Adding Financial Data
- **Income**: Add income sources with frequency
- **Expenses**: Track expenses by category with recurring options
- **Debts**: Add debts with interest rates and minimum payments
- **Goals**: Set financial targets with dates

### AI Analysis Features
- **Budget Analysis**: Get AI recommendations and health scores
- **Investment Advice**: Personalized portfolio suggestions
- **Debt Optimization**: Compare repayment strategies
- **Forecasting**: 12-month predictions using LSTM models
- **Anomaly Detection**: Identify unusual spending patterns

## 🏗️ Project Structure

```
Personal Finance Advisor/
├── backend/                 # Flask API Server
│   ├── app.py              # Main application
│   ├── models.py           # Database models
│   ├── ai_models.py        # AI/ML implementations
│   ├── lstm_forecaster.py  # Deep learning models
│   ├── report_generator.py # PDF generation
│   └── requirements.txt    # Python dependencies
├── frontend/               # React Application
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── Dashboard.js
│   │   │   ├── AIForecasting.js
│   │   │   ├── BusinessIntelligence.js
│   │   │   └── ...
│   │   └── services/
│   │       └── api.js      # API service layer
│   └── package.json        # Node dependencies
└── start_app.bat          # Quick start script
```

## 🤖 AI Models & Technologies

### Machine Learning Stack
- **TensorFlow/Keras**: LSTM neural networks for time-series forecasting
- **Scikit-learn**: Random Forest, XGBoost for classification
- **Pandas/NumPy**: Data processing and analysis
- **ARIMA**: Statistical forecasting models

### Frontend Technologies
- **React 18**: Modern UI framework
- **Chart.js**: Interactive data visualizations
- **Tailwind CSS**: Responsive styling
- **Axios**: API communication

### Backend Technologies
- **Flask**: Python web framework
- **SQLAlchemy**: Database ORM
- **SQLite**: Local database storage
- **Plotly**: Advanced charting

## 📊 AI Capabilities

### 🧠 LSTM Forecasting
- Predicts future expenses using deep learning
- Analyzes historical patterns for accurate forecasts
- Category-wise spending predictions

### 📈 Business Intelligence
- Financial health scoring (0-100)
- Spending pattern analysis
- Trend identification (increasing/decreasing/stable)
- Peer comparison benchmarks

### ⚠️ Anomaly Detection
- Identifies unusual transactions
- Z-score based statistical analysis
- Severity classification (high/medium/low)

### 💡 Smart Recommendations
- Budget optimization suggestions
- Investment portfolio allocation
- Debt repayment strategies
- Savings goal planning

## 🔧 Configuration

### Backend (backend/config.py)
- Database: SQLite (local storage)
- Budget rules: Customizable percentages
- AI model parameters

### Frontend
- API endpoint: http://localhost:5000/api
- Charts: Chart.js configuration
- Styling: Tailwind CSS

## 🚨 Troubleshooting

### Common Issues

**Port conflicts:**
- Backend: Change port in `app.py` (default: 5000)
- Frontend: Change in `package.json` (default: 3000)

**Database errors:**
- Delete `finance_advisor.db` to reset
- Application recreates database automatically

**Missing dependencies:**
```bash
pip install -r requirements.txt
cd frontend && npm install
```

**AI model errors:**
- Ensure TensorFlow is properly installed
- Check NumPy version compatibility

## 📈 Advanced Features

### Investment Management
- Portfolio tracking with real-time prices
- Asset allocation optimization
- SIP (Systematic Investment Plan) management
- Tax-loss harvesting opportunities

### Advanced Budgeting
- Zero-based budgeting
- Envelope budgeting system
- Seasonal budget planning
- Family budget management

### Indian Financial Features
- Income tax calculation (old/new regime)
- GST tracking for businesses
- PPF, FD, SIP calculators
- EMI and loan comparison tools

## 🔒 Security Features

- **Multi-factor Authentication**: Email/SMS OTP
- **Data Encryption**: AES encryption for sensitive data
- **Audit Logging**: Complete activity tracking
- **Backup System**: Automated database backups
- **Local Storage**: No cloud dependencies

## 📱 Mobile Features

- **Receipt Scanning**: OCR-based expense capture
- **Voice Commands**: Add transactions via voice
- **Offline Mode**: Works without internet
- **PWA Support**: Install as mobile app

## 🌟 Performance Optimizations

- **Caching**: Redis/Memcached support
- **Background Tasks**: Celery integration
- **Database Optimization**: Indexed queries
- **Lazy Loading**: Efficient data fetching

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## 📄 License

Open source - Available for personal and educational use

## 🆘 Support

For issues:
1. Check troubleshooting section
2. Review error logs in console
3. Ensure all dependencies are installed
4. Verify Python 3.11+ and Node.js 16+

## 🎯 Future Enhancements

- Multi-user authentication system
- Real-time market data integration
- Cryptocurrency portfolio tracking
- Advanced tax planning features
- Mobile app (React Native)
- Cloud synchronization option

---

**⚠️ Disclaimer**: This is an educational project demonstrating AI integration in financial management. Always consult qualified financial advisors for important financial decisions.

**🚀 Quick Start**: Run `start_app.bat` and visit http://localhost:3000