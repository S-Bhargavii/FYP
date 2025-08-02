import paho.mqtt.client as mqtt
import json 
import subprocess
import time 
import yaml
import signal
import rospy
import threading
from geometry_msgs.msg import Point

BROKER = "broker.hivemq.com"
PORT = 1883
# topic where commands get published by the server --> the jetson subscribes to this topic
COMMANDS_TOPIC = "/jetson/commands/jetson_001" 
# topic where the user pose is published by the jetson 
POSE_TOPIC = "/jetson/pose/jetson_001"
ROS_TOPIC = "camera_real_world_position"

# process handles
processes = []
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    """
        Subscribe to the commands topic as soon 
        as the connection is established with the 
        broker.
    """
    if rc == 0 :
        print("Connected to MQTT broker")
        client.subscribe(COMMANDS_TOPIC)
    else:
        print(f"Failed to connect to broker with code {rc}")

def on_message(client, userdata, msg):
    """
        Callback function that gets called when a message 
        is received on the subscribed topic.
    """
    try:
        payload = json.loads(msg.payload.decode())

        if payload["action"] == "load_map":
            print(f"Loading map: {payload['map_id']} and starting localisation")
            start_processes(payload["map_id"])

            # Start ROS Subscriber in a separate thread
            ros_thread = threading.Thread(target=ros_listener)
            ros_thread.start()
    except Exception as e:
        print(f"Error processing message: {e}")

def update_yaml_with_map_id(map_id):
    with open('RealSense_D435i.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    config["LoadAtlasFromFile"] = f"{map_id}"

    with open("RealSense_D435i.yaml", "w") as file:
        yaml.safe_dump(config, file, default_flow_style=False)

    print("Updated yaml with requested map")

def start_processes(map_id):
    """
        Start the necessary processes for running SLAM 
        in localisation mode
    """

    # start the camera streaming process 
    cam = subprocess.Popen(
        ["roslaunch", "realsense2_camera", "rs_camera.launch",
        "align_depth:=true",
        "depth_width:=640", "depth_height:=480",
        "color_width:=640", "color_height:=480",
        "color_fps:=30", "depth_fps:=30"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    processes.append(cam)

    time.sleep(5) # wait for the camera process to start 

    # update the yaml file with the map id
    update_yaml_with_map_id(map_id)
    # start ORB_SLAM3
    slam = subprocess.Popen(["rosrun", "ORB_SLAM3", "real_sense_rgbd_ros",
                             "/home/bhargavi/Dev/ORB_SLAM3/Vocabulary/ORBvoc.txt",
                             "/home/bhargavi/Dev/ORB_SLAM3/Examples_old/ROS/ORB_SLAM3/src/Updated_RealSense_D435i.yaml",
                             "loc"]) # run in localisation mode
    # add processes to the list of running processes
    processes.append(slam)

def shutdown():
    """
        Stop the running processes
    """
    print("Shutting down processes")
    for p in processes:
        p.send_signal(signal.SIGINT) # clean shutdown 

    time.sleep(3) # wait for the processes to shut down completely

def pose_callback(msg):
    """
        Calbasck function to be executed when a pose message is received.
        Publishes the user pose to the MQTT Broker for the backend to consume.
    """
    try:
        user_pose = {
            'x': msg.x,
            'y': msg.y,
        }
        # Only strings can be published to MQTT
        client.publish(POSE_TOPIC, json.dumps(user_pose))
        rospy.loginfo(f"Published user pose: {user_pose}")
    except Exception as e:
        print(f"Error publishing pose: {e}")

def ros_listener():
    """
        The Slam node publishes the user pose to this topic.
        The server subscribes to this topic and listens for 
        the user pose. Once received, it publishes the user on
        the MQTT topic for the backend to consume.
    """
    # creat a subscriber node to listen for user pose
    rospy.init_node('pose_listener', anonymous=True)
    # publishes the x,y co-ordinates of the user 
    # position on the 2D map
    rospy.Subscriber(ROS_TOPIC, Point, pose_callback)
    rospy.spin()

if __name__ == "__main__":
    # setup MQTT client 
    client.on_connect = on_connect
    client.on_message = on_message

    # connect to broker 
    client.connect(BROKER, PORT, 60)

    # blocking loop to process network traffic and dispatch callbacks
    try:
        client.loop_forever()  # Blocking call
    except KeyboardInterrupt:
        shutdown()
        client.loop_stop()
        print("Shutting down...")