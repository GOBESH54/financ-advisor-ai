import React, { useState, useEffect } from 'react';
import { analysisAPI } from '../services/api';
import { toast } from 'react-toastify';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Pie } from 'react-chartjs-2';
import { 
  ChartBarIcon, 
  LightBulbIcon, 
  ShieldCheckIcon,
  ArrowTrendingUpIcon 
} from '@heroicons/react/24/outline';

ChartJS.register(ArcElement, Tooltip, Legend);

const InvestmentRecommendations = () => {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInvestmentRecommendations();
  }, []);

  const fetchInvestmentRecommendations = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.getInvestmentRecommendations();
      setRecommendations(response.data);
    } catch (error) {
      toast.error('Failed to fetch investment recommendations');
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!recommendations) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-500">No investment recommendations available</p>
      </div>
    );
  }

  const { investment_type, confidence, allocation, recommendations: specificRecommendations } = recommendations;

  // Prepare chart data for allocation
  const allocationData = {
    labels: ['Stocks', 'Bonds', 'Cash/Emergency'],
    datasets: [{
      data: [
        allocation.stocks || 0,
        allocation.bonds || 0,
        allocation.cash || 0
      ],
      backgroundColor: [
        '#3498db',
        '#2ecc71',
        '#f39c12'
      ],
      borderWidth: 2,
      borderColor: '#fff'
    }],
  };

  const getInvestmentTypeColor = (type) => {
    switch(type) {
      case 'conservative':
        return 'bg-green-100 text-green-800';
      case 'moderate':
        return 'bg-blue-100 text-blue-800';
      case 'aggressive':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getInvestmentTypeIcon = (type) => {
    switch(type) {
      case 'conservative':
        return <ShieldCheckIcon className="h-6 w-6" />;
      case 'moderate':
        return <ChartBarIcon className="h-6 w-6" />;
      case 'aggressive':
        return <ArrowTrendingUpIcon className="h-6 w-6" />;
      default:
        return <LightBulbIcon className="h-6 w-6" />;
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Investment Recommendations</h1>

      {/* Investment Profile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Your Investment Profile</h2>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-500 mb-2">Investment Type</p>
              <div className={`inline-flex items-center space-x-2 px-3 py-2 rounded-lg ${getInvestmentTypeColor(investment_type)}`}>
                {getInvestmentTypeIcon(investment_type)}
                <span className="font-semibold capitalize">{investment_type}</span>
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-2">Confidence Score</p>
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 rounded-full h-4">
                  <div 
                    className="bg-primary h-4 rounded-full"
                    style={{ width: `${confidence * 100}%` }}
                  ></div>
                </div>
                <span className="font-semibold">{(confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Recommended Asset Allocation</h2>
          <div className="flex items-center justify-center">
            <div className="w-64">
              <Pie
                data={allocationData}
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'right',
                    },
                    tooltip: {
                      callbacks: {
                        label: function(context) {
                          return context.label + ': ' + context.parsed + '%';
                        }
                      }
                    }
                  }
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Specific Recommendations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Specific Investment Recommendations</h2>
        {specificRecommendations && specificRecommendations.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {specificRecommendations.map((rec, index) => (
              <div key={index} className="border rounded-lg p-4 hover:shadow-lg transition-shadow">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-lg capitalize">{rec.type}</h3>
                  <span className="text-2xl font-bold text-primary">{rec.allocation_percentage}%</span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Recommended Amount:</span>
                    <span className="font-medium">${rec.amount.toLocaleString()}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-2">{rec.specific}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No specific recommendations available</p>
        )}
      </div>

      {/* Investment Strategy Guide */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Investment Strategy Guide</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <ShieldCheckIcon className="h-6 w-6 text-green-600" />
              <h3 className="font-semibold">Conservative</h3>
            </div>
            <p className="text-sm text-gray-600">
              Focus on capital preservation with 70% bonds, 20% stocks, 10% cash. 
              Suitable for risk-averse investors or those near retirement.
            </p>
          </div>
          
          <div className="bg-white rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <ChartBarIcon className="h-6 w-6 text-blue-600" />
              <h3 className="font-semibold">Moderate</h3>
            </div>
            <p className="text-sm text-gray-600">
              Balanced approach with 60% stocks, 30% bonds, 10% cash. 
              Ideal for investors seeking growth with controlled risk.
            </p>
          </div>
          
          <div className="bg-white rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <ArrowTrendingUpIcon className="h-6 w-6 text-red-600" />
              <h3 className="font-semibold">Aggressive</h3>
            </div>
            <p className="text-sm text-gray-600">
              Growth-focused with 80% stocks, 15% bonds, 5% cash. 
              Best for younger investors with high risk tolerance.
            </p>
          </div>
        </div>
      </div>

      {/* Important Considerations */}
      <div className="bg-yellow-50 rounded-lg p-6 border border-yellow-200">
        <h3 className="font-semibold text-gray-800 mb-3">⚠️ Important Investment Considerations</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>• These recommendations are based on general financial principles and your profile</li>
          <li>• Past performance doesn't guarantee future results</li>
          <li>• Consider consulting with a licensed financial advisor for personalized advice</li>
          <li>• Diversification is key to managing investment risk</li>
          <li>• Regular portfolio rebalancing helps maintain your target allocation</li>
          <li>• Consider tax implications of your investment decisions</li>
        </ul>
      </div>
    </div>
  );
};

export default InvestmentRecommendations;
