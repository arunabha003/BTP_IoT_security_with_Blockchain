"""
Blockchain Client for IoT Identity Gateway

Web3 client for interacting with RegistryMock contract on Anvil.
Handles all blockchain operations including accumulator updates.
"""

import time
import logging
from typing import Tuple, Optional
from web3 import Web3
from web3.contract import Contract
from eth_account import Account

from settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChainClient:
    """Web3 client for RegistryMock contract interactions."""
    
    def __init__(self):
        # Initialize Web3 connection
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        
        # Validate connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to blockchain at {settings.rpc_url}")
        
        # Set up account from private key
        self.account = Account.from_key(settings.private_key_admin)
        self.w3.eth.default_account = self.account.address
        
        # Initialize contract
        self.contract = self._init_contract()
        
        logger.info(f"ChainClient initialized")
        logger.info(f"Connected to: {settings.rpc_url}")
        logger.info(f"Account: {self.account.address}")
        logger.info(f"Registry: {settings.registry_address}")
        
        # Verify we're the owner
        self._verify_ownership()
    
    def _init_contract(self) -> Contract:
        """Initialize contract instance."""
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(settings.registry_address),
                abi=settings.get_registry_abi()
            )
            
            # Test contract connectivity
            state = contract.functions.getCurrentState().call()
            
            # AccumulatorRegistry returns 7 values
            acc, hash_val, ver, safe_addr, threshold, owner_count, paused = state
            logger.info(f"Multi-sig contract connectivity verified")
            logger.info(f"Safe: {safe_addr}, Threshold: {threshold}, Owners: {owner_count}")
            logger.info(f"Contract version: {ver}")
            
            return contract
        except Exception as e:
            raise ConnectionError(f"Cannot initialize contract: {e}")
    
    def _verify_ownership(self) -> None:
        """Verify Safe configuration."""
        logger.info("Multi-sig mode: Safe-based authorization")
        logger.info(f"Contract controlled by Safe: {settings.safe_address}")
        return
    
    def get_state(self) -> Tuple[str, str, int]:
        """
        Get current accumulator state from contract.
        
        Returns:
            Tuple[str, str, int]: (accumulator_hex, hash_hex, version)
        """
        try:
            state = self.contract.functions.getCurrentState().call()
            
            # AccumulatorRegistry returns 7 values
            accumulator_bytes, hash_bytes32, version, _, _, _, _ = state
            
            # Convert bytes to hex strings
            accumulator_hex = accumulator_bytes.hex()
            hash_hex = hash_bytes32.hex()
            
            logger.debug(f"Retrieved state: version={version}, hash={hash_hex[:16]}...")
            
            return accumulator_hex, hash_hex, version
        except Exception as e:
            logger.error(f"Failed to get state: {e}")
            raise
    
    def get_parent_hash(self) -> str:
        """Get current stored hash to use as parent hash."""
        _, hash_hex, _ = self.get_state()
        return hash_hex
    
    def _generate_operation_id(self, new_accumulator_hex: str, parent_hash: str) -> str:
        """Generate unique operation ID."""
        timestamp = int(time.time())
        data = f"{timestamp}{new_accumulator_hex}{parent_hash}"
        return self.w3.keccak(text=data).hex()
    
    def _send_transaction(self, tx_function, *args):
        """Send transaction through Safe multi-sig.
        
        Returns:
            tuple: (safe_tx_hash, tx_params)
        """
        try:
            return self._execute_through_safe(tx_function, *args)
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise
    
    def _execute_through_safe(self, tx_function, *args):
        """Execute transaction through Gnosis Safe (multisig mode).
        
        For threshold > 1: This creates a PENDING transaction that requires
        additional signatures. Returns a tuple of (safe_tx_hash, tx_params dict).
        
        Returns:
            tuple: (safe_tx_hash, tx_params) where tx_params contains all Safe transaction parameters
        to track the pending transaction in the multi-sig system.
        """
        from web3 import Web3
        import json
        
        # Encode the call data for the target contract
        call_data = tx_function(*args).build_transaction({
            'from': settings.safe_address,
            'gas': 2000000,
            'gasPrice': 0,
        })['data']
        
        # Get Safe nonce
        safe_abi_minimal = [
            {"inputs": [], "name": "nonce", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "getThreshold", "outputs": [{"type": "uint256"}], "stateMutability": "view", "type": "function"}
        ]
        
        safe_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(settings.safe_address),
            abi=safe_abi_minimal
        )
        
        threshold = safe_contract.functions.getThreshold().call()
        nonce = safe_contract.functions.nonce().call()
        
        # Transaction parameters for Safe
        to = settings.registry_address
        value = 0
        data = call_data
        operation = 0  # Call
        safeTxGas = 0
        baseGas = 0
        gasPrice = 0
        gasToken = "0x0000000000000000000000000000000000000000"
        refundReceiver = "0x0000000000000000000000000000000000000000"
        
        # Import eth_abi for encoding
        from eth_abi import encode
        
        # Calculate Safe transaction hash (EIP-712)
        # Domain separator
        domain_separator = self.w3.keccak(
            encode(
                ['bytes32', 'uint256', 'address'],
                [
                    self.w3.keccak(text="EIP712Domain(uint256 chainId,address verifyingContract)"),
                    31337,  # Anvil chain ID
                    Web3.to_checksum_address(settings.safe_address)
                ]
            )
        )
        
        # Safe tx type hash
        safe_tx_typehash = self.w3.keccak(
            text="SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)"
        )
        
        # Encode Safe transaction
        safe_tx_hash_data = self.w3.keccak(
            encode(
                ['bytes32', 'address', 'uint256', 'bytes32', 'uint8', 'uint256', 'uint256', 'uint256', 'address', 'address', 'uint256'],
                [
                    safe_tx_typehash,
                    Web3.to_checksum_address(to),
                    value,
                    self.w3.keccak(bytes.fromhex(data[2:])),
                    operation,
                    safeTxGas,
                    baseGas,
                    gasPrice,
                    Web3.to_checksum_address(gasToken),
                    Web3.to_checksum_address(refundReceiver),
                    nonce
                ]
            )
        )
        
        # Final Safe transaction hash
        safe_tx_hash = self.w3.keccak(
            b"\x19\x01" + domain_separator + safe_tx_hash_data
        ).hex()
        
        logger.info(f"📝 Multi-sig transaction created")
        logger.info(f"   Safe TX Hash: {safe_tx_hash}")
        logger.info(f"   Threshold: {threshold} signatures required")
        logger.info(f"   Status: PENDING (not executed)")
        logger.info(f"   Next: Go to http://localhost:3000/multisig-approve to sign & execute")
        
        # Return the Safe transaction hash and parameters
        tx_params = {
            'to': to,
            'value': value,
            'data': data,
            'operation': operation,
            'safeTxGas': safeTxGas,
            'baseGas': baseGas,
            'gasPrice': gasPrice,
            'gasToken': gasToken,
            'refundReceiver': refundReceiver,
            'nonce': nonce
        }
        
        return safe_tx_hash, tx_params

    @staticmethod
    def _to_bytes(hex_str: str) -> bytes:
        """Convert hex string (with or without 0x) to bytes."""
        if hex_str.startswith('0x') or hex_str.startswith('0X'):
            hex_str = hex_str[2:]
        return bytes.fromhex(hex_str)
    
    def update_accumulator(self, new_accumulator_hex: str) -> str:
        """
        Update accumulator value on contract.
        
        Args:
            new_accumulator_hex: New accumulator as hex string (512 chars)
            
        Returns:
            str: Transaction hash
        """
        # Validate accumulator format
        if not new_accumulator_hex or len(new_accumulator_hex) != 512:
            raise ValueError(f"Invalid accumulator hex length: {len(new_accumulator_hex)}")
        
        # Get parent hash
        parent_hash = self.get_parent_hash()
        
        # Generate operation ID
        operation_id = self._generate_operation_id(new_accumulator_hex, parent_hash)
        
        # Convert hex to bytes
        accumulator_bytes = self._to_bytes(new_accumulator_hex)
        parent_hash_bytes = self._to_bytes(parent_hash)
        operation_id_bytes = self._to_bytes(operation_id)
        
        logger.info(f"Updating accumulator (op_id: {operation_id[:16]}...)")
        
        return self._send_transaction(
            self.contract.functions.updateAccumulator,
            accumulator_bytes,
            parent_hash_bytes, 
            operation_id_bytes
        )
    
    def register_device(self, device_id_hex: str, new_accumulator_hex: str) -> str:
        """
        Register device on contract.
        
        Args:
            device_id_hex: Device ID as hex string (64 chars = 32 bytes)
            new_accumulator_hex: New accumulator after adding device
            
        Returns:
            str: Transaction hash
        """
        # Validate device ID format
        if not device_id_hex or len(device_id_hex) != 64:
            raise ValueError(f"Invalid device ID hex length: {len(device_id_hex)}")
        
        # Validate accumulator format
        if not new_accumulator_hex or len(new_accumulator_hex) != 512:
            raise ValueError(f"Invalid accumulator hex length: {len(new_accumulator_hex)}")
        
        # Get parent hash
        parent_hash = self.get_parent_hash()
        
        # Generate operation ID
        operation_id = self._generate_operation_id(new_accumulator_hex, parent_hash)
        
        # Convert hex to bytes
        device_id_bytes = self._to_bytes(device_id_hex)
        accumulator_bytes = self._to_bytes(new_accumulator_hex)
        parent_hash_bytes = self._to_bytes(parent_hash)
        operation_id_bytes = self._to_bytes(operation_id)
        
        logger.info(f"Registering device {device_id_hex[:16]}... (op_id: {operation_id[:16]}...)")
        
        return self._send_transaction(
            self.contract.functions.registerDevice,
            device_id_bytes,
            accumulator_bytes,
            parent_hash_bytes,
            operation_id_bytes
        )
    
    def revoke_device(self, device_id_hex: str, new_accumulator_hex: str) -> str:
        """
        Revoke device on contract.
        
        Args:
            device_id_hex: Device ID as hex string (64 chars = 32 bytes)
            new_accumulator_hex: New accumulator after removing device
            
        Returns:
            str: Transaction hash
        """
        # Validate device ID format
        if not device_id_hex or len(device_id_hex) != 64:
            raise ValueError(f"Invalid device ID hex length: {len(device_id_hex)}")
        
        # Validate accumulator format 
        if not new_accumulator_hex or len(new_accumulator_hex) != 512:
            raise ValueError(f"Invalid accumulator hex length: {len(new_accumulator_hex)}")
        
        # Get parent hash
        parent_hash = self.get_parent_hash()
        
        # Generate operation ID
        operation_id = self._generate_operation_id(new_accumulator_hex, parent_hash)
        
        # Convert hex to bytes
        device_id_bytes = self._to_bytes(device_id_hex)
        accumulator_bytes = self._to_bytes(new_accumulator_hex)
        parent_hash_bytes = self._to_bytes(parent_hash)
        operation_id_bytes = self._to_bytes(operation_id)
        
        logger.info(f"Revoking device {device_id_hex[:16]}... (op_id: {operation_id[:16]}...)")
        
        return self._send_transaction(
            self.contract.functions.revokeDevice,
            device_id_bytes,
            accumulator_bytes,
            parent_hash_bytes,
            operation_id_bytes
        )
    
    def get_chain_info(self) -> dict:
        """Get blockchain connection information."""
        try:
            latest_block = self.w3.eth.get_block('latest')
            balance = self.w3.eth.get_balance(self.account.address)
            
            return {
                'connected': self.w3.is_connected(),
                'chain_id': self.w3.eth.chain_id,
                'latest_block': latest_block.number,
                'account_address': self.account.address,
                'account_balance_wei': balance,
                'account_balance_eth': self.w3.from_wei(balance, 'ether'),
                'registry_address': settings.registry_address,
                'rpc_url': settings.rpc_url
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def get_safe_info(self) -> dict:
        """Get Gnosis Safe configuration."""
        return {
            "safe_address": settings.safe_address,
            "registry_address": settings.registry_address,
            "threshold": settings.safe_threshold,
            "owners": [owner.lower() for owner in settings.safe_owners]
        }


def main():
    """Test chain client functionality."""
    try:
        print("Testing Chain Client")
        print("=" * 40)
        
        # Initialize client
        client = ChainClient()
        
        # Get chain info
        info = client.get_chain_info()
        print(f"Chain ID: {info['chain_id']}")
        print(f"Latest block: {info['latest_block']}")
        print(f"Account: {info['account_address']}")
        print(f"Balance: {info['account_balance_eth']} ETH")
        
        # Get current state
        acc_hex, hash_hex, version = client.get_state()
        print(f"Current version: {version}")
        print(f"Accumulator: {acc_hex[:32]}...{acc_hex[-32:]}")
        print(f"Hash: {hash_hex}")
        
        print("Chain client test complete")
        
    except Exception as e:
        print(f"Chain client test failed: {e}")


if __name__ == "__main__":
    main()
