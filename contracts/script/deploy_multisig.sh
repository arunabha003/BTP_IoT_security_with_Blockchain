#!/bin/bash

# Multi-Sig Deployment Script
# Deploys AccumulatorRegistry with Gnosis Safe for production use

set -e

echo "=========================================="
echo "Multi-Sig Contract Deployment"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

# Check if Anvil is running
if ! curl -s http://127.0.0.1:8545 > /dev/null; then
    echo -e "${RED}Error: Anvil is not running!${NC}"
    echo "Please start Anvil first:"
    echo "  anvil"
    exit 1
fi

# Check if forge is installed
if ! command -v forge &> /dev/null; then
    echo -e "${RED}Error: Foundry (forge) is not installed!${NC}"
    echo "Install from: https://book.getfoundry.sh/getting-started/installation"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Navigate to contracts directory
cd contracts

echo -e "${BLUE}Deploying multi-sig contracts...${NC}"
echo ""

# Deploy contracts
forge script script/DeploySecureMultisig.s.sol:DeploySecureMultisig \
    --rpc-url http://127.0.0.1:8545 \
    --broadcast \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

echo ""
echo -e "${GREEN}✓ Contracts deployed successfully!${NC}"
echo ""

# Extract deployed addresses from broadcast file
BROADCAST_FILE="broadcast/DeploySecureMultisig.s.sol/31337/run-latest.json"

if [ -f "$BROADCAST_FILE" ]; then
    echo -e "${BLUE}Extracting deployed addresses...${NC}"
    
    # Use jq to parse addresses (install with: brew install jq)
    if command -v jq &> /dev/null; then
        SAFE_ADDRESS=$(jq -r '.transactions[] | select(.contractName == "GnosisSafeProxy") | .contractAddress' "$BROADCAST_FILE" | head -1)
        REGISTRY_ADDRESS=$(jq -r '.transactions[] | select(.contractName == "AccumulatorRegistry") | .contractAddress' "$BROADCAST_FILE" | head -1)
        
        echo ""
        echo -e "${GREEN}Deployed Addresses:${NC}"
        echo "  Safe Proxy:           $SAFE_ADDRESS"
        echo "  AccumulatorRegistry:  $REGISTRY_ADDRESS"
        echo ""
        
        # Update backend configuration
        echo -e "${BLUE}Updating backend configuration...${NC}"
        
        cd ..
        
        # Create .env file for backend
        cat > gateway/.env.multisig << EOF
# Multi-Sig Configuration (Auto-generated)
REGISTRY_ADDRESS=$REGISTRY_ADDRESS
SAFE_ADDRESS=$SAFE_ADDRESS
USE_MULTISIG=true

# Safe Owners (from deployment script)
OWNER_1=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
OWNER_2=0x70997970C51812dc3A010C7d01b50e0d17dc79C8
OWNER_3=0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
OWNER_4=0x90F79bf6EB2c4f870365E785982E1f101E93b906
OWNER_5=0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65

# Threshold
THRESHOLD=3
EOF
        
        echo -e "${GREEN}✓ Configuration saved to gateway/.env.multisig${NC}"
        echo ""
        
    else
        echo -e "${YELLOW}Warning: jq not installed. Cannot extract addresses automatically.${NC}"
        echo "Check deployment logs above for addresses."
        echo ""
    fi
else
    echo -e "${YELLOW}Warning: Broadcast file not found. Check deployment logs above.${NC}"
fi

echo -e "${GREEN}=========================================="
echo "Deployment Complete!"
echo "==========================================${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Update gateway/settings.py with the deployed addresses"
echo "2. Import 5 owner accounts to MetaMask for testing:"
echo "   - 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
echo "   - 0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
echo "   - 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC"
echo "   - 0x90F79bf6EB2c4f870365E785982E1f101E93b906"
echo "   - 0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65"
echo "3. Restart the backend with multi-sig configuration"
echo "4. Test multi-sig workflow in frontend:"
echo "   - Visit http://localhost:3000/multisig-propose"
echo "   - Create a transaction proposal"
echo "   - Switch accounts and sign on /multisig-approve"
echo ""
echo "See MULTISIG_GUIDE.md for complete instructions."
