import React, { useState, useEffect } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title } from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';
import { dashboardAPI } from '../services/api';
import { toast } from 'react-toastify';
import { 
  CurrencyDollarIcon, 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon,
  BanknotesIcon 
} from '@heroicons/react/24/outline';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await dashboardAPI.getSummary();
      setDashboardData(response.data);
    } catch (error) {
      toast.error('Failed to fetch dashboard data');
      console.error('Error fetching dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="text-center py-10">
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  const { summary, expense_breakdown, recent_transactions, goals_progress } = dashboardData;

  // Prepare chart data for expense breakdown
  const expenseChartData = {
    labels: Object.keys(expense_breakdown || {}),
    datasets: [{
      data: Object.values(expense_breakdown || {}),
      backgroundColor: [
        '#3498db',
        '#2ecc71',
        '#e74c3c',
        '#f39c12',
        '#9b59b6',
        '#1abc9c',
        '#34495e',
        '#e67e22',
      ],
    }],
  };

  // Prepare data for income vs expenses bar chart
  const incomeExpenseData = {
    labels: ['Income', 'Expenses', 'Net Savings'],
    datasets: [{
      label: 'Monthly Amount',
      data: [summary.total_income, summary.total_expenses, summary.net_savings],
      backgroundColor: ['#2ecc71', '#e74c3c', '#3498db'],
    }],
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Financial Dashboard</h1>
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Monthly Income</p>
              <p className="text-2xl font-bold text-green-600">
                ${summary.total_income?.toLocaleString() || 0}
              </p>
            </div>
            <ArrowTrendingUpIcon className="h-10 w-10 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Monthly Expenses</p>
              <p className="text-2xl font-bold text-red-600">
                ${summary.total_expenses?.toLocaleString() || 0}
              </p>
            </div>
            <ArrowTrendingDownIcon className="h-10 w-10 text-red-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Net Savings</p>
              <p className={`text-2xl font-bold ${summary.net_savings >= 0 ? 'text-blue-600' : 'text-red-600'}`}>
                ${summary.net_savings?.toLocaleString() || 0}
              </p>
            </div>
            <BanknotesIcon className="h-10 w-10 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Debt</p>
              <p className="text-2xl font-bold text-orange-600">
                ${summary.total_debt?.toLocaleString() || 0}
              </p>
            </div>
            <CurrencyDollarIcon className="h-10 w-10 text-orange-500" />
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Income vs Expenses Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Income vs Expenses</h2>
          <Bar 
            data={incomeExpenseData}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  display: false,
                },
                title: {
                  display: false,
                },
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

        {/* Expense Breakdown Pie Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Expense Breakdown</h2>
          {Object.keys(expense_breakdown || {}).length > 0 ? (
            <Pie 
              data={expenseChartData}
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
          ) : (
            <p className="text-gray-500 text-center py-10">No expense data available</p>
          )}
        </div>
      </div>

      {/* Recent Transactions and Goals Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Transactions */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Recent Transactions</h2>
          <div className="space-y-3">
            {recent_transactions && recent_transactions.length > 0 ? (
              recent_transactions.map((transaction, index) => (
                <div key={index} className="flex justify-between items-center py-2 border-b">
                  <div>
                    <p className="font-medium">{transaction.description}</p>
                    <p className="text-sm text-gray-500">
                      {transaction.type === 'income' ? 'Income' : 'Expense'}
                    </p>
                  </div>
                  <p className={`font-bold ${transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    ${Math.abs(transaction.amount).toLocaleString()}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-gray-500">No recent transactions</p>
            )}
          </div>
        </div>

        {/* Savings Goals Progress */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Savings Goals Progress</h2>
          <div className="space-y-4">
            {goals_progress && goals_progress.length > 0 ? (
              goals_progress.map((goal, index) => (
                <div key={index}>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm font-medium">{goal.name}</span>
                    <span className="text-sm text-gray-500">{goal.progress.toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div 
                      className="bg-primary h-2.5 rounded-full" 
                      style={{ width: `${Math.min(goal.progress, 100)}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    ${goal.remaining.toLocaleString()} remaining
                  </p>
                </div>
              ))
            ) : (
              <p className="text-gray-500">No savings goals set</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
