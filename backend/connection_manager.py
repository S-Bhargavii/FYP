from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
 
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
        # message is a json object of x, y
        websocket = self.active_connections[jetson_id]
        if websocket:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(jetson_id)