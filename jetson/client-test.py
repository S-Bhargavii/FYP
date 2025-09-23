# test_client.py
import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPIC_COMMANDS = "/commands"

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Received message: {payload}")
    except json.JSONDecodeError:
        print(f"Invalid message: {msg.payload.decode()}")

client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.subscribe(TOPIC_COMMANDS)
client.loop_forever()
