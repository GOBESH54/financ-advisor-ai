import React, { useState, useCallback } from 'react';
import { statementAPI } from '../services/api';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Checkbox,
  Tooltip,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Fade,
  Zoom,
  CircularProgress,
  Snackbar
} from '@mui/material';
import {
  CloudUpload,
  Description,
  CheckCircle,
  Preview,
  AccountBalance,
  TrendingUp,
  DateRange,
  AttachMoney,
  Refresh,
  GetApp
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';
import { styled } from '@mui/material/styles';

const DropzoneContainer = styled(Card, {
  shouldForwardProp: (prop) => prop !== 'isDragActive'
})(({ theme, isDragActive }) => ({
  border: `2px dashed ${isDragActive ? theme.palette.primary.main : theme.palette.grey[300]}`,
  borderRadius: theme.spacing(2),
  padding: theme.spacing(4),
  textAlign: 'center',
  cursor: 'pointer',
  transition: 'all 0.3s ease',
  backgroundColor: isDragActive ? theme.palette.primary.light + '10' : 'transparent',
  '&:hover': {
    borderColor: theme.palette.primary.main,
    backgroundColor: theme.palette.primary.light + '05',
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[4]
  }
}));

const StatCard = styled(Card)(({ theme }) => ({
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  color: 'white',
  transition: 'transform 0.3s ease',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[8]
  }
}));

const CategoryChip = styled(Chip)(({ theme }) => ({
  margin: theme.spacing(0.5),
  borderRadius: theme.spacing(2),
  fontWeight: 600,
  '&.credit': {
    backgroundColor: '#4caf50',
    color: 'white'
  },
  '&.debit': {
    backgroundColor: '#f44336',
    color: 'white'
  }
}));

const BankStatementUpload = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [parsing, setParsing] = useState(false);
  const [parsedData, setParsedData] = useState(null);
  const [selectedTransactions, setSelectedTransactions] = useState([]);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const supportedBanks = [
    { code: 'HDFC', name: 'HDFC Bank', icon: '🏦' },
    { code: 'ICICI', name: 'ICICI Bank', icon: '🏦' },
    { code: 'SBI', name: 'State Bank of India', icon: '🏦' },
    { code: 'AXIS', name: 'Axis Bank', icon: '🏦' },
    { code: 'KOTAK', name: 'Kotak Mahindra Bank', icon: '🏦' }
  ];

  const supportedFormats = [
    { ext: 'PDF', icon: '📄', desc: 'Bank statement PDFs' },
    { ext: 'CSV', icon: '📊', desc: 'Comma-separated values' },
    { ext: 'Excel', icon: '📈', desc: 'Excel spreadsheets' },
    { ext: 'Image', icon: '🖼️', desc: 'JPG, PNG images (OCR)' }
  ];

  const onDrop = useCallback((acceptedFiles) => {
    const file = acceptedFiles[0];
    if (file) {
      setUploadedFile(file);
      setActiveStep(1);
      handleFileUpload(file);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxFiles: 1,
    maxSize: 16 * 1024 * 1024 // 16MB
  });

  const handleFileUpload = async (file) => {
    setParsing(true);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', '1'); // Replace with actual user ID

    try {
      const response = await statementAPI.uploadStatement(formData);
      
      if (response.data.success) {
        setParsedData(response.data);
        setSelectedTransactions(response.data.transactions.map((_, idx) => idx));
        setActiveStep(2);
        setSnackbar({
          open: true,
          message: `Successfully parsed ${response.data.total_transactions} transactions!`,
          severity: 'success'
        });
      } else {
        throw new Error(response.data.error || 'Failed to parse statement');
      }
    } catch (error) {
      setSnackbar({
        open: true,
        message: `Error: ${error.response?.data?.error || error.message || 'Failed to upload file'}`,
        severity: 'error'
      });
    } finally {
      setParsing(false);
    }
  };

  const handleImportTransactions = async () => {
    if (!parsedData || selectedTransactions.length === 0) return;

    console.log('Starting import...');
    setImporting(true);
    setActiveStep(3);

    const transactionsToImport = parsedData.transactions.filter((_, idx) => 
      selectedTransactions.includes(idx)
    );

    console.log('Transactions to import:', transactionsToImport.length);
    console.log('Sample transaction:', transactionsToImport[0]);

    try {
      console.log('Making import request...');
      console.log('Request payload:', JSON.stringify(transactionsToImport, null, 2));
      
      const response = await statementAPI.importTransactions(transactionsToImport);
      const result = response.data;
      
      console.log('Import result:', result);
      
      if (result.success) {
        setImportResult(result);
        setActiveStep(4);
        
        let message = `Successfully imported ${result.imported} transactions!`;
        if (result.errors && result.errors.length > 0) {
          message += ` (${result.errors.length} errors occurred)`;
        }
        
        setSnackbar({
          open: true,
          message: message,
          severity: result.errors && result.errors.length > 0 ? 'warning' : 'success'
        });
      } else {
        throw new Error(result.error || 'Failed to import transactions');
      }
    } catch (error) {
      console.error('Import error:', error);
      console.error('Error details:', error.response?.data);
      
      const errorMessage = error.response?.data?.error || error.message || 'Failed to import transactions';
      
      setSnackbar({
        open: true,
        message: `Import Error: ${errorMessage}`,
        severity: 'error'
      });
      setActiveStep(2); // Go back to review step
    } finally {
      setImporting(false);
    }
  };

  const handleTransactionSelect = (index) => {
    setSelectedTransactions(prev => 
      prev.includes(index) 
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  const resetUpload = () => {
    setActiveStep(0);
    setUploadedFile(null);
    setParsedData(null);
    setSelectedTransactions([]);
    setImportResult(null);
  };

  const getCategoryIcon = (category) => {
    const icons = {
      'food_dining': '🍽️', 'groceries': '🛒', 'fuel': '⛽', 'utilities': '💡',
      'entertainment': '🎬', 'transportation': '🚗', 'shopping': '🛍️',
      'medical': '🏥', 'education': '📚', 'investment': '📈',
      'transfer': '💸', 'salary': '💰', 'bank_charges': '🏦',
      'cash_withdrawal': '💳', 'others': '📝'
    };
    return icons[category] || '📝';
  };

  return (
    <Box sx={{ maxWidth: 1200, margin: 'auto', p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography variant="h3" component="h1" sx={{ 
          fontWeight: 'bold', 
          background: 'linear-gradient(45deg, #2196F3 30%, #21CBF3 90%)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          mb: 2
        }}>
          🏦 Smart Bank Statement Reader
        </Typography>
        <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
          Upload your bank statement and let AI automatically categorize your transactions
        </Typography>
      </Box>

      {/* Supported Banks */}
      <Card sx={{ mb: 4, overflow: 'visible' }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center' }}>
            <AccountBalance sx={{ mr: 1, color: 'primary.main' }} />
            Supported Banks
          </Typography>
          <Grid container spacing={2}>
            {supportedBanks.map((bank) => (
              <Grid item xs={6} sm={4} md={2.4} key={bank.code}>
                <Tooltip title={`${bank.name} statements supported`}>
                  <Card sx={{ 
                    p: 2, 
                    textAlign: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    '&:hover': {
                      transform: 'scale(1.05)',
                      boxShadow: 4
                    }
                  }}>
                    <Typography variant="h4">{bank.icon}</Typography>
                    <Typography variant="caption" display="block">
                      {bank.name}
                    </Typography>
                  </Card>
                </Tooltip>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Upload Stepper */}
      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Stepper activeStep={activeStep} orientation="vertical">
            {/* Step 1: Upload */}
            <Step>
              <StepLabel>
                <Typography variant="h6">Upload Bank Statement</Typography>
              </StepLabel>
              <StepContent>
                <Fade in={activeStep === 0}>
                  <Box>
                    <DropzoneContainer isDragActive={isDragActive} {...getRootProps()}>
                      <input {...getInputProps()} />
                      <CloudUpload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                      <Typography variant="h6" sx={{ mb: 2 }}>
                        {isDragActive ? 'Drop your statement here!' : 'Drag & drop your bank statement'}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                        Or click to browse files
                      </Typography>
                      
                      {/* Supported Formats */}
                      <Grid container spacing={2} justifyContent="center">
                        {supportedFormats.map((format) => (
                          <Grid item key={format.ext}>
                            <Chip
                              icon={<span>{format.icon}</span>}
                              label={format.ext}
                              variant="outlined"
                              size="small"
                            />
                          </Grid>
                        ))}
                      </Grid>
                    </DropzoneContainer>

                    {uploadedFile && (
                      <Zoom in={Boolean(uploadedFile)}>
                        <Alert severity="info" sx={{ mt: 2 }}>
                          <strong>File selected:</strong> {uploadedFile.name} 
                          ({(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)
                        </Alert>
                      </Zoom>
                    )}
                  </Box>
                </Fade>
              </StepContent>
            </Step>

            {/* Step 2: Processing */}
            <Step>
              <StepLabel>
                <Typography variant="h6">Processing Statement</Typography>
              </StepLabel>
              <StepContent>
                {parsing ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <CircularProgress size={60} sx={{ mb: 2 }} />
                    <Typography variant="h6">Analyzing your statement...</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Our AI is reading and categorizing your transactions
                    </Typography>
                  </Box>
                ) : parsedData && (
                  <Fade in={Boolean(parsedData)}>
                    <Box>
                      {/* Summary Cards */}
                      <Grid container spacing={3} sx={{ mb: 3 }}>
                        <Grid item xs={12} sm={6} md={3}>
                          <StatCard>
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                <Description sx={{ fontSize: 40, mr: 2 }} />
                                <Box>
                                  <Typography variant="h4">
                                    {parsedData.total_transactions}
                                  </Typography>
                                  <Typography variant="body2">
                                    Total Transactions
                                  </Typography>
                                </Box>
                              </Box>
                            </CardContent>
                          </StatCard>
                        </Grid>
                        
                        <Grid item xs={12} sm={6} md={3}>
                          <StatCard sx={{ background: 'linear-gradient(135deg, #4caf50 0%, #45a047 100%)' }}>
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                <TrendingUp sx={{ fontSize: 40, mr: 2 }} />
                                <Box>
                                  <Typography variant="h5">
                                    ₹{parsedData.summary?.total_credits?.toLocaleString() || '0'}
                                  </Typography>
                                  <Typography variant="body2">
                                    Total Credits
                                  </Typography>
                                </Box>
                              </Box>
                            </CardContent>
                          </StatCard>
                        </Grid>

                        <Grid item xs={12} sm={6} md={3}>
                          <StatCard sx={{ background: 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)' }}>
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                <AttachMoney sx={{ fontSize: 40, mr: 2 }} />
                                <Box>
                                  <Typography variant="h5">
                                    ₹{parsedData.summary?.total_debits?.toLocaleString() || '0'}
                                  </Typography>
                                  <Typography variant="body2">
                                    Total Debits
                                  </Typography>
                                </Box>
                              </Box>
                            </CardContent>
                          </StatCard>
                        </Grid>

                        <Grid item xs={12} sm={6} md={3}>
                          <StatCard sx={{ background: 'linear-gradient(135deg, #ff9800 0%, #f57c00 100%)' }}>
                            <CardContent>
                              <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                <DateRange sx={{ fontSize: 40, mr: 2 }} />
                                <Box>
                                  <Typography variant="body1">
                                    {parsedData.summary?.date_range?.start} - {parsedData.summary?.date_range?.end}
                                  </Typography>
                                  <Typography variant="body2">
                                    Date Range
                                  </Typography>
                                </Box>
                              </Box>
                            </CardContent>
                          </StatCard>
                        </Grid>
                      </Grid>

                      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                        <Button
                          variant="contained"
                          startIcon={<Preview />}
                          onClick={() => setPreviewOpen(true)}
                          size="large"
                        >
                          Preview Transactions
                        </Button>
                        <Button
                          variant="outlined"
                          startIcon={<GetApp />}
                          onClick={handleImportTransactions}
                          disabled={selectedTransactions.length === 0}
                          size="large"
                        >
                          Import Selected ({selectedTransactions.length})
                        </Button>
                      </Box>
                    </Box>
                  </Fade>
                )}
              </StepContent>
            </Step>

            {/* Step 3: Import */}
            <Step>
              <StepLabel>
                <Typography variant="h6">Importing Transactions</Typography>
              </StepLabel>
              <StepContent>
                {importing ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <CircularProgress size={60} sx={{ mb: 2 }} />
                    <Typography variant="h6">Importing transactions...</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Adding transactions to your account
                    </Typography>
                  </Box>
                ) : null}
              </StepContent>
            </Step>

            {/* Step 4: Complete */}
            <Step>
              <StepLabel>
                <Typography variant="h6">Import Complete</Typography>
              </StepLabel>
              <StepContent>
                {importResult && (
                  <Fade in={Boolean(importResult)}>
                    <Box sx={{ textAlign: 'center', py: 4 }}>
                      <CheckCircle sx={{ 
                        fontSize: 80, 
                        color: 'success.main', 
                        mb: 2 
                      }} />
                      <Typography variant="h5" sx={{ mb: 2 }}>
                        Successfully Imported!
                      </Typography>
                      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
                        {importResult.imported} transactions have been added to your account
                      </Typography>
                      
                      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                        <Button
                          variant="contained"
                          onClick={() => window.location.href = '/dashboard'}
                          size="large"
                        >
                          View Dashboard
                        </Button>
                        <Button
                          variant="outlined"
                          onClick={resetUpload}
                          startIcon={<Refresh />}
                          size="large"
                        >
                          Upload Another Statement
                        </Button>
                      </Box>
                    </Box>
                  </Fade>
                )}
              </StepContent>
            </Step>
          </Stepper>
        </CardContent>
      </Card>

      {/* Transaction Preview Dialog */}
      <Dialog
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          <Typography variant="h6">Transaction Preview</Typography>
          <Typography variant="body2" color="text.secondary">
            Select transactions to import (duplicates are automatically detected)
          </Typography>
        </DialogTitle>
        
        <DialogContent>
          {parsedData && (
            <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
              <Table stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selectedTransactions.length === parsedData.transactions.length}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedTransactions(parsedData.transactions.map((_, idx) => idx));
                          } else {
                            setSelectedTransactions([]);
                          }
                        }}
                      />
                    </TableCell>
                    <TableCell>Date</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell align="right">Amount</TableCell>
                    <TableCell>Type</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {parsedData.transactions.map((transaction, index) => (
                    <TableRow key={index}>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={selectedTransactions.includes(index)}
                          onChange={() => handleTransactionSelect(index)}
                        />
                      </TableCell>
                      <TableCell>{transaction.formatted_date}</TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap>
                          {transaction.description?.substring(0, 50)}...
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <span style={{ marginRight: 8 }}>
                            {getCategoryIcon(transaction.category)}
                          </span>
                          <Typography variant="caption">
                            {transaction.category?.replace('_', ' ')}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        <Typography
                          variant="body2"
                          sx={{
                            color: transaction.type === 'credit' ? 'success.main' : 'error.main',
                            fontWeight: 'bold'
                          }}
                        >
                          {transaction.formatted_amount}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <CategoryChip
                          label={transaction.type}
                          size="small"
                          className={transaction.type}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setPreviewOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => {
              setPreviewOpen(false);
              handleImportTransactions();
            }}
            disabled={selectedTransactions.length === 0}
          >
            Import Selected ({selectedTransactions.length})
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert 
          severity={snackbar.severity} 
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default BankStatementUpload;
