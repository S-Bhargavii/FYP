import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple
import json
import os

class Map:
    """Represents a navigable map with landmarks and obstacles"""
    
    def __init__(self, map_path: str):
        """
        Initialize map from directory containing map files
        
        Args:
            map_path: Path to directory containing tile_id.xml, image.png, landmarks.json
        """
        self.map_id = os.path.basename(map_path)
        self.map_xml_path = os.path.join(map_path, "tile_id.xml")
        self.map_image_path = os.path.join(map_path, "image.png")
        self.map_landmarks_path = os.path.join(map_path, "landmarks.json")
        
        # Parse map data
        map_data, map_metadata = self._parse_tileset(self.map_xml_path)
        self.landmarks_mapping = self._parse_landmarks(self.map_landmarks_path)
        
        # Grid data
        self.grid: List[List[int]] = map_data["grid"]
        self.landmark_cells: Dict[int, List[Tuple[int, int]]] = map_data["landmark_cells"]
        
        # Tile dimensions
        self.tile_width: int = map_metadata["tile_width"]
        self.tile_height: int = map_metadata["tile_height"]
        
        # Map dimensions in tiles
        self.map_width_in_tiles: int = map_metadata["map_width_in_tiles"]
        self.map_height_in_tiles: int = map_metadata["map_height_in_tiles"]
        
        # Map dimensions in pixels
        self.map_width_in_px: int = map_metadata["map_width_in_px"]
        self.map_height_in_px: int = map_metadata["map_height_in_px"]
    
    def _parse_tileset(self, xml_file: str) -> Tuple[Dict, Dict]:
        """Parse XML tileset file"""
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        map_width_in_tiles = int(root.attrib["columns"])
        tile_count = int(root.attrib["tilecount"])
        tile_width = int(root.attrib["tilewidth"])
        tile_height = int(root.attrib["tileheight"])
        
        map_height_in_tiles = tile_count // map_width_in_tiles
        map_width_in_px = map_width_in_tiles * tile_width
        map_height_in_px = map_height_in_tiles * tile_height
        
        # Initialize grid
        grid = [[0 for _ in range(map_width_in_tiles)] for _ in range(map_height_in_tiles)]
        landmark_cells = defaultdict(list)
        
        # Parse tiles
        for tile in root.findall("tile"):
            tile_id = int(tile.attrib["id"])
            tile_type = int(tile.attrib.get("type", 0))
            
            x = tile_id % map_width_in_tiles
            y = tile_id // map_width_in_tiles
            
            # 0 = free space, 1 = obstacle, other = landmarks
            if tile_type not in (0, 1):
                landmark_cells[tile_type].append((x, y))
            
            grid[y][x] = tile_type
        
        map_data = {
            "grid": grid,
            "landmark_cells": dict(landmark_cells)
        }
        
        map_metadata = {
            "tile_width": tile_width,
            "tile_height": tile_height,
            "map_width_in_tiles": map_width_in_tiles,
            "map_height_in_tiles": map_height_in_tiles,
            "map_width_in_px": map_width_in_px,
            "map_height_in_px": map_height_in_px
        }
        
        return map_data, map_metadata
    
    def _parse_landmarks(self, json_file: str) -> Dict[str, int]:
        """Parse landmarks JSON file"""
        with open(json_file, "r") as f:
            return json.load(f)
    
    def get_goal_nodes(self, destination_landmark: str) -> List[Tuple[int, int]]:
        """
        Get grid cells for a landmark
        
        Args:
            destination_landmark: Name of the landmark
            
        Returns:
            List of (x, y) grid coordinates
        """
        landmark_id = self.landmarks_mapping.get(destination_landmark)
        if landmark_id is None:
            return []
        return self.landmark_cells.get(landmark_id, [])
    
    def get_goal_id(self, destination_landmark: str) -> int:
        """Get the numeric ID for a landmark"""
        return self.landmarks_mapping.get(destination_landmark, 0)
    
    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if grid position is valid and not an obstacle"""
        if not (0 <= x < self.map_width_in_tiles and 0 <= y < self.map_height_in_tiles):
            return False
        return self.grid[y][x] != 1  # 1 = obstacle
    
    def pixel_to_grid(self, px_x: float, px_y: float) -> Tuple[int, int]:
        """Convert pixel coordinates to grid coordinates"""
        grid_x = int(px_x // self.tile_width)
        grid_y = int(px_y // self.tile_height)
        return (grid_x, grid_y)
    
    def grid_to_pixel(self, grid_x: int, grid_y: int, center: bool = True) -> Tuple[int, int]:
        """
        Convert grid coordinates to pixel coordinates
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            center: If True, return center of tile; otherwise top-left corner
        """
        px_x = grid_x * self.tile_width
        px_y = grid_y * self.tile_height
        
        if center:
            px_x += self.tile_width // 2
            px_y += self.tile_height // 2
        
        return (px_x, px_y)