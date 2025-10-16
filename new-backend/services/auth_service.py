from datetime import datetime, timedelta
from typing import Optional
import jwt
from config import Settings
from exceptions import UnauthorizedException

class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def create_token(self, jetson_id: str, map_id: str) -> str:
        """Create a JWT token for a device session"""
        expiration = datetime.utcnow() + timedelta(hours=self.settings.jwt_expiration_hours)
        
        payload = {
            "jetson_id": jetson_id,
            "map_id": map_id,
            "exp": expiration,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )
        
        return token
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnauthorizedException()
        except jwt.InvalidTokenError:
            raise UnauthorizedException()
    
    def get_jetson_id(self, token: str) -> str:
        """Extract jetson_id from token"""
        payload = self.verify_token(token)
        return payload.get("jetson_id")
    
    def get_map_id(self, token: str) -> str:
        """Extract map_id from token"""
        payload = self.verify_token(token)
        return payload.get("map_id")