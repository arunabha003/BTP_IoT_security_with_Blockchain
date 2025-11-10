import React, { useState, useEffect } from 'react';
import { Users, CheckCircle, Clock, XCircle, Wallet, Shield } from 'lucide-react';
import { ethers } from 'ethers';
import toast from 'react-hot-toast';
import { signTransaction, splitSignature, combineSignatures } from '../utils/multisig';

export default function MultiSigApprove() {
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState('');
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  const [chainId, setChainId] = useState(null);
  
  const [pendingTxs, setPendingTxs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  
  const [safeAddress, setSafeAddress] = useState('');
  const [registryAddress, setRegistryAddress] = useState('');
  const [threshold, setThreshold] = useState(3);
  const [owners, setOwners] = useState([]);

  // Connect MetaMask
  const connectWallet = async () => {
    if (typeof window.ethereum === 'undefined') {
      toast.error('MetaMask is not installed!');
      return;
    }

    try {
      setLoading(true);
      const provider = new ethers.providers.Web3Provider(window.ethereum);
      
      // Check network
      const network = await provider.getNetwork();
      console.log('Current network:', network);
      
      if (network.chainId !== 31337) {
        toast.error(`Wrong network! Please switch to Anvil (Chain ID: 31337). Current: ${network.chainId}`);
        
        // Try to switch to Anvil network
        try {
          await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: '0x7a69' }], // 31337 in hex
          });
          toast.success('Switched to Anvil network');
        } catch (switchError) {
          // Network doesn't exist, try to add it
          if (switchError.code === 4902) {
            try {
              await window.ethereum.request({
                method: 'wallet_addEthereumChain',
                params: [{
                  chainId: '0x7a69',
                  chainName: 'Anvil Local',
                  nativeCurrency: {
                    name: 'Ethereum',
                    symbol: 'ETH',
                    decimals: 18
                  },
                  rpcUrls: ['http://127.0.0.1:8545'],
                  blockExplorerUrls: null
                }]
              });
              toast.success('Anvil network added to MetaMask');
            } catch (addError) {
              console.error('Error adding network:', addError);
              toast.error('Please manually add Anvil network to MetaMask');
              setLoading(false);
              return;
            }
          } else {
            console.error('Error switching network:', switchError);
            setLoading(false);
            return;
          }
        }
      }
      
      const accounts = await provider.send('eth_requestAccounts', []);
      const signer = provider.getSigner();
      
      setProvider(provider);
      setSigner(signer);
      setAccount(accounts[0]);
      setChainId(network.chainId); // Use the network variable from above
      setConnected(true);
      
      toast.success(`Connected: ${accounts[0].slice(0, 6)}...${accounts[0].slice(-4)}`);
      
      // Load Safe info and pending transactions
      await loadSafeInfo();
      await loadPendingTransactions();
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

  // Load pending transactions
  const loadPendingTransactions = async () => {
    try {
      setRefreshing(true);
      const response = await fetch('/api/multisig/pending');
      if (response.ok) {
        const data = await response.json();
        setPendingTxs(data.transactions || []);
      }
    } catch (error) {
      console.error('Error loading pending transactions:', error);
    } finally {
      setRefreshing(false);
    }
  };

  // Sign transaction
  const handleSign = async (tx) => {
    console.log('=== handleSign called ===');
    console.log('Connected:', connected);
    console.log('Account:', account);
    console.log('Transaction:', tx);
    console.log('Owners:', owners);
    
    if (!connected) {
      toast.error('Please connect your wallet first');
      return;
    }

    if (!owners.includes(account.toLowerCase())) {
      toast.error('You are not a Safe owner');
      console.log('Account not in owners list:', { account: account.toLowerCase(), owners });
      return;
    }

    // Check if already signed
    const alreadySigned = tx.signatures.some(
      sig => sig.signer.toLowerCase() === account.toLowerCase()
    );
    if (alreadySigned) {
      toast.error('You have already signed this transaction');
      return;
    }

    setLoading(true);

    try {
      console.log('Calling signTransaction...');
      console.log('Provider:', provider);
      console.log('Signer:', signer);
      console.log('SafeTxHash:', tx.safeTxHash);
      console.log('Transaction data:', tx);
      
      // Sign with MetaMask using EIP-712
      const signature = await signTransaction(provider, signer, tx.safeTxHash, tx, safeAddress, chainId);
      console.log('Signature received:', signature);
      
      const { r, s, v } = splitSignature(signature);
      console.log('Signature split:', { r, s, v });

      // Submit signature to backend
      const response = await fetch('/api/multisig/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          safeTxHash: tx.safeTxHash,
          signer: account,
          signature,
          r,
          s,
          v
        })
      });

      if (response.ok) {
        toast.success('Transaction signed successfully!');
        await loadPendingTransactions();
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to sign transaction');
      }
    } catch (error) {
      console.error('Error signing transaction:', error);
      toast.error(error.message || 'Failed to sign transaction');
    } finally {
      setLoading(false);
    }
  };

  // Execute transaction
  const handleExecute = async (tx) => {
    if (!connected) {
      toast.error('Please connect your wallet first');
      return;
    }

    if (tx.signatures.length < threshold) {
      toast.error(`Not enough signatures (${tx.signatures.length}/${threshold})`);
      return;
    }

    setLoading(true);

    try {
      // Combine signatures
      const combinedSigs = combineSignatures(tx.signatures, owners);

      // Prepare Safe execTransaction call
      const safeABI = [
        'function execTransaction(address to, uint256 value, bytes calldata data, uint8 operation, uint256 safeTxGas, uint256 baseGas, uint256 gasPrice, address gasToken, address refundReceiver, bytes calldata signatures) external payable returns (bool success)'
      ];
      
      const safeContract = new ethers.Contract(safeAddress, safeABI, signer);

      // Execute transaction
      const txResponse = await safeContract.execTransaction(
        tx.to,
        tx.value,
        tx.data,
        tx.operation,
        tx.safeTxGas,
        tx.baseGas,
        tx.gasPrice,
        tx.gasToken,
        tx.refundReceiver,
        combinedSigs,
        {
          gasLimit: 500000
        }
      );

      toast.loading('Transaction submitted. Waiting for confirmation...', { id: 'exec-tx' });
      
      const receipt = await txResponse.wait();
      
      toast.dismiss('exec-tx');
      
      if (receipt.status === 1) {
        toast.success('Transaction executed successfully!');
        
        // Update backend
        await fetch('/api/multisig/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            safeTxHash: tx.safeTxHash,
            txHash: receipt.transactionHash,
            blockNumber: receipt.blockNumber
          })
        });
        
        await loadPendingTransactions();
      } else {
        toast.error('Transaction execution failed');
      }
    } catch (error) {
      console.error('Error executing transaction:', error);
      toast.dismiss('exec-tx');
      toast.error(error.message || 'Failed to execute transaction');
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh
  useEffect(() => {
    if (connected) {
      const interval = setInterval(() => {
        loadPendingTransactions();
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [connected]);

  const getStatusBadge = (tx) => {
    const signatureCount = tx.signatures.length;
    if (signatureCount >= threshold) {
      return <span className="badge badge-success">Ready to Execute</span>;
    }
    return <span className="badge badge-warning">Pending ({signatureCount}/{threshold})</span>;
  };

  const hasUserSigned = (tx) => {
    return tx.signatures.some(sig => sig.signer.toLowerCase() === account.toLowerCase());
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Multi-Sig Approvals</h1>
          <p className="mt-1 text-sm text-gray-500">
            Review and sign pending multi-signature transactions
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
          <div className="flex items-center space-x-3">
            <button
              onClick={loadPendingTransactions}
              disabled={refreshing}
              className="btn btn-secondary"
            >
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
            <div className="badge badge-success flex items-center">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              {account.slice(0, 6)}...{account.slice(-4)}
            </div>
          </div>
        )}
      </div>

      {/* Safe Info */}
      {connected && safeAddress && (
        <div className="card bg-blue-50 border-blue-200">
          <h3 className="text-sm font-semibold text-blue-900 mb-3">Gnosis Safe Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-blue-700 font-medium">Threshold:</span>
              <p className="text-blue-900">{threshold} of {owners.length} signatures required</p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Your Role:</span>
              <p className="text-blue-900">
                {owners.includes(account.toLowerCase()) ? '✓ Owner (can sign)' : '✗ Not an owner'}
              </p>
            </div>
            <div>
              <span className="text-blue-700 font-medium">Pending Transactions:</span>
              <p className="text-blue-900">{pendingTxs.length} awaiting approval</p>
            </div>
          </div>
        </div>
      )}

      {/* Pending Transactions */}
      {connected && (
        <div className="space-y-4">
          {pendingTxs.length === 0 ? (
            <div className="card text-center py-12">
              <CheckCircle className="h-12 w-12 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-500">No pending transactions</p>
              <p className="text-sm text-gray-400 mt-1">
                All transactions have been executed or there are no proposals yet
              </p>
            </div>
          ) : (
            pendingTxs.map((tx, index) => (
              <div key={tx.safeTxHash} className="card hover:shadow-lg transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {tx.operationType === 'enroll' ? '📥 Enroll Device' : '🗑️ Revoke Device'}
                      </h3>
                      {getStatusBadge(tx)}
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                      Proposed by {tx.proposer.slice(0, 6)}...{tx.proposer.slice(-4)} on{' '}
                      {new Date(tx.createdAt).toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Transaction Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4 text-sm">
                  <div>
                    <span className="text-gray-600 font-medium">Device ID:</span>
                    <p className="font-mono text-xs text-gray-900 break-all">{tx.deviceIdHex}</p>
                  </div>
                  <div>
                    <span className="text-gray-600 font-medium">Safe Tx Hash:</span>
                    <p className="font-mono text-xs text-gray-900 break-all">
                      {tx.safeTxHash.slice(0, 20)}...{tx.safeTxHash.slice(-20)}
                    </p>
                  </div>
                </div>

                {/* Signatures */}
                <div className="mb-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Signatures ({tx.signatures.length}/{threshold})
                  </h4>
                  <div className="space-y-1">
                    {tx.signatures.map((sig, idx) => (
                      <div key={idx} className="flex items-center text-xs">
                        <CheckCircle className="h-4 w-4 text-green-500 mr-2" />
                        <span className="font-mono text-gray-700">
                          {sig.signer.slice(0, 10)}...{sig.signer.slice(-8)}
                        </span>
                        {sig.signer.toLowerCase() === account.toLowerCase() && (
                          <span className="ml-2 text-blue-600 font-medium">(You)</span>
                        )}
                      </div>
                    ))}
                    {Array.from({ length: threshold - tx.signatures.length }).map((_, idx) => (
                      <div key={`pending-${idx}`} className="flex items-center text-xs">
                        <Clock className="h-4 w-4 text-gray-400 mr-2" />
                        <span className="text-gray-400">Awaiting signature...</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-3">
                  {!hasUserSigned(tx) && owners.includes(account.toLowerCase()) && (
                    <button
                      onClick={() => handleSign(tx)}
                      disabled={loading}
                      className="btn btn-primary"
                    >
                      <Shield className="h-4 w-4 mr-2" />
                      Sign Transaction
                    </button>
                  )}
                  
                  {hasUserSigned(tx) && (
                    <div className="badge badge-success">
                      <CheckCircle className="h-4 w-4 mr-1" />
                      You signed this
                    </div>
                  )}
                  
                  {tx.signatures.length >= threshold && (
                    <button
                      onClick={() => handleExecute(tx)}
                      disabled={loading}
                      className="btn btn-success"
                    >
                      Execute Transaction
                    </button>
                  )}
                  
                  {tx.signatures.length < threshold && (
                    <span className="text-sm text-gray-500">
                      {threshold - tx.signatures.length} more signature(s) needed
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Info Box */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="text-sm font-medium text-blue-900 mb-2">Approval Workflow</h3>
        <ol className="list-decimal list-inside text-sm text-blue-800 space-y-1">
          <li>Review pending transaction details carefully</li>
          <li>Click "Sign Transaction" to approve with your private key</li>
          <li>Wait for other owners to sign (need {threshold} total signatures)</li>
          <li>Once threshold is reached, any owner can execute</li>
          <li>Execution submits the transaction to the Safe contract</li>
          <li>Safe contract validates signatures and executes on-chain</li>
        </ol>
      </div>
    </div>
  );
}
