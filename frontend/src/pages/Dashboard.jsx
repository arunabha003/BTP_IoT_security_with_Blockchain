import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Database, 
  Shield, 
  TrendingUp,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import { getStatus, getRoot } from '../api/gateway';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const [status, setStatus] = useState(null);
  const [root, setRoot] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [statusRes, rootRes] = await Promise.all([
        getStatus(),
        getRoot()
      ]);
      setStatus(statusRes.data);
      setRoot(rootRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      toast.error('Failed to fetch system data');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const stats = [
    {
      label: 'Total Devices',
      value: status?.totalDevices || 0,
      icon: Database,
      color: 'blue',
      change: null
    },
    {
      label: 'Active Devices',
      value: status?.activeDevices || 0,
      icon: CheckCircle,
      color: 'green',
      change: null
    },
    {
      label: 'Revoked Devices',
      value: status?.revokedDevices || 0,
      icon: XCircle,
      color: 'red',
      change: null
    },
    {
      label: 'Accumulator Version',
      value: status?.version || 0,
      icon: TrendingUp,
      color: 'purple',
      change: null
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            IoT Identity Management with RSA Accumulator
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            status?.chainConnected 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            <div className={`w-2 h-2 rounded-full mr-2 ${
              status?.chainConnected ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
            {status?.chainConnected ? 'Blockchain Connected' : 'Blockchain Disconnected'}
          </div>
          <div className={`flex items-center px-3 py-1 rounded-full text-sm font-medium ${
            status?.status === 'healthy'
              ? 'bg-green-100 text-green-800' 
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            <Activity className="h-3 w-3 mr-2" />
            {status?.status || 'Unknown'}
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          const colorClasses = {
            blue: 'bg-blue-500',
            green: 'bg-green-500',
            red: 'bg-red-500',
            purple: 'bg-purple-500'
          };
          
          return (
            <div key={stat.label} className="card">
              <div className="flex items-center">
                <div className={`flex-shrink-0 p-3 rounded-lg ${colorClasses[stat.color]}`}>
                  <Icon className="h-6 w-6 text-white" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {stat.label}
                    </dt>
                    <dd className="flex items-baseline">
                      <div className="text-2xl font-semibold text-gray-900">
                        {stat.value}
                      </div>
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Accumulator Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Current Root */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Shield className="h-5 w-5 mr-2 text-primary-600" />
            Current Accumulator Root
          </h3>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-gray-500">Root Hash (Hex)</label>
              <div className="mt-1 p-3 bg-gray-50 rounded-lg border border-gray-200">
                <code className="text-xs text-gray-800 break-all font-mono">
                  {root?.rootHex || 'Loading...'}
                </code>
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Version:</span>
              <span className="font-semibold text-gray-900">{root?.version || 0}</span>
            </div>
          </div>
        </div>

        {/* System Info */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Activity className="h-5 w-5 mr-2 text-primary-600" />
            System Information
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Gateway Status</span>
              <span className={`badge ${
                status?.status === 'healthy' ? 'badge-success' : 'badge-warning'
              }`}>
                {status?.status || 'Unknown'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Blockchain</span>
              <span className={`badge ${
                status?.chainConnected ? 'badge-success' : 'badge-danger'
              }`}>
                {status?.chainConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Total Operations</span>
              <span className="font-semibold text-gray-900">{status?.version || 0}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm text-gray-600">Active Rate</span>
              <span className="font-semibold text-gray-900">
                {status?.totalDevices > 0 
                  ? `${((status.activeDevices / status.totalDevices) * 100).toFixed(1)}%`
                  : '0%'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <a
            href="/enroll"
            className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors cursor-pointer"
          >
            <div className="p-3 bg-primary-100 rounded-full mb-2">
              <Database className="h-6 w-6 text-primary-600" />
            </div>
            <span className="text-sm font-medium text-gray-900">Enroll Device</span>
            <span className="text-xs text-gray-500 mt-1">Add new device</span>
          </a>
          <a
            href="/authenticate"
            className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors cursor-pointer"
          >
            <div className="p-3 bg-green-100 rounded-full mb-2">
              <Shield className="h-6 w-6 text-green-600" />
            </div>
            <span className="text-sm font-medium text-gray-900">Authenticate</span>
            <span className="text-xs text-gray-500 mt-1">Verify device</span>
          </a>
          <a
            href="/revoke"
            className="flex flex-col items-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors cursor-pointer"
          >
            <div className="p-3 bg-red-100 rounded-full mb-2">
              <XCircle className="h-6 w-6 text-red-600" />
            </div>
            <span className="text-sm font-medium text-gray-900">Revoke Device</span>
            <span className="text-xs text-gray-500 mt-1">Remove access</span>
          </a>
        </div>
      </div>
    </div>
  );
}
