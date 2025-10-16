from pydantic import BaseModel, Field, validator
from typing import Optional, Tuple, Dict, List
from enum import Enum

class RouteType(str, Enum):
    FAST = "fast"
    LESS_CROWD = "less_crowd"

class SessionRegistrationRequest(BaseModel):
    jetson_id: str = Field(..., min_length=1, description="Unique device identifier")
    map_id: str = Field(..., min_length=1, description="Map identifier")

class SessionRegistrationResponse(BaseModel):
    token: str
    message: str = "Registration successful"

class MapInfoResponse(BaseModel):
    map_width_in_px: int
    map_height_in_px: int
    tile_height: int
    tile_width: int
    landmarks_mapping: Dict[str, int]

class LocationUpdate(BaseModel):
    x: float
    y: float
    timestamp: Optional[float] = None

class GridLocation(BaseModel):
    grid_x: int
    grid_y: int

class RouteRequest(BaseModel):
    route_type: RouteType
    destination: str

class RouteResponse(BaseModel):
    path: List[Tuple[int, int]]
    distance: Optional[float] = None

class CrowdDensityResponse(BaseModel):
    density_grid: Dict[str, float]

class TerminationResponse(BaseModel):
    message: str = "Termination successful"

class MQTTCommand(BaseModel):
    action: str
    map_id: Optional[str] = None
    payload: Optional[Dict] = None