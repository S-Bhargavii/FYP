import paho.mqtt.client as mqtt
import subprocess
import threading
import signal
import sys
import json
import os

# MQTT_BROKER = "broker.hivemq.com"
MQTT_BROKER = "192.168.1.11"
MQTT_PORT = 1883
TOPIC_COMMANDS = "/commands/jetson_01"
TOPIC_POSE = "/pose/jetson_01"

slam_process = None
reader_thread = None
running = True

def read_slam_output(process):
    """Reads stdout from SLAM process, prints logs, and publishes pose lines to MQTT"""
    for line in iter(process.stdout.readline, b''):
        try:
            line = line.decode().strip()
            # Print every SLAM output line
            print(f"[SLAM LOG] {line}")

            # If the line contains the current pose, publish it
            if line.startswith("Current pose"):
                # apply co-ordinate transformation here
                parts = line.split(",")
                x = float(parts[0].split(":")[-1].strip())
                y = float(parts[1].split(":")[-1].strip())

                # applying transform
                x = int(x / 0.08)
                y = int(-y / 0.08)
                
                # timestamp = float(parts[3].split(":")[-1].strip())
                
                # pose_msg = {"x": x, "y": y, "timestamp":timestamp}
                pose_msg = {"x": x, "y": y}
                mqtt_client.publish(TOPIC_POSE, json.dumps(pose_msg))
                print(f"[POSE PUBLISHED] {pose_msg}")
                # print(timestamp)

        except Exception as e:
            print(f"Error parsing line: {e}")


def on_message(client, userdata, msg):
    global slam_process, reader_thread
    try:
        payload = json.loads(msg.payload.decode())
        action = payload.get("action", "").strip()
        print(f"Received command: {payload}")

        if action == "load_map":
            if slam_process is None:
                print("Starting ORB-SLAM3...")
                slam_process = subprocess.Popen(
                    ["./Examples/RGB-D/rgbd_realsense_D435i",
                     "/home/bhargavi/ORB_SLAM3/Vocabulary/ORBvoc.txt",
                     "/home/bhargavi/ORB_SLAM3/Examples/RGB-D/RealSense_D435i.yaml",
                     "loc"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
                reader_thread = threading.Thread(target=read_slam_output, args=(slam_process,))
                reader_thread.daemon = True
                reader_thread.start()
            else:
                print("SLAM process already running.")

        elif action == "shutdown":
            if slam_process is not None:
                print("Shutting down ORB-SLAM3...")
                # Send SIGINT to mimic Ctrl+C
                slam_process.send_signal(signal.SIGINT)
                slam_process.wait()  # wait for clean exit
                slam_process = None
            else:
                print("No SLAM process to shut down.")

    except json.JSONDecodeError:
        print(f"Received invalid JSON: {msg.payload.decode()}")

def cleanup(sig=None, frame=None):
    global slam_process
    print("Cleaning up...")
    if slam_process is not None:
        print("Sending SIGINT to SLAM process...")
        slam_process.send_signal(signal.SIGINT)
        slam_process.wait()
        slam_process = None
    mqtt_client.disconnect()
    sys.exit(0)

# ---------------- MQTT SETUP ----------------
mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.subscribe(TOPIC_COMMANDS)
mqtt_client.loop_start()

# Catch Ctrl+C
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

print("Jetson listener running...")
while running:
    pass
