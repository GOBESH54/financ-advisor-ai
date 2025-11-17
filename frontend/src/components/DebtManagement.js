import React, { useState, useEffect } from 'react';
import { debtAPI, analysisAPI } from '../services/api';
import { toast } from 'react-toastify';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { PlusIcon, TrashIcon, CalculatorIcon } from '@heroicons/react/24/outline';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const DebtManagement = () => {
  const [debts, setDebts] = useState([]);
  const [debtAnalysis, setDebtAnalysis] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [extraPayment, setExtraPayment] = useState(0);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    principal_amount: '',
    current_balance: '',
    interest_rate: '',
    minimum_payment: '',
    due_date: ''
  });

  useEffect(() => {
    fetchDebts();
  }, []);

  useEffect(() => {
    if (debts.length > 0) {
      analyzeDebts();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debts, extraPayment]);

  const fetchDebts = async () => {
    try {
      const response = await debtAPI.getAll();
      setDebts(response.data);
    } catch (error) {
      toast.error('Failed to fetch debts');
      console.error('Error:', error);
    }
  };

  const analyzeDebts = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.getDebtAnalysis(extraPayment);
      setDebtAnalysis(response.data);
    } catch (error) {
      console.error('Error analyzing debts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await debtAPI.add({
        name: formData.name,
        principal_amount: parseFloat(formData.principal_amount),
        current_balance: parseFloat(formData.current_balance),
        interest_rate: parseFloat(formData.interest_rate),
        minimum_payment: parseFloat(formData.minimum_payment),
        due_date: formData.due_date || null
      });
      toast.success('Debt added successfully');
      setShowAddForm(false);
      setFormData({
        name: '',
        principal_amount: '',
        current_balance: '',
        interest_rate: '',
        minimum_payment: '',
        due_date: ''
      });
      fetchDebts();
    } catch (error) {
      toast.error('Failed to add debt');
      console.error('Error:', error);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this debt?')) {
      try {
        await debtAPI.delete(id);
        toast.success('Debt deleted successfully');
        fetchDebts();
      } catch (error) {
        toast.error('Failed to delete debt');
        console.error('Error:', error);
      }
    }
  };

  const getStrategyColor = (strategy) => {
    switch(strategy) {
      case 'avalanche':
        return 'bg-blue-100 text-blue-800';
      case 'snowball':
        return 'bg-green-100 text-green-800';
      case 'hybrid':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Prepare chart data for strategy comparison
  const strategyChartData = debtAnalysis?.comparison && !loading ? {
    labels: Object.keys(debtAnalysis.comparison.strategies),
    datasets: [
      {
        label: 'Total Interest',
        data: Object.values(debtAnalysis.comparison.strategies).map(s => s.total_interest),
        backgroundColor: 'rgba(231, 76, 60, 0.6)',
      },
      {
        label: 'Payoff Months',
        data: Object.values(debtAnalysis.comparison.strategies).map(s => s.payoff_months),
        backgroundColor: 'rgba(52, 152, 219, 0.6)',
      }
    ],
  } : null;

  const totalDebt = debts.reduce((sum, debt) => sum + debt.current_balance, 0);
  const totalMinPayment = debts.reduce((sum, debt) => sum + debt.minimum_payment, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Debt Management</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Debt</p>
          <p className="text-2xl font-bold text-red-600">${totalDebt.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Monthly Minimum</p>
          <p className="text-2xl font-bold text-orange-600">${totalMinPayment.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Number of Debts</p>
          <p className="text-2xl font-bold text-gray-700">{debts.length}</p>
        </div>
      </div>

      {/* Add Debt Button */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center space-x-2 bg-primary text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Add Debt</span>
        </button>

        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-700">Extra Monthly Payment:</label>
          <input
            type="number"
            value={extraPayment}
            onChange={(e) => setExtraPayment(parseFloat(e.target.value) || 0)}
            className="w-32 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
            placeholder="0"
            step="50"
          />
        </div>
      </div>

      {/* Add Debt Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Add New Debt</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Debt Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Original Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.principal_amount}
                onChange={(e) => setFormData({ ...formData, principal_amount: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Balance</label>
              <input
                type="number"
                step="0.01"
                value={formData.current_balance}
                onChange={(e) => setFormData({ ...formData, current_balance: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Interest Rate (%)</label>
              <input
                type="number"
                step="0.01"
                value={formData.interest_rate}
                onChange={(e) => setFormData({ ...formData, interest_rate: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Minimum Payment</label>
              <input
                type="number"
                step="0.01"
                value={formData.minimum_payment}
                onChange={(e) => setFormData({ ...formData, minimum_payment: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Due Date (Optional)</label>
              <input
                type="date"
                value={formData.due_date}
                onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
              />
            </div>
            <div className="md:col-span-2 flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                Add Debt
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Debt List */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-3 bg-gray-50 border-b">
          <h2 className="text-lg font-semibold">Your Debts</h2>
        </div>
        {debts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Balance</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Interest Rate</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Min Payment</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {debts.map((debt) => (
                  <tr key={debt.id}>
                    <td className="px-6 py-4 whitespace-nowrap font-medium">{debt.name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-red-600 font-medium">
                      ${debt.current_balance.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">{debt.interest_rate}%</td>
                    <td className="px-6 py-4 whitespace-nowrap">${debt.minimum_payment}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <button
                        onClick={() => handleDelete(debt.id)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-center py-8 text-gray-500">No debts recorded</p>
        )}
      </div>

      {/* Debt Repayment Strategies */}
      {debtAnalysis && debts.length > 0 && !loading && (
        <>
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Repayment Strategy Comparison</h2>
            {debtAnalysis.comparison && (
              <div className="space-y-4">
                <div className="flex items-center space-x-2 mb-4">
                  <CalculatorIcon className="h-5 w-5 text-gray-600" />
                  <span className="text-sm text-gray-600">
                    Analysis based on ${totalMinPayment + extraPayment}/month payment
                  </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.entries(debtAnalysis.comparison.strategies).map(([strategy, data]) => (
                    <div 
                      key={strategy} 
                      className={`border rounded-lg p-4 ${
                        strategy === debtAnalysis.comparison.recommended ? 'border-primary border-2' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className={`px-2 py-1 rounded text-sm font-semibold capitalize ${getStrategyColor(strategy)}`}>
                          {strategy}
                        </span>
                        {strategy === debtAnalysis.comparison.recommended && (
                          <span className="text-xs text-primary font-semibold">RECOMMENDED</span>
                        )}
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Total Interest:</span>
                          <span className="font-medium">${data.total_interest.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-500">Payoff Time:</span>
                          <span className="font-medium">{data.payoff_months} months</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {strategyChartData && (
                  <div className="mt-6">
                    <Bar
                      data={strategyChartData}
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
                            beginAtZero: true
                          }
                        }
                      }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Detailed Repayment Plan */}
          {debtAnalysis.recommended_plan && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold mb-4">
                Recommended Repayment Plan ({debtAnalysis.recommended_plan.strategy})
              </h2>
              <div className="space-y-4">
                {debtAnalysis.recommended_plan.plan.map((debt, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">{debt.debt_name}</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm">
                      <div>
                        <span className="text-gray-500">Balance:</span>
                        <span className="ml-2 font-medium">${debt.original_balance.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Payment:</span>
                        <span className="ml-2 font-medium">${debt.monthly_payment.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Payoff:</span>
                        <span className="ml-2 font-medium">{debt.payoff_months} months</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Total Interest:</span>
                        <span className="ml-2 font-medium">${debt.total_interest.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default DebtManagement;
