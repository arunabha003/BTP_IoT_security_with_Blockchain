import React, { useState } from 'react';
import { Trash2, AlertCircle, CheckCircle } from 'lucide-react';
import { revokeDevice } from '../api/gateway';
import toast from 'react-hot-toast';

export default function RevokeDevice() {
  const [deviceIdHex, setDeviceIdHex] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleRevoke = async () => {
    setLoading(true);
    setResult(null);
    setShowConfirmation(false);

    try {
      const response = await revokeDevice(deviceIdHex.trim());
      setResult({ success: true, data: response.data });
      toast.success('Device revoked successfully!');
      setDeviceIdHex('');
    } catch (error) {
      console.error('Revocation error:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to revoke device';
      setResult({ success: false, error: errorMsg });
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setShowConfirmation(true);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Revoke Device</h1>
        <p className="mt-1 text-sm text-gray-500">
          Remove a device from the accumulator using trapdoor operations
        </p>
      </div>

      {/* Warning Banner */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex">
          <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-900">
              Warning: Permanent Action
            </h3>
            <p className="mt-1 text-sm text-yellow-800">
              Revoking a device permanently removes it from the accumulator. This action cannot be undone.
              The device will no longer be able to authenticate.
            </p>
          </div>
        </div>
      </div>

      {/* Revocation Form */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
          <Trash2 className="h-5 w-5 mr-2 text-red-600" />
          Device Information
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Device ID (Hex)
            </label>
            <input
              type="text"
              value={deviceIdHex}
              onChange={(e) => setDeviceIdHex(e.target.value)}
              placeholder="Enter device ID in hexadecimal format..."
              className="input font-mono"
              required
            />
            <p className="mt-2 text-sm text-gray-500">
              Enter the hexadecimal device ID from enrollment
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || !deviceIdHex.trim()}
            className="btn btn-danger w-full"
          >
            Revoke Device
          </button>
        </form>
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center mb-4">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
              <h3 className="ml-4 text-lg font-semibold text-gray-900">
                Confirm Revocation
              </h3>
            </div>
            
            <p className="text-sm text-gray-600 mb-4">
              Are you sure you want to revoke this device? This action cannot be undone.
            </p>
            
            <div className="bg-gray-50 rounded-lg p-3 mb-4">
              <p className="text-xs font-medium text-gray-700 mb-1">Device ID:</p>
              <code className="text-xs text-gray-900 break-all">{deviceIdHex}</code>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleRevoke}
                disabled={loading}
                className="btn btn-danger flex-1"
              >
                {loading ? 'Revoking...' : 'Yes, Revoke'}
              </button>
              <button
                onClick={() => setShowConfirmation(false)}
                disabled={loading}
                className="btn btn-secondary flex-1"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Result Display */}
      {result && (
        <div className={`card ${result.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
          <div className="flex items-start">
            <div className={`flex-shrink-0 ${result.success ? 'text-green-600' : 'text-red-600'}`}>
              {result.success ? (
                <CheckCircle className="h-6 w-6" />
              ) : (
                <AlertCircle className="h-6 w-6" />
              )}
            </div>
            <div className="ml-3 flex-1">
              <h3 className={`text-sm font-medium ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                {result.success ? 'Device Revoked Successfully' : 'Revocation Failed'}
              </h3>
              
              {result.success ? (
                <div className="mt-3 space-y-3">
                  <p className="text-sm text-green-700">
                    {result.data.message}
                  </p>
                  
                  <div>
                    <label className="block text-xs font-medium text-green-900 mb-1">
                      New Accumulator Root (Hex)
                    </label>
                    <textarea
                      value={result.data.rootHex}
                      readOnly
                      rows={3}
                      className="w-full px-3 py-2 border border-green-300 rounded-lg bg-white font-mono text-xs"
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-xs font-medium text-blue-900 mb-1">What happens next?</p>
                    <ul className="list-disc list-inside text-xs text-blue-800 space-y-1">
                      <li>Device removed from accumulator using trapdoor operations</li>
                      <li>Blockchain updated with new accumulator state</li>
                      <li>Witnesses refreshed for all remaining active devices</li>
                      <li>Device marked as revoked in database</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="mt-2 text-sm text-red-700">
                  <p>{result.error}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-sm font-medium text-blue-900 mb-2">How Device Revocation Works</h3>
        <ol className="list-decimal list-inside text-sm text-blue-800 space-y-1">
          <li>Gateway retrieves device's prime number from database</li>
          <li>Trapdoor operation removes prime from accumulator (using λ(N))</li>
          <li>New accumulator state is computed and stored on blockchain</li>
          <li>All remaining active devices receive updated witnesses</li>
          <li>Revoked device can no longer authenticate</li>
        </ol>
      </div>
    </div>
  );
}
