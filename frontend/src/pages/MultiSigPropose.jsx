import React, { useState, useEffect } from 'react';
import { Users, FileText, Clock, CheckCircle, XCircle, Wallet } from 'lucide-react';
import { ethers } from 'ethers';
import toast from 'react-hot-toast';
import { generateSafeTxHash, signTransaction, splitSignature } from '../utils/multisig';

export default function MultiSigPropose() {
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState('');
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  
  const [operation, setOperation] = useState('enroll');
  const [deviceIdHex, setDeviceIdHex] = useState('');
  const [accumulatorHex, setAccumulatorHex] = useState('');
  const [parentHash, setParentHash] = useState('');
  const [operationId, setOperationId] = useState('');
  
  const [safeAddress, setSafeAddress] = useState('');
  const [registryAddress, setRegistryAddress] = useState('');
  const [threshold, setThreshold] = useState(3);
  const [owners, setOwners] = useState([]);
  
  const [proposedTx, setProposedTx] = useState(null);
  const [loading, setLoading] = useState(false);

  // Connect MetaMask
  const connectWallet = async () => {
    if (typeof window.ethereum === 'undefined') {
      toast.error('MetaMask is not installed!');
      return;
    }

    try {
      setLoading(true);
      const provider = new ethers.providers.Web3Provider(window.ethereum);
      const accounts = await provider.send('eth_requestAccounts', []);
      const signer = provider.getSigner();
      
      setProvider(provider);
      setSigner(signer);
      setAccount(accounts[0]);
      setConnected(true);
      
      toast.success(`Connected: ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)}`);
      
      // Load Safe info from backend
      await loadSafeInfo();
    } catch (error) {
      console.error('Error connecting wallet:', error);
      toast.error('Failed to connect wallet');
    } finally {
      setLoading(false);
    }
  };

  // Load Safe configuration
  const loadSafeInfo = async () => {
    try {
      const response = await fetch('/api/multisig/safe-info');
      if (response.ok) {
        const data = await response.json();
        setSafeAddress(data.safeAddress);
        setRegistryAddress(data.registryAddress);
        setThreshold(data.threshold);
        setOwners(data.owners);
      }
    } catch (error) {
      console.error('Error loading Safe info:', error);
    }
  };

  // Generate operation ID
  const generateOperationId = () => {
    return ethers.utils.hexlify(ethers.utils.randomBytes(32));
  };

  // Propose transaction
  const handlePropose = async (e) => {
    e.preventDefault();
    
    if (!connected) {
      toast.error('Please connect your wallet first');
      return;
    }

    setLoading(true);

    try {
      // Get current Safe nonce
      const safeContract = new ethers.Contract(
        safeAddress,
        ['function nonce() view returns (uint256)'],
        provider
      );
      const nonce = await safeContract.nonce();

      // Prepare transaction data
      let txData;
      if (operation === 'enroll') {
        const iface = new ethers.utils.Interface([
          'function registerDevice(bytes32 deviceId, bytes calldata newAccumulator, bytes32 parentHash, bytes32 operationId)'
        ]);
        
        txData = iface.encodeFunctionData('registerDevice', [
          deviceIdHex,
          accumulatorHex,
          parentHash || ethers.constants.HashZero,
          operationId || generateOperationId()
        ]);
      } else {
        const iface = new ethers.utils.Interface([
          'function revokeDevice(bytes32 deviceId, bytes calldata newAccumulator, bytes32 parentHash, bytes32 operationId)'
        ]);
        
        txData = iface.encodeFunctionData('revokeDevice', [
          deviceIdHex,
          accumulatorHex,
          parentHash || ethers.constants.HashZero,
          operationId || generateOperationId()
        ]);
      }

      // Generate Safe transaction hash
      const network = await provider.getNetwork();
      const safeTxHash = generateSafeTxHash(
        safeAddress,
        registryAddress,
        0, // value
        txData,
        0, // operation (Call)
        0, // safeTxGas
        0, // baseGas
        0, // gasPrice
        ethers.constants.AddressZero, // gasToken
        ethers.constants.AddressZero, // refundReceiver
        nonce,
        network.chainId
      );

      // Sign with MetaMask
      const signature = await signTransaction(provider, signer, safeTxHash);
      const { r, s, v } = splitSignature(signature);

      // Create transaction proposal
      const proposal = {
        safeAddress,
        to: registryAddress,
        value: '0',
        data: txData,
        operation: 0,
        safeTxGas: '0',
        baseGas: '0',
        gasPrice: '0',
        gasToken: ethers.constants.AddressZero,
        refundReceiver: ethers.constants.AddressZero,
        nonce: nonce.toString(),
        safeTxHash,
        proposer: account,
        signatures: [{
          signer: account,
          signature,
          r,
          s,
          v
        }],
        operationType: operation,
        deviceIdHex,
        status: 'pending',
        requiredSignatures: threshold,
        createdAt: new Date().toISOString()
      };

      // Submit to backend
      const response = await fetch('/api/multisig/propose', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(proposal)
      });

      if (response.ok) {
        const result = await response.json();
        setProposedTx(result);
        toast.success('Transaction proposed successfully!');
        
        // Clear form
        setDeviceIdHex('');
        setAccumulatorHex('');
        setParentHash('');
        setOperationId('');
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to propose transaction');
      }
    } catch (error) {
      console.error('Error proposing transaction:', error);
      toast.error(error.message || 'Failed to propose transaction');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Multi-Sig Transaction Proposal</h1>
          <p className="mt-1 text-sm text-gray-500">
            Propose device operations for multi-signature approval
          </p>
        </div>
        
        {/* Connect Wallet */}
        {!connected ? (
          <button
            onClick={connectWallet}
            disabled={loading}
            className="btn btn-primary flex items-center"
          >
            <Wallet className="h-4 w-4 mr-2" />
            Connect Wallet
          </button>
        ) : (
          <div className="badge badge-success flex items-center">
            <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
            {account.slice(0, 6)}...{account.slice(-4)}
          </div>
        )}
      </div>

      {/* Safe Info */}
      {connected && safeAddress && (
        <div className="card bg-blue-50 border-blue-200">
          <h3 className="text-sm font-semibold text-blue-900 mb-3">Gnosis Safe Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-blue-700 font-medium">Safe Address:</span>
              <p className="font-mono text-xs text-blue-900 break-all">{safeAddress}</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Registry Address:</span>
              <p className="font-mono text-xs text-blue-900 break-all">{registryAddress}</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Threshold:</span>
              <p className="text-blue-900">{threshold} of {owners.length} signatures required</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Your Role:</span>
              <p className="text-blue-900">
                {owners.includes(account.toLowerCase()) ? '✓ Owner' : '✗ Not an owner'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Proposal Form */}
      {connected && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
            <FileText className="h-5 w-5 mr-2 text-primary-600" />
            Create Transaction Proposal
          </h2>

          <form onSubmit={handlePropose} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Operation Type
              </label>
              <select
                value={operation}
                onChange={(e) => setOperation(e.target.value)}
                className="input"
              >
                <option value="enroll">Enroll Device</option>
                <option value="revoke">Revoke Device</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Device ID (bytes32)
              </label>
              <input
                type="text"
                value={deviceIdHex}
                onChange={(e) => setDeviceIdHex(e.target.value)}
                placeholder="0x..."
                className="input font-mono text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                New Accumulator (hex)
              </label>
              <textarea
                value={accumulatorHex}
                onChange={(e) => setAccumulatorHex(e.target.value)}
                placeholder="0x..."
                rows={3}
                className="input font-mono text-xs"
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Parent Hash (optional)
                </label>
                <input
                  type="text"
                  value={parentHash}
                  onChange={(e) => setParentHash(e.target.value)}
                  placeholder="0x... (auto-generated if empty)"
                  className="input font-mono text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Operation ID (optional)
                </label>
                <input
                  type="text"
                  value={operationId}
                  onChange={(e) => setOperationId(e.target.value)}
                  placeholder="0x... (auto-generated if empty)"
                  className="input font-mono text-sm"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !owners.includes(account.toLowerCase())}
              className="btn btn-primary w-full"
            >
              {loading ? 'Proposing...' : 'Propose Transaction'}
            </button>

            {!owners.includes(account.toLowerCase()) && (
              <p className="text-sm text-red-600 text-center">
                ⚠️ You are not a Safe owner and cannot propose transactions
              </p>
            )}
          </form>
        </div>
      )}

      {/* Proposed Transaction */}
      {proposedTx && (
        <div className="card border-green-200 bg-green-50">
          <div className="flex items-start">
            <CheckCircle className="h-6 w-6 text-green-600 mt-1" />
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-green-900">
                Transaction Proposed Successfully
              </h3>
              <div className="mt-3 space-y-2 text-sm text-green-800">
                <p><strong>Transaction Hash:</strong></p>
                <code className="block bg-white p-2 rounded border border-green-200 text-xs break-all">
                  {proposedTx.safeTxHash}
                </code>
                <p className="mt-2">
                  <strong>Status:</strong> Pending ({proposedTx.signatures?.length || 1} of {threshold} signatures)
                </p>
                <p className="mt-2 text-blue-800 bg-blue-50 p-2 rounded">
                  ℹ️ Share this transaction hash with other Safe owners to collect signatures
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-sm font-medium text-blue-900 mb-2">How Multi-Sig Works</h3>
        <ol className="list-decimal list-inside text-sm text-blue-800 space-y-1">
          <li>Connect your wallet (must be a Safe owner)</li>
          <li>Create transaction proposal with device operation details</li>
          <li>Sign the transaction with your private key (via MetaMask)</li>
          <li>Share transaction hash with other owners</li>
          <li>Other owners sign the same transaction on the Approvals page</li>
          <li>Once threshold is reached ({threshold} signatures), anyone can execute</li>
          <li>Transaction executes on-chain through the Safe</li>
        </ol>
      </div>
    </div>
  );
}
