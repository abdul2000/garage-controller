#!/usr/bin/env python3
"""
System check script for Garage Controller
Verifies hardware and configuration
"""

import sys
import os
import yaml
import subprocess

def check_gpio():
    """Check GPIO availability"""
    print("Checking GPIO...")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
        print("✓ GPIO is available")
        return True
    except ImportError:
        print("✗ RPi.GPIO not installed")
        return False
    except RuntimeError as e:
        print(f"✗ GPIO error: {e}")
        return False

def check_python_deps():
    """Check Python dependencies"""
    print("Checking Python dependencies...")
    try:
        import paho.mqtt.client
        print("✓ paho-mqtt is available")
    except ImportError:
        print("✗ paho-mqtt not installed")
        return False
    
    try:
        import yaml
        print("✓ PyYAML is available")
    except ImportError:
        print("✗ PyYAML not installed")
        return False
    
    return True

def check_config(config_file="config.yaml"):
    """Check configuration file"""
    print(f"Checking configuration file: {config_file}")
    
    if not os.path.exists(config_file):
        print(f"✗ Configuration file {config_file} not found")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['garage', 'mqtt', 'logging', 'gpio']
        for section in required_sections:
            if section not in config:
                print(f"✗ Missing configuration section: {section}")
                return False
        
        # Check GPIO pins
        relay_pin = config['garage']['relay_pin']
        sensor_pin = config['garage']['door_sensor_pin']
        
        if not (1 <= relay_pin <= 27):
            print(f"✗ Invalid relay pin: {relay_pin} (should be 1-27)")
            return False
            
        if not (1 <= sensor_pin <= 27):
            print(f"✗ Invalid sensor pin: {sensor_pin} (should be 1-27)")
            return False
            
        if relay_pin == sensor_pin:
            print(f"✗ Relay and sensor pins cannot be the same: {relay_pin}")
            return False
        
        print("✓ Configuration file is valid")
        print(f"  - Garage: {config['garage']['name']}")
        print(f"  - Relay pin: GPIO {relay_pin}")
        print(f"  - Sensor pin: GPIO {sensor_pin}")
        print(f"  - MQTT broker: {config['mqtt']['broker']}:{config['mqtt']['port']}")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"✗ Configuration file error: {e}")
        return False
    except KeyError as e:
        print(f"✗ Missing configuration key: {e}")
        return False

def check_permissions():
    """Check user permissions"""
    print("Checking permissions...")
    
    # Check if user is in gpio group
    try:
        import grp
        gpio_group = grp.getgrnam('gpio')
        current_user = os.getenv('USER', 'unknown')
        
        if current_user in gpio_group.gr_mem:
            print(f"✓ User {current_user} is in gpio group")
        else:
            print(f"✗ User {current_user} is not in gpio group")
            print("  Run: sudo usermod -a -G gpio $USER")
            print("  Then log out and back in")
            return False
    except KeyError:
        print("! GPIO group not found (this is normal on some systems)")
    
    return True

def check_service():
    """Check systemd service"""
    print("Checking systemd service...")
    
    service_file = "/etc/systemd/system/garage-controller.service"
    if not os.path.exists(service_file):
        print("✗ Service file not installed")
        print("  Run: sudo ./install.sh")
        return False
    
    try:
        result = subprocess.run(['systemctl', 'is-enabled', 'garage-controller'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Service is enabled")
        else:
            print("✗ Service is not enabled")
            return False
            
        result = subprocess.run(['systemctl', 'is-active', 'garage-controller'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Service is active")
        else:
            print("! Service is not running")
            print("  Start with: sudo systemctl start garage-controller")
    
    except FileNotFoundError:
        print("✗ systemctl not found")
        return False
    
    return True

def test_mqtt_connection(config_file="config.yaml"):
    """Test MQTT connection"""
    print("Testing MQTT connection...")
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        import paho.mqtt.client as mqtt
        
        connected = False
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connected
            if rc == 0:
                connected = True
            
        client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        client.on_connect = on_connect
        
        if config['mqtt']['username']:
            client.username_pw_set(config['mqtt']['username'], config['mqtt']['password'])
        
        client.connect(config['mqtt']['broker'], config['mqtt']['port'], 10)
        client.loop_start()
        
        import time
        time.sleep(2)
        
        client.loop_stop()
        client.disconnect()
        
        if connected:
            print("✓ MQTT connection successful")
            return True
        else:
            print("✗ MQTT connection failed")
            return False
            
    except Exception as e:
        print(f"✗ MQTT test error: {e}")
        return False

def main():
    """Main check function"""
    print("Garage Controller System Check")
    print("=" * 40)
    
    checks = [
        check_python_deps,
        lambda: check_config("config.yaml"),
        check_gpio,
        check_permissions,
        check_service,
        lambda: test_mqtt_connection("config.yaml")
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        try:
            if check():
                passed += 1
        except Exception as e:
            print(f"✗ Check failed with error: {e}")
        print()
    
    print("=" * 40)
    print(f"Checks passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All checks passed! System is ready.")
        return 0
    else:
        print("✗ Some checks failed. Please resolve the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())