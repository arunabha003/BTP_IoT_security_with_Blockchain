#!/bin/bash

# IoT Identity Gateway - Frontend Setup and Run Script

set -e

echo "=========================================="
echo "IoT Identity Gateway - Frontend Setup"
echo "=========================================="

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "⚠️  Warning: Node.js version 18+ is recommended (you have v$NODE_VERSION)"
fi

echo "✓ Node.js $(node -v) detected"

# Navigate to frontend directory
cd "$(dirname "$0")"

# Install dependencies
echo ""
echo "Installing dependencies..."
npm install

echo ""
echo "=========================================="
echo "✓ Frontend setup complete!"
echo "=========================================="
echo ""
echo "To start the development server:"
echo "  npm run dev"
echo ""
echo "The frontend will be available at:"
echo "  http://localhost:3000"
echo ""
echo "Make sure the backend gateway is running at:"
echo "  http://127.0.0.1:8000"
echo ""
