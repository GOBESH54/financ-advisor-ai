import React, { useState, useEffect } from 'react';
import { Line, Bar, Doughnut, Radar } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, RadialLinearScale, Title, Tooltip, Legend } from 'chart.js';
import api from '../services/api';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, RadialLinearScale, Title, Tooltip, Legend);

const BusinessIntelligence = () => {
  const [biData, setBiData] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('dashboard');

  useEffect(() => {
    fetchBIData();
  }, []);

  const fetchBIData = async () => {
    try {
      const [dashboardRes, patternsRes, healthRes, anomaliesRes, insightsRes] = await Promise.all([
        api.get('/bi/dashboard'),
        api.get('/bi/spending-patterns?months=12'),
        api.get('/bi/financial-health'),
        api.get('/bi/anomalies?months=6'),
        api.get('/bi/insights')
      ]);

      setBiData({
        dashboard: dashboardRes.data,
        patterns: patternsRes.data,
        health: healthRes.data,
        anomalies: anomaliesRes.data,
        insights: insightsRes.data
      });
    } catch (error) {
      console.error('Error fetching BI data:', error);
    } finally {
      setLoading(false);
    }
  };

  const renderDashboard = () => {
    if (!biData.dashboard) return <div>No dashboard data available</div>;

    const healthScore = biData.health?.overall_score || 0;
    const getHealthColor = (score) => {
      if (score >= 80) return 'text-green-600';
      if (score >= 60) return 'text-yellow-600';
      return 'text-red-600';
    };

    return (
      <div className="space-y-6">
        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 rounded-lg">
                <span className="text-2xl">💚</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Financial Health</p>
                <p className={`text-2xl font-bold ${getHealthColor(healthScore)}`}>{healthScore}/100</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 rounded-lg">
                <span className="text-2xl">📊</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Spending Trends</p>
                <p className="text-2xl font-bold text-blue-600">{Object.keys(biData.patterns?.patterns || {}).length}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <div className="p-2 bg-red-100 rounded-lg">
                <span className="text-2xl">⚠️</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Anomalies</p>
                <p className="text-2xl font-bold text-red-600">{biData.anomalies?.summary?.total_anomalies || 0}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 rounded-lg">
                <span className="text-2xl">🎯</span>
              </div>
              <div className="ml-4">
                <p className="text-sm text-gray-600">Insights</p>
                <p className="text-2xl font-bold text-purple-600">{biData.insights?.key_insights?.length || 0}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Health Score Breakdown */}
        {biData.health && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">💚 Financial Health Breakdown</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(biData.health.component_scores || {}).map(([component, score]) => (
                <div key={component} className="text-center">
                  <div className={`text-3xl font-bold ${getHealthColor(score)}`}>{score}</div>
                  <div className="text-sm text-gray-600 capitalize">{component.replace('_', ' ')}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Insights */}
        {biData.insights && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">🤖 AI Insights</h3>
            <div className="space-y-3">
              {biData.insights.key_insights?.map((insight, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg">
                  <span className="text-blue-600">💡</span>
                  <div>
                    <p className="text-sm font-medium text-blue-900">{insight.message}</p>
                    <p className="text-xs text-blue-600 capitalize">{insight.category}</p>
                  </div>
                </div>
              ))}
              {biData.insights.alerts?.map((alert, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-red-50 rounded-lg">
                  <span className="text-red-600">⚠️</span>
                  <div>
                    <p className="text-sm font-medium text-red-900">{alert.message}</p>
                    <p className="text-xs text-red-600 capitalize">{alert.severity} priority</p>
                  </div>
                </div>
              ))}
              {biData.insights.opportunities?.map((opp, index) => (
                <div key={index} className="flex items-start space-x-3 p-3 bg-green-50 rounded-lg">
                  <span className="text-green-600">🎯</span>
                  <div>
                    <p className="text-sm font-medium text-green-900">{opp.message}</p>
                    <p className="text-xs text-green-600 capitalize">{opp.action}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderSpendingPatterns = () => {
    if (!biData.patterns?.patterns) return <div>No patterns data available</div>;

    const categories = Object.keys(biData.patterns.patterns);
    const trends = categories.map(cat => biData.patterns.patterns[cat].trend);
    const averages = categories.map(cat => biData.patterns.patterns[cat].monthly_average);

    const trendData = {
      labels: categories,
      datasets: [{
        label: 'Monthly Average',
        data: averages,
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
      }]
    };

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">📈 Spending Patterns Analysis</h3>
          <Bar data={trendData} options={{
            responsive: true,
            plugins: {
              legend: { position: 'top' },
              title: { display: true, text: 'Average Monthly Spending by Category' }
            }
          }} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {categories.map(category => {
            const pattern = biData.patterns.patterns[category];
            const trendIcon = pattern.trend === 'increasing' ? '📈' : pattern.trend === 'decreasing' ? '📉' : '➡️';
            const trendColor = pattern.trend === 'increasing' ? 'text-red-600' : pattern.trend === 'decreasing' ? 'text-green-600' : 'text-gray-600';
            
            return (
              <div key={category} className="bg-white p-4 rounded-lg shadow">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium capitalize">{category}</h4>
                  <span className="text-xl">{trendIcon}</span>
                </div>
                <p className={`text-sm ${trendColor} capitalize`}>{pattern.trend} trend</p>
                <p className="text-lg font-bold">₹{pattern.monthly_average.toLocaleString()}</p>
                <p className="text-xs text-gray-500">{pattern.anomalies.length} anomalies detected</p>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderAnomalies = () => {
    if (!biData.anomalies?.anomalies) return <div>No anomalies data available</div>;

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">⚠️ Spending Anomalies</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-red-50 p-4 rounded-lg">
              <p className="text-sm text-red-600">Total Anomalies</p>
              <p className="text-2xl font-bold text-red-700">{biData.anomalies.summary.total_anomalies}</p>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <p className="text-sm text-orange-600">High Severity</p>
              <p className="text-2xl font-bold text-orange-700">{biData.anomalies.summary.high_severity}</p>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <p className="text-sm text-yellow-600">Medium Severity</p>
              <p className="text-2xl font-bold text-yellow-700">{biData.anomalies.summary.medium_severity}</p>
            </div>
          </div>

          <div className="space-y-3">
            {biData.anomalies.anomalies.slice(0, 10).map((anomaly, index) => {
              const severityColor = anomaly.z_score > 3 ? 'border-red-500' : 'border-yellow-500';
              const severityBg = anomaly.z_score > 3 ? 'bg-red-50' : 'bg-yellow-50';
              
              return (
                <div key={index} className={`border-l-4 ${severityColor} ${severityBg} p-4 rounded`}>
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium">{anomaly.description}</p>
                      <p className="text-sm text-gray-600">{anomaly.date}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold">₹{anomaly.amount.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">Z-score: {anomaly.z_score.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">📊 Business Intelligence</h1>
        <button
          onClick={fetchBIData}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700"
        >
          Refresh Analysis
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'dashboard', name: 'BI Dashboard', icon: '📊' },
            { id: 'patterns', name: 'Spending Patterns', icon: '📈' },
            { id: 'anomalies', name: 'Anomaly Detection', icon: '⚠️' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`${
                activeTab === tab.id
                  ? 'border-purple-500 text-purple-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm flex items-center space-x-2`}
            >
              <span>{tab.icon}</span>
              <span>{tab.name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'patterns' && renderSpendingPatterns()}
        {activeTab === 'anomalies' && renderAnomalies()}
      </div>
    </div>
  );
};

export default BusinessIntelligence;