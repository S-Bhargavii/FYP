from fastapi import HTTPException
import redis
import json
import heapq
from constants import (
    REDIS_LOCATION_PREFIX
)
import time
from map import Map

class PathPlanner:
    def __init__(self, map: Map, redis_client: redis.Redis, jetson_to_map):
        self.redis_client = redis_client
        self.jetson_to_map = jetson_to_map
        self.map = map

    def fetch_jetson_current_location(self, jetson_id):
        """
            Gets the grid co-ordinates where the user is located at.
        """
        user_location_key = f"{REDIS_LOCATION_PREFIX}:{jetson_id}"
        user_location_json = self.redis_client.get(user_location_key)

        if not user_location_json:
            raise HTTPException(status_code=404, detail="User location not found")

        user_location = json.loads(user_location_json)
        x, y = user_location["x"], user_location["y"]

        grid_x = int(x // self.map.tile_width)
        grid_y = int(y // self.map.tile_height)

        return (grid_x, grid_y)

    def compute_crowd_density(self, for_heatmap = False):
        keys = self.redis_client.keys(f"{REDIS_LOCATION_PREFIX}:*")
        grid_density = {}

        for key in keys:
            _, current_jetson_id = key.split(":")
            if self.jetson_to_map.get(current_jetson_id) != self.map.map_id:
                continue

            user_location_data = json.loads(self.redis_client.get(key))
            x, y, time_stamp = user_location_data["x"], user_location_data["y"], user_location_data["timestamp"]
            if (time.time() - time_stamp) > 5:
                # if the time at which the current user location is 
                # recorded is more than 5s skip it.
                continue
            grid_x = int(x // self.map.tile_width)
            grid_y = int(y // self.map.tile_height)
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

        return density_grid

    def find_nearest_path(self, start, destination_landmark: str, route_type: str):
        # route_type can be less_crowd or fast
        best_path = None
        best_cost = float('inf')
        goal_nodes = self.map.get_goal_nodes(destination_landmark)

        if route_type == "less_crowd":
            density_grid = self.compute_crowd_density(for_heatmap=False)
        else:
            density_grid = {}

        for goal in goal_nodes:
            # path = self.a_star_path_finding(start, goal, destination_landmark, density_grid, route_type)
            path = self.theta_star_path_finding(start, goal, destination_landmark, density_grid, route_type)
            if path and len(path) < best_cost:
                best_path = path
                best_cost = len(path)

        return best_path or []

    def interpolate_line(self,p1, p2):
        """Return list of integer grid points between p1 and p2 using Bresenham."""
        x1, y1 = p1
        x2, y2 = p2
        points = []
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        x, y = x1, y1
        sx = 1 if x2 > x1 else -1
        sy = 1 if y2 > y1 else -1
        if dx > dy:
            err = dx / 2.0
            while x != x2:
                points.append((x, y))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y2:
                points.append((x, y))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        points.append((x2, y2))
        return points


    def get_neighbours(self, current):
        x, y = current
        columns, rows = self.map.map_width_in_tiles, self.map.map_height_in_tiles

        # explore all 8 dimensions
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        neighbours = []

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < columns and 0 <= ny < rows:
                neighbours.append((nx, ny))
        return neighbours

    # def reconstruct_path(self, came_from, current): --> can remove
    #     total_path = [current]

    #     while current in came_from:
    #         current = came_from[current]
    #         x_pixel = (current[0] * self.map.tile_width) + self.map.tile_width//2
    #         y_pixel = (current[1] * self.map.tile_height) + self.map.tile_height//2
    #         total_path.append((x_pixel, y_pixel))
            
    #     total_path.reverse()
    #     return total_path # [(x,y)] --> grid lo centre pixel oka value kindha maarchemu

    # def reconstruct_path(self, came_from, current):
    #     total_path = []
    #     while current in came_from and came_from[current] != current:
    #         x_pixel = (current[0] * self.map.tile_width) + self.map.tile_width//2
    #         y_pixel = (current[1] * self.map.tile_height) + self.map.tile_height//2
    #         total_path.append((x_pixel, y_pixel))
    #         current = came_from[current]

    #     # add the start node
    #     x_pixel = (current[0] * self.map.tile_width) + self.map.tile_width//2
    #     y_pixel = (current[1] * self.map.tile_height) + self.map.tile_height//2
    #     total_path.append((x_pixel, y_pixel))

    #     total_path.reverse()
    #     return total_path

    def reconstruct_path(self, came_from, current):
        path = []
        points = []

        # backtrack to get waypoints
        while current in came_from and came_from[current] != current:
            path.append(current)
            current = came_from[current]
        path.append(current)
        path.reverse()

        # interpolate between waypoints
        for i in range(len(path) - 1):
            x1 = (path[i][0] * self.map.tile_width) + self.map.tile_width//2
            y1 = (path[i][1] * self.map.tile_height) + self.map.tile_height//2
            x2 = (path[i+1][0] * self.map.tile_width) + self.map.tile_width//2
            y2 = (path[i+1][1] * self.map.tile_height) + self.map.tile_height//2

            segment = self.interpolate_line((x1, y1), (x2, y2))
            if i > 0:
                segment = segment[1:]  # avoid duplicating junction point
            points.extend(segment)

        return points

    def a_star_path_finding(self, start, goal, landmark, density_grid, route_type):
        open_set = []
        heapq.heappush(open_set, (0,start))
        came_from = {} # to retrace path
        g_score = {start: 0}
        goal_id = self.map.get_goal_id(landmark)

        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == goal:
                return self.reconstruct_path(came_from, current)

            neighbours = self.get_neighbours(current)

            for neighbour in neighbours:
                grid_value = self.map.grid[neighbour[1]][neighbour[0]]
                if grid_value != 0 and grid_value != goal_id:
                    continue

                tentative_g_score = g_score[current] + 1

                if route_type == "less_crowd":
                    density_cost = density_grid.get(neighbour, 0)
                    tentative_g_score += density_cost * 10

                if neighbour not in g_score or tentative_g_score < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbour, goal)
                    heapq.heappush(open_set, (f_score, neighbour))

        return []

    def theta_star_path_finding(self, start, goal, landmark, density_grid, route_type):
        print("Calling theta star path finding")
        import heapq

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {start: start}  # parent of start is itself
        g_score = {start: 0}

        def heuristic(a, b):
            # Euclidean distance heuristic
            return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

        def distance(a, b):
            # Euclidean distance between two grid nodes
            return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5

        def line_of_sight(node1, node2):
            # Bresenham's line algorithm
            x0, y0 = node1
            x1, y1 = node2
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            sx = 1 if x1 > x0 else -1
            sy = 1 if y1 > y0 else -1
            err = dx - dy
            x, y = x0, y0

            while (x, y) != (x1, y1):
                if self.map.grid[y][x] != 0 and self.map.grid[y][x] != self.map.get_goal_id(landmark):
                    return False
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x += sx
                if e2 < dx:
                    err += dx
                    y += sy
            return True

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == goal:
                path = self.reconstruct_path(came_from, current)
                print(path)
                return path

            for neighbour in self.get_neighbours(current):
                grid_value = self.map.grid[neighbour[1]][neighbour[0]]
                if grid_value != 0 and grid_value != self.map.get_goal_id(landmark):
                    continue

                parent = came_from.get(current, current)

                if line_of_sight(parent, neighbour):
                    tentative_g_score = g_score[parent] + distance(parent, neighbour)
                    candidate_parent = parent
                else:
                    tentative_g_score = g_score[current] + distance(current, neighbour)
                    candidate_parent = current

                # Add crowd-density cost
                if route_type == "less_crowd":
                    density_cost = density_grid.get(neighbour, 0)
                    tentative_g_score += density_cost * 10

                if neighbour not in g_score or tentative_g_score < g_score[neighbour]:
                    g_score[neighbour] = tentative_g_score
                    came_from[neighbour] = candidate_parent
                    f_score = tentative_g_score + heuristic(neighbour, goal)
                    heapq.heappush(open_set, (f_score, neighbour))

        return []
