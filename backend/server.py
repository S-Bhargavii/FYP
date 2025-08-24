from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
import redis
import paho.mqtt.client as mqtt
import json 
import asyncio
import time
from constants import MQTT_BROKER, MQTT_PORT, REDIS_HOST, REDIS_LOCATION_PREFIX, REDIS_DB, REDIS_PORT, MQTT_COMMANDS_TOPIC_PREFIX, MQTT_POSE_TOPIC_PREFIX
from connection_manager import SSEConnectionManager
from input_validation import SessionRegistration
from path_planning import PathPlanner
from map import Map

# Store main event loop globally
main_event_loop = asyncio.get_event_loop()

# app 
app = FastAPI()

# mqtt client 
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# redis client 
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# websocket connection manager 
sse_connection_manager = SSEConnectionManager()

# jetson_to_map --> contains mapping between jetson id and 
# the map the jetson is currently being used in
# jetson_id : map_id
jetson_to_map = {}

# each map will have its corresponding path planner object 
# has the map info and computes the optimal path, gets crowd info so on
map_to_map_and_path_planner = {}

async def sse_event_generator(queue: asyncio.Queue):
    while True:
        message = await queue.get()
        yield f"data: {message}\n\n"

def on_pose_msg(client, userdata, msg):
    """
        Callback function called when the jetson 
        publishes pose on corresponding MQTT topic.
    """
    try:
        topic_parts = msg.topic.split("/")
        jetson_id = topic_parts[-1]
        
        payload_str = msg.payload.decode()
        payload =  json.loads(payload_str)

        # add the user position to redis 
        # this is for keeping track of crowd density later
        redis_key = f"{REDIS_LOCATION_PREFIX}:{jetson_id}"
        redis_value = {
            "x": payload["x"], 
            "y": payload["y"], 
            "timestamp": time.time()
        }
        redis_client.set(redis_key, json.dumps(redis_value))

        # send the user's current position to the corresponding 
        # websocket connection
        # this is moved to a thread because you don't want the program to be paused 
        # meaning you don't want to stop listening to incoming messages while this 
        # part of the code is running.
        asyncio.run_coroutine_threadsafe(
            sse_connection_manager.send_to_jetson_user(jetson_id, payload_str),
            main_event_loop
        )

    except Exception as e:
        print(f"Error processing pose message : {e}")

# listen to any requests that start with POSE_TOPIC_PREFIX and add callback 
mqtt_client.message_callback_add(f"{MQTT_POSE_TOPIC_PREFIX}/"+"#", on_pose_msg) # "#" is a wildcard
mqtt_client.subscribe(f"{MQTT_POSE_TOPIC_PREFIX}/"+"#")

############ API ENDPOINTS #################

@app.post("/register")
def register(session: SessionRegistration):
    print(f"Registration required for : {session.jetson_id} and {session.map_id}")
    if not session.jetson_id or not session.map_id:
        raise HTTPException(status_code=400, detail="jetson_id and map_id are required.")
    
    if session.jetson_id in jetson_to_map:
        raise HTTPException(status_code=400, detail="jetson_id already registered.")

    # publish to commands/1 topic for example 
    # jetson1 will be listening on this topic for commands 
    topic = f"{MQTT_COMMANDS_TOPIC_PREFIX}/{session.jetson_id}"
    payload = {
        "action" : "load_map", 
        "map_id" : session.map_id
    }
    jetson_to_map[session.jetson_id] = session.map_id
    
    if session.map_id not in map_to_map_and_path_planner:
        map = Map(session.map_id)
        map_to_map_and_path_planner[session.map_id] = [map, PathPlanner(map, redis_client, jetson_to_map)]

    # publish on corresponding jetson's topic 
    mqtt_client.publish(topic=topic, payload=json.dumps(payload))

    return JSONResponse(content={"message": "Registration successful."}, status_code=200)

@app.get("/map-data/{jetson_id}")
def get_map_info(jetson_id: str):
    map: Map =  map_to_map_and_path_planner[jetson_to_map[jetson_id]][0]
    map_info = {
        "map_width_in_px": map.map_width_in_px,
        "map_height_in_px": map.map_height_in_px,
        "tile_height": map.tile_height,
        "tile_width": map.tile_width,
        "landmarks_mapping": map.landmarks_mapping
    }
    return {"map_info":map_info}

@app.get("/terminate")
def terminate(jetson_id:str):
    print(f"Termination requested for {jetson_id}")
    if jetson_id not in jetson_to_map:
        raise HTTPException(status_code=400, detail="jetson has not been registered.")
    
    topic = f"{MQTT_COMMANDS_TOPIC_PREFIX}/{jetson_id}"
    payload = {"action" : "shutdown"}

    # publish on corresponding jetson's topic 
    mqtt_client.publish(topic=topic, payload=json.dumps(payload))
    
    # delete mapping 
    del jetson_to_map[jetson_id]

    # delete websocket connection
    sse_connection_manager.disconnect(jetson_id)

    return JSONResponse(content={"message": "Termination successful."}, status_code=200)

@app.get("/sse/{jetson_id}")
async def sse_endpoint(jetson_id: str):
    queue = sse_connection_manager.connect(jetson_id)
    response = StreamingResponse(sse_event_generator(queue), media_type="text/event-stream")
    return response


@app.get("/route/{route_type}/{destination}/{jetson_id}")
def get_fast_route(route_type:str, destination: str, jetson_id: str):
    path_planner :PathPlanner = map_to_map_and_path_planner[jetson_to_map[jetson_id]][1]
    start = path_planner.fetch_jetson_current_location(jetson_id)
    path = path_planner.find_nearest_path(start, destination, route_type)
    return {"path":path}

@app.get("/crowd-heatmap/{jetson_id}")
def get_crowd_density(jetson_id:str):
    path_planner : PathPlanner = map_to_map_and_path_planner[jetson_to_map[jetson_id]][1]
    density_grid = path_planner.compute_crowd_density(for_heatmap=True)
    return {"density_grid":density_grid}
