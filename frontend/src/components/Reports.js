import React, { useState } from 'react';
import { reportAPI } from '../services/api';
import { toast } from 'react-toastify';
import { 
  DocumentArrowDownIcon, 
  CalendarIcon, 
  ChartBarIcon,
  DocumentTextIcon 
} from '@heroicons/react/24/outline';

const Reports = () => {
  const [generating, setGenerating] = useState(false);
  const [reportType, setReportType] = useState('monthly');

  const handleGenerateReport = async () => {
    try {
      setGenerating(true);
      const response = await reportAPI.generateReport(reportType);
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `financial_report_${reportType}_${new Date().toISOString().split('T')[0]}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Report generated successfully!');
    } catch (error) {
      toast.error('Failed to generate report');
      console.error('Error:', error);
    } finally {
      setGenerating(false);
    }
  };

  const reportTypes = [
    {
      id: 'monthly',
      title: 'Monthly Report',
      description: 'Comprehensive monthly financial overview including income, expenses, budgets, and goals',
      icon: CalendarIcon,
      features: [
        'Income & expense summary',
        'Budget analysis',
        'Savings progress',
        'Debt overview',
        'Monthly trends'
      ]
    },
    {
      id: 'quarterly',
      title: 'Quarterly Report',
      description: 'Three-month financial performance analysis with trends and projections',
      icon: ChartBarIcon,
      features: [
        '3-month comparison',
        'Spending patterns',
        'Investment performance',
        'Goal achievement rate',
        'Quarterly projections'
      ]
    },
    {
      id: 'annual',
      title: 'Annual Report',
      description: 'Complete yearly financial review with detailed analytics and recommendations',
      icon: DocumentTextIcon,
      features: [
        'Year-over-year comparison',
        'Tax summary',
        'Annual budget review',
        'Investment returns',
        'Long-term goal progress'
      ]
    }
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Financial Reports</h1>
      
      <div className="bg-blue-50 rounded-lg p-6">
        <div className="flex items-center space-x-3">
          <DocumentArrowDownIcon className="h-6 w-6 text-blue-600" />
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Generate Financial Reports</h2>
            <p className="text-sm text-gray-600 mt-1">
              Create detailed PDF reports of your financial data for record-keeping and analysis
            </p>
          </div>
        </div>
      </div>

      {/* Report Type Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {reportTypes.map((type) => {
          const Icon = type.icon;
          return (
            <div 
              key={type.id}
              className={`bg-white rounded-lg shadow-lg p-6 cursor-pointer transition-all hover:shadow-xl ${
                reportType === type.id ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => setReportType(type.id)}
            >
              <div className="flex items-center justify-between mb-4">
                <Icon className="h-8 w-8 text-primary" />
                {reportType === type.id && (
                  <span className="text-sm font-semibold text-primary">Selected</span>
                )}
              </div>
              <h3 className="text-lg font-semibold mb-2">{type.title}</h3>
              <p className="text-sm text-gray-600 mb-4">{type.description}</p>
              <div className="space-y-1">
                {type.features.map((feature, index) => (
                  <div key={index} className="flex items-start">
                    <span className="text-green-500 mr-2">✓</span>
                    <span className="text-xs text-gray-700">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Generate Button */}
      <div className="flex justify-center">
        <button
          onClick={handleGenerateReport}
          disabled={generating}
          className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-colors ${
            generating 
              ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
              : 'bg-primary text-white hover:bg-blue-600'
          }`}
        >
          {generating ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              <span>Generating Report...</span>
            </>
          ) : (
            <>
              <DocumentArrowDownIcon className="h-5 w-5" />
              <span>Generate {reportTypes.find(t => t.id === reportType)?.title}</span>
            </>
          )}
        </button>
      </div>

      {/* Report History Section */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Report Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-semibold mb-3">What's Included</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                Executive summary of your financial health
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                Detailed income and expense breakdowns
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                Visual charts and graphs for easy understanding
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                Budget compliance analysis
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                Debt repayment progress tracking
              </li>
              <li className="flex items-start">
                <span className="text-primary mr-2">•</span>
                Savings goals achievement status
              </li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-3">Report Benefits</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                Track financial progress over time
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                Identify spending patterns and trends
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                Make informed financial decisions
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                Share with financial advisors or accountants
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                Keep records for tax purposes
              </li>
              <li className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                Monitor goal achievement progress
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Tips Section */}
      <div className="bg-gray-50 rounded-lg p-6">
        <h3 className="font-semibold text-gray-800 mb-3">📊 Report Tips</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700">
          <div className="flex items-start">
            <span className="text-blue-500 mr-2">💡</span>
            <p>Generate monthly reports regularly to track your financial progress consistently</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-500 mr-2">💡</span>
            <p>Review quarterly reports to identify seasonal spending patterns</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-500 mr-2">💡</span>
            <p>Use annual reports for tax preparation and year-end financial planning</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-500 mr-2">💡</span>
            <p>Keep digital copies of all reports for your financial records</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Reports;
