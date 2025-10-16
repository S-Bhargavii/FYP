import heapq
import time
from typing import List, Tuple, Dict, Optional
import redis
from map import Map
from models import RouteType
import logging

logger = logging.getLogger(__name__)

class PathPlanner:
    def __init__(self, map: Map, redis_client: redis.Redis, session_service):
        self.redis = redis_client
        self.session_service = session_service
        self.map = map
    
    def compute_crowd_density(self, for_heatmap: bool = False) -> Dict:
        """Compute crowd density across the map grid"""
        from services.location_service import LocationService
        from config import get_settings
        
        settings = get_settings()
        location_service = LocationService(self.redis, settings)
        
        # Get all active locations for this map
        active_locations = location_service.get_all_active_locations(
            self.map.map_id,
            self.session_service
        )
        
        grid_density = {}
        
        for x, y, timestamp in active_locations:
            # Skip stale locations
            if (time.time() - timestamp) > settings.location_ttl_seconds:
                continue
            
            grid_x = int(x // self.map.tile_width)
            grid_y = int(y // self.map.tile_height)
            grid_key = (grid_x, grid_y)
            
            grid_density[grid_key] = grid_density.get(grid_key, 0) + 1
        
        # Normalize density scores
        max_density = max(grid_density.values(), default=1)
        normalized_density = {}
        
        for (grid_x, grid_y), count in grid_density.items():
            density_score = count / max_density
            
            if for_heatmap:
                key_str = f"({grid_x},{grid_y})"
                normalized_density[key_str] = density_score
            else:
                normalized_density[(grid_x, grid_y)] = density_score
        
        return normalized_density
    
    def find_optimal_path(
        self,
        start: Tuple[int, int],
        destination_landmark: str,
        route_type: RouteType
    ) -> List[Tuple[int, int]]:
        """Find the optimal path from start to destination"""
        goal_nodes = self.map.get_goal_nodes(destination_landmark)
        
        if not goal_nodes:
            logger.warning(f"No goal nodes found for landmark: {destination_landmark}")
            return []
        
        # Get crowd density if needed
        density_grid = {}
        if route_type == RouteType.LESS_CROWD:
            density_grid = self.compute_crowd_density(for_heatmap=False)
        
        best_path = None
        best_cost = float('inf')
        
        for goal in goal_nodes:
            path = self._theta_star(start, goal, destination_landmark, density_grid, route_type)
            
            if path and len(path) < best_cost:
                best_path = path
                best_cost = len(path)
        
        return best_path or []
    
    def _theta_star(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        landmark: str,
        density_grid: Dict,
        route_type: RouteType
    ) -> List[Tuple[int, int]]:
        """Theta* pathfinding algorithm with any-angle paths"""
        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {start: start}
        g_score = {start: 0}
        
        goal_id = self.map.get_goal_id(landmark)
        
        while open_set:
            current = heapq.heappop(open_set)[1]
            
            if current == goal:
                return self._reconstruct_path(came_from, current)
            
            for neighbour in self._get_neighbours(current):
                grid_value = self.map.grid[neighbour[1]][neighbour[0]]
                
                # Skip obstacles
                if grid_value != 0 and grid_value != goal_id:
                    continue
                
                parent = came_from.get(current, current)
                
                # Try line-of-sight to parent
                if self._has_line_of_sight(parent, neighbour, goal_id):
                    tentative_g = g_score[parent] + self._compute_cost(
                        parent, neighbour, density_grid, route_type
                    )
                    candidate_parent = parent
                else:
                    tentative_g = g_score[current] + self._compute_cost(
                        current, neighbour, density_grid, route_type
                    )
                    candidate_parent = current
                
                if neighbour not in g_score or tentative_g < g_score[neighbour]:
                    g_score[neighbour] = tentative_g
                    came_from[neighbour] = candidate_parent
                    f_score = tentative_g + self._heuristic(neighbour, goal)
                    heapq.heappush(open_set, (f_score, neighbour))
        
        return []
    
    def _get_neighbours(self, node: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Get all 8-connected neighbours"""
        x, y = node
        directions = [
            (-1, 0), (1, 0), (0, -1), (0, 1),
            (-1, -1), (-1, 1), (1, -1), (1, 1)
        ]
        neighbours = []
        
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.map.map_width_in_tiles and 0 <= ny < self.map.map_height_in_tiles:
                neighbours.append((nx, ny))
        
        return neighbours
    
    def _has_line_of_sight(
        self,
        node1: Tuple[int, int],
        node2: Tuple[int, int],
        goal_id: int
    ) -> bool:
        """Check if there's clear line of sight between two nodes"""
        for x, y in self._bresenham_line(node1, node2):
            grid_value = self.map.grid[y][x]
            if grid_value != 0 and grid_value != goal_id:
                return False
        return True
    
    def _compute_cost(
        self,
        node1: Tuple[int, int],
        node2: Tuple[int, int],
        density_grid: Dict,
        route_type: RouteType
    ) -> float:
        """Compute cost between two nodes including crowd density"""
        base_cost = self._euclidean_distance(node1, node2)
        
        if route_type != RouteType.LESS_CROWD:
            return base_cost
        
        # Add density penalty along the path
        density_penalty = 0
        for x, y in self._bresenham_line(node1, node2):
            density_penalty += density_grid.get((x, y), 0) * 10
        
        return base_cost + density_penalty
    
    @staticmethod
    def _heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Euclidean distance heuristic"""
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    
    @staticmethod
    def _euclidean_distance(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Euclidean distance between two points"""
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    
    @staticmethod
    def _bresenham_line(
        node1: Tuple[int, int],
        node2: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Bresenham's line algorithm"""
        x0, y0 = node1
        x1, y1 = node2
        cells = []
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                cells.append((x, y))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                cells.append((x, y))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        
        cells.append((x1, y1))
        return cells
    
    def _reconstruct_path(
        self,
        came_from: Dict,
        current: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Reconstruct path from came_from dict and interpolate to pixels"""
        waypoints = []
        
        # Backtrack to get waypoints
        while current in came_from and came_from[current] != current:
            waypoints.append(current)
            current = came_from[current]
        waypoints.append(current)
        waypoints.reverse()
        
        # Convert grid coordinates to pixel coordinates and interpolate
        pixel_path = []
        for i in range(len(waypoints) - 1):
            x1 = waypoints[i][0] * self.map.tile_width + self.map.tile_width // 2
            y1 = waypoints[i][1] * self.map.tile_height + self.map.tile_height // 2
            x2 = waypoints[i + 1][0] * self.map.tile_width + self.map.tile_width // 2
            y2 = waypoints[i + 1][1] * self.map.tile_height + self.map.tile_height // 2
            
            segment = self._interpolate_line((x1, y1), (x2, y2))
            
            # Avoid duplicating junction points
            if i > 0:
                segment = segment[1:]
            
            pixel_path.extend(segment)
        
        return pixel_path
    
    @staticmethod
    def _interpolate_line(
        p1: Tuple[int, int],
        p2: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """Interpolate points between two pixels using Bresenham"""
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