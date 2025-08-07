import xml.etree.ElementTree as ET
from collections import defaultdict
import json

def parse_tileset(xml_file: str):
    tree  = ET.parse(xml_file)
    root = tree.getroot()

    map_width_in_tiles = int(root.attrib["columns"])
    map_height_in_tiles = int(root.attrib["tilecount"]) // map_width_in_tiles

    tile_width = int(root.attrib["tilewidth"])
    tile_height = int(root.attrib["tileheight"])

    map_height_in_px = map_height_in_tiles * tile_height;
    map_width_in_px = map_width_in_tiles * tile_width;

    grid = grid = [[None for _ in range(map_width_in_tiles)] for _ in range(map_height_in_tiles)] # map grid
    landmark_cells = defaultdict(list) # landmark_id --> array of (x,y) on the grid where the landmark is placed 

    for tile in root.findall("tile"):
        tile_id = int(tile.attrib['id'])
        tile_type = int(tile.attrib.get("type", 0))

        x = tile_id % map_width_in_tiles
        y = tile_id // map_width_in_tiles

        if tile_type != 0 and tile_type != 1:
            # 0 means free and 1 means obstacle while 
            # the other ids represent landmarks
            landmark_cells[tile_type].append((x,y))

        grid[y][x] = tile_type
    
    map_data = {
        "grid":grid, 
        "landmark_cells":landmark_cells
    }
    map_metadata = {
        "tile_width": tile_width, 
        "tile_height": tile_height, 
        "map_width_in_tiles":map_width_in_tiles,
        "map_height_in_tiles":map_height_in_tiles, 
        "map_width_in_px": map_width_in_px, 
        "map_height_in_px":map_height_in_px
    }

    return map_data, map_metadata

def parse_landmarks_json(json_file:str):
    with open(json_file, "r") as f:
        landmark_mapping = json.load(f)

    return landmark_mapping

class Map:
    def __init__(self, map_id:str):
        self.map_xml_path = f"{map_id}/tile_id.xml"
        self.map_image_path = f"{map_id}/image.png"
        self.map_landmarks_path = f"{map_id}/landmarks.json"

        map_data, map_metadata = parse_tileset(self.map_xml_path)
        self.landmarks_mapping = parse_landmarks_json(self.map_landmarks_path)

        self.grid = map_data["grid"]
        self.landmark_cells = map_data["landmark_cells"]

        self.tile_width = map_metadata["tile_width"]
        self.tile_height = map_metadata["tile_height"]

        self.map_width_in_tiles = map_metadata["map_width_in_tiles"]
        self.map_height_in_tiles = map_metadata["map_height_in_tiles"]

        self.map_width_in_px = map_metadata["map_width_in_px"]
        self.map_height_in_px = map_metadata["map_height_in_px"]
    
    def get_goal_nodes(self, destination_landmark:str):
        return self.landmark_cells.get(self.landmarks_mapping[destination_landmark], [])

    def get_goal_id(self, destination_landmark:str):
        return self.landmarks_mapping[destination_landmark]


        
        