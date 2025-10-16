from fastapi import FastAPI, Depends, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import json
import logging

from config import get_settings
from models import (
    SessionRegistrationRequest,
    SessionRegistrationResponse,
    MapInfoResponse,
    RouteResponse,
    RouteType,
    CrowdDensityResponse,
    TerminationResponse,
    LocationUpdate
)
from dependencies import (
    get_auth_service,
    get_session_service,
    get_location_service,
    get_map_service,
    get_mqtt_service,
    get_jetson_id,
    get_map_id
)
from services.auth_service import AuthService
from services.session_service import SessionService
from services.location_service import LocationService
from services.map_service import MapService
from services.mqtt_service import MQTTService
from connection_manager import SSEConnectionManager
from exceptions import MapNotFoundException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global SSE connection manager
sse_manager = SSEConnectionManager()

# Store event loop for MQTT callbacks
main_event_loop = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown"""
    global main_event_loop
    main_event_loop = asyncio.get_event_loop()
    
    # Startup
    logger.info("Starting navigation server...")
    
    # Initialize MQTT and register callbacks
    mqtt_service = get_mqtt_service()
    session_service = get_session_service()
    location_service = get_location_service()
    
    def on_pose_callback(jetson_id: str, payload: dict):
        """Handle pose updates from devices"""
        try:
            # Update location in Redis
            location = LocationUpdate(**payload)
            location_service.update_location(jetson_id, location)
            
            # Send to SSE connection
            asyncio.run_coroutine_threadsafe(
                sse_manager.send_to_device(jetson_id, json.dumps(payload)),
                main_event_loop
            )
        except Exception as e:
            logger.error(f"Error processing pose for {jetson_id}: {e}")
    
    mqtt_service.register_pose_callback(on_pose_callback)
    
    logger.info("Server started successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down server...")
    mqtt_service.disconnect()
    logger.info("Server shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Indoor Navigation API",
    description="API for indoor navigation system with crowd-aware pathfinding",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

############ API ENDPOINTS #################

@app.post("/api/v1/register", response_model=SessionRegistrationResponse)
async def register_session(
    request: SessionRegistrationRequest,
    auth_service: AuthService = Depends(get_auth_service),
    session_service: SessionService = Depends(get_session_service),
    map_service: MapService = Depends(get_map_service),
    mqtt_service: MQTTService = Depends(get_mqtt_service)
):
    """
    Register a new device session
    
    Creates a session, loads the map, and sends initial commands to device
    """
    logger.info(f"Registration request: {request.jetson_id} -> {request.map_id}")
    
    # Load map (will raise exception if not found)
    map_service.load_map(request.map_id, session_service)
    
    # Create JWT token
    token = auth_service.create_token(request.jetson_id, request.map_id)
    
    # Create session in Redis
    session_service.create_session(request.jetson_id, request.map_id, token)
    
    # Send load map command to device
    mqtt_service.send_load_map_command(request.jetson_id, request.map_id)
    
    logger.info(f"Session registered successfully for {request.jetson_id}")
    
    return SessionRegistrationResponse(token=token)

@app.get("/api/v1/map-info", response_model=MapInfoResponse)
async def get_map_info(
    map_id: str = Depends(get_map_id),
    map_service: MapService = Depends(get_map_service)
):
    """Get map metadata and configuration"""
    map_obj = map_service.get_map(map_id)
    
    if not map_obj:
        raise MapNotFoundException(map_id)
    
    return MapInfoResponse(
        map_width_in_px=map_obj.map_width_in_px,
        map_height_in_px=map_obj.map_height_in_px,
        tile_height=map_obj.tile_height,
        tile_width=map_obj.tile_width,
        landmarks_mapping=map_obj.landmarks_mapping
    )

@app.get("/api/v1/route", response_model=RouteResponse)
async def get_route(
    destination: str = Query(..., description="Destination landmark name"),
    route_type: RouteType = Query(RouteType.FAST, description="Route optimization type"),
    jetson_id: str = Depends(get_jetson_id),
    map_id: str = Depends(get_map_id),
    map_service: MapService = Depends(get_map_service),
    location_service: LocationService = Depends(get_location_service)
):
    """
    Calculate optimal route to destination
    
    Supports both fast routes and crowd-avoiding routes
    """
    logger.info(f"Route request: {jetson_id} -> {destination} ({route_type})")
    
    # Get map and path planner
    map_obj = map_service.get_map(map_id)
    path_planner = map_service.get_path_planner(map_id)
    
    if not map_obj or not path_planner:
        raise MapNotFoundException(map_id)
    
    # Get current location
    grid_location = location_service.get_grid_location(
        jetson_id,
        map_obj.tile_width,
        map_obj.tile_height
    )
    
    start = (grid_location.grid_x, grid_location.grid_y)
    
    # Calculate path
    path = path_planner.find_optimal_path(start, destination, route_type)
    
    logger.info(f"Path calculated: {len(path)} waypoints")
    
    return RouteResponse(path=path)

@app.get("/api/v1/crowd-heatmap", response_model=CrowdDensityResponse)
async def get_crowd_heatmap(
    map_id: str = Depends(get_map_id),
    map_service: MapService = Depends(get_map_service)
):
    """Get current crowd density heatmap for the map"""
    path_planner = map_service.get_path_planner(map_id)
    
    if not path_planner:
        raise MapNotFoundException(map_id)
    
    density_grid = path_planner.compute_crowd_density(for_heatmap=True)
    
    return CrowdDensityResponse(density_grid=density_grid)

@app.get("/api/v1/sse")
async def sse_stream(jetson_id: str = Depends(get_jetson_id)):
    """
    Server-Sent Events endpoint for real-time position updates
    
    Maintains a persistent connection to stream location updates
    """
    logger.info(f"SSE connection requested for {jetson_id}")
    
    queue = sse_manager.connect(jetson_id)
    
    async def event_generator():
        try:
            while True:
                message = await queue.get()
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for {jetson_id}")
        finally:
            sse_manager.disconnect(jetson_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@app.delete("/api/v1/session", response_model=TerminationResponse)
async def terminate_session(
    jetson_id: str = Depends(get_jetson_id),
    session_service: SessionService = Depends(get_session_service),
    location_service: LocationService = Depends(get_location_service),
    mqtt_service: MQTTService = Depends(get_mqtt_service)
):
    """Terminate an active session and cleanup resources"""
    logger.info(f"Termination requested for {jetson_id}")
    
    # Send shutdown command
    mqtt_service.send_shutdown_command(jetson_id)
    
    # Cleanup
    session_service.delete_session(jetson_id)
    location_service.delete_location(jetson_id)
    sse_manager.disconnect(jetson_id)
    
    logger.info(f"Session terminated for {jetson_id}")
    
    return TerminationResponse()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": sse_manager.get_connection_count()
    }

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )