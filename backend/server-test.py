# test_server.py
import paho.mqtt.client as mqtt
import json
import time

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_COMMANDS = "/commands"

client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

try:
    while True:
        # Example command payload
        payload = {
            "action": "load_map",
            "map_id": "test123"
        }
        client.publish(TOPIC_COMMANDS, json.dumps(payload))
        print(f"Published: {payload}")
        time.sleep(5)
except KeyboardInterrupt:
    print("Exiting...")
    client.disconnect()
