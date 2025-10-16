from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # MQTT Configuration
    mqtt_broker: str = "broker.hivemq.com"
    mqtt_port: int = 1883
    mqtt_commands_topic_prefix: str = "/commands"
    mqtt_pose_topic_prefix: str = "/pose"
    
    # Redis Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_location_prefix: str = "user_location"
    redis_session_prefix: str = "session"
    
    # JWT Configuration
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # Application Configuration
    location_ttl_seconds: int = 5
    map_data_path: str = "./maps"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()