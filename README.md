# Garage Controller

A Python script for controlling garage doors via MQTT, designed for integration with Home Assistant (HA). This system uses a Raspberry Pi to monitor reed switches and control a relay for garage door operation.

## Features

- **MQTT Integration**: Full Home Assistant compatibility
- **Physical Remote Support**: Detects and reports state changes from physical garage remote
- **Reed Switch Monitoring**: Tracks open/closed positions using GPIO pins
- **Debouncing**: Prevents false readings from electrical noise
- **Obstruction Detection**: Monitors for door movement issues
- **State Tracking**: Reports door states: `open`, `closed`, `opening`, `closing`, `moving`, `stopped`

## Hardware Requirements

- Raspberry Pi (tested on Pi Zero)
- 2x Reed switches (for open/closed position detection)
- 1x Relay module (for garage door control)
- Appropriate GPIO connections

## GPIO Pin Configuration

- **GPIO 4**: Relay control pin
- **GPIO 23**: Closed position reed switch
- **GPIO 24**: Open position reed switch

## MQTT Topics

- **Command**: `garage/command` - Send `TOGGLE_OPEN` or `TOGGLE_CLOSE`
- **State**: `garage/state` - Reports current door state
- **Obstruction**: `garage/obstruction` - Reports `true`/`false` for obstructions

## Installation

1. Clone this repository to your Raspberry Pi
2. Install required Python packages:
   ```bash
   sudo apt update
   sudo apt install mosquitto mosquitto-clients python3-pip
   pip3 install paho-mqtt RPi.GPIO
   ```
3. Update the MQTT broker IP in `garage_control.py`
4. Set up as a systemd service (see Service Management below)
   ```bash
   sudo nano /etc/systemd/system/garage_control.service
   ```
5. Add the following
   ```bash
   [Unit]
   Description=Garage Door Controller
   After=network.target
   
   [Service]
   ExecStart=/usr/bin/python3 /home/pi/garage_control.py
   Restart=always
   User=pi
   
   [Install]
   WantedBy=multi-user.target
   ```

## Service Management

### Start the service
```bash
sudo systemctl start garage_control.service
```

### Stop the service
```bash
sudo systemctl stop garage_control.service
```

### Check service status
```bash
sudo systemctl status garage_control.service
```

### Restart the service
```bash
sudo systemctl restart garage_control.service
```

### Enable auto-start on boot
```bash
sudo systemctl enable garage_control.service
```

## Troubleshooting

### Monitor GPIO Pins
Install WiringPi and check GPIO states:
```bash
sudo apt install wiringpi
gpio readall
```

### View Service Logs
```bash
sudo journalctl -u garage_control.service -f
```

### Common Issues
- Ensure MQTT broker is accessible and credentials are correct
- Verify GPIO connections and reed switch functionality
- Check that the relay is properly connected and functioning

## Configuration

Update the following variables in `garage_control.py` to match your setup:
- `MQTT_BROKER`: Your MQTT broker IP address
- `RELAY_PIN`: GPIO pin connected to relay (default: GPIO 4)
- `CLOSED_REED_PIN`: GPIO pin for closed position reed switch (default: GPIO 23)
- `OPEN_REED_PIN`: GPIO pin for open position reed switch (default: GPIO 24)

