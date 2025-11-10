import React, { useState, useEffect } from 'react';
import { Activity, Server, Database, TrendingUp, AlertCircle } from 'lucide-react';
import { getStatus, getRoot } from '../api/gateway';
import toast from 'react-hot-toast';

export default function SystemStatus() {
  const [status, setStatus] = useState(null);
  const [root, setRoot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      fetchData();
      setLastUpdate(new Date());
    }, 3000);
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
      console.error('Failed to fetch status:', error);
      if (loading) {
        toast.error('Failed to connect to gateway');
      }
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">System Status</h1>
          <p className="mt-1 text-sm text-gray-500">
            Real-time monitoring of gateway and blockchain
          </p>
        </div>
        <div className="text-sm text-gray-500">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      </div>

      {/* Overall Health */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Overall System Health</h2>
            <p className="text-sm text-gray-500 mt-1">
              All systems operational
            </p>
          </div>
          <div className={`px-6 py-3 rounded-full text-lg font-semibold ${
            status?.status === 'healthy' && status?.chainConnected
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            {status?.status === 'healthy' && status?.chainConnected ? '✓ Healthy' : '⚠ Warning'}
          </div>
        </div>
      </div>

      {/* Service Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gateway Status */}
        <div className="card">
          <div className="flex items-center mb-4">
            <div className={`p-3 rounded-lg ${
              status?.status === 'healthy' ? 'bg-green-100' : 'bg-yellow-100'
            }`}>
              <Server className={`h-6 w-6 ${
                status?.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'
              }`} />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">Gateway Service</h3>
              <p className={`text-sm ${
                status?.status === 'healthy' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {status?.status || 'Unknown'}
              </p>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">API Endpoint:</span>
              <span className="font-medium text-gray-900">http://127.0.0.1:8000</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Status:</span>
              <span className={`badge ${
                status?.status === 'healthy' ? 'badge-success' : 'badge-warning'
              }`}>
                {status?.status || 'Unknown'}
              </span>
            </div>
          </div>
        </div>

        {/* Blockchain Status */}
        <div className="card">
          <div className="flex items-center mb-4">
            <div className={`p-3 rounded-lg ${
              status?.chainConnected ? 'bg-green-100' : 'bg-red-100'
            }`}>
              <Database className={`h-6 w-6 ${
                status?.chainConnected ? 'text-green-600' : 'text-red-600'
              }`} />
            </div>
            <div className="ml-4">
              <h3 className="text-lg font-semibold text-gray-900">Blockchain</h3>
              <p className={`text-sm ${
                status?.chainConnected ? 'text-green-600' : 'text-red-600'
              }`}>
                {status?.chainConnected ? 'Connected' : 'Disconnected'}
              </p>
            </div>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Network:</span>
              <span className="font-medium text-gray-900">Anvil (Local)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Connection:</span>
              <span className={`badge ${
                status?.chainConnected ? 'badge-success' : 'badge-danger'
              }`}>
                {status?.chainConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Accumulator Statistics */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <TrendingUp className="h-5 w-5 mr-2 text-primary-600" />
          Accumulator Statistics
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <div className="text-3xl font-bold text-gray-900">{status?.totalDevices || 0}</div>
            <div className="text-sm text-gray-600 mt-1">Total Devices</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg">
            <div className="text-3xl font-bold text-green-600">{status?.activeDevices || 0}</div>
            <div className="text-sm text-gray-600 mt-1">Active</div>
          </div>
          <div className="text-center p-4 bg-red-50 rounded-lg">
            <div className="text-3xl font-bold text-red-600">{status?.revokedDevices || 0}</div>
            <div className="text-sm text-gray-600 mt-1">Revoked</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg">
            <div className="text-3xl font-bold text-purple-600">{status?.version || 0}</div>
            <div className="text-sm text-gray-600 mt-1">Version</div>
          </div>
        </div>
      </div>

      {/* Current Accumulator State */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Activity className="h-5 w-5 mr-2 text-primary-600" />
          Current Accumulator State
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Accumulator Root (Hex)
            </label>
            <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
              <code className="text-xs text-gray-800 break-all font-mono">
                {root?.rootHex || 'Loading...'}
              </code>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <span className="text-sm font-medium text-blue-900">Version</span>
              <span className="text-lg font-bold text-blue-700">{root?.version || 0}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <span className="text-sm font-medium text-blue-900">Root Length</span>
              <span className="text-lg font-bold text-blue-700">
                {root?.rootHex ? `${root.rootHex.length} chars` : '0 chars'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* System Information */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-700">Configuration</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">RSA Key Size:</span>
                <span className="font-medium text-gray-900">2048 bits</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Hash Function:</span>
                <span className="font-medium text-gray-900">SHA3-256</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Trapdoor Operations:</span>
                <span className="badge badge-success">Enabled</span>
              </div>
            </div>
          </div>
          <div className="space-y-3">
            <h4 className="text-sm font-medium text-gray-700">Supported Operations</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Device Enrollment:</span>
                <span className="badge badge-success">Active</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Authentication:</span>
                <span className="badge badge-success">Active</span>
              </div>
              <div className="flex justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Revocation:</span>
                <span className="badge badge-success">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Warnings/Alerts */}
      {(!status?.chainConnected || status?.status !== 'healthy') && (
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-start">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-900">System Alerts</h3>
              <div className="mt-2 text-sm text-yellow-800 space-y-1">
                {!status?.chainConnected && (
                  <p>• Blockchain connection unavailable. Ensure Anvil is running.</p>
                )}
                {status?.status !== 'healthy' && (
                  <p>• Gateway service is not healthy. Check logs for details.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
