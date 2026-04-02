#!/bin/bash
# Install dependencies for Volumio Display Service
# Run on Pi with: bash setup-pi.sh

set -e

echo "================================"
echo "Installing Dependencies"
echo "================================"

# Update system packages
echo "[1/2] Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip

# Install Python dependencies (Volumio 3 requires Socket.IO 2.x)
echo "[2/2] Installing Python dependencies..."
pip3 install --upgrade pip
pip3 uninstall -y python-socketio python-engineio 2>/dev/null || true
pip3 install python-socketio==4.6.0 python-engineio==3.14.2

echo ""
echo "================================"
echo "Dependencies Installed!"
echo "================================"
echo ""
