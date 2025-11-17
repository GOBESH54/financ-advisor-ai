import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import {
  HomeIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  DocumentTextIcon,
  CogIcon,
  BanknotesIcon,
  CreditCardIcon,
  TrophyIcon,
  CloudArrowUpIcon,
  BellIcon,
  ShieldCheckIcon,
  PresentationChartBarIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';

// Import components
import Dashboard from './components/Dashboard';
import IncomeExpense from './components/IncomeExpense';
import BudgetAnalysis from './components/BudgetAnalysis';
import InvestmentRecommendations from './components/InvestmentRecommendations';
import DebtManagement from './components/DebtManagement';
import SavingsGoals from './components/SavingsGoals';
import Reports from './components/Reports';
import Settings from './components/Settings';
import BankStatementUpload from './components/BankStatementUpload';
import AIForecasting from './components/AIForecasting';
import BusinessIntelligence from './components/BusinessIntelligence';

// Placeholder components
const SecurityDashboard = () => <div className="p-6"><h2 className="text-2xl font-bold mb-4">🔒 Security Dashboard</h2><p>Advanced security features and audit logs...</p></div>;
const NotificationsCenter = () => <div className="p-6"><h2 className="text-2xl font-bold mb-4">🔔 Notifications Center</h2><p>Smart notifications and alerts...</p></div>;

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation Sidebar */}
        <div className="fixed inset-y-0 left-0 w-64 bg-dark text-white shadow-lg">
          <div className="p-4">
            <h1 className="text-2xl font-bold text-center mb-8">
              💰 Finance Advisor
            </h1>
            <nav className="space-y-1 text-sm">
              {/* Core Features */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Core</h3>
                <NavLink
                  to="/"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <HomeIcon className="h-4 w-4" />
                  <span>Dashboard</span>
                </NavLink>
                
                <NavLink
                  to="/income-expense"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <BanknotesIcon className="h-4 w-4" />
                  <span>Income & Expenses</span>
                </NavLink>
                
                <NavLink
                  to="/budget"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <ChartBarIcon className="h-4 w-4" />
                  <span>Budget Analysis</span>
                </NavLink>
              </div>

              {/* Banking & Statements */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Banking</h3>
                <NavLink
                  to="/bank-upload"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <CloudArrowUpIcon className="h-4 w-4" />
                  <span>Bank Statements</span>
                </NavLink>
                
                <NavLink
                  to="/investments"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <CurrencyDollarIcon className="h-4 w-4" />
                  <span>Investments</span>
                </NavLink>
              </div>

              {/* Advanced AI */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">AI Features</h3>
                <NavLink
                  to="/ai-forecasting"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <CpuChipIcon className="h-4 w-4" />
                  <span>AI Forecasting</span>
                </NavLink>
                
                <NavLink
                  to="/business-intelligence"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <PresentationChartBarIcon className="h-4 w-4" />
                  <span>Business Intelligence</span>
                </NavLink>
              </div>

              {/* Planning & Goals */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Planning</h3>
                <NavLink
                  to="/debt"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <CreditCardIcon className="h-4 w-4" />
                  <span>Debt Management</span>
                </NavLink>
                
                <NavLink
                  to="/savings-goals"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <TrophyIcon className="h-4 w-4" />
                  <span>Savings Goals</span>
                </NavLink>
              </div>

              {/* Reports & System */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">System</h3>
                <NavLink
                  to="/reports"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <DocumentTextIcon className="h-4 w-4" />
                  <span>Reports</span>
                </NavLink>

                <NavLink
                  to="/notifications"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <BellIcon className="h-4 w-4" />
                  <span>Notifications</span>
                </NavLink>

                <NavLink
                  to="/security"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <ShieldCheckIcon className="h-4 w-4" />
                  <span>Security</span>
                </NavLink>
                
                <NavLink
                  to="/settings"
                  className={({ isActive }) =>
                    `flex items-center space-x-2 p-2 rounded-lg transition-colors ${
                      isActive ? 'bg-primary text-white' : 'hover:bg-gray-700'
                    }`
                  }
                >
                  <CogIcon className="h-4 w-4" />
                  <span>Settings</span>
                </NavLink>
              </div>
            </nav>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="ml-64">
          <div className="p-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/income-expense" element={<IncomeExpense />} />
              <Route path="/budget" element={<BudgetAnalysis />} />
              <Route path="/bank-upload" element={<BankStatementUpload />} />
              <Route path="/investments" element={<InvestmentRecommendations />} />
              <Route path="/ai-forecasting" element={<AIForecasting />} />
              <Route path="/business-intelligence" element={<BusinessIntelligence />} />
              <Route path="/debt" element={<DebtManagement />} />
              <Route path="/savings-goals" element={<SavingsGoals />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/notifications" element={<NotificationsCenter />} />
              <Route path="/security" element={<SecurityDashboard />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </div>
        </div>

        <ToastContainer
          position="top-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop={false}
          closeOnClick
          rtl={false}
          pauseOnFocusLoss
          draggable
          pauseOnHover
        />
      </div>
    </Router>
  );
}

export default App;
