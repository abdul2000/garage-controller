import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

MQTT_BROKER = '192.168.1.120'
MQTT_TOPIC_COMMAND = 'garage/command'
MQTT_TOPIC_STATE = 'garage/state'
MQTT_TOPIC_OBSTRUCTION = 'garage/obstruction'

RELAY_PIN = 4         # GPIO4 for relay
CLOSED_REED_PIN = 23  # GPIO23 for closed position
OPEN_REED_PIN = 24    # GPIO24 for open position

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT, initial=GPIO.LOW)  # Keep inactive at boot
GPIO.setup(CLOSED_REED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(OPEN_REED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

boot_time = time.time()
last_state = None
target_state = None
transition_start_time = None

def get_door_state():
    # Read pins multiple times to debounce
    closed_readings = []
    open_readings = []
    
    for _ in range(3):  # Take 3 readings
        closed_readings.append(GPIO.input(CLOSED_REED_PIN))
        open_readings.append(GPIO.input(OPEN_REED_PIN))
        time.sleep(0.01)  # 10ms between readings
    
    # All readings must be consistent for a stable state
    if all(reading == GPIO.LOW for reading in closed_readings):
        return "closed"
    elif all(reading == GPIO.LOW for reading in open_readings):
        return "open"
    else:
        return "moving"

def toggle_relay():
    print("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(RELAY_PIN, GPIO.LOW)

def publish_state(state):
    global last_state
    if state != last_state:
        print(f"Publishing state: {state}")
        client.publish(MQTT_TOPIC_STATE, state, retain=True)
        last_state = state

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC_COMMAND)

def on_message(client, userdata, msg):
    print(f"Received MQTT: {msg.topic} → {msg.payload.decode()}")
    global target_state, transition_start_time

    toggle_command = msg.payload.decode()
    if toggle_command.startswith('TOGGLE'):
        if time.time() - boot_time < 5:
            print("Ignoring TOGGLE during boot protection window")
            return
        current = get_door_state()
        print(f"current state: {current}, target state: {target_state}")
        if current == "closed" and toggle_command == 'TOGGLE_OPEN':
            target_state = "open"
            publish_state("opening")
            toggle_relay()
        elif current == "open" and toggle_command == 'TOGGLE_CLOSE':
            target_state = "closed"
            publish_state("closing")
            toggle_relay()
        else:
            publish_state("moving")
        print(f"Toggling relay → current: {current}, setting target_state: {target_state}")
        transition_start_time = time.time()

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.username_pw_set("admin", "admin")
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

try:
    while True:
        current_state = get_door_state()

        # Normal state change
        if current_state in ("open", "closed"):
            publish_state(current_state)  # Only publishes if state changed
            client.publish(MQTT_TOPIC_OBSTRUCTION, "false", retain=True)
            if current_state == target_state:
                target_state = None
                transition_start_time = None

        # Obstruction check
        elif target_state and transition_start_time:
            elapsed = time.time() - transition_start_time
            print(f"Expecting target: {target_state}, current state: {current_state}")
            if elapsed > 30:
                print("Detected obstruction — door did not reach target state.")
                publish_state("stopped")
                client.publish(MQTT_TOPIC_OBSTRUCTION, "true", retain=True)
                target_state = None
                transition_start_time = None

        time.sleep(1)

except KeyboardInterrupt:
    print("Shutting down...")
finally:
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.cleanup()
    client.loop_stop()
    client.disconnect()
