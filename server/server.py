from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import uuid
import paho.mqtt.client as mqtt
import json

app = FastAPI()
mqtt_client = mqtt.Client()
BROKER = "broker.hivemq.com"
COMMANDS_TOPIC = "jetson/commands"
mqtt_client.connect(BROKER, 1883, 60)
mqtt_client.loop_start()

# redis client setup 
redis_client : redis.Redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

class SessionRegistration(BaseModel):
    jetson_id : str
    map_id : str

@app.post("/register-session")
def register_session(session: SessionRegistration):
    if not session.jetson_id or not session.map_id:
        raise HTTPException(status_code=400, detail="jetson_id and map_id are required.")
    
    session_token = str(uuid.uuid4())
    topic = f"{COMMANDS_TOPIC}/{session.jetson_id}"
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

    return {"message": "Session registered", "session_token":session_token}

@app.get("/terminate-session/{session_token}")
def terminate_session(session_token:str):
    redis_key = f"session:{session_token}"
    session_data = redis_client.hgetall(redis_key) # gets the value of that key (dictionary with values for user_id and jetson_id)

    if not session_data:
        raise HTTPException("Session not found")
    jetson_id = session_data.get("jetson_id")
    if not jetson_id:
        raise HTTPException(status_code=404, detail="Jetson ID not found in session.")
    
    topic = f"{COMMANDS_TOPIC}/{jetson_id}"
    payload  = {"action":"shutdown"}

    mqtt_client.publish(topic=topic, payload=payload)
    
    # delete session info from the redis database
    redis_client.delete(redis_key)

    return {"message":"Session terminated successfully"}

