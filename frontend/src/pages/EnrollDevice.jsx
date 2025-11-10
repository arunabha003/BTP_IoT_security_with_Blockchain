import React, { useState } from 'react';
import { UserPlus, Key, Check, Copy } from 'lucide-react';
import { generateKeypair, enrollDevice } from '../api/gateway';
import toast from 'react-hot-toast';

export default function EnrollDevice() {
  const [step, setStep] = useState(1);
  const [keyType, setKeyType] = useState('ed25519');
  const [keypair, setKeypair] = useState(null);
  const [enrollmentResult, setEnrollmentResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerateKeypair = async () => {
    setLoading(true);
    try {
      const response = await generateKeypair(keyType);
      setKeypair(response.data);
      setStep(2);
      toast.success('Keypair generated successfully!');
    } catch (error) {
      console.error('Failed to generate keypair:', error);
      toast.error(error.response?.data?.detail || 'Failed to generate keypair');
    } finally {
      setLoading(false);
    }
  };

  const handleEnrollDevice = async () => {
    setLoading(true);
    try {
      const response = await enrollDevice(keypair.publicKeyPEM, keyType);
      console.log('Enrollment response:', response);
      setEnrollmentResult(response.data);
      setStep(3);
      
      // Check if multi-sig pending (status 202) or successful (status 201)
      if (response.data.status === 'pending') {
        toast.success('Device enrollment submitted! Requires multi-sig approval.', { duration: 5000 });
      } else {
        toast.success('Device enrolled successfully!');
      }
    } catch (error) {
      console.error('Failed to enroll device:', error);
      toast.error(error.response?.data?.detail || 'Failed to enroll device');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard!`);
  };

  const resetForm = () => {
    setStep(1);
    setKeypair(null);
    setEnrollmentResult(null);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Enroll New Device</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generate cryptographic keys and register a new IoT device
        </p>
      </div>

      {/* Progress Steps */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center">
              <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
                step >= 1 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {step > 1 ? <Check className="h-6 w-6" /> : '1'}
              </div>
              <div className="ml-4">
                <p className={`text-sm font-medium ${step >= 1 ? 'text-gray-900' : 'text-gray-500'}`}>
                  Generate Keypair
                </p>
              </div>
            </div>
          </div>
          <div className={`flex-1 h-1 ${step >= 2 ? 'bg-primary-600' : 'bg-gray-200'}`}></div>
          <div className="flex-1">
            <div className="flex items-center">
              <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
                step >= 2 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {step > 2 ? <Check className="h-6 w-6" /> : '2'}
              </div>
              <div className="ml-4">
                <p className={`text-sm font-medium ${step >= 2 ? 'text-gray-900' : 'text-gray-500'}`}>
                  Enroll Device
                </p>
              </div>
            </div>
          </div>
          <div className={`flex-1 h-1 ${step >= 3 ? 'bg-primary-600' : 'bg-gray-200'}`}></div>
          <div className="flex-1">
            <div className="flex items-center">
              <div className={`flex items-center justify-center w-10 h-10 rounded-full ${
                step >= 3 ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {step > 3 ? <Check className="h-6 w-6" /> : '3'}
              </div>
              <div className="ml-4">
                <p className={`text-sm font-medium ${step >= 3 ? 'text-gray-900' : 'text-gray-500'}`}>
                  Complete
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Step 1: Generate Keypair */}
      {step === 1 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
            <Key className="h-5 w-5 mr-2 text-primary-600" />
            Step 1: Generate Cryptographic Keypair
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Key Type
              </label>
              <select
                value={keyType}
                onChange={(e) => setKeyType(e.target.value)}
                className="input"
              >
                <option value="ed25519">Ed25519 (Recommended)</option>
                <option value="rsa">RSA-2048</option>
              </select>
              <p className="mt-2 text-sm text-gray-500">
                {keyType === 'ed25519' 
                  ? 'Ed25519: Fast, secure elliptic curve signatures' 
                  : 'RSA-2048: Traditional public key cryptography'}
              </p>
            </div>
            <button
              onClick={handleGenerateKeypair}
              disabled={loading}
              className="btn btn-primary w-full"
            >
              {loading ? 'Generating...' : 'Generate Keypair'}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Review and Enroll */}
      {step === 2 && keypair && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
            <UserPlus className="h-5 w-5 mr-2 text-primary-600" />
            Step 2: Review and Enroll Device
          </h2>
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Public Key (PEM)
                </label>
                <button
                  onClick={() => copyToClipboard(keypair.publicKeyPEM, 'Public key')}
                  className="text-primary-600 hover:text-primary-700"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
              <textarea
                value={keypair.publicKeyPEM}
                readOnly
                rows={6}
                className="input font-mono text-xs"
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Private Key (Keep Secret!)
                </label>
                <button
                  onClick={() => copyToClipboard(keypair.privateKey, 'Private key')}
                  className="text-primary-600 hover:text-primary-700"
                >
                  <Copy className="h-4 w-4" />
                </button>
              </div>
              <textarea
                value={keypair.privateKey}
                readOnly
                rows={6}
                className="input font-mono text-xs bg-yellow-50 border-yellow-300"
              />
              <p className="mt-2 text-sm text-yellow-800 bg-yellow-50 p-3 rounded-lg">
                ⚠️ <strong>Important:</strong> Save this private key securely. It will be needed for device authentication.
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={handleEnrollDevice}
                disabled={loading}
                className="btn btn-primary flex-1"
              >
                {loading ? 'Enrolling...' : 'Enroll Device'}
              </button>
              <button
                onClick={resetForm}
                className="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 3: Enrollment Success */}
      {step === 3 && enrollmentResult && (
        <div className="card">
          {/* Check if pending multi-sig or completed */}
          {enrollmentResult.status === 'pending' ? (
            // Pending Multi-Sig Approval
            <>
              <div className="text-center mb-6">
                <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-yellow-100 mb-4">
                  <UserPlus className="h-10 w-10 text-yellow-600" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-900">
                  Enrollment Pending Multi-Sig Approval
                </h2>
                <p className="mt-2 text-sm text-gray-500">
                  This transaction requires {enrollmentResult.required_signatures} signatures
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Device ID (Hex)
                    </label>
                    <button
                      onClick={() => copyToClipboard(enrollmentResult.device_id, 'Device ID')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={enrollmentResult.device_id || 'N/A'}
                    readOnly
                    className="input font-mono text-sm"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Safe Transaction Hash
                    </label>
                    <button
                      onClick={() => copyToClipboard(enrollmentResult.safeTxHash, 'Safe TX Hash')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={enrollmentResult.safeTxHash || 'N/A'}
                    readOnly
                    className="input font-mono text-sm"
                  />
                </div>

                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-yellow-900 mb-2">⚠️ Multi-Sig Required</h4>
                  <ul className="list-disc list-inside text-sm text-yellow-800 space-y-1">
                    <li>Transaction requires {enrollmentResult.required_signatures} signatures</li>
                    <li>Go to the <a href={enrollmentResult.multisig_url} className="underline font-medium">Multi-Sig Approval page</a></li>
                    <li>Sign with {enrollmentResult.required_signatures} different Safe owner accounts</li>
                    <li>Device will be active after execution</li>
                  </ul>
                </div>

                <button
                  onClick={() => window.location.href = enrollmentResult.multisig_url}
                  className="btn btn-primary w-full"
                >
                  Go to Multi-Sig Approval
                </button>

                <button
                  onClick={resetForm}
                  className="btn btn-secondary w-full"
                >
                  Enroll Another Device
                </button>
              </div>
            </>
          ) : (
            // Successful Enrollment
            <>
              <div className="text-center mb-6">
                <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
                  <Check className="h-10 w-10 text-green-600" />
                </div>
                <h2 className="text-2xl font-semibold text-gray-900">
                  Device Enrolled Successfully!
                </h2>
                <p className="mt-2 text-sm text-gray-500">
                  The device has been added to the accumulator
                </p>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Device ID (Hex)
                    </label>
                    <button
                      onClick={() => copyToClipboard(enrollmentResult.deviceIdHex, 'Device ID')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={enrollmentResult.deviceIdHex || 'N/A'}
                    readOnly
                    className="input font-mono text-sm"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Device Prime
                    </label>
                    <button
                      onClick={() => copyToClipboard(enrollmentResult.idPrime, 'Device prime')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <input
                    type="text"
                    value={enrollmentResult.idPrime || 'N/A'}
                    readOnly
                    className="input font-mono text-xs"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Witness (Hex)
                    </label>
                    <button
                      onClick={() => copyToClipboard(enrollmentResult.witnessHex, 'Witness')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <textarea
                    value={enrollmentResult.witnessHex || 'N/A'}
                    readOnly
                    rows={4}
                    className="input font-mono text-xs"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Accumulator Root (Hex)
                    </label>
                    <button
                      onClick={() => copyToClipboard(enrollmentResult.rootHex, 'Root')}
                      className="text-primary-600 hover:text-primary-700"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <textarea
                    value={enrollmentResult.rootHex || 'N/A'}
                    readOnly
                    rows={4}
                    className="input font-mono text-xs"
                  />
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h4 className="text-sm font-medium text-blue-900 mb-2">Next Steps:</h4>
                  <ul className="list-disc list-inside text-sm text-blue-800 space-y-1">
                    <li>Save the device credentials securely</li>
                    <li>Store the private key on the device</li>
                    <li>Use the device ID and witness for authentication</li>
                    <li>Test authentication on the Authenticate page</li>
                  </ul>
                </div>

                <button
                  onClick={resetForm}
                  className="btn btn-primary w-full"
                >
                  Enroll Another Device
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
