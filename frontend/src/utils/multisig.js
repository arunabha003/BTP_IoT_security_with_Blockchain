// Multi-signature transaction utilities for Gnosis Safe integration

import { ethers } from 'ethers';

/**
 * Generate Safe transaction hash for EIP-712 signing
 */
export function generateSafeTxHash(
  safeAddress,
  to,
  value,
  data,
  operation,
  safeTxGas,
  baseGas,
  gasPrice,
  gasToken,
  refundReceiver,
  nonce,
  chainId
) {
  // EIP-712 Domain Separator
  const domainSeparator = ethers.utils.keccak256(
    ethers.utils.defaultAbiCoder.encode(
      ['bytes32', 'uint256', 'address'],
      [
        ethers.utils.id('EIP712Domain(uint256 chainId,address verifyingContract)'),
        chainId,
        safeAddress
      ]
    )
  );

  // Safe Transaction Hash
  const safeTxHashData = ethers.utils.keccak256(
    ethers.utils.defaultAbiCoder.encode(
      [
        'bytes32',
        'address',
        'uint256',
        'bytes32',
        'uint8',
        'uint256',
        'uint256',
        'uint256',
        'address',
        'address',
        'uint256'
      ],
      [
        ethers.utils.id(
          'SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)'
        ),
        to,
        value,
        ethers.utils.keccak256(data),
        operation,
        safeTxGas,
        baseGas,
        gasPrice,
        gasToken,
        refundReceiver,
        nonce
      ]
    )
  );

  // Combine with EIP-712 prefix
  return ethers.utils.keccak256(
    ethers.utils.solidityPack(
      ['bytes1', 'bytes1', 'bytes32', 'bytes32'],
      ['0x19', '0x01', domainSeparator, safeTxHashData]
    )
  );
}

/**
 * Encode registerDevice call data
 */
export function encodeRegisterDevice(deviceId, newAccumulator, parentHash, operationId) {
  const iface = new ethers.utils.Interface([
    'function registerDevice(bytes32 deviceId, bytes calldata newAccumulator, bytes32 parentHash, bytes32 operationId)'
  ]);
  
  return iface.encodeFunctionData('registerDevice', [
    deviceId,
    newAccumulator,
    parentHash,
    operationId
  ]);
}

/**
 * Encode revokeDevice call data
 */
export function encodeRevokeDevice(deviceId, newAccumulator, parentHash, operationId) {
  const iface = new ethers.utils.Interface([
    'function revokeDevice(bytes32 deviceId, bytes calldata newAccumulator, bytes32 parentHash, bytes32 operationId)'
  ]);
  
  return iface.encodeFunctionData('revokeDevice', [
    deviceId,
    newAccumulator,
    parentHash,
    operationId
  ]);
}

/**
 * Sign transaction with MetaMask (EIP-712 typed data)
 */
export async function signTransaction(provider, signer, safeTxHash, tx, safeAddress, chainId) {
  console.log('signTransaction called');
  
  const address = await signer.getAddress();
  console.log('Signer address:', address);
  console.log('Transaction:', tx);
  console.log('Safe address:', safeAddress);
  console.log('Chain ID:', chainId);
  
  // Ensure all numeric values are properly converted
  const message = {
    to: tx.to,
    value: String(tx.value || 0),
    data: tx.data || '0x',
    operation: Number(tx.operation || 0),
    safeTxGas: String(tx.safeTxGas || 0),
    baseGas: String(tx.baseGas || 0),
    gasPrice: String(tx.gasPrice || 0),
    gasToken: tx.gasToken || '0x0000000000000000000000000000000000000000',
    refundReceiver: tx.refundReceiver || '0x0000000000000000000000000000000000000000',
    nonce: Number(tx.nonce || 0)
  };
  
  // Build EIP-712 typed data structure for Gnosis Safe
  const typedData = {
    types: {
      EIP712Domain: [
        { name: 'chainId', type: 'uint256' },
        { name: 'verifyingContract', type: 'address' }
      ],
      SafeTx: [
        { name: 'to', type: 'address' },
        { name: 'value', type: 'uint256' },
        { name: 'data', type: 'bytes' },
        { name: 'operation', type: 'uint8' },
        { name: 'safeTxGas', type: 'uint256' },
        { name: 'baseGas', type: 'uint256' },
        { name: 'gasPrice', type: 'uint256' },
        { name: 'gasToken', type: 'address' },
        { name: 'refundReceiver', type: 'address' },
        { name: 'nonce', type: 'uint256' }
      ]
    },
    primaryType: 'SafeTx',
    domain: {
      chainId: chainId,
      verifyingContract: safeAddress
    },
    message: message
  };
  
  console.log('EIP-712 typed data:', JSON.stringify(typedData, null, 2));
  
  // Manually compute the hash for verification
  const domainSeparator = ethers.utils.keccak256(
    ethers.utils.defaultAbiCoder.encode(
      ['bytes32', 'uint256', 'address'],
      [
        ethers.utils.id('EIP712Domain(uint256 chainId,address verifyingContract)'),
        chainId,
        safeAddress
      ]
    )
  );
  
  const safeTxTypeHash = ethers.utils.id(
    'SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)'
  );
  
  const safeTxHashData = ethers.utils.keccak256(
    ethers.utils.defaultAbiCoder.encode(
      ['bytes32', 'address', 'uint256', 'bytes32', 'uint8', 'uint256', 'uint256', 'uint256', 'address', 'address', 'uint256'],
      [
        safeTxTypeHash,
        message.to,
        message.value,
        ethers.utils.keccak256(message.data),
        message.operation,
        message.safeTxGas,
        message.baseGas,
        message.gasPrice,
        message.gasToken,
        message.refundReceiver,
        message.nonce
      ]
    )
  );
  
  const computedHash = ethers.utils.keccak256(
    ethers.utils.solidityPack(
      ['bytes1', 'bytes1', 'bytes32', 'bytes32'],
      ['0x19', '0x01', domainSeparator, safeTxHashData]
    )
  );
  
  console.log('Computed Safe TX Hash:', computedHash);
  console.log('Expected Safe TX Hash:', safeTxHash);
  console.log('Hashes match:', computedHash.toLowerCase() === safeTxHash.toLowerCase());
  
  console.log('Requesting EIP-712 signature from MetaMask...');
  
  // Sign using eth_signTypedData_v4
  const signature = await provider.send('eth_signTypedData_v4', [
    address.toLowerCase(),
    JSON.stringify(typedData)
  ]);
  
  console.log('Signature received from MetaMask:', signature);
  return signature;
}

/**
 * Split signature into r, s, v components
 */
export function splitSignature(signature) {
  const sig = ethers.utils.splitSignature(signature);
  
  // For EIP-712 typed data signatures, v is already correct (27/28)
  // No need to add offset
  let v = sig.v;
  if (v < 27) {
    v += 27;
  }
  
  return {
    r: sig.r,
    s: sig.s,
    v: v
  };
}

/**
 * Combine multiple signatures for Safe execution
 * Signatures must be sorted by signer address (ascending)
 */
export function combineSignatures(signatures, owners) {
  // Sort signatures by signer address (ascending)
  const sortedSignatures = [...signatures].sort((a, b) => {
    const addrA = a.signer.toLowerCase();
    const addrB = b.signer.toLowerCase();
    return addrA < addrB ? -1 : addrA > addrB ? 1 : 0;
  });

  // Concatenate r, s, v for each signature
  let combinedSigs = '0x';
  for (const sig of sortedSignatures) {
    // Remove '0x' prefix and concatenate
    const r = sig.r.startsWith('0x') ? sig.r.slice(2) : sig.r;
    const s = sig.s.startsWith('0x') ? sig.s.slice(2) : sig.s;
    const v = typeof sig.v === 'number' ? sig.v.toString(16).padStart(2, '0') : sig.v;
    
    combinedSigs += r;
    combinedSigs += s;
    combinedSigs += v;
  }

  return combinedSigs;
}

/**
 * Get Safe contract instance
 */
export function getSafeContract(safeAddress, provider) {
  const abi = [
    'function nonce() view returns (uint256)',
    'function getThreshold() view returns (uint256)',
    'function getOwners() view returns (address[])',
    'function execTransaction(address to, uint256 value, bytes calldata data, uint8 operation, uint256 safeTxGas, uint256 baseGas, uint256 gasPrice, address gasToken, address refundReceiver, bytes calldata signatures) external payable returns (bool success)'
  ];
  
  return new ethers.Contract(safeAddress, abi, provider);
}
