#!/bin/bash
# Installation script for Garage Controller

set -e

echo "Installing Garage Door Controller..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Create log directory
echo "Creating log directory..."
mkdir -p /var/log
touch /var/log/garage_controller.log
chown pi:pi /var/log/garage_controller.log

# Copy service file
echo "Installing systemd service..."
cp garage-controller.service /etc/systemd/system/
systemctl daemon-reload

# Enable service
systemctl enable garage-controller.service

# Add pi user to gpio group if it exists
if getent group gpio > /dev/null 2>&1; then
    usermod -a -G gpio pi
    echo "Added pi user to gpio group"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Configuration:"
echo "1. Edit config.yaml to match your setup"
echo "2. Start the service: sudo systemctl start garage-controller"
echo "3. Check status: sudo systemctl status garage-controller"
echo "4. View logs: sudo journalctl -u garage-controller -f"
echo ""
echo "GPIO Pin Configuration:"
echo "- Default relay pin: GPIO 18 (Physical pin 12)"
echo "- Default sensor pin: GPIO 24 (Physical pin 18)"
echo "- Make sure to connect a pull-up resistor to the sensor pin"
echo ""