#!/usr/bin/env python3 

import rospy 
import subprocess
import signal
import time
from std_msgs.msg import Float32
import websocket
import threading 
import json 
import os 

# Websocket Server API 
# SERVER_WS_URL = "ws://<server-ip>:8000/ws"
SERVER_WS_URL = "ws://localhost:8000/ws"

# ros topic that publishes the camera position wrt the map
ROS_TOPIC = "camera_real_world_position"

# process handles 
processes = []

def start_processes():
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

    # start ORB_SLAM3
    slam = subprocess.Popen(["rosrun", "ORB_SLAM3", "real_sense_rgbd_ros",
                             "/home/bhargavi/Dev/ORB_SLAM3/Vocabulary/ORBvoc.txt",
                             "/home/bhargavi/Dev/ORB_SLAM3/Examples_old/ROS/ORB_SLAM3/src/Updated_RealSense_D435i.yaml",
                             "loc"]) # run in localisation mode
    processes.append(slam)

def shutdown():
    """
        Stop the running processes
    """
    print("Shutting down processes")
    for p in processes:
        p.send_signal(signal.SIGINT) # clean shutdown 

    time.sleep(3) # wait for the processes to shut down completely

def pose_callback(msg, ws):
    """
        Callback function to be executed when the 
        location info is recieved from the ros node
    """
    try:
        # wrap the data published by the ros node 
        # in a json object
        data = {'x':msg.data}
        ws.send(json.dumps(data)) # send to the server
        rospy.loginfo(f"Sent to server: {data}")

    except Exception as e:
        rospy.logerr(f"Websocket error: {e}")

def main():
    start_processes()

    # connect websocket 
    ws = websocket.WebSocket()
    try:
        ws.connect(SERVER_WS_URL)
        print("Connected to the server")
    except Exception as e:
        print(f"Failed to connect to the server : {e}")
        shutdown()
        return

    rospy.init_node("slam_ws_forwarder", anonymous=True) # create a subscriber node
    rospy.Subscriber(ROS_TOPIC, Float32, lambda msg: pose_callback(msg=msg, ws=ws))

    def handle_exit(sig, frame):
        shutdown()
        ws.close()
        os._exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    rospy.spin()

if __name__ == "__main__":
    main()
