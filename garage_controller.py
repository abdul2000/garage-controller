#!/usr/bin/env python3
"""
Garage Door Controller for Raspberry Pi Zero
Controls garage door opener and provides Home Assistant integration via MQTT
"""

import time
import json
import logging
import signal
import sys
import threading
from typing import Optional
import yaml

try:
    import RPi.GPIO as GPIO
except (ImportError, RuntimeError):
    # Mock GPIO for development/testing on non-Pi systems
    class MockGPIO:
        BCM = "BCM"
        BOARD = "BOARD"
        OUT = "OUT"
        IN = "IN"
        PUD_UP = "PUD_UP"
        HIGH = 1
        LOW = 0
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, pull_up_down=None): pass
        @staticmethod
        def output(pin, state): pass
        @staticmethod
        def input(pin): return 0
        @staticmethod
        def cleanup(): pass
        @staticmethod
        def add_event_detect(pin, edge, callback=None, bouncetime=None): pass
        @staticmethod
        def remove_event_detect(pin): pass
        @staticmethod
        def RISING(): return "RISING"
        @staticmethod
        def FALLING(): return "FALLING"
        @staticmethod
        def BOTH(): return "BOTH"
    
    GPIO = MockGPIO()
    print("Warning: RPi.GPIO not available, using mock GPIO")

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Error: paho-mqtt not installed. Run: pip install paho-mqtt")
    sys.exit(1)


class GarageController:
    """Controls garage door and communicates with Home Assistant via MQTT"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """Initialize the garage controller"""
        self.config = self._load_config(config_file)
        self._setup_logging()
        
        # Door state tracking - initialize before GPIO setup
        self.door_state = "unknown"  # unknown, open, closed, opening, closing
        self.last_activation = 0
        self.running = True
        
        self._setup_mqtt()
        self._setup_gpio()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Garage Controller initialized")
    
    def _load_config(self, config_file: str) -> dict:
        """Load configuration from YAML file"""
        try:
            with open(config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file {config_file} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config['logging']['level'].upper())
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Try to use /var/log if writable, otherwise use current directory
        log_file = self.config['logging']['file']
        if not log_file.startswith('/'):
            # Try /var/log first, fall back to current directory
            try:
                log_file = f"/var/log/{log_file}"
                # Test if we can write to /var/log
                with open(log_file, 'a') as f:
                    pass
            except (PermissionError, FileNotFoundError):
                log_file = self.config['logging']['file']
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('GarageController')
        self.logger.info(f"Logging to: {log_file}")
    
    def _setup_gpio(self):
        """Setup GPIO pins"""
        gpio_config = self.config['gpio']
        
        # Set GPIO mode
        if gpio_config['mode'] == 'BCM':
            GPIO.setmode(GPIO.BCM)
        else:
            GPIO.setmode(GPIO.BOARD)
        
        # Setup relay pin (output)
        self.relay_pin = self.config['garage']['relay_pin']
        GPIO.setup(self.relay_pin, GPIO.OUT)
        GPIO.output(self.relay_pin, GPIO.LOW)  # Ensure relay is off
        
        # Setup door sensor pin (input with pull-up)
        self.door_sensor_pin = self.config['garage']['door_sensor_pin']
        GPIO.setup(self.door_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Add event detection for door sensor
        GPIO.add_event_detect(
            self.door_sensor_pin, 
            GPIO.BOTH, 
            callback=self._door_sensor_callback,
            bouncetime=300
        )
        
        # Initial door state detection
        self._update_door_state()
        
        self.logger.info(f"GPIO setup complete - Relay: {self.relay_pin}, Sensor: {self.door_sensor_pin}")
    
    def _setup_mqtt(self):
        """Setup MQTT client and connect to broker"""
        self.mqtt_client = mqtt.Client(
            client_id=self.config['mqtt']['client_id'],
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        
        # Set username/password if provided
        if self.config['mqtt']['username']:
            self.mqtt_client.username_pw_set(
                self.config['mqtt']['username'],
                self.config['mqtt']['password']
            )
        
        # Setup callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        
        # Connect to broker
        try:
            self.mqtt_client.connect(
                self.config['mqtt']['broker'],
                self.config['mqtt']['port'],
                60
            )
            self.mqtt_client.loop_start()
            self.logger.info(f"Connecting to MQTT broker: {self.config['mqtt']['broker']}")
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            sys.exit(1)
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            
            # Subscribe to command topic
            command_topic = f"{self.config['mqtt']['topic_prefix']}/set"
            client.subscribe(command_topic)
            self.logger.info(f"Subscribed to: {command_topic}")
            
            # Publish discovery message for Home Assistant
            self._publish_discovery()
            
            # Publish initial state
            self._publish_state()
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            self.logger.info(f"Received MQTT message: {topic} = {payload}")
            
            if topic.endswith("/set"):
                if payload.upper() in ["OPEN", "CLOSE"]:
                    self.activate_door()
                else:
                    self.logger.warning(f"Unknown command: {payload}")
        except Exception as e:
            self.logger.error(f"Error processing MQTT message: {e}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        if rc != 0:
            self.logger.warning("Unexpected MQTT disconnection")
    
    def _publish_discovery(self):
        """Publish Home Assistant MQTT discovery message"""
        garage_name = self.config['garage']['name']
        topic_prefix = self.config['mqtt']['topic_prefix']
        
        discovery_config = {
            "name": garage_name,
            "unique_id": f"garage_controller_{garage_name.lower().replace(' ', '_')}",
            "command_topic": f"{topic_prefix}/set",
            "state_topic": f"{topic_prefix}/state",
            "availability_topic": f"{topic_prefix}/availability",
            "payload_open": "OPEN",
            "payload_close": "CLOSE",
            "payload_available": "online",
            "payload_not_available": "offline",
            "state_open": "open",
            "state_closed": "closed",
            "state_opening": "opening",
            "state_closing": "closing",
            "device_class": "garage"
        }
        
        discovery_topic = f"homeassistant/cover/garage_controller/config"
        self.mqtt_client.publish(
            discovery_topic,
            json.dumps(discovery_config),
            retain=True
        )
        
        # Publish availability
        availability_topic = f"{topic_prefix}/availability"
        self.mqtt_client.publish(availability_topic, "online", retain=True)
        
        self.logger.info("Published Home Assistant discovery message")
    
    def _publish_state(self):
        """Publish current door state to MQTT"""
        state_topic = f"{self.config['mqtt']['topic_prefix']}/state"
        self.mqtt_client.publish(state_topic, self.door_state, retain=True)
        self.logger.info(f"Published state: {self.door_state}")
    
    def _door_sensor_callback(self, channel):
        """Callback for door sensor state change"""
        self.logger.debug("Door sensor triggered")
        time.sleep(0.1)  # Small delay to avoid bouncing
        self._update_door_state()
    
    def _update_door_state(self):
        """Update door state based on sensor reading"""
        sensor_state = GPIO.input(self.door_sensor_pin)
        
        # Assuming sensor is LOW when door is closed (pulled to ground)
        if sensor_state == GPIO.LOW:
            new_state = "closed"
        else:
            new_state = "open"
        
        if new_state != self.door_state:
            self.door_state = new_state
            self.logger.info(f"Door state changed to: {self.door_state}")
            self._publish_state()
    
    def activate_door(self):
        """Activate the garage door opener"""
        current_time = time.time()
        
        # Prevent rapid activations (safety feature)
        if current_time - self.last_activation < 2.0:
            self.logger.warning("Ignoring activation - too soon after last activation")
            return
        
        self.logger.info("Activating garage door")
        
        # Set state to opening/closing based on current state
        if self.door_state == "closed":
            self.door_state = "opening"
        elif self.door_state == "open":
            self.door_state = "closing"
        
        self._publish_state()
        
        # Activate relay
        GPIO.output(self.relay_pin, GPIO.HIGH)
        time.sleep(self.config['garage']['activation_time'])
        GPIO.output(self.relay_pin, GPIO.LOW)
        
        self.last_activation = current_time
        self.logger.info("Door activation complete")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of the controller"""
        self.logger.info("Shutting down garage controller...")
        
        # Publish offline status
        availability_topic = f"{self.config['mqtt']['topic_prefix']}/availability"
        self.mqtt_client.publish(availability_topic, "offline", retain=True)
        
        # Stop MQTT loop and disconnect
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        
        # Cleanup GPIO
        if self.config['gpio']['cleanup_on_exit']:
            GPIO.cleanup()
        
        self.logger.info("Shutdown complete")
    
    def run(self):
        """Main run loop"""
        self.logger.info("Starting garage controller main loop")
        
        try:
            while self.running:
                time.sleep(1)  # Keep the main thread alive
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self.shutdown()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Garage Door Controller")
    parser.add_argument(
        "--config", 
        default="config.yaml",
        help="Configuration file path (default: config.yaml)"
    )
    
    args = parser.parse_args()
    
    controller = GarageController(args.config)
    controller.run()


if __name__ == "__main__":
    main()