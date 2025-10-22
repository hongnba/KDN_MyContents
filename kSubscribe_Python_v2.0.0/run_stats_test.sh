#!/bin/bash
# Run Stats Test Script
# This script shows the correct way to run the stats test

echo "🚀 Running Stats Test..."
echo "Current directory: $(pwd)"
echo ""

# Change to the correct directory (src directory where Python modules are)
cd /home/themiraclesoft/projects/mycontents/KDN_MyContents/kSubscribe_Python_v2.0.0/src

echo "Changed to src directory: $(pwd)"
echo ""

# Run the test from the src directory
python3 ksubscribe_share/test/cli_stats_test.py

echo ""
echo "✅ Stats test completed!"
