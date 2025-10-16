import json
from typing import Optional
import redis
from config import Settings
from exceptions import SessionNotFoundException, SessionAlreadyExistsException

class SessionService:
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings
        self.session_prefix = settings.redis_session_prefix
    
    def _session_key(self, jetson_id: str) -> str:
        return f"{self.session_prefix}:{jetson_id}"
    
    def create_session(self, jetson_id: str, map_id: str, token: str) -> None:
        """Create a new session in Redis"""
        session_key = self._session_key(jetson_id)
        
        if self.redis.exists(session_key):
            raise SessionAlreadyExistsException()
        
        session_data = {
            "jetson_id": jetson_id,
            "map_id": map_id,
            "token": token,
            "created_at": str(self._get_current_time())
        }
        
        # Store with expiration matching JWT expiration
        expiration = self.settings.jwt_expiration_hours * 3600
        self.redis.setex(
            session_key,
            expiration,
            json.dumps(session_data)
        )
    
    def get_session(self, jetson_id: str) -> dict:
        """Retrieve session data"""
        session_key = self._session_key(jetson_id)
        session_json = self.redis.get(session_key)
        
        if not session_json:
            raise SessionNotFoundException()
        
        return json.loads(session_json)
    
    def delete_session(self, jetson_id: str) -> None:
        """Delete a session"""
        session_key = self._session_key(jetson_id)
        self.redis.delete(session_key)
    
    def session_exists(self, jetson_id: str) -> bool:
        """Check if session exists"""
        session_key = self._session_key(jetson_id)
        return self.redis.exists(session_key) > 0
    
    def get_map_id(self, jetson_id: str) -> str:
        """Get map_id for a session"""
        session = self.get_session(jetson_id)
        return session["map_id"]
    
    @staticmethod
    def _get_current_time():
        from datetime import datetime
        return datetime.utcnow()