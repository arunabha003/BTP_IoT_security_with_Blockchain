# IoT Identity System - Makefile
# Unified build commands for all components

.PHONY: help start test-system stop clean setup
.PHONY: contracts-build contracts-test contracts-deploy contracts-install
.PHONY: accum-install accum-test gateway-install gateway-run gateway-test
.PHONY: test-integration test-performance

# Default target
help:
	@echo "🎯 IoT Identity System - Available Commands"
	@echo "==========================================="
	@echo ""
	@echo "🚀 System Management:"
	@echo "  start          - Start complete system (Anvil + Contracts + Gateway)"
	@echo "  test-system    - Run quick system health test"
	@echo "  stop           - Stop all running services"
	@echo "  clean          - Clean all build artifacts"
	@echo "  setup          - Set up complete development environment"
	@echo ""
	@echo "🔗 Smart Contracts:"
	@echo "  contracts-build    - Compile contracts with Foundry"
	@echo "  contracts-test     - Run contract tests"
	@echo "  contracts-deploy   - Deploy to local Anvil"
	@echo "  contracts-install  - Install contract dependencies"
	@echo ""
	@echo "🧮 RSA Accumulator:"
	@echo "  accum-install  - Install accumulator package"
	@echo "  accum-test     - Run accumulator tests"
	@echo ""
	@echo "🌐 Gateway Service:"
	@echo "  gateway-install - Install gateway dependencies"
	@echo "  gateway-run     - Start gateway server"
	@echo "  gateway-test    - Run gateway tests"
	@echo ""
	@echo "🧪 Integration Testing:"
	@echo "  test-integration - Run full integration test suite"
	@echo "  test-performance - Performance benchmarking"
	@echo ""

# System management
start:
	@echo "🚀 Starting complete IoT Identity System..."
	@./start-system.sh

test-system:
	@echo "🧪 Running quick system test..."
	@./test-system.sh

stop:
	@echo "🛑 Stopping all services..."
	@pkill -f "anvil" 2>/dev/null || true
	@pkill -f "uvicorn.*gateway" 2>/dev/null || true
	@echo "✅ All services stopped"

# Smart contract operations
contracts-install:
	@echo "📦 Installing contract dependencies..."
	@cd contracts && forge install --no-commit || true
	@echo "✅ Contract dependencies installed"

contracts-build:
	@echo "🔨 Building smart contracts..."
	@cd contracts && forge build
	@echo "✅ Smart contracts built"

contracts-test:
	@echo "🧪 Running contract tests..."
	@cd contracts && forge test -vv
	@echo "✅ Contract tests completed"

contracts-deploy:
	@echo "📜 Deploying contracts to local Anvil..."
	@cd contracts && forge script script/DeploySecureMultisig.s.sol \
		--rpc-url http://127.0.0.1:8545 \
		--private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
		--broadcast
	@echo "✅ Contracts deployed"

# RSA Accumulator operations
accum-install:
	@echo "🧮 Installing RSA accumulator package..."
	@cd accum && python3 -m venv venv || true
	@cd accum && source venv/bin/activate && pip install -r requirements-dev.txt && pip install -e .
	@echo "✅ RSA accumulator package installed"

accum-test:
	@echo "🧪 Running RSA accumulator tests..."
	@cd accum && source venv/bin/activate && pytest tests/ -v
	@echo "✅ RSA accumulator tests completed"

# Gateway operations
gateway-install:
	@echo "🌐 Installing gateway dependencies..."
	@cd gateway && python3 -m venv venv || true
	@cd gateway && source venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Gateway dependencies installed"

gateway-run:
	@echo "🚀 Starting gateway server..."
	@cd gateway && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

gateway-test:
	@echo "🧪 Running gateway tests..."
	@cd gateway && source venv/bin/activate && pytest tests/ -v
	@echo "✅ Gateway tests completed"

# Integration testing
test-integration:
	@echo "🧪 Running integration tests..."
	@cd tests && python3 -m venv venv || true
	@cd tests && source venv/bin/activate && pip install -r requirements.txt setuptools
	@cd tests && source venv/bin/activate && pytest -v -s
	@echo "✅ Integration tests completed"

test-performance:
	@echo "⚡ Running performance tests..."
	@cd tests && source venv/bin/activate && python test_minimal_integration.py
	@echo "✅ Performance tests completed"

# Development utilities
clean:
	@echo "🧹 Cleaning build artifacts..."
	@cd contracts && forge clean || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@rm -f gateway/gateway.log gateway/.env gateway/gateway.db* 2>/dev/null || true
	@rm -f contracts/deployment_output.log 2>/dev/null || true
	@echo "✅ Clean completed"

setup:
	@echo "🔧 Setting up complete development environment..."
	@$(MAKE) contracts-install
	@$(MAKE) accum-install
	@$(MAKE) gateway-install
	@echo "✅ Development environment setup completed"
	@echo ""
	@echo "🎯 Next steps:"
	@echo "  make start      # Start the complete system"
	@echo "  make test-system # Test system health"
