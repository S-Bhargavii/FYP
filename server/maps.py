import xml.etree.ElementTree as ET
from collections import defaultdict

# 0 --> free
# 1 --> obstacle 
# 2,3,4,5.... --> landmark --> also should be treated as obstacles 
LANDMARK_MAPPING = {
    2: "Join or Die : An Americal Army Takes Shape Boston, 1775",
    3: "King George's Statue",
    4 : "Chain Of States",
    5: "Independence Theatre",
    6 : "The War Begins, 1775",
    7: "Boston's Liberty Tree",
    8: "Prologue: Tearing Down The King",
    9: "The Price Of Victory"
}

def parse_tileset(xml_file: str):
    tree  = ET.parse(xml_file)
    root = tree.getroot()

    landmark_cells = defaultdict(list) # landmark_id --> array of (x,y) on the grid where the landmark is placed 
    obstructions = set()
    columns = int(root.attrib["columns"])
    rows = int(root.attrib["tilecount"]) // columns

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
    
    return landmark_cells, obstructions, (tile_width, tile_height), (rows, columns)