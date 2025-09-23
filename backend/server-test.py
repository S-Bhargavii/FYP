# test_server.py
import paho.mqtt.client as mqtt
import json
import signal
import sys

MQTT_BROKER = "192.168.1.11"
MQTT_PORT = 1883
TOPIC_COMMANDS = "/commands"
TOPIC_POSE = "/pose"

def on_pose(client, userdata, msg):
    try:
        pose = json.loads(msg.payload.decode())
        print(f"Received pose: {pose}")
    except json.JSONDecodeError:
        print(f"Invalid pose message: {msg.payload.decode()}")

def cleanup(sig=None, frame=None):
    # Send shutdown command before exiting
    shutdown_payload = {"action": "shutdown"}
    client.publish(TOPIC_COMMANDS, json.dumps(shutdown_payload))
    print(f"Published shutdown: {shutdown_payload}")
    client.disconnect()
    sys.exit(0)

# Setup MQTT client
client = mqtt.Client()
client.on_message = on_pose
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Subscribe to pose updates
client.subscribe(TOPIC_POSE)
client.loop_start()

# Send load_map command once
load_map_payload = {"action": "load_map", "map_id": "test123"}
client.publish(TOPIC_COMMANDS, json.dumps(load_map_payload))
print(f"Published load_map: {load_map_payload}")

# Catch Ctrl+C to send shutdown
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

# Keep running and listening for poses
print("Listening for poses... Press Ctrl+C to exit.")
while True:
    pass
