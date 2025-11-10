import React, { useState, useEffect } from 'react';
import { Database, Search, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { getDevices } from '../api/gateway';

export default function DeviceList() {
  const [devices, setDevices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [stats, setStats] = useState({ total: 0, active: 0, revoked: 0 });

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    setLoading(true);
    try {
      const response = await getDevices();
      const data = response.data;
      
      // Transform backend data to frontend format
      const transformedDevices = data.devices.map(device => ({
        id: device.deviceIdHex.substring(0, 8), // Use first 8 chars as display ID
        deviceIdHex: device.deviceIdHex,
        idPrime: device.idPrime.toString(),
        status: device.status === 1 ? 'active' : 'revoked',
        enrolledAt: device.createdAt,
        lastAuth: device.updatedAt,
        keyType: device.keyType
      }));
      
      setDevices(transformedDevices);
      setStats({
        total: data.total,
        active: data.active,
        revoked: data.revoked
      });
      
      toast.success(`Loaded ${data.total} device(s)`);
    } catch (error) {
      console.error('Failed to fetch devices:', error);
      toast.error('Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  const filteredDevices = devices.filter(device => {
    const matchesSearch = device.deviceIdHex.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         device.idPrime.includes(searchTerm);
    const matchesFilter = filterStatus === 'all' || device.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Device Registry</h1>
          <p className="mt-1 text-sm text-gray-500">
            View and manage enrolled IoT devices
          </p>
        </div>
        <button
          onClick={fetchDevices}
          className="btn btn-secondary flex items-center"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Search Devices
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search by device ID or prime..."
                className="input pl-10"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Filter by Status
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="input"
            >
              <option value="all">All Devices</option>
              <option value="active">Active Only</option>
              <option value="revoked">Revoked Only</option>
            </select>
          </div>
        </div>
      </div>

      {/* Device Count */}
      <div className="flex items-center justify-between text-sm text-gray-600">
        <span>
          Showing {filteredDevices.length} of {stats.total} devices
        </span>
        <div className="flex items-center space-x-4">
          <span className="flex items-center">
            <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
            Active: {stats.active}
          </span>
          <span className="flex items-center">
            <span className="w-2 h-2 bg-red-500 rounded-full mr-2"></span>
            Revoked: {stats.revoked}
          </span>
        </div>
      </div>

      {/* Device List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : filteredDevices.length === 0 ? (
        <div className="card text-center py-12">
          <Database className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Devices Found</h3>
          <p className="text-sm text-gray-500">
            {searchTerm || filterStatus !== 'all'
              ? 'Try adjusting your search or filter criteria'
              : 'Start by enrolling your first device'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredDevices.map((device) => (
            <div key={device.id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center mb-2">
                    <h3 className="text-sm font-semibold text-gray-900">
                      Device {device.id}
                    </h3>
                    <span className={`ml-3 badge ${
                      device.status === 'active' ? 'badge-success' : 'badge-danger'
                    }`}>
                      {device.status}
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    <div>
                      <label className="text-xs font-medium text-gray-500">Device ID:</label>
                      <p className="text-xs font-mono text-gray-900 break-all mt-1">
                        {device.deviceIdHex}
                      </p>
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                      <div>
                        <label className="font-medium text-gray-500">Prime:</label>
                        <p className="font-mono text-gray-900 truncate" title={device.idPrime}>
                          {device.idPrime}
                        </p>
                      </div>
                      <div>
                        <label className="font-medium text-gray-500">Enrolled:</label>
                        <p className="text-gray-900">
                          {new Date(device.enrolledAt).toLocaleDateString()}
                        </p>
                      </div>
                      <div>
                        <label className="font-medium text-gray-500">Last Auth:</label>
                        <p className="text-gray-900">
                          {device.lastAuth ? new Date(device.lastAuth).toLocaleDateString() : 'Never'}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="ml-4 flex-shrink-0 flex space-x-2">
                  {device.status === 'active' && (
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(device.deviceIdHex);
                        toast.success('Device ID copied!');
                      }}
                      className="btn btn-secondary text-xs"
                    >
                      Copy ID
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info Box */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-sm font-medium text-blue-900 mb-2">About Device Registry</h3>
        <p className="text-sm text-blue-800">
          This registry displays all devices that have been enrolled in the system. Active devices can authenticate,
          while revoked devices are permanently removed from the accumulator. Device credentials include a unique
          device ID (derived from public key hash) and a prime number used in the accumulator.
        </p>
      </div>
    </div>
  );
}
