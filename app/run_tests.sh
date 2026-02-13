#!/bin/bash

# Test runner script for Patient Monitoring System
# Sets up Django environment and runs pytest

# Set Django settings module
export DJANGO_SETTINGS_MODULE=patient_monitoring_system.settings_test

# Change to app directory
cd /Users/vp0023/capestone/app

echo "🧪 Running Patient Monitoring System Tests"
echo "=========================================="

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test requirements..."
    pip install -r requirements-test.txt
fi

# Run tests with proper Django configuration
if [ "$1" = "unit" ]; then
    echo "🔧 Running Unit Tests..."
    python -m pytest tests/ -m unit -v --tb=short
elif [ "$1" = "integration" ]; then
    echo "🔗 Running Integration Tests..."
    python -m pytest tests/test_integration.py -m integration -v --tb=short
elif [ "$1" = "system" ]; then
    echo "🌐 Running System Tests..."
    python -m pytest tests/test_integration.py -m system -v --tb=short
elif [ "$1" = "coverage" ]; then
    echo "📊 Running All Tests with Coverage..."
    python -m pytest tests/ --cov=core --cov-report=html --cov-report=term-missing -v
else
    echo "🚀 Running All Tests..."
    python -m pytest tests/ -v --tb=short
fi

echo ""
echo "✅ Test run completed!"