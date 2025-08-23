#!/bin/bash

# IoT Identity System - Complete Startup Script
# This script starts all necessary services for the IoT Identity System

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
ANVIL_PORT=8545
GATEWAY_PORT=8000
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANVIL_PID=""
GATEWAY_PID=""

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}🛑 Shutting down services...${NC}"
    
    if [ ! -z "$GATEWAY_PID" ]; then
        echo -e "${BLUE}   Stopping Gateway (PID: $GATEWAY_PID)${NC}"
        kill $GATEWAY_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$ANVIL_PID" ]; then
        echo -e "${BLUE}   Stopping Anvil (PID: $ANVIL_PID)${NC}"
        kill $ANVIL_PID 2>/dev/null || true
    fi
    
    # Kill any remaining processes
    pkill -f "anvil" 2>/dev/null || true
    pkill -f "uvicorn.*gateway" 2>/dev/null || true
    
    echo -e "${GREEN}✅ All services stopped${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Print banner
echo -e "${PURPLE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                   IoT Identity System                         ║"
echo "║              RSA Accumulator + Blockchain                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check prerequisites
echo -e "${CYAN}🔍 Checking prerequisites...${NC}"

# Check if foundry is installed
if ! command -v forge &> /dev/null; then
    echo -e "${RED}❌ Foundry not found. Please install: https://getfoundry.sh${NC}"
    exit 1
fi

if ! command -v anvil &> /dev/null; then
    echo -e "${RED}❌ Anvil not found. Please install Foundry: https://getfoundry.sh${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Function to check if port is available
check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${RED}❌ Port $port is already in use (needed for $service)${NC}"
        echo -e "${YELLOW}   Please stop the service using port $port or choose a different port${NC}"
        exit 1
    fi
}

# Check if required ports are available
echo -e "${CYAN}🔌 Checking port availability...${NC}"
check_port $ANVIL_PORT "Anvil blockchain"
check_port $GATEWAY_PORT "Gateway service"
echo -e "${GREEN}✅ Ports are available${NC}"

# Step 1: Build smart contracts
echo -e "\n${CYAN}🔨 Building smart contracts...${NC}"
cd "$PROJECT_ROOT/contracts"

if ! forge build; then
    echo -e "${RED}❌ Smart contract build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Smart contracts built successfully${NC}"

# Step 2: Start Anvil blockchain
echo -e "\n${CYAN}⛓️  Starting Anvil blockchain...${NC}"
anvil --port $ANVIL_PORT --accounts 10 --balance 10000 > /dev/null 2>&1 &
ANVIL_PID=$!

# Wait for Anvil to start
echo -e "${BLUE}   Waiting for Anvil to start...${NC}"
for i in {1..30}; do
    if curl -s -X POST -H "Content-Type: application/json" \
        --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
        http://127.0.0.1:$ANVIL_PORT > /dev/null 2>&1; then
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Anvil failed to start within 30 seconds${NC}"
        cleanup
        exit 1
    fi
done

echo -e "${GREEN}✅ Anvil blockchain started (PID: $ANVIL_PID)${NC}"
echo -e "${BLUE}   RPC URL: http://127.0.0.1:$ANVIL_PORT${NC}"

# Step 3: Deploy smart contracts
echo -e "\n${CYAN}📜 Deploying smart contracts...${NC}"

# Use the first Anvil account as deployer
DEPLOYER_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

if ! forge script script/DeploySecureMultisig.s.sol \
    --rpc-url http://127.0.0.1:$ANVIL_PORT \
    --private-key $DEPLOYER_KEY \
    --broadcast > deployment_output.log 2>&1; then
    echo -e "${RED}❌ Smart contract deployment failed${NC}"
    echo -e "${YELLOW}   Check deployment_output.log for details${NC}"
    cleanup
    exit 1
fi

# Extract contract address from deployment output
CONTRACT_ADDRESS=$(grep "AccumulatorRegistry deployed to:" deployment_output.log | awk '{print $4}' | tail -1)

if [ -z "$CONTRACT_ADDRESS" ]; then
    echo -e "${RED}❌ Could not extract contract address from deployment${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}✅ Smart contracts deployed successfully${NC}"
echo -e "${BLUE}   AccumulatorRegistry: $CONTRACT_ADDRESS${NC}"

# Step 4: Set up Python environments
echo -e "\n${CYAN}🐍 Setting up Python environments...${NC}"

# Set up accum package
cd "$PROJECT_ROOT/accum"
if [ ! -d "venv" ]; then
    echo -e "${BLUE}   Creating accum virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "${BLUE}   Installing accum dependencies...${NC}"
source venv/bin/activate
pip install -q -r requirements-dev.txt
pip install -q -e .
deactivate

# Set up gateway service
cd "$PROJECT_ROOT/gateway"
if [ ! -d "venv" ]; then
    echo -e "${BLUE}   Creating gateway virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "${BLUE}   Installing gateway dependencies...${NC}"
source venv/bin/activate
pip install -q -r requirements.txt
deactivate

echo -e "${GREEN}✅ Python environments set up${NC}"

# Step 5: Configure gateway
echo -e "\n${CYAN}⚙️  Configuring gateway service...${NC}"
cd "$PROJECT_ROOT/gateway"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cp env.example .env
fi

# Update .env with deployed contract address
cat > .env << EOF
# Blockchain Configuration
RPC_URL=http://127.0.0.1:$ANVIL_PORT
CONTRACT_ADDRESS=$CONTRACT_ADDRESS
ADMIN_KEY=test-admin-key-for-development

# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./gateway.db

# Security Configuration
NONCE_TTL_SECONDS=300
IP_RATE_LIMIT_PER_MINUTE=20
DEVICE_RATE_LIMIT_PER_5_MINUTES=5

# Logging Configuration
LOG_LEVEL=INFO
APP_VERSION=1.0.0
EVENT_POLLING_INTERVAL_SECONDS=5
EOF

echo -e "${GREEN}✅ Gateway configured${NC}"

# Step 6: Start gateway service
echo -e "\n${CYAN}🚀 Starting gateway service...${NC}"

cd "$PROJECT_ROOT/gateway"
source venv/bin/activate

# Start gateway in background
uvicorn main:app --host 0.0.0.0 --port $GATEWAY_PORT --reload > gateway.log 2>&1 &
GATEWAY_PID=$!

# Wait for gateway to start
echo -e "${BLUE}   Waiting for gateway to start...${NC}"
for i in {1..30}; do
    if curl -s http://127.0.0.1:$GATEWAY_PORT/healthz > /dev/null 2>&1; then
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Gateway failed to start within 30 seconds${NC}"
        echo -e "${YELLOW}   Check gateway.log for details${NC}"
        cleanup
        exit 1
    fi
done

echo -e "${GREEN}✅ Gateway service started (PID: $GATEWAY_PID)${NC}"
echo -e "${BLUE}   Gateway URL: http://127.0.0.1:$GATEWAY_PORT${NC}"

# Step 7: Verify system health
echo -e "\n${CYAN}🏥 Verifying system health...${NC}"

# Check gateway health
if ! curl -s http://127.0.0.1:$GATEWAY_PORT/healthz | grep -q '"ok":true'; then
    echo -e "${RED}❌ Gateway health check failed${NC}"
    cleanup
    exit 1
fi

# Check accumulator endpoint
if ! curl -s http://127.0.0.1:$GATEWAY_PORT/accumulator > /dev/null; then
    echo -e "${RED}❌ Accumulator endpoint check failed${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}✅ System health verification passed${NC}"

# Step 8: Display system information
echo -e "\n${PURPLE}🎉 IoT Identity System is now running!${NC}"
echo -e "\n${CYAN}📊 System Information:${NC}"
echo -e "${BLUE}   Anvil Blockchain:      http://127.0.0.1:$ANVIL_PORT${NC}"
echo -e "${BLUE}   Gateway Service:       http://127.0.0.1:$GATEWAY_PORT${NC}"
echo -e "${BLUE}   AccumulatorRegistry:   $CONTRACT_ADDRESS${NC}"
echo -e "${BLUE}   Admin Key:             test-admin-key-for-development${NC}"

echo -e "\n${CYAN}🔗 Available Endpoints:${NC}"
echo -e "${BLUE}   Health Check:          GET  http://127.0.0.1:$GATEWAY_PORT/healthz${NC}"
echo -e "${BLUE}   System Status:         GET  http://127.0.0.1:$GATEWAY_PORT/status${NC}"
echo -e "${BLUE}   Accumulator Root:      GET  http://127.0.0.1:$GATEWAY_PORT/root${NC}"
echo -e "${BLUE}   Accumulator Info:      GET  http://127.0.0.1:$GATEWAY_PORT/accumulator${NC}"
echo -e "${BLUE}   Device Enrollment:     POST http://127.0.0.1:$GATEWAY_PORT/enroll${NC}"
echo -e "${BLUE}   Device Revocation:     POST http://127.0.0.1:$GATEWAY_PORT/revoke${NC}"
echo -e "${BLUE}   Auth Challenge:        GET  http://127.0.0.1:$GATEWAY_PORT/auth/start${NC}"
echo -e "${BLUE}   Auth Verification:     POST http://127.0.0.1:$GATEWAY_PORT/auth/verify${NC}"

echo -e "\n${CYAN}📋 Quick Test Commands:${NC}"
echo -e "${BLUE}   # Check system health${NC}"
echo -e "${YELLOW}   curl http://127.0.0.1:$GATEWAY_PORT/healthz${NC}"
echo -e ""
echo -e "${BLUE}   # Get current accumulator${NC}"
echo -e "${YELLOW}   curl http://127.0.0.1:$GATEWAY_PORT/accumulator${NC}"
echo -e ""
echo -e "${BLUE}   # Get system status${NC}"
echo -e "${YELLOW}   curl http://127.0.0.1:$GATEWAY_PORT/status${NC}"

echo -e "\n${CYAN}🧪 Run Integration Tests:${NC}"
echo -e "${BLUE}   cd tests && python -m venv venv && source venv/bin/activate${NC}"
echo -e "${BLUE}   pip install -r requirements.txt setuptools${NC}"
echo -e "${BLUE}   pytest test_end_to_end_system.py -v -s${NC}"

echo -e "\n${CYAN}📚 Documentation:${NC}"
echo -e "${BLUE}   Protocol Specification: ./PROTOCOL_SPECIFICATION.md${NC}"
echo -e "${BLUE}   File Structure Guide:   ./FILE_STRUCTURE_GUIDE.md${NC}"
echo -e "${BLUE}   Gateway Documentation:  ./gateway/README.md${NC}"
echo -e "${BLUE}   Accumulator Package:    ./accum/README.md${NC}"
echo -e "${BLUE}   Smart Contracts:        ./contracts/README.md${NC}"

echo -e "\n${GREEN}✨ System is ready for development and testing!${NC}"
echo -e "\n${YELLOW}💡 Press Ctrl+C to stop all services${NC}"

# Keep the script running and wait for interrupt
while true; do
    # Check if services are still running
    if ! kill -0 $ANVIL_PID 2>/dev/null; then
        echo -e "\n${RED}❌ Anvil blockchain stopped unexpectedly${NC}"
        cleanup
        exit 1
    fi
    
    if ! kill -0 $GATEWAY_PID 2>/dev/null; then
        echo -e "\n${RED}❌ Gateway service stopped unexpectedly${NC}"
        cleanup
        exit 1
    fi
    
    sleep 5
done
