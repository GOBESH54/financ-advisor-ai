import React, { useState, useEffect } from 'react';
import { userAPI } from '../services/api';
import { toast } from 'react-toastify';
import { 
  UserCircleIcon, 
  BellIcon, 
  ShieldCheckIcon,
  CogIcon 
} from '@heroicons/react/24/outline';

const Settings = () => {
  const [user, setUser] = useState({
    name: '',
    email: '',
    age: '',
    risk_tolerance: 'medium'
  });
  const [notifications, setNotifications] = useState({
    budgetAlerts: true,
    goalReminders: true,
    monthlyReports: true,
    investmentUpdates: false
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchUser();
  }, []);

  const fetchUser = async () => {
    try {
      const response = await userAPI.getUser();
      setUser(response.data);
    } catch (error) {
      console.error('Error fetching user:', error);
    }
  };

  const handleUserUpdate = async (e) => {
    e.preventDefault();
    try {
      setSaving(true);
      await userAPI.updateUser(user);
      toast.success('Profile updated successfully');
    } catch (error) {
      toast.error('Failed to update profile');
      console.error('Error:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleNotificationToggle = (key) => {
    setNotifications(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
    toast.info('Notification preferences updated');
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">Settings</h1>

      {/* Profile Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-3 mb-6">
          <UserCircleIcon className="h-6 w-6 text-gray-600" />
          <h2 className="text-xl font-semibold">Profile Settings</h2>
        </div>
        
        <form onSubmit={handleUserUpdate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={user.name}
              onChange={(e) => setUser({ ...user, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={user.email}
              onChange={(e) => setUser({ ...user, email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
              required
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Age
            </label>
            <input
              type="number"
              value={user.age}
              onChange={(e) => setUser({ ...user, age: parseInt(e.target.value) || '' })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
              min="18"
              max="100"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Risk Tolerance
            </label>
            <select
              value={user.risk_tolerance}
              onChange={(e) => setUser({ ...user, risk_tolerance: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-primary"
            >
              <option value="low">Low - Conservative</option>
              <option value="medium">Medium - Moderate</option>
              <option value="high">High - Aggressive</option>
            </select>
          </div>
          
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={saving}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                saving 
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
                  : 'bg-primary text-white hover:bg-blue-600'
              }`}
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
          </div>
        </form>
      </div>

      {/* Notification Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-3 mb-6">
          <BellIcon className="h-6 w-6 text-gray-600" />
          <h2 className="text-xl font-semibold">Notification Preferences</h2>
        </div>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b">
            <div>
              <h3 className="font-medium">Budget Alerts</h3>
              <p className="text-sm text-gray-600">Get notified when spending exceeds budget limits</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('budgetAlerts')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                notifications.budgetAlerts ? 'bg-primary' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  notifications.budgetAlerts ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between py-3 border-b">
            <div>
              <h3 className="font-medium">Savings Goal Reminders</h3>
              <p className="text-sm text-gray-600">Receive reminders about your savings goals</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('goalReminders')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                notifications.goalReminders ? 'bg-primary' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  notifications.goalReminders ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between py-3 border-b">
            <div>
              <h3 className="font-medium">Monthly Reports</h3>
              <p className="text-sm text-gray-600">Automatically generate monthly financial reports</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('monthlyReports')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                notifications.monthlyReports ? 'bg-primary' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  notifications.monthlyReports ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
          
          <div className="flex items-center justify-between py-3">
            <div>
              <h3 className="font-medium">Investment Updates</h3>
              <p className="text-sm text-gray-600">Get updates on investment recommendations</p>
            </div>
            <button
              onClick={() => handleNotificationToggle('investmentUpdates')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                notifications.investmentUpdates ? 'bg-primary' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  notifications.investmentUpdates ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-3 mb-6">
          <ShieldCheckIcon className="h-6 w-6 text-gray-600" />
          <h2 className="text-xl font-semibold">Security & Privacy</h2>
        </div>
        
        <div className="space-y-4">
          <div className="p-4 bg-green-50 rounded-lg">
            <div className="flex items-center space-x-2">
              <ShieldCheckIcon className="h-5 w-5 text-green-600" />
              <span className="font-medium text-green-800">Your data is stored locally</span>
            </div>
            <p className="text-sm text-green-700 mt-2">
              All your financial data is stored securely on your local device. No data is sent to external servers.
            </p>
          </div>
          
          <div className="border rounded-lg p-4">
            <h3 className="font-medium mb-2">Data Privacy</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li>• Your financial information is never shared with third parties</li>
              <li>• All calculations and analysis are performed locally</li>
              <li>• You have full control over your data</li>
              <li>• Regular backups are recommended to prevent data loss</li>
            </ul>
          </div>
        </div>
      </div>

      {/* System Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-3 mb-6">
          <CogIcon className="h-6 w-6 text-gray-600" />
          <h2 className="text-xl font-semibold">System Information</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Version:</span>
            <span className="ml-2 font-medium">1.0.0</span>
          </div>
          <div>
            <span className="text-gray-500">Database:</span>
            <span className="ml-2 font-medium">SQLite (Local)</span>
          </div>
          <div>
            <span className="text-gray-500">AI Models:</span>
            <span className="ml-2 font-medium">Loaded</span>
          </div>
          <div>
            <span className="text-gray-500">Last Updated:</span>
            <span className="ml-2 font-medium">{new Date().toLocaleDateString()}</span>
          </div>
        </div>
        
        <div className="mt-6 space-y-3">
          <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
            Export All Data
          </button>
          <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors ml-3">
            Create Backup
          </button>
          <button className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors ml-3">
            Clear All Data
          </button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
