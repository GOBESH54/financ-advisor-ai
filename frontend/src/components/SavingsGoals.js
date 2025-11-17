import React, { useState, useEffect } from 'react';
import { savingsGoalsAPI, analysisAPI } from '../services/api';
import { toast } from 'react-toastify';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { PlusIcon, TrashIcon, TrophyIcon } from '@heroicons/react/24/outline';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const SavingsGoals = () => {
  const [goals, setGoals] = useState([]);
  const [savingsForecast, setSavingsForecast] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    target_amount: '',
    current_amount: '',
    target_date: '',
    priority: 'medium'
  });

  useEffect(() => {
    fetchGoals();
    fetchSavingsForecast();
  }, []);

  const fetchGoals = async () => {
    try {
      const response = await savingsGoalsAPI.getAll();
      setGoals(response.data);
    } catch (error) {
      toast.error('Failed to fetch savings goals');
      console.error('Error:', error);
    }
  };

  const fetchSavingsForecast = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.getSavingsForecast();
      setSavingsForecast(response.data);
    } catch (error) {
      console.error('Error fetching forecast:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await savingsGoalsAPI.add({
        name: formData.name,
        target_amount: parseFloat(formData.target_amount),
        current_amount: parseFloat(formData.current_amount) || 0,
        target_date: formData.target_date || null,
        priority: formData.priority
      });
      toast.success('Savings goal added successfully');
      setShowAddForm(false);
      setFormData({
        name: '',
        target_amount: '',
        current_amount: '',
        target_date: '',
        priority: 'medium'
      });
      fetchGoals();
    } catch (error) {
      toast.error('Failed to add savings goal');
      console.error('Error:', error);
    }
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this savings goal?')) {
      try {
        await savingsGoalsAPI.delete(id);
        toast.success('Savings goal deleted successfully');
        fetchGoals();
      } catch (error) {
        toast.error('Failed to delete savings goal');
        console.error('Error:', error);
      }
    }
  };

  const updateProgress = async (id, newAmount) => {
    try {
      const goal = goals.find(g => g.id === id);
      await savingsGoalsAPI.update(id, {
        ...goal,
        current_amount: parseFloat(newAmount)
      });
      toast.success('Progress updated successfully');
      fetchGoals();
    } catch (error) {
      toast.error('Failed to update progress');
      console.error('Error:', error);
    }
  };

  const getPriorityColor = (priority) => {
    switch(priority) {
      case 'high':
        return 'text-red-600 bg-red-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getProgressColor = (progress) => {
    if (progress >= 80) return 'bg-green-500';
    if (progress >= 50) return 'bg-yellow-500';
    if (progress >= 25) return 'bg-orange-500';
    return 'bg-red-500';
  };

  // Prepare forecast chart data
  const forecastChartData = savingsForecast?.forecast ? {
    labels: savingsForecast.forecast.map((_, index) => `Month ${index + 1}`),
    datasets: [
      {
        label: 'Projected Savings',
        data: savingsForecast.forecast.map(f => f.forecast),
        borderColor: 'rgb(52, 152, 219)',
        backgroundColor: 'rgba(52, 152, 219, 0.1)',
        tension: 0.4
      },
      {
        label: 'Upper Bound',
        data: savingsForecast.forecast.map(f => f.upper_bound),
        borderColor: 'rgba(46, 204, 113, 0.5)',
        borderDash: [5, 5],
        backgroundColor: 'transparent',
        pointRadius: 0
      },
      {
        label: 'Lower Bound',
        data: savingsForecast.forecast.map(f => f.lower_bound),
        borderColor: 'rgba(231, 76, 60, 0.5)',
        borderDash: [5, 5],
        backgroundColor: 'transparent',
        pointRadius: 0
      }
    ]
  } : null;

  const totalTargetAmount = goals.reduce((sum, goal) => sum + goal.target_amount, 0);
  const totalCurrentAmount = goals.reduce((sum, goal) => sum + goal.current_amount, 0);
  const overallProgress = totalTargetAmount > 0 ? (totalCurrentAmount / totalTargetAmount * 100) : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Savings Goals</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Goals</p>
          <p className="text-2xl font-bold text-gray-700">{goals.length}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Target</p>
          <p className="text-2xl font-bold text-primary">${totalTargetAmount.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Current Savings</p>
          <p className="text-2xl font-bold text-green-600">${totalCurrentAmount.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Overall Progress</p>
          <p className="text-2xl font-bold text-blue-600">{overallProgress.toFixed(1)}%</p>
        </div>
      </div>

      {/* Add Goal Button */}
      <div className="flex justify-end">
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="flex items-center space-x-2 bg-primary text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          <span>Add Savings Goal</span>
        </button>
      </div>

      {/* Add Goal Form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Add New Savings Goal</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Goal Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                placeholder="e.g., Emergency Fund, Vacation, New Car"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.target_amount}
                onChange={(e) => setFormData({ ...formData, target_amount: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Amount</label>
              <input
                type="number"
                step="0.01"
                value={formData.current_amount}
                onChange={(e) => setFormData({ ...formData, current_amount: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
                placeholder="0"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Target Date</label>
              <input
                type="date"
                value={formData.target_date}
                onChange={(e) => setFormData({ ...formData, target_date: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
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
                Add Goal
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Goals List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {goals.map((goal) => {
          const progress = goal.target_amount > 0 ? (goal.current_amount / goal.target_amount * 100) : 0;
          const remaining = goal.target_amount - goal.current_amount;
          const daysUntilTarget = goal.target_date ? 
            Math.ceil((new Date(goal.target_date) - new Date()) / (1000 * 60 * 60 * 24)) : null;

          return (
            <div key={goal.id} className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold flex items-center space-x-2">
                    <TrophyIcon className="h-5 w-5 text-yellow-500" />
                    <span>{goal.name}</span>
                  </h3>
                  <span className={`inline-block mt-1 px-2 py-1 rounded text-xs font-medium ${getPriorityColor(goal.priority)}`}>
                    {goal.priority} priority
                  </span>
                </div>
                <button
                  onClick={() => handleDelete(goal.id)}
                  className="text-red-600 hover:text-red-900"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Progress</span>
                  <span className="font-medium">{progress.toFixed(1)}%</span>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div 
                    className={`h-3 rounded-full ${getProgressColor(progress)}`}
                    style={{ width: `${Math.min(progress, 100)}%` }}
                  ></div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-500">Current:</span>
                    <span className="ml-2 font-medium">${goal.current_amount.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Target:</span>
                    <span className="ml-2 font-medium">${goal.target_amount.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Remaining:</span>
                    <span className="ml-2 font-medium text-orange-600">${remaining.toLocaleString()}</span>
                  </div>
                  {daysUntilTarget && (
                    <div>
                      <span className="text-gray-500">Days left:</span>
                      <span className="ml-2 font-medium">{daysUntilTarget}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-2 mt-4">
                  <input
                    type="number"
                    step="0.01"
                    placeholder="Add to savings"
                    className="flex-1 px-3 py-1 border border-gray-300 rounded text-sm"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const newAmount = goal.current_amount + parseFloat(e.target.value);
                        updateProgress(goal.id, newAmount);
                        e.target.value = '';
                      }
                    }}
                  />
                  <button className="px-3 py-1 bg-green-500 text-white rounded text-sm hover:bg-green-600">
                    Add
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Savings Forecast */}
      {forecastChartData && !loading && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">12-Month Savings Forecast</h2>
          {savingsForecast && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="text-center">
                <p className="text-sm text-gray-500">Total Projected</p>
                <p className="text-xl font-bold text-green-600">
                  ${savingsForecast.total_projected?.toLocaleString() || 0}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Average Monthly</p>
                <p className="text-xl font-bold text-blue-600">
                  ${savingsForecast.average_monthly?.toLocaleString() || 0}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-500">Forecast Model</p>
                <p className="text-xl font-bold text-gray-700">
                  {savingsForecast.model_type?.toUpperCase() || 'N/A'}
                </p>
              </div>
            </div>
          )}
          <Line
            data={forecastChartData}
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
      )}
    </div>
  );
};

export default SavingsGoals;
