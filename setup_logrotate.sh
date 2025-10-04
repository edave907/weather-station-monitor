#!/bin/bash
# Setup script for logrotate integration

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGROTATE_CONF="$PROJECT_DIR/logrotate/weather-daemon"

echo "Setting up logrotate for Weather Station Daemon..."
echo "Project directory: $PROJECT_DIR"

# Check if logrotate config exists
if [ ! -f "$LOGROTATE_CONF" ]; then
    echo "Error: Logrotate configuration not found at $LOGROTATE_CONF"
    exit 1
fi

# Test the logrotate configuration
echo "Testing logrotate configuration..."
sudo logrotate -d "$LOGROTATE_CONF"

if [ $? -eq 0 ]; then
    echo "✓ Logrotate configuration is valid"
else
    echo "✗ Logrotate configuration has errors"
    exit 1
fi

# Install logrotate configuration
echo "Installing logrotate configuration..."
sudo cp "$LOGROTATE_CONF" /etc/logrotate.d/weather-daemon

echo "✓ Logrotate configuration installed to /etc/logrotate.d/weather-daemon"

# Set proper permissions
sudo chmod 644 /etc/logrotate.d/weather-daemon
sudo chown root:root /etc/logrotate.d/weather-daemon

echo "✓ Permissions set correctly"

# Test the installation
echo "Testing installed configuration..."
sudo logrotate -d /etc/logrotate.d/weather-daemon

if [ $? -eq 0 ]; then
    echo "✓ Installation successful!"
    echo ""
    echo "Logrotate is now configured for weather_daemon.log"
    echo "Log rotation will happen daily, keeping 30 days of logs"
    echo ""
    echo "Manual log rotation test:"
    echo "  sudo logrotate -f /etc/logrotate.d/weather-daemon"
    echo ""
    echo "Check logrotate status:"
    echo "  sudo cat /var/lib/logrotate/status | grep weather"
else
    echo "✗ Installation verification failed"
    exit 1
fi