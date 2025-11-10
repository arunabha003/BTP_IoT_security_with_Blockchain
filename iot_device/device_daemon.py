#!/usr/bin/env python3
"""
IoT Device Daemon - Production Flow
====================================
Runs periodic authentication to maintain active device status.

Usage:
    python device_daemon.py [gateway_url] [--interval SECONDS]

Examples:
    python device_daemon.py http://127.0.0.1:8000 --interval 30
    DEVICE_STATE_DIR=./device_state_1 python device_daemon.py
"""

import argparse
import time
import sys
import logging
from pathlib import Path

from auth import authenticate_device
from state import load_state, save_state
from check_enrollment import check_and_update_enrollment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DeviceDaemon:
    """Manages periodic device authentication."""
    
    def __init__(self, gateway_url: str, auth_interval: int = 60):
        """
        Initialize daemon.
        
        Args:
            gateway_url: Base URL of the gateway API
            auth_interval: Seconds between authentication attempts
        """
        self.gateway_url = gateway_url.rstrip('/')
        self.auth_interval = auth_interval
        self.consecutive_failures = 0
        self.max_failures = 5
        self.running = False
        
    def check_enrollment_status(self) -> bool:
        """
        Check if device is enrolled and approved.
        
        Returns:
            True if ready to authenticate, False otherwise
        """
        state = load_state()
        
        # Check if device has basic enrollment data
        if not state.get('device_id_hex') or not state.get('public_key_pem'):
            logger.error("Device not enrolled. Run keygen.py and enroll.py first.")
            return False
        
        # Check if pending multi-sig approval
        if state.get('pending_enrollment'):
            logger.info("Device enrollment pending multi-sig approval.")
            logger.info("Checking if enrollment has been executed...")
            
            try:
                # Try to update enrollment status
                check_and_update_enrollment(self.gateway_url)
                state = load_state()  # Reload after update
                
                if state.get('pending_enrollment'):
                    logger.warning("Still pending approval. Waiting...")
                    return False
                else:
                    logger.info("✓ Enrollment approved! Device ready to authenticate.")
                    return True
            except Exception as e:
                logger.error(f"Failed to check enrollment status: {e}")
                return False
        
        # Check if device has required auth credentials
        if not state.get('id_prime') or not state.get('witness_hex'):
            logger.error("Missing credentials (id_prime or witness). Run check_enrollment.py")
            return False
        
        return True
    
    def authenticate_once(self) -> bool:
        """
        Perform single authentication attempt.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            result = authenticate_device(self.gateway_url)
            
            if result.get('success'):
                logger.info(f"✓ Authentication successful - {result.get('message', 'Device authenticated')}")
                
                # Check if witness was updated
                if result.get('newWitnessHex'):
                    logger.info("↻ Witness updated by gateway")
                    state = load_state()
                    state['witness_hex'] = result['newWitnessHex']
                    save_state(state)
                    logger.info("✓ Local witness saved")
                
                self.consecutive_failures = 0
                return True
            else:
                logger.warning(f"✗ Authentication failed: {result.get('message', 'Unknown error')}")
                self.consecutive_failures += 1
                return False
                
        except Exception as e:
            logger.error(f"✗ Authentication error: {e}")
            self.consecutive_failures += 1
            return False
    
    def run(self):
        """Main daemon loop."""
        logger.info("=" * 60)
        logger.info("IoT Device Authentication Daemon")
        logger.info("=" * 60)
        logger.info(f"Gateway: {self.gateway_url}")
        logger.info(f"Auth interval: {self.auth_interval}s")
        logger.info(f"Max consecutive failures: {self.max_failures}")
        logger.info("=" * 60)
        
        # Initial enrollment check
        if not self.check_enrollment_status():
            logger.error("Device not ready. Exiting.")
            return 1
        
        self.running = True
        logger.info("Starting authentication loop... (Press Ctrl+C to stop)")
        
        try:
            while self.running:
                # Authenticate
                success = self.authenticate_once()
                
                # Check failure threshold
                if self.consecutive_failures >= self.max_failures:
                    logger.error(f"✗ {self.max_failures} consecutive failures. Stopping daemon.")
                    logger.error("Check device enrollment status and gateway connectivity.")
                    return 1
                
                # Wait before next authentication
                if success:
                    logger.info(f"Waiting {self.auth_interval}s until next auth...")
                else:
                    # Exponential backoff on failure
                    backoff = min(self.auth_interval * (2 ** (self.consecutive_failures - 1)), 300)
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue
                
                time.sleep(self.auth_interval)
                
        except KeyboardInterrupt:
            logger.info("\n⚠ Received interrupt signal. Shutting down gracefully...")
            self.running = False
            return 0
        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}", exc_info=True)
            return 1
        
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='IoT Device Authentication Daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default 60s interval
  python device_daemon.py http://127.0.0.1:8000
  
  # Custom 30s interval
  python device_daemon.py http://127.0.0.1:8000 --interval 30
  
  # Multiple devices (separate terminals)
  DEVICE_STATE_DIR=./device_state_1 python device_daemon.py http://127.0.0.1:8000
  DEVICE_STATE_DIR=./device_state_2 python device_daemon.py http://127.0.0.1:8000
        """
    )
    
    parser.add_argument(
        'gateway_url',
        nargs='?',
        default='http://127.0.0.1:8000',
        help='Gateway base URL (default: http://127.0.0.1:8000)'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Seconds between authentication attempts (default: 60)'
    )
    
    args = parser.parse_args()
    
    # Validate interval
    if args.interval < 5:
        logger.error("Interval must be at least 5 seconds")
        return 1
    
    # Run daemon
    daemon = DeviceDaemon(args.gateway_url, args.interval)
    return daemon.run()


if __name__ == '__main__':
    sys.exit(main())
