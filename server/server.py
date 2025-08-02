from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import redis
import uuid
import paho.mqtt.client as mqtt
import json 
from typing import List, Dict
import asyncio
import time

# constants
BROKER = "broker.hivemq.com"
COMMANDS_TOPIC_PREFIX = "jetson/commands"
POSE_TOPIC_PREFIX = "jetson/pose"

# app
app = FastAPI()

# mqtt client
mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER, 1883, 60)
mqtt_client.loop_start() # connection kept alive with the broker 

# redis client 
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

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

        redis_key = f"user_location:{jetson_id}"
        redis_value = {
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