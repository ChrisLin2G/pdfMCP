#!/bin/bash
# Setup script for PDF MCP virtual environment

set -e

echo "Setting up PDF MCP virtual environment..."

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install package in editable mode
pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To test the server, run:"
echo "  python3 -c 'from mcp_server.tools import mcp; mcp.run()'"
echo ""
echo "Make sure OCRmyPDF is installed on your system:"
echo "  Ubuntu/Debian: sudo apt-get install ocrmypdf tesseract-ocr"
