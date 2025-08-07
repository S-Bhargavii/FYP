import xml.etree.ElementTree as ET
from collections import defaultdict
from fastapi import HTTPException
import redis
import json
import heapq
from constants import (
    MAP_PATH_DICTIONARY, MAP_LANDMARKS_DICTIONARY, 
    REDIS_LOCATION_PREFIX, MQTT_COMMANDS_TOPIC_PREFIX
)
import time
from maps import parse_tileset

class PathPlanner:
    def __init__(self, redis_client: redis.Redis, map_id: str, jetson_to_map):
        self.redis_client = redis_client
        self.map_id = map_id
        self.jetson_to_map = jetson_to_map
        self.map_path = MAP_PATH_DICTIONARY[map_id]
        self.landmarks = MAP_LANDMARKS_DICTIONARY[map_id]
        # landmark_cells is the landmark to cells mapping --> cells is an array comprising of the 
        # cells where the landmark is located at. 
        # obstructions --> list of obstructions
        # self.tile_dimensions --> (tile width in pixels, tile height in pixels)
        # self.grid_dimensions --> (number of columns , number of rows) in total grid
        self.landmark_cells, self.obstructions, self.grid, self.tile_dimensions, self.grid_dimensions = parse_tileset(self.map_path)

    def fetch_jetson_current_location(self, jetson_id):
        """
            Gets the grid co-ordinates where the user is located at.
        """
        print("Fetching current user location")
        user_location_key = f"{REDIS_LOCATION_PREFIX}:{jetson_id}"
        user_location_json = self.redis_client.get(user_location_key)

        if not user_location_json:
            raise HTTPException(status_code=404, detail="User location not found")

        user_location = json.loads(user_location_json)
        x, y = user_location["x"], user_location["y"]

        grid_x = int(x // self.tile_dimensions[0])
        grid_y = int(y // self.tile_dimensions[1])

        return (grid_x, grid_y)

    def compute_crowd_density(self, for_heatmap = False):
        keys = self.redis_client.keys(f"{REDIS_LOCATION_PREFIX}:*")
        grid_density = {}

        for key in keys:
            _, current_jetson_id = key.split(":")
            if self.jetson_to_map.get(current_jetson_id) != self.map_id:
                continue

            user_location_data = json.loads(self.redis_client.get(key))
            x, y, time_stamp = user_location_data["x"], user_location_data["y"], user_location_data["timestamp"]
            if (time.time() - time_stamp) > 5:
                # if the time at which the current user location is 
                # recorded is more than 5s skip it.
                continue
            grid_x = int(x // self.tile_dimensions[0])
            grid_y = int(y // self.tile_dimensions[1])
            grid_key = (grid_x, grid_y)

            grid_density[grid_key] = grid_density.get(grid_key, 0) + 1

        max_density = max(grid_density.values(), default=1)
        density_grid = {}

        for (grid_x, grid_y), count in grid_density.items():
            density_score = count / max_density
            if for_heatmap:
                key_str = f"({grid_x}, {grid_y})"
                density_grid[key_str] = density_score
            else:
                density_grid[(grid_x, grid_y)] = density_score

        print(density_grid)
        density_grid = {
            "(5,10)": 0.9,   # Very dense
            "(12,20)": 0.8,
            "(25,35)": 0.7,
            "(30,40)": 0.5,
            "(15,25)": 0.3,
            "(7,12)": 0.2,
            "(3,4)": 0.1,
            "(0,0)": 0.0,
            "(10,15)": 0.0,
            "(20,30)": 0.0,
        }

        return density_grid

    def find_nearest_path(self, start, destination_landmark: str, preference: str):
        best_path = None
        best_cost = float('inf')
        goal_nodes = self.landmark_cells.get(MAP_LANDMARKS_DICTIONARY[self.map_id][destination_landmark], [])

        if preference == "least_crowded":
            density_grid = self.compute_crowd_density(for_heatmap=False)
        else:
            density_grid = {}

        for goal in goal_nodes:
            path = self.a_star_path_finding(start, goal, destination_landmark, density_grid, preference)
            if path and len(path) < best_cost:
                best_path = path
                best_cost = len(path)

        return best_path or []

    def get_neighbours(self, current):
        x, y = current
        columns, rows = self.grid_dimensions
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbours = []

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < columns and 0 <= ny < rows:
                neighbours.append((nx, ny))
        return neighbours

    def reconstruct_path(self, came_from, current):
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            x_pixel = (current[0] * self.tile_dimensions[0]) + self.tile_dimensions[0]//2
            y_pixel = (current[1] * self.tile_dimensions[1]) + self.tile_dimensions[1]//2
            total_path.append((x_pixel, y_pixel))
        total_path.reverse()
        return total_path # [(x,y)] --> grid lo centre pixel oka value kindha maarchemu

    def a_star_path_finding(self, start, goal, landmark, density_grid, preference):
        print("running a*")
        open_set = []
        heapq.heappush(open_set, (0,start))
        came_from = {} # to retrace path
        g_score = {start: 0}

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == goal:
                return self.reconstruct_path(came_from, current)

            neighbours = self.get_neighbours(current)

            for neighbour in neighbours:
                grid_value = self.grid[neighbour[1]][neighbour[0]]
                if grid_value != 0 and grid_value != MAP_LANDMARKS_DICTIONARY[self.map_id][landmark]:
                    continue

                tentative_g_score = g_score[current] + 1

                if preference == "least_crowded":
                    density_cost = density_grid.get(neighbour, 0)
                    tentative_g_score += density_cost * 10

                if neighbour not in g_score or tentative_g_score < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbour, goal)
                    heapq.heappush(open_set, (f_score, neighbour))

        return []
