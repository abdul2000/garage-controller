#!/usr/bin/env python3
"""
Test script for garage controller
Tests basic functionality without requiring MQTT broker
"""

import time
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the current directory to the path so we can import our module
sys.path.insert(0, '.')

class TestGarageController(unittest.TestCase):
    """Test cases for GarageController"""
    
    @patch('garage_controller.mqtt')
    def test_config_loading(self, mock_mqtt):
        """Test configuration file loading"""
        from garage_controller import GarageController
        
        # Mock MQTT client to avoid connection
        mock_client = MagicMock()
        mock_mqtt.Client.return_value = mock_client
        
        controller = GarageController('test_config.yaml')
        
        # Check basic configuration values
        self.assertEqual(controller.config['garage']['name'], 'Test Garage')
        self.assertEqual(controller.config['garage']['relay_pin'], 18)
        self.assertEqual(controller.config['garage']['door_sensor_pin'], 24)
        self.assertEqual(controller.config['mqtt']['broker'], '127.0.0.1')
        
        # Verify initial state
        self.assertIn(controller.door_state, ['open', 'closed', 'unknown'])
        
        controller.shutdown()
    
    @patch('garage_controller.mqtt')
    def test_door_activation(self, mock_mqtt):
        """Test door activation functionality"""
        from garage_controller import GarageController
        
        mock_client = MagicMock()
        mock_mqtt.Client.return_value = mock_client
        
        controller = GarageController('test_config.yaml')
        
        # Test activation
        initial_state = controller.door_state
        controller.activate_door()
        
        # Should change to opening or closing
        self.assertIn(controller.door_state, ['opening', 'closing'])
        
        controller.shutdown()
    
    @patch('garage_controller.mqtt')
    def test_mqtt_message_handling(self, mock_mqtt):
        """Test MQTT message processing"""
        from garage_controller import GarageController
        import paho.mqtt.client as mqtt
        
        mock_client = MagicMock()
        mock_mqtt.Client.return_value = mock_client
        
        controller = GarageController('test_config.yaml')
        
        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = f"{controller.config['mqtt']['topic_prefix']}/set"
        mock_msg.payload.decode.return_value = "OPEN"
        
        # Test message handling
        controller._on_mqtt_message(mock_client, None, mock_msg)
        
        controller.shutdown()


def test_basic_functionality():
    """Simple functional test"""
    print("Testing basic functionality...")
    
    # Patch MQTT to avoid connection issues
    with patch('garage_controller.mqtt') as mock_mqtt:
        mock_client = MagicMock()
        mock_mqtt.Client.return_value = mock_client
        
        from garage_controller import GarageController
        
        print("✓ Importing GarageController")
        
        controller = GarageController('test_config.yaml')
        print("✓ Controller initialization")
        
        print(f"✓ Initial door state: {controller.door_state}")
        
        controller.activate_door()
        print(f"✓ Door activation, new state: {controller.door_state}")
        
        controller.shutdown()
        print("✓ Controller shutdown")
    
    print("All tests passed!")


if __name__ == "__main__":
    # Run basic functionality test
    test_basic_functionality()
    
    # Run unit tests
    print("\nRunning unit tests...")
    unittest.main(verbosity=2)