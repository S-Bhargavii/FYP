from typing import Dict, Optional
from map import Map
from path_planning import PathPlanner
from exceptions import MapNotFoundException
import redis
from config import Settings
import os

class MapService:
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self._maps: Dict[str, Map] = {}
        self._path_planners: Dict[str, PathPlanner] = {}
    
    def load_map(self, map_id: str, session_service) -> Map:
        """Load a map and create its path planner if not already loaded"""
        if map_id in self._maps:
            return self._maps[map_id]
        
        # Verify map exists
        map_path = os.path.join(self.settings.map_data_path, map_id)
        if not os.path.exists(map_path):
            raise MapNotFoundException(map_id)
        
        try:
            # Load map
            map_obj = Map(os.path.join(self.settings.map_data_path, map_id))
            self._maps[map_id] = map_obj
            
            # Create path planner
            path_planner = PathPlanner(map_obj, self.redis, session_service)
            self._path_planners[map_id] = path_planner
            
            return map_obj
        except Exception as e:
            raise MapNotFoundException(f"{map_id}: {str(e)}")
    
    def get_map(self, map_id: str) -> Optional[Map]:
        """Get a loaded map"""
        return self._maps.get(map_id)
    
    def get_path_planner(self, map_id: str) -> Optional[PathPlanner]:
        """Get path planner for a map"""
        return self._path_planners.get(map_id)
    
    def unload_map(self, map_id: str) -> None:
        """Unload a map if no active sessions"""
        # TODO: Add logic to check if any active sessions use this map
        if map_id in self._maps:
            del self._maps[map_id]
        if map_id in self._path_planners:
            del self._path_planners[map_id]
    
    def is_map_loaded(self, map_id: str) -> bool:
        """Check if map is loaded"""
        return map_id in self._maps