import json
import paho.mqtt.client as mqtt
from typing import Callable, Optional
from config import Settings
import logging

logger = logging.getLogger(__name__)

class MQTTService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Optional[mqtt.Client] = None
        self._pose_callback: Optional[Callable] = None
    
    def connect(self) -> None:
        """Connect to MQTT broker"""
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        try:
            self.client.connect(
                self.settings.mqtt_broker,
                self.settings.mqtt_port,
                60
            )
            self.client.loop_start()
            logger.info(f"Connected to MQTT broker at {self.settings.mqtt_broker}:{self.settings.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from MQTT broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Disconnected from MQTT broker")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for when connected to broker"""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
            # Subscribe to pose updates
            topic = f"{self.settings.mqtt_pose_topic_prefix}/#"
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for when disconnected from broker"""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection: {rc}")
    
    def register_pose_callback(self, callback: Callable) -> None:
        """Register callback for pose messages"""
        self._pose_callback = callback
        
        def on_pose_message(client, userdata, msg):
            try:
                topic_parts = msg.topic.split("/")
                jetson_id = topic_parts[-1]
                
                payload_str = msg.payload.decode()
                payload = json.loads(payload_str)
                
                if self._pose_callback:
                    self._pose_callback(jetson_id, payload)
            except Exception as e:
                logger.error(f"Error processing pose message: {e}")
        
        pose_topic = f"{self.settings.mqtt_pose_topic_prefix}/#"
        self.client.message_callback_add(pose_topic, on_pose_message)
    
    def send_command(self, jetson_id: str, action: str, **kwargs) -> None:
        """Send a command to a specific device"""
        topic = f"{self.settings.mqtt_commands_topic_prefix}/{jetson_id}"
        
        payload = {
            "action": action,
            **kwargs
        }
        
        self.client.publish(topic, json.dumps(payload))
        logger.info(f"Sent command '{action}' to {jetson_id}")
    
    def send_load_map_command(self, jetson_id: str, map_id: str) -> None:
        """Send load map command to device"""
        self.send_command(jetson_id, "load_map", map_id=map_id)
    
    def send_shutdown_command(self, jetson_id: str) -> None:
        """Send shutdown command to device"""
        self.send_command(jetson_id, "shutdown")