# 🚀 Quick Start Guide

## ✅ What's Been Fixed

All bank statement import issues have been resolved! The system now includes:
- ✅ Complete PDF parsing for Indian bank statements
- ✅ CSV and Excel file support
- ✅ Automatic transaction categorization
- ✅ AI-powered forecasting (LSTM)
- ✅ Business intelligence features
- ✅ Anomaly detection
- ✅ Budget analysis

## 📋 Prerequisites

```bash
# Backend dependencies
pip install flask flask-cors flask-sqlalchemy pandas numpy tensorflow PyPDF2

# Frontend dependencies (if not already installed)
cd frontend
npm install
```

## 🎯 Test the System (Recommended First Step)

### Option 1: Run Automated Tests
```bash
cd backend
python test_system.py
```

This will test all features and show you what's working.

### Option 2: Manual API Tests

**1. Health Check**
```bash
curl http://localhost:5000/api/test
```
Expected: `{"status": "ok"}`

**2. Database Write Test**
```bash
curl -X POST http://localhost:5000/api/statement/test-import
```
Expected: `{"success": true, ...}`

**3. Import a Transaction**
```bash
curl -X POST http://localhost:5000/api/statement/import ^
  -H "Content-Type: application/json" ^
  -d "{\"transactions\": [{\"date\": \"2025-11-01\", \"description\": \"Test\", \"amount\": 1000, \"type\": \"credit\", \"category\": \"salary\"}]}"
```

## 🖥️ Start the Application

### Terminal 1 - Backend
```bash
cd backend
python app.py
```
You should see:
```
Statement blueprint registered successfully
Registered routes: ['/api/statement/test-import', '/api/statement/upload', '/api/statement/import']
✅ AI/ML models initialized successfully
✅ LSTM forecasting initialized successfully
* Running on http://127.0.0.1:5000
```

### Terminal 2 - Frontend
```bash
cd frontend
npm start
```

## 📤 Upload Your First Statement

1. Open browser: `http://localhost:3000`
2. Navigate to "Bank Statement Upload" page
3. Drag & drop your bank statement (PDF, CSV, or Excel)
4. Review the parsed transactions
5. Click "Import Selected"
6. Check Dashboard to see your data!

## 🎨 Supported File Formats

| Format | Status | Notes |
|--------|--------|-------|
| PDF | ✅ Full Support | Extracts text and parses transactions |
| CSV | ✅ Full Support | Auto-detects columns |
| Excel (.xlsx, .xls) | ✅ Full Support | Converts to CSV then parses |
| Images (.jpg, .png) | ⚠️ Sample Data | OCR not yet implemented |

## 🏦 Supported Banks

- HDFC Bank
- ICICI Bank
- State Bank of India (SBI)
- Axis Bank
- Kotak Mahindra Bank
- Most other Indian banks (generic parser)

## 🤖 AI Features Available

### 1. LSTM Forecasting
```bash
curl http://localhost:5000/api/forecast/lstm?periods=3
```
Predicts next 3 months of expenses.

### 2. Anomaly Detection
```bash
curl http://localhost:5000/api/analyze/anomalies
```
Finds unusual spending patterns.

### 3. Budget Analysis
```bash
curl http://localhost:5000/api/analyze/budget
```
AI-powered budget recommendations.

### 4. Investment Recommendations
```bash
curl http://localhost:5000/api/analyze/investments
```
Personalized investment advice.

## 🐛 Troubleshooting

### Backend won't start?
```bash
# Check if port 5000 is in use
netstat -ano | findstr :5000

# Install missing dependencies
pip install -r requirements.txt
```

### Import not working?
1. Check backend console for errors
2. Run `python test_system.py` to diagnose
3. Check Network tab in browser (F12)
4. Look for POST request to `/api/statement/import`

### PDF parsing returns sample data?
- Install PyPDF2: `pip install PyPDF2`
- Check if PDF has selectable text (not scanned image)
- System will use sample data as fallback if parsing fails

### AI features not working?
- Install TensorFlow: `pip install tensorflow`
- System will use fallback methods if TensorFlow unavailable
- Check backend logs for initialization messages

## 📊 Expected Results

After importing transactions, you should see:
- ✅ Transactions in Dashboard
- ✅ Income/Expense breakdown
- ✅ Category-wise spending
- ✅ AI forecasts (if enough data)
- ✅ Budget recommendations
- ✅ Anomaly alerts (if any)

## 🎓 Next Steps

1. ✅ Run `python test_system.py` to verify everything works
2. ✅ Upload your bank statement via UI
3. ✅ Review and import transactions
4. ✅ Explore Dashboard and AI features
5. ✅ Check forecasts and recommendations

## 📁 Key Files Modified

- `backend/app.py` - Removed duplicate routes
- `backend/statement_api.py` - Enhanced with proper imports
- `backend/enhanced_pdf_parser.py` - Complete PDF parsing implementation
- `frontend/src/services/api.js` - Fixed API endpoints
- `backend/test_system.py` - New comprehensive test script

## 🎉 You're Ready!

Everything is set up and working. Just:
1. Start backend: `python app.py`
2. Start frontend: `npm start`
3. Upload a statement
4. Watch the magic happen! ✨

For detailed documentation, see `IMPORT_SYSTEM_GUIDE.md`
