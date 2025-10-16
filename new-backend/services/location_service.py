import json
import time
from typing import List, Tuple, Dict
import redis
from config import Settings
from models import LocationUpdate, GridLocation
from exceptions import LocationNotFoundException

class LocationService:
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self.location_prefix = settings.redis_location_prefix
    
    def _location_key(self, jetson_id: str) -> str:
        return f"{self.location_prefix}:{jetson_id}"
    
    def update_location(self, jetson_id: str, location: LocationUpdate) -> None:
        """Update device location in Redis"""
        location_key = self._location_key(jetson_id)
        
        location_data = {
            "x": location.x,
            "y": location.y,
            "timestamp": location.timestamp or time.time()
        }
        
        # Set with TTL to auto-expire old locations
        self.redis.setex(
            location_key,
            self.settings.location_ttl_seconds * 2,  # 2x TTL for safety
            json.dumps(location_data)
        )
    
    def get_location(self, jetson_id: str) -> LocationUpdate:
        """Get current location for a device"""
        location_key = self._location_key(jetson_id)
        location_json = self.redis.get(location_key)
        
        if not location_json:
            raise LocationNotFoundException()
        
        location_data = json.loads(location_json)
        return LocationUpdate(**location_data)
    
    def get_grid_location(self, jetson_id: str, tile_width: int, tile_height: int) -> GridLocation:
        """Convert pixel location to grid coordinates"""
        location = self.get_location(jetson_id)
        
        grid_x = int(location.x // tile_width)
        grid_y = int(location.y // tile_height)
        
        return GridLocation(grid_x=grid_x, grid_y=grid_y)
    
    def get_all_active_locations(self, map_id: str, session_service) -> List[Tuple[int, int, float]]:
        """Get all active locations for devices on a specific map"""
        keys = self.redis.keys(f"{self.location_prefix}:*")
        active_locations = []
        
        current_time = time.time()
        
        for key in keys:
            jetson_id = key.decode().split(":")[-1]
            
            # Check if device is on the correct map
            try:
                device_map_id = session_service.get_map_id(jetson_id)
                if device_map_id != map_id:
                    continue
            except:
                continue
            
            location_data = json.loads(self.redis.get(key))
            timestamp = location_data["timestamp"]
            
            # Skip stale locations
            if (current_time - timestamp) > self.settings.location_ttl_seconds:
                continue
            
            active_locations.append((
                location_data["x"],
                location_data["y"],
                timestamp
            ))
        
        return active_locations
    
    def delete_location(self, jetson_id: str) -> None:
        """Delete location data"""
        location_key = self._location_key(jetson_id)
        self.redis.delete(location_key)