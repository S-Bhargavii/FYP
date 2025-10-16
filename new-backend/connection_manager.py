
import asyncio
from typing import Dict
import logging

class SSEConnectionManager:
    """Manages Server-Sent Events connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, asyncio.Queue] = {}
    
    def connect(self, jetson_id: str) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)  # Prevent memory issues
        self.active_connections[jetson_id] = queue
        return queue
    
    def disconnect(self, jetson_id: str) -> None:
        if jetson_id in self.active_connections:
            del self.active_connections[jetson_id]
    
    async def send_to_device(self, jetson_id: str, message: str) -> bool:
        if jetson_id not in self.active_connections:
            return False
        
        try:
            # Non-blocking put with timeout to prevent hangs
            await asyncio.wait_for(
                self.active_connections[jetson_id].put(message),
                timeout=1.0
            )
            return True
        except asyncio.TimeoutError:
            return False
        except Exception as e:
            return False
    
    def is_connected(self, jetson_id: str) -> bool:
        return jetson_id in self.active_connections
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)
    
    async def broadcast(self, message: str) -> int:
        sent_count = 0
        for jetson_id in list(self.active_connections.keys()):
            if await self.send_to_device(jetson_id, message):
                sent_count += 1
        return sent_count