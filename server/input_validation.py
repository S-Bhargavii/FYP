from pydantic import BaseModel

class SessionRegistration(BaseModel):
    jetson_id : str
    map_id : str