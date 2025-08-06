# MQTT constants
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_COMMANDS_TOPIC_PREFIX = "/commands"
MQTT_POSE_TOPIC_PREFIX = "/pose"

# REDIS constants 
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_LOCATION_PREFIX = "user_location"

# contains the mapping from the map_id to the corresponding xml file
MAP_PATH_DICTIONARY = {
    "map_01" : "map_01.xml"
}

# contains the mapping from the map_id to the landmarks and ids
MAP_LANDMARKS_DICTIONARY = {
    "map_01": {
        "Join or Die : An Americal Army Takes Shape Boston, 1775": 2,
        "King George's Statue": 3,
        "Chain Of States": 4,
        "Independence Theatre": 5,
        "The War Begins, 1775": 6,
        "Boston's Liberty Tree": 7,
        "Prologue: Tearing Down The King": 8,
        "The Price Of Victory": 9
    }
}