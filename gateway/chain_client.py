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
            contract.functions.getCurrentState().call()
            logger.info("Contract connectivity verified")
            
            return contract
        except Exception as e:
            raise ConnectionError(f"Cannot initialize contract: {e}")
    
    def _verify_ownership(self) -> None:
        """Verify that our account is the contract owner."""
        try:
            contract_owner = self.contract.functions.owner().call()
            if contract_owner.lower() != self.account.address.lower():
                raise PermissionError(
                    f"Account {self.account.address} is not the contract owner. "
                    f"Owner is: {contract_owner}"
                )
            logger.info("Ownership verified")
        except Exception as e:
            raise PermissionError(f"Cannot verify ownership: {e}")
    
    def get_state(self) -> Tuple[str, str, int]:
        """
        Get current accumulator state from contract.
        
        Returns:
            Tuple[str, str, int]: (accumulator_hex, hash_hex, version)
        """
        try:
            accumulator_bytes, hash_bytes32, version = self.contract.functions.getCurrentState().call()
            
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
    
    def _send_transaction(self, tx_function, *args) -> str:
        """Send transaction with proper gas estimation and nonce management."""
        try:
            # Build transaction
            tx = tx_function(*args).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 2000000,  # High gas limit for safety 
                'gasPrice': self.w3.to_wei('1', 'gwei'),
            })
            
            # Sign and send transaction
            signed_tx = self.account.sign_transaction(tx)
            # Handle both old and new web3 versions
            raw_tx = getattr(signed_tx, 'rawTransaction', getattr(signed_tx, 'raw_transaction', None))
            tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
            
            if receipt.status != 1:
                raise Exception(f"Transaction failed with status: {receipt.status}")
            
            tx_hash_hex = tx_hash.hex()
            logger.info(f"Transaction successful: {tx_hash_hex}")
            
            return tx_hash_hex
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise

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
