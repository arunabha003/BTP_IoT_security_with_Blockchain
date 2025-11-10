import React, { useState } from 'react';
import { Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AuthenticateDevice() {
  const [formData, setFormData] = useState({
    deviceIdHex: '',
    idPrime: '',
    witnessHex: '',
    signatureB64: '',
    nonceHex: '',
    publicKeyPEM: '',
    keyType: 'ed25519'
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleAuthenticate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch('/api/auth', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();
      
      if (response.ok) {
        setResult({ success: true, data });
        toast.success('Device authenticated successfully!');
      } else {
        setResult({ success: false, error: data.detail || 'Authentication failed' });
        toast.error(data.detail || 'Authentication failed');
      }
    } catch (error) {
      console.error('Authentication error:', error);
      setResult({ success: false, error: error.message });
      toast.error('Failed to authenticate device');
    } finally {
      setLoading(false);
    }
  };

  const loadSampleData = () => {
    setFormData({
      deviceIdHex: 'a1b2c3d4e5f6...',
      idPrime: '123456789...',
      witnessHex: 'abcdef123456...',
      signatureB64: 'SGVsbG8gV29ybGQ=...',
      nonceHex: 'deadbeef...',
      publicKeyPEM: '-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----',
      keyType: 'ed25519'
    });
    toast.info('Sample data loaded. Replace with actual device credentials.');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Authenticate Device</h1>
        <p className="mt-1 text-sm text-gray-500">
          Verify device membership in the accumulator and validate signatures
        </p>
      </div>

      {/* Authentication Form */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900 flex items-center">
            <Shield className="h-5 w-5 mr-2 text-primary-600" />
            Device Credentials
          </h2>
          <button
            onClick={loadSampleData}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Load Sample Data
          </button>
        </div>

        <form onSubmit={handleAuthenticate} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Device ID (Hex)
              </label>
              <input
                type="text"
                name="deviceIdHex"
                value={formData.deviceIdHex}
                onChange={handleChange}
                placeholder="a1b2c3d4e5f6..."
                className="input"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Device Prime
              </label>
              <input
                type="text"
                name="idPrime"
                value={formData.idPrime}
                onChange={handleChange}
                placeholder="123456789..."
                className="input"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Witness (Hex)
            </label>
            <textarea
              name="witnessHex"
              value={formData.witnessHex}
              onChange={handleChange}
              placeholder="abcdef123456..."
              rows={3}
              className="input font-mono text-xs"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nonce (Hex)
              </label>
              <input
                type="text"
                name="nonceHex"
                value={formData.nonceHex}
                onChange={handleChange}
                placeholder="deadbeef..."
                className="input font-mono text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Signature (Base64)
              </label>
              <input
                type="text"
                name="signatureB64"
                value={formData.signatureB64}
                onChange={handleChange}
                placeholder="SGVsbG8gV29ybGQ=..."
                className="input font-mono text-sm"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Public Key (PEM)
            </label>
            <textarea
              name="publicKeyPEM"
              value={formData.publicKeyPEM}
              onChange={handleChange}
              placeholder="-----BEGIN PUBLIC KEY-----&#10;...&#10;-----END PUBLIC KEY-----"
              rows={5}
              className="input font-mono text-xs"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Key Type
            </label>
            <select
              name="keyType"
              value={formData.keyType}
              onChange={handleChange}
              className="input"
            >
              <option value="ed25519">Ed25519</option>
              <option value="rsa">RSA-2048</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full"
          >
            {loading ? 'Authenticating...' : 'Authenticate Device'}
          </button>
        </form>
      </div>

      {/* Authentication Result */}
      {result && (
        <div className={`card ${result.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
          <div className="flex items-start">
            <div className={`flex-shrink-0 ${result.success ? 'text-green-600' : 'text-red-600'}`}>
              {result.success ? (
                <CheckCircle className="h-6 w-6" />
              ) : (
                <XCircle className="h-6 w-6" />
              )}
            </div>
            <div className="ml-3 flex-1">
              <h3 className={`text-sm font-medium ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                {result.success ? 'Authentication Successful' : 'Authentication Failed'}
              </h3>
              
              {result.success ? (
                <div className="mt-2 text-sm text-green-700 space-y-2">
                  <p><strong>Status:</strong> {result.data.authenticated ? 'Authenticated ✓' : 'Not Authenticated ✗'}</p>
                  <p><strong>Message:</strong> {result.data.message}</p>
                  
                  {result.data.newWitnessHex && (
                    <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <div className="flex items-start">
                        <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 mr-2" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-yellow-900">Witness Update Required</p>
                          <p className="text-xs text-yellow-800 mt-1">
                            Your witness is outdated. Please update with the new witness below:
                          </p>
                          <div className="mt-2">
                            <label className="block text-xs font-medium text-yellow-900 mb-1">
                              New Witness (Hex)
                            </label>
                            <textarea
                              value={result.data.newWitnessHex}
                              readOnly
                              rows={3}
                              className="w-full px-3 py-2 border border-yellow-300 rounded-lg bg-white font-mono text-xs"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
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
        <h3 className="text-sm font-medium text-blue-900 mb-2">Authentication Process</h3>
        <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
          <li>Verifies device membership using accumulator witness</li>
          <li>Validates cryptographic signature with nonce</li>
          <li>Checks device status (active/revoked)</li>
          <li>Returns updated witness if accumulator changed</li>
        </ul>
      </div>
    </div>
  );
}
