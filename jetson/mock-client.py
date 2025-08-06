import threading
import time
import json
import paho.mqtt.client as mqtt

BROKER = "broker.hivemq.com"
PORT = 1883
COMMANDS_TOPIC = "/commands/jetson_01"
POSE_TOPIC = "/pose/jetson_01"

client = mqtt.Client()
stop_event = threading.Event()
publisher_thread = None

def pose_publisher():
    x, y = 0, 8
    while not stop_event.is_set():
        pose = {"x": x, "y": y}
        client.publish(POSE_TOPIC, json.dumps(pose))
        print(f"Published: {pose}")
        x = (x + 1) % 296
        # Wait for 0.5 seconds or until stop_event is set
        if stop_event.wait(0.5):
            break

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to broker.")
        client.subscribe(COMMANDS_TOPIC)
    else:
        print(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    global publisher_thread
    try:
        payload = json.loads(msg.payload.decode())
        action = payload.get("action")
        print(f"Received command: {action}")

        if action == "load_map":
            if publisher_thread is None or not publisher_thread.is_alive():
                stop_event.clear()
                publisher_thread = threading.Thread(target=pose_publisher)
                publisher_thread.start()
                print("Started publishing thread.")
            else:
                print("Publishing thread already running.")

        elif action == "shutdown":
            if publisher_thread and publisher_thread.is_alive():
                stop_event.set()
                publisher_thread.join() # wait till the thread finishes
                print("Publishing thread stopped.")
            else:
                print("No publishing thread to stop.")

    except Exception as e:
        print(f"Error handling message: {e}")

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Exiting...")
    stop_event.set()
    if publisher_thread and publisher_thread.is_alive():
        publisher_thread.join()
