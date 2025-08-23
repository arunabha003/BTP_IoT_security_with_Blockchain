"""
Blockchain Client and Event Monitoring

Web3.py client for interacting with the AccumulatorRegistry contract
and monitoring blockchain events.
"""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from web3 import Web3
from web3.contract import Contract
from web3.types import FilterParams, LogReceipt
from sqlalchemy import select, desc

try:
    from .config import get_settings
    from .database import get_db_session
    from .models import AccumulatorRoot, EventLog
except ImportError:
    from config import get_settings
    from database import get_db_session
    from models import AccumulatorRoot, EventLog

logger = logging.getLogger(__name__)


class BlockchainClient:
    """Web3.py client for AccumulatorRegistry contract interaction."""
    
    def __init__(self):
        self.w3: Web3 | None = None
        self.contract: Contract | None = None
        self.current_root: str = "0x"
        self._monitoring_task: asyncio.Task | None = None
        
    async def initialize(self) -> None:
        """Initialize Web3 connection and load contract."""
        settings = get_settings()
        
        # Connect to RPC
        logger.info(f"Connecting to RPC: {settings.rpc_url}")
        self.w3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        
        # Check connection
        try:
            is_connected = self.w3.is_connected()
            if not is_connected:
                logger.warning("Web3 connection failed - continuing without blockchain")
                return
                
            latest_block = self.w3.eth.block_number
            logger.info(f"Connected to blockchain - latest block: {latest_block}")
            
        except Exception as e:
            logger.warning(f"Blockchain connection error: {e} - continuing without blockchain")
            return
        
        # Load contract if address provided
        if settings.contract_address:
            await self._load_contract(settings.contract_address)
            await self._sync_current_root()
        else:
            logger.info("No contract address provided - skipping contract loading")
    
    async def _load_contract(self, contract_address: str) -> None:
        """Load AccumulatorRegistry contract from build artifacts."""
        settings = get_settings()
        
        # Find contract ABI
        contracts_dir = Path(settings.contracts_out_dir)
        abi_file = contracts_dir / "AccumulatorRegistry.sol" / "AccumulatorRegistry.json"
        
        if not abi_file.exists():
            logger.warning(f"Contract ABI not found at {abi_file}")
            return
            
        try:
            with open(abi_file, 'r') as f:
                contract_data = json.load(f)
                
            abi = contract_data.get('abi', [])
            if not abi:
                logger.error("No ABI found in contract file")
                return
                
            # Create contract instance
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=abi
            )
            
            logger.info(f"Loaded AccumulatorRegistry contract at {contract_address}")
            
        except Exception as e:
            logger.error(f"Failed to load contract: {e}")
            
    async def _sync_current_root(self) -> None:
        """Sync current accumulator root from contract."""
        if not self.contract:
            return
            
        try:
            # Get current accumulator from contract
            current_accumulator = self.contract.functions.currentAccumulator().call()
            self.current_root = current_accumulator.hex() if isinstance(current_accumulator, bytes) else hex(current_accumulator)
            
            logger.info(f"Synced current root: {self.current_root}")
            
        except Exception as e:
            logger.error(f"Failed to sync current root: {e}")
    
    async def get_current_root(self) -> str:
        """Get current accumulator root (cached or from contract)."""
        if self.current_root and self.current_root != "0x":
            return self.current_root
            
        # Try to get from contract
        if self.contract:
            try:
                current_accumulator = self.contract.functions.currentAccumulator().call()
                self.current_root = current_accumulator.hex() if isinstance(current_accumulator, bytes) else hex(current_accumulator)
                return self.current_root
            except Exception as e:
                logger.error(f"Failed to get current root from contract: {e}")
        
        # Fallback to database
        async with get_db_session() as session:
            stmt = select(AccumulatorRoot).order_by(desc(AccumulatorRoot.block)).limit(1)
            result = await session.execute(stmt)
            latest_root = result.scalar_one_or_none()
            
            if latest_root:
                self.current_root = latest_root.value
                return self.current_root
        
        # Return empty if nothing found
        return "0x"
    
    async def start_event_monitoring(self) -> None:
        """Start monitoring AccumulatorUpdated events."""
        if not self.contract or not self.w3:
            logger.info("Contract not loaded - skipping event monitoring")
            return
            
        logger.info("Starting event monitoring...")
        self._monitoring_task = asyncio.create_task(self._event_monitor_loop())
    
    async def stop_event_monitoring(self) -> None:
        """Stop event monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Event monitoring stopped")
    
    async def _event_monitor_loop(self) -> None:
        """Main event monitoring loop."""
        settings = get_settings()
        last_processed_block = await self._get_last_processed_block()
        
        logger.info(f"Starting event monitoring from block {last_processed_block + 1}")
        
        while True:
            try:
                current_block = self.w3.eth.block_number
                
                if current_block > last_processed_block:
                    await self._process_events(last_processed_block + 1, current_block)
                    last_processed_block = current_block
                
                await asyncio.sleep(settings.event_poll_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in event monitoring: {e}")
                await asyncio.sleep(settings.event_poll_interval)
    
    async def _get_last_processed_block(self) -> int:
        """Get the last processed block number from database."""
        async with get_db_session() as session:
            stmt = select(EventLog.block_number).order_by(desc(EventLog.block_number)).limit(1)
            result = await session.execute(stmt)
            last_block = result.scalar_one_or_none()
            
            if last_block is not None:
                return last_block
            
            # If no events processed yet, start from current block
            return self.w3.eth.block_number if self.w3 else 0
    
    async def _process_events(self, from_block: int, to_block: int) -> None:
        """Process AccumulatorUpdated events in block range."""
        try:
            # Get AccumulatorUpdated events
            event_filter = self.contract.events.AccumulatorUpdated.create_filter(
                fromBlock=from_block,
                toBlock=to_block
            )
            
            events = event_filter.get_all_entries()
            
            for event in events:
                await self._handle_accumulator_updated_event(event)
                
            if events:
                logger.info(f"Processed {len(events)} events from blocks {from_block}-{to_block}")
                
        except Exception as e:
            logger.error(f"Failed to process events: {e}")
    
    async def _handle_accumulator_updated_event(self, event: LogReceipt) -> None:
        """Handle a single AccumulatorUpdated event."""
        try:
            # Extract event data
            args = event['args']
            new_root = args.get('newRoot', 0)
            parent_hash = args.get('parentHash', '0x')
            block_number = event['blockNumber']
            tx_hash = event['transactionHash'].hex()
            
            # Convert root to hex
            if isinstance(new_root, int):
                root_hex = hex(new_root)
            elif isinstance(new_root, bytes):
                root_hex = new_root.hex()
            else:
                root_hex = str(new_root)
                
            logger.info(f"AccumulatorUpdated: root={root_hex}, block={block_number}")
            
            # Update cache
            self.current_root = root_hex
            
            # Store in database
            async with get_db_session() as session:
                # Store accumulator root
                acc_root = AccumulatorRoot(
                    value=root_hex,
                    block=block_number,
                    hash=parent_hash,
                    tx_hash=tx_hash,
                    operation="AccumulatorUpdated"
                )
                session.add(acc_root)
                
                # Store event log
                event_log = EventLog(
                    event_type="AccumulatorUpdated",
                    block_number=block_number,
                    tx_hash=tx_hash,
                    log_index=event['logIndex'],
                    event_data=json.dumps({
                        'newRoot': root_hex,
                        'parentHash': parent_hash,
                        'blockNumber': block_number
                    }),
                    status="processed"
                )
                session.add(event_log)
                
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to handle AccumulatorUpdated event: {e}")


# Global blockchain client instance
blockchain_client = BlockchainClient()


async def init_blockchain() -> None:
    """Initialize blockchain client - called on startup."""
    await blockchain_client.initialize()
    await blockchain_client.start_event_monitoring()


async def close_blockchain() -> None:
    """Close blockchain client - called on shutdown."""
    await blockchain_client.stop_event_monitoring()
