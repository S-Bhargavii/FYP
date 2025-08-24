from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio

class WebSocketConnectionManager:
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

class SSEConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, asyncio.Queue] = {}
    
    def connect(self, jetson_id: str):
        queue = asyncio.Queue()
        # create a seperate queue for each connection
        self.active_connections[jetson_id] = queue
        return queue

    def disconnect(self, jetson_id):
        if jetson_id in self.active_connections:
            del self.active_connections[jetson_id]
    
    async def send_to_jetson_user(self, jetson_id:str, message:str):
        if jetson_id in self.active_connections:
            # put the message on the queue so that it can be sent later by SSE
            await self.active_connections[jetson_id].put(message)
