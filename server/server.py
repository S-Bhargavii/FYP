from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import redis
import uuid
import paho.mqtt.client as mqtt
import json 
from typing import List, Dict, Tuple
import asyncio
import time
import heapq 
from maps import parse_tileset

# constants
BROKER = "broker.hivemq.com"
COMMANDS_TOPIC_PREFIX = "jetson/commands"
POSE_TOPIC_PREFIX = "jetson/pose"
MAP_PATH = "map.xml"
# app
app = FastAPI()

# mqtt client
mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER, 1883, 60)
mqtt_client.loop_start() # connection kept alive with the broker 

# redis client 
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
landmark_cells, obstructions, tile_dimensions, grid_dimensions = parse_tileset(MAP_PATH) 
# tile_dimensions is the dimensions of the tile in pixels

class ConnectionManager:
    def __init__(self):
        self.active_connections : Dict[str, WebSocket] = {}  # jetson_id -> websocket mapping

    async def connect(self, websocket: WebSocket, jetson_id : str):
        await websocket.accept()
        self.active_connections[jetson_id] = websocket

    def disconnect(self, jetson_id:str):
        if jetson_id in self.active_connections:
            del self.active_connections[jetson_id]
    
    async def send_to_jetson_user(self, jetson_id:str, message:str):
        websocket = self.active_connections[jetson_id]
        if websocket:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(jetson_id)

# connection mananger 
websocket_connection_manager = ConnectionManager()

class SessionRegistration(BaseModel):
    jetson_id : str
    map_id : str

@app.post("/register-session")
def register_session(session: SessionRegistration):
    if not session.jetson_id or not session.map_id:
        raise HTTPException(status_code=400, detail="jetson_id and map_id are required.")
    
    session_token = str(uuid.uuid4())
    topic = f"{COMMANDS_TOPIC_PREFIX}/{session.jetson_id}"
    payload = {
        "action":"load_map",
        "map_id":session.map_id
    }

    # publish to jetson to start the processes
    mqtt_client.publish(topic=topic, payload=json.dumps(payload))

    # store the session token in the redis database 
    redis_key = f"session:{session_token}"
    redis_client.hmset(redis_key, 
                       {
                           "jetson_id":session.jetson_id,
                           "map_id":session.map_id
                       })
    # set expiry for 1 day --> 24 hours
    redis_client.expire(redis_key,86400)

    return {"message": "Session registered successfully", "session_token":session_token}

@app.get("/terminate-session/{session_token}")
def terminate_session(session_token: str):
    redis_key = f"session:{session_token}"
    session_data = redis_client.hgetall(redis_key)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    jetson_id = session_data.get("jetson_id")
    if not jetson_id:
        raise HTTPException(status_code=404, detail="Jetson ID not found in session.")

    topic = f"{COMMANDS_TOPIC_PREFIX}/{jetson_id}"
    payload = {"action": "shutdown"}

    mqtt_client.publish(topic=topic, payload=json.dumps(payload))

    redis_client.delete(redis_key)

    return {"message": "Session terminated successfully"}

@app.websocket("/ws/{session_token}")
async def websocket_endpoint(websocket:WebSocket, session_token:str):
    redis_key = f"session:{session_token}"
    session_data = redis_client.hgetall(redis_key)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    jetson_id = session_data.get("jetson_id")
    if not jetson_id:
        raise HTTPException(status_code=404, detail="Jetson ID not found in session.")
    
    await websocket_connection_manager.connect(websocket, jetson_id)

    try:
        while True:
            await websocket.receive_text() # to keep connection alive 
    except WebSocketDisconnect:
        websocket_connection_manager.disconnect(jetson_id)

def on_pose_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split("/")
        jetson_id = topic_parts[-1]
        payload_str = msg.payload.decode()
        payload = json.loads(payload_str)

        # the redis database stores the latest location of the user
        redis_key = f"user_location:{jetson_id}"
        redis_value = {
            "map_id": payload["map_id"],
            "x": payload["x"],
            "y": payload["y"], 
            "timestamp": time.time()
        }
        redis_client.setex(redis_key, 300, json.dumps(redis_value))

        asyncio.run_coroutine_threadsafe(
            websocket_connection_manager.send_to_jetson_user(jetson_id, payload_str), asyncio.get_event_loop()
        )
    except Exception as e:
        print(f"Error processing pose message: {e}")

mqtt_client.message_callback_add(POSE_TOPIC_PREFIX+"#", on_pose_message)
mqtt_client.subscribe(POSE_TOPIC_PREFIX + "#")

def fetch_user_current_location_grid_cell(session_token:str):
    redis_key = f"session:{session_token}"
    session_data = redis_client.hgetall(redis_key)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    jetson_id = session_data.get("jetson_id")
    user_location_key = f"user_location:{jetson_id}"
    user_data_json = redis_client.get(user_location_key)

    if not user_data_json:
        raise HTTPException(status_code=404, detail="User location not found")

    user_data = json.loads(user_data_json)
    x = user_data["x"]
    y = user_data["y"]
    grid_x = int(x//tile_dimensions[0])
    grid_y = int(y//tile_dimensions[1])

    return (grid_x, grid_y)

def compute_crowd_density(map_id:str):
    keys = redis_client.keys("user_location:*") # get all the user's latest location
    grid_density = {}

    for key in keys:
        user_location_data = json.loads(redis_client.get(key))
        if user_location_data["map_id"] != map_id:
            continue
        
        x, y = user_location_data["x"], user_location_data["y"]
        grid_x, grid_y = x//tile_dimensions[0], y//tile_dimensions[1]
        grid_key = (grid_x, grid_y)

        grid_density[grid_key] = grid_density.get(grid_key, 0) + 1

    max_density = max(grid_density.values(), default=1)
    density_grid = {}

    for (grid_x, grid_y), count in grid_density.items():
        density_score = count / max_density
        density_grid[(grid_x, grid_y)]  = density_score

    return density_grid 

def find_nearest_path(start: Tuple[int, int], goals: List[Tuple[int, int]], density_grid: dict, preference:str):
    best_path = None
    best_cost = float('inf')
    for goal in goals:
        path = a_star_path_finding(start, goal, density_grid, preference)
        if path and len(path) < best_cost:
            best_path = path 
            best_cost = len(path)

    return best_path or []

def reconstruct_path(came_from, current):
    total_path = [current]
    while current in came_from:
        current = came_from[current]
        total_path.append(current)
    
    total_path.reverse()
    return [{"x": c[0]*tile_dimensions[0] + tile_dimensions[0]/2, "y": c[1]*tile_dimensions[1] + tile_dimensions[1]/2} for c in total_path]

def a_star_path_finding(start, goal, density_grid, preference):
    open_set =[]
    heapq.heappush(open_set, (0, start)) # cost, start_node
    came_from = {}

    # g score is the measure of distance from the start to the current state
    # h score is the measure of the distance from the current state to the goal
    # A* is done by calculating f_score g_score + h_score --> higher the score, lesser desirable the state is
    g_score = {start: 0}

    def heuristic(a, b):
        # manhattan distance
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    while open_set:
        # current is the current state or the current cell that we are exploring 
        current = heapq.heappop(open_set)[1]

        if current == goal:
            return reconstruct_path(came_from, current)
        
        neighbours = get_neighbours(current)

        for neighbour in neighbours:
            if neighbour in obstructions:
                continue
            tentative_g_score = g_score[current] + 1 # for the g score, just count the number of grids moved
        
            if preference == "least_crowded":
                density_cost = density_grid.get(neighbour,0)
                tentative_g_score += density_cost*10 # add the density 
            
            if neighbour not in g_score or tentative_g_score < g_score[neighbour]:
                # only update the g_score if it hasn't been recorded before 
                # or the current path gave a lower g_score that previous paths
                came_from[neighbour] = current
                g_score[neighbour]  = tentative_g_score
                f_score = tentative_g_score + heuristic(neighbour, goal)
                heapq.heappush(open_set, (f_score, neighbour))
    return []

def get_neighbours(current):
    x, y = current[0], current[1] # current cell's x and y co-ordinate
    rows, columns = grid_dimensions[0], grid_dimensions[1]
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1),  # cardinal
                  (-1, -1), (-1, 1), (1, -1), (1, 1)]  # diagonals
    neighbours = []
    
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if 0 <= nx < columns and 0 <= ny < rows:  # Add proper map dimensions
            neighbours.append((nx, ny))
    return neighbours
    

@app.get("/get-route/fast/{destination}/{session_token}")
def get_fast_route(destination:int, session_token:str):
    redis_key = f"session:{session_token}"
    session_data = redis_client.hgetall(redis_key)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    start = fetch_user_current_location_grid_cell(session_token) # fetches the grid x,y of the user's current location
    goal_cells = landmark_cells.get(destination) # fetchs the grid x,y of the destination
    if not goal_cells:
        raise HTTPException(status_code=404, detail="Destination landmark not found")

    path = find_nearest_path(start, goal_cells, density_grid={}, preference='fastest')
    return {"path": path}

@app.get("/get-route/less-crowd/{destination}/{session_token}")
def get_less_crowded_route(destination:str, session_token:str):
    redis_key = f"session:{session_token}"
    session_data = redis_client.hgetall(redis_key)
    
    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")

    start = fetch_user_current_location_grid_cell(session_token)
    goal_cells = landmark_cells.get(destination)
    if not goal_cells:
        raise HTTPException(status_code=404, detail="Destination landmark not found")

    density_grid = compute_crowd_density(session_data.get("map_id"))
    path = find_nearest_path(start, goal_cells, density_grid=density_grid, preference='least_crowded')
    return {"path": path}

@app.get("/crowd-heatmap/{session_token}")
def get_crowd_density(session_token :str):
    redis_key = f"sesion:{session_token}"
    session_data = redis_client.hgetall(redis_key)

    if not session_data:
        raise HTTPException(status_code=404, detail="Session not found")
    map_id = session_data.get("map_id")
    return compute_crowd_density(map_id)