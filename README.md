# Garage Controller

A Python script to control garage door openers via Raspberry Pi Zero with Home Assistant integration.

## Features

- **GPIO Control**: Controls relay for garage door activation
- **Door State Detection**: Uses magnetic sensor to detect open/closed state
- **Home Assistant Integration**: Full MQTT integration with auto-discovery
- **Safety Features**: Prevents rapid activations and includes error handling
- **Systemd Service**: Automatic startup and monitoring
- **Configurable**: YAML configuration file for easy customization

## Hardware Requirements

- Raspberry Pi Zero W (or any Pi with WiFi)
- 5V Relay Module (1-channel)
- Magnetic Door Sensor (Reed Switch)
- 10kΩ Pull-up Resistor
- Jumper wires and breadboard

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/abdul2000/garage-controller.git
   cd garage-controller
   ```

2. **Run the installation script**:
   ```bash
   sudo ./install.sh
   ```

3. **Configure the system**:
   ```bash
   sudo nano config.yaml
   ```
   Update the MQTT broker settings and GPIO pins as needed.

4. **Start the service**:
   ```bash
   sudo systemctl start garage-controller
   sudo systemctl status garage-controller
   ```

## Configuration

Edit `config.yaml` to match your setup:

```yaml
garage:
  name: "Main Garage"
  relay_pin: 18         # GPIO pin for relay control
  door_sensor_pin: 24   # GPIO pin for door sensor
  activation_time: 0.5  # Relay activation time

mqtt:
  broker: "your-ha-ip"  # Home Assistant IP
  port: 1883
  topic_prefix: "homeassistant/cover/garage"
```

## Wiring

See [example_wiring.md](example_wiring.md) for detailed wiring instructions.

### Quick Reference:
- **Relay Control**: GPIO 18 (Pin 12)
- **Door Sensor**: GPIO 24 (Pin 18) with pull-up resistor

## Home Assistant Integration

The controller automatically registers with Home Assistant via MQTT discovery. Once running, you'll see a new garage door entity in your Home Assistant interface.

### Manual MQTT Configuration (if needed):

```yaml
cover:
  - platform: mqtt
    name: "Garage Door"
    command_topic: "homeassistant/cover/garage/set"
    state_topic: "homeassistant/cover/garage/state"
    availability_topic: "homeassistant/cover/garage/availability"
    payload_open: "OPEN"
    payload_close: "CLOSE"
    state_open: "open"
    state_closed: "closed"
    device_class: garage
```

## Usage

### Manual Control:
```bash
# Test the controller
python3 garage_controller.py --config config.yaml
```

### Service Management:
```bash
# Start service
sudo systemctl start garage-controller

# Stop service
sudo systemctl stop garage-controller

# View logs
sudo journalctl -u garage-controller -f
```

## Files Overview

- `garage_controller.py` - Main controller script
- `config.yaml` - Configuration file
- `requirements.txt` - Python dependencies
- `install.sh` - Installation script
- `garage-controller.service` - Systemd service file
- `check_system.py` - System verification script
- `test_controller.py` - Unit tests
- `example_wiring.md` - Hardware wiring guide
- `home_assistant_example.yaml` - HA configuration examples

## Testing and Verification

Before deploying to your Raspberry Pi, you can test the configuration:

### System Check
Run the system check script to verify your setup:
```bash
python3 check_system.py
```

This will check:
- Python dependencies
- Configuration file validity  
- GPIO availability
- User permissions
- Systemd service status
- MQTT connectivity

### Unit Tests
Run the included unit tests:
```bash
python3 test_controller.py
```

## Troubleshooting

### Common Issues:

1. **Permission denied on GPIO**: Add user to gpio group:
   ```bash
   sudo usermod -a -G gpio pi
   ```

2. **MQTT connection failed**: Check broker IP and credentials in config.yaml

3. **Door sensor not working**: Verify wiring and pull-up resistor

4. **Service won't start**: Check logs:
   ```bash
   sudo journalctl -u garage-controller -n 50
   ```

### Testing:

```bash
# Test GPIO pins
python3 -c "import RPi.GPIO as GPIO; GPIO.setmode(GPIO.BCM); GPIO.setup(18, GPIO.OUT); print('GPIO test OK')"

# Test MQTT connection
mosquitto_pub -h your-broker-ip -t test/topic -m "test message"
```

## Safety

- Always disconnect power when making electrical connections
- Test thoroughly before regular use
- Consider adding manual override switches
- Use appropriate fuses and circuit protection

## License

MIT License - see LICENSE file for details

## Contributing

Pull requests are welcome! Please read the contributing guidelines first.
