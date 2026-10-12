import time
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from datetime import datetime

MQTT_BROKER = 'homeassistant.local'
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
last_connect_time = None
last_state = None
target_state = None
transition_start_time = None
last_moving_time = None
last_obstruction = None
start_position_since = None

# While the door is travelling, the reed switch at the position it just left can
# flicker. A reading of that starting position only counts once it has held this
# long (e.g. the door was stopped or reversed straight away).
START_POSITION_CONFIRM_SECONDS = 5

def log(msg):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}", flush=True)

def get_door_state():
    # Read pins multiple times to debounce
    closed_readings = []
    open_readings = []
    
    for _ in range(5):  # Take 5 readings for better reliability
        closed_readings.append(GPIO.input(CLOSED_REED_PIN))
        open_readings.append(GPIO.input(OPEN_REED_PIN))
        time.sleep(0.02)  # 20ms between readings
    
    # Count how many readings are LOW (triggered)
    closed_low_count = closed_readings.count(GPIO.LOW)
    open_low_count = open_readings.count(GPIO.LOW)
    
    # Determine state
    if closed_low_count >= 3:  # 3 out of 5 readings LOW = closed position
        state = "closed"
    elif open_low_count >= 3:  # 3 out of 5 readings LOW = open position
        state = "open"
    else:
        state = "moving"
    
    # Debug output (only when state changes or for diagnostics)
    global last_debug_state
    if not 'last_debug_state' in globals():
        last_debug_state = None
    
    if state != last_debug_state:
        log(f"Reed switches - Closed: {closed_readings} (LOW: {closed_low_count}), Open: {open_readings} (LOW: {open_low_count}) → State: {state}")
        last_debug_state = state
    
    return state

def toggle_relay():
    log("Toggling relay")
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(RELAY_PIN, GPIO.LOW)

def publish_state(state):
    global last_state
    if state != last_state:
        log(f"Publishing state: {state}")
        client.publish(MQTT_TOPIC_STATE, state, retain=True)
        last_state = state

def publish_obstruction(obstructed):
    # Only publish when the value changes, not on every loop
    global last_obstruction
    if obstructed != last_obstruction:
        client.publish(MQTT_TOPIC_OBSTRUCTION, "true" if obstructed else "false", retain=True)
        last_obstruction = obstructed

def on_connect(client, userdata, flags, rc):
    log("Connected to MQTT broker")
    global last_connect_time
    last_connect_time = time.time()
    client.subscribe(MQTT_TOPIC_COMMAND)

def on_message(client, userdata, msg):
    log(f"Received MQTT: {msg.topic} → {msg.payload.decode()} (retain={msg.retain})")
    global target_state, transition_start_time, last_moving_time

    # Never act on a retained payload: the broker replays the last retained
    # message on this topic to us every time we (re)subscribe, e.g. after a
    # network outage. Treating that replay as a live command is what causes
    # the door to trigger on reconnect.
    if msg.retain:
        log("Ignoring retained message on command topic")
        return

    toggle_command = msg.payload.decode()
    if toggle_command.startswith('TOGGLE'):
        if time.time() - boot_time < 5:
            log("Ignoring TOGGLE during boot protection window")
            return
        if last_connect_time and time.time() - last_connect_time < 5:
            log("Ignoring TOGGLE during post-reconnect protection window")
            return
        current = get_door_state()
        log(f"current state: {current}, target state: {target_state}")
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
        log(f"Toggling relay → current: {current}, setting target_state: {target_state}")
        transition_start_time = time.time()
        last_moving_time = time.time()

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.username_pw_set("admin", "admin")
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

try:
    while True:
        current_state = get_door_state()

        # Detect movement from physical remote control
        if current_state == "moving" and last_state in ("open", "closed") and not target_state:
            # Physical remote was used, infer direction from last stable state
            if last_state == "closed":
                target_state = "open"
                publish_state("opening")
                log("Physical remote detected: opening garage")
            elif last_state == "open":
                target_state = "closed"
                publish_state("closing")
                log("Physical remote detected: closing garage")
            transition_start_time = time.time()
            last_moving_time = time.time()


        # Door is at an end position
        elif current_state in ("open", "closed"):
            # Mid-transition and reading the position we started from: likely the
            # reed switch flickering as the door leaves. Wait until it holds.
            if target_state and current_state != target_state:
                if start_position_since is None:
                    start_position_since = time.time()
                if time.time() - start_position_since < START_POSITION_CONFIRM_SECONDS:
                    time.sleep(1)
                    continue
                log(f"Door stayed {current_state}; abandoning transition to {target_state}")
            start_position_since = None
            # If previously obstructed, recover
            if last_state == "stopped":
                log(f"Recovered from stopped: Door is now {current_state}")
            publish_state(current_state)  # Only publishes if state changed
            publish_obstruction(False)
            target_state = None
            transition_start_time = None

        # Obstruction check
        elif target_state and transition_start_time:
            start_position_since = None
            elapsed = time.time() - transition_start_time
            log(f"Expecting target: {target_state}, current state: {current_state}")
            # Only set stopped if still moving
            if elapsed > 30 and current_state == "moving":
                log("Detected obstruction — door did not reach target state.")
                publish_state("stopped")
                publish_obstruction(True)
                target_state = None
                transition_start_time = None

        time.sleep(1)

except KeyboardInterrupt:
    log("Shutting down...")
finally:
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.cleanup()
    client.loop_stop()
    client.disconnect()
