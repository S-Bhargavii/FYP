import xml.etree.ElementTree as ET
from collections import defaultdict

# 0 --> free
# 1 --> obstacle 
# 2,3,4,5.... --> landmark --> also should be treated as obstacles 

def parse_tileset(xml_file: str):
    tree  = ET.parse(xml_file)
    root = tree.getroot()

    landmark_cells = defaultdict(list) # landmark_id --> array of (x,y) on the grid where the landmark is placed 
    obstructions = set()
    columns = int(root.attrib["columns"])
    rows = int(root.attrib["tilecount"]) // columns
    grid = {}

    tile_width, tile_height = int(root.attrib["tilewidth"]), int(root.attrib["tileheight"])

    for tile in root.findall("tile"):
        tile_id = int(tile.attrib['id'])
        tile_type = int(tile.attrib.get("type", 0))

        x = tile_id % columns
        y = tile_id // columns

        if tile_type!=0:
            obstructions.add((x,y))
        if tile_type >= 2:
            landmark_cells[tile_type].append((x,y))

        grid[x][y] = tile_type
    
    return landmark_cells, obstructions, grid, (tile_width, tile_height), (columns, rows)