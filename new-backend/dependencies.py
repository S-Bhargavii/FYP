from fastapi import Depends, Header
from typing import Optional
import redis
from config import get_settings, Settings
from services.auth_service import AuthService
from services.session_service import SessionService
from services.location_service import LocationService
from services.map_service import MapService
from services.mqtt_service import MQTTService
from exceptions import UnauthorizedException

# Singleton instances
_redis_client = None
_mqtt_service = None
_map_service = None

def get_redis_client() -> redis.Redis:
    """Get Redis client singleton"""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
    return _redis_client

def get_mqtt_service() -> MQTTService:
    """Get MQTT service singleton"""
    global _mqtt_service
    if _mqtt_service is None:
        settings = get_settings()
        _mqtt_service = MQTTService(settings)
        _mqtt_service.connect()
    return _mqtt_service

def get_map_service(
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings)
) -> MapService:
    """Get Map service singleton"""
    global _map_service
    if _map_service is None:
        _map_service = MapService(redis_client, settings)
    return _map_service

def get_auth_service(settings: Settings = Depends(get_settings)) -> AuthService:
    """Get Auth service"""
    return AuthService(settings)

def get_session_service(
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings)
) -> SessionService:
    """Get Session service"""
    return SessionService(redis_client, settings)

def get_location_service(
    redis_client: redis.Redis = Depends(get_redis_client),
    settings: Settings = Depends(get_settings)
) -> LocationService:
    """Get Location service"""
    return LocationService(redis_client, settings)

def get_current_jetson(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """Extract and verify JWT token from Authorization header"""
    if not authorization:
        raise UnauthorizedException()
    
    # Expected format: "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise UnauthorizedException()
    
    token = parts[1]
    payload = auth_service.verify_token(token)
    
    return payload

def get_jetson_id(current_jetson: dict = Depends(get_current_jetson)) -> str:
    """Get jetson_id from verified token"""
    return current_jetson["jetson_id"]

def get_map_id(current_jetson: dict = Depends(get_current_jetson)) -> str:
    """Get map_id from verified token"""
    return current_jetson["map_id"]