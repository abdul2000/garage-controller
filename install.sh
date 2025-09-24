#!/bin/bash
# Installation script for Garage Controller

set -e

echo "Installing Garage Door Controller..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if we're on a Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update package list
echo "Updating package list..."
apt-get update -qq

# Install Python3 and pip if not present
echo "Installing Python dependencies..."
apt-get install -y python3 python3-pip

# Install Python dependencies
echo "Installing Python packages..."
pip3 install -r requirements.txt

# Create installation directory
INSTALL_DIR="/home/pi/garage-controller"
echo "Creating installation directory: ${INSTALL_DIR}"
mkdir -p ${INSTALL_DIR}

# Copy files to installation directory
echo "Copying files..."
cp garage_controller.py ${INSTALL_DIR}/
cp config.yaml ${INSTALL_DIR}/
cp requirements.txt ${INSTALL_DIR}/

# Set ownership
chown -R pi:pi ${INSTALL_DIR}

# Create log directory
echo "Creating log directory..."
mkdir -p /var/log
touch /var/log/garage_controller.log
chown pi:pi /var/log/garage_controller.log

# Update service file with correct paths
echo "Installing systemd service..."
sed "s|/home/pi/garage-controller|${INSTALL_DIR}|g" garage-controller.service > /etc/systemd/system/garage-controller.service
systemctl daemon-reload

# Enable service
systemctl enable garage-controller.service

# Add pi user to gpio group if it exists
if getent group gpio > /dev/null 2>&1; then
    usermod -a -G gpio pi
    echo "Added pi user to gpio group"
fi

# Test configuration
echo "Testing configuration..."
if ! python3 -c "import yaml; yaml.safe_load(open('${INSTALL_DIR}/config.yaml'))"; then
    echo "Error: Invalid configuration file"
    exit 1
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit the configuration: sudo nano ${INSTALL_DIR}/config.yaml"
echo "2. Update MQTT broker settings to match your Home Assistant"
echo "3. Verify GPIO pin assignments match your wiring"
echo "4. Start the service: sudo systemctl start garage-controller"
echo "5. Check status: sudo systemctl status garage-controller"
echo "6. View logs: sudo journalctl -u garage-controller -f"
echo ""
echo "GPIO Pin Configuration (BCM numbering):"
echo "- Default relay pin: GPIO 18 (Physical pin 12)"
echo "- Default sensor pin: GPIO 24 (Physical pin 18)"
echo ""
echo "Wiring guide: see example_wiring.md"
echo "Home Assistant config: see home_assistant_example.yaml"
echo ""