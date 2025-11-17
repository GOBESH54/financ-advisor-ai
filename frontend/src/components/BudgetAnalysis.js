import React, { useState, useEffect } from 'react';
import { analysisAPI } from '../services/api';
import { toast } from 'react-toastify';
import { Chart as ChartJS, ArcElement, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { ExclamationTriangleIcon, CheckCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline';

ChartJS.register(ArcElement, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const BudgetAnalysis = () => {
  const [budgetAnalysis, setBudgetAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBudgetAnalysis();
  }, []);

  const fetchBudgetAnalysis = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.getBudgetAnalysis();
      setBudgetAnalysis(response.data);
    } catch (error) {
      toast.error('Failed to fetch budget analysis');
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

  if (!budgetAnalysis) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-500">No budget analysis available</p>
      </div>
    );
  }

  const { current_allocation, recommended_allocation, recommendations, budget_health_score } = budgetAnalysis;

  // Prepare chart data for current vs recommended allocation
  const comparisonData = {
    labels: ['Needs', 'Wants', 'Savings', 'Debt'],
    datasets: [
      {
        label: 'Current Allocation',
        data: [
          current_allocation.needs || 0,
          current_allocation.wants || 0,
          current_allocation.savings || 0,
          current_allocation.debt || 0
        ],
        backgroundColor: 'rgba(52, 152, 219, 0.6)',
      },
      {
        label: 'Recommended Allocation',
        data: [
          recommended_allocation.needs || 0,
          recommended_allocation.wants || 0,
          recommended_allocation.savings || 0,
          recommended_allocation.debt || 0
        ],
        backgroundColor: 'rgba(46, 204, 113, 0.6)',
      }
    ],
  };

  // Prepare doughnut chart for current allocation
  const currentAllocationData = {
    labels: ['Needs', 'Wants', 'Savings', 'Debt'],
    datasets: [{
      data: [
        current_allocation.needs || 0,
        current_allocation.wants || 0,
        current_allocation.savings || 0,
        current_allocation.debt || 0
      ],
      backgroundColor: [
        '#3498db',
        '#f39c12',
        '#2ecc71',
        '#e74c3c'
      ],
    }],
  };

  const getHealthScoreColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthScoreLabel = (score) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Needs Improvement';
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Budget Analysis</h1>

      {/* Budget Health Score */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Budget Health Score</h2>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <svg className="w-32 h-32">
              <circle
                className="text-gray-300"
                strokeWidth="10"
                stroke="currentColor"
                fill="transparent"
                r="56"
                cx="64"
                cy="64"
              />
              <circle
                className={getHealthScoreColor(budget_health_score)}
                strokeWidth="10"
                strokeDasharray={`${budget_health_score * 3.52} 352`}
                strokeLinecap="round"
                stroke="currentColor"
                fill="transparent"
                r="56"
                cx="64"
                cy="64"
                transform="rotate(-90 64 64)"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className={`text-3xl font-bold ${getHealthScoreColor(budget_health_score)}`}>
                {budget_health_score.toFixed(0)}
              </span>
            </div>
          </div>
          <div>
            <p className={`text-2xl font-semibold ${getHealthScoreColor(budget_health_score)}`}>
              {getHealthScoreLabel(budget_health_score)}
            </p>
            <p className="text-gray-600">Your budget health is based on the 50/30/20 rule</p>
          </div>
        </div>
      </div>

      {/* Allocation Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Current Budget Allocation</h2>
          <Doughnut
            data={currentAllocationData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: 'bottom',
                },
                tooltip: {
                  callbacks: {
                    label: function(context) {
                      return context.label + ': $' + context.parsed.toLocaleString();
                    }
                  }
                }
              }
            }}
          />
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Current vs Recommended</h2>
          <Bar
            data={comparisonData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: 'top',
                },
                title: {
                  display: false,
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  ticks: {
                    callback: function(value) {
                      return '$' + value.toLocaleString();
                    }
                  }
                }
              }
            }}
          />
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recommendations</h2>
        {recommendations && recommendations.length > 0 ? (
          <div className="space-y-4">
            {recommendations.map((rec, index) => (
              <div key={index} className="border-l-4 border-warning p-4 bg-yellow-50">
                <div className="flex items-start">
                  <ExclamationTriangleIcon className="h-6 w-6 text-warning mr-3 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-800 capitalize">
                      {rec.category} - {rec.issue.replace('_', ' ')}
                    </h3>
                    <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2">
                      <div>
                        <span className="text-sm text-gray-600">Current:</span>
                        <span className="ml-2 font-medium">${rec.actual.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-600">Recommended:</span>
                        <span className="ml-2 font-medium">${rec.recommended.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-sm text-gray-600">Difference:</span>
                        <span className="ml-2 font-medium text-red-600">
                          ${Math.abs(rec.actual - rec.recommended).toFixed(2)}
                        </span>
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-gray-700">{rec.action}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center space-x-3 text-green-600">
            <CheckCircleIcon className="h-6 w-6" />
            <p>Your budget is well-balanced! Keep up the good work.</p>
          </div>
        )}
      </div>

      {/* Budget Tips */}
      <div className="bg-blue-50 rounded-lg p-6">
        <div className="flex items-start">
          <InformationCircleIcon className="h-6 w-6 text-primary mr-3 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-gray-800 mb-2">Budget Tips</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
              <li>The 50/30/20 rule suggests spending 50% on needs, 30% on wants, and 20% on savings</li>
              <li>Track your expenses regularly to identify areas where you can cut back</li>
              <li>Automate your savings to ensure you meet your savings goals</li>
              <li>Review and adjust your budget monthly based on your actual spending</li>
              <li>Consider using cash envelopes for discretionary spending categories</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BudgetAnalysis;
