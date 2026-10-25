"""
Pathfinding and Emergency Optimization Algorithms.
Includes:
- Custom Dijkstra's Algorithm with Step Tracing & Multi-Criteria Risk Weighting
- NetworkX Standard Dijkstra Benchmark
- A* Heuristic Search (Euclidean Distance Heuristic)
- Multi-Destination Triage Routing (Nearest Hospital / Shelter)
- Dynamic Obstacle Detour Re-Routing
"""

import heapq
import math
import time
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional


class AlgorithmResult:
    """Encapsulates the result metrics of a pathfinding query."""

    def __init__(
        self,
        algorithm_name: str,
        path: List[str],
        total_cost: float,
        physical_distance: float,
        average_hazard: float,
        execution_time_us: float,
        nodes_explored_count: int,
        visited_order: List[str],
        success: bool = True,
        error_message: str = ""
    ):
        self.algorithm_name = algorithm_name
        self.path = path
        self.total_cost = round(total_cost, 2)
        self.physical_distance = round(physical_distance, 2)
        self.average_hazard = round(average_hazard, 2)
        self.execution_time_us = round(execution_time_us, 2)
        self.nodes_explored_count = nodes_explored_count
        self.visited_order = visited_order
        self.success = success
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm_name,
            "success": self.success,
            "path": self.path,
            "path_length": len(self.path),
            "total_cost": self.total_cost,
            "physical_distance_km": self.physical_distance,
            "average_hazard_index": self.average_hazard,
            "execution_time_us": self.execution_time_us,
            "nodes_explored": self.nodes_explored_count,
            "error": self.error_message
        }


def custom_dijkstra(
    graph: nx.Graph,
    source: str,
    target: str,
    vehicle_terrain_bias: float = 1.0,
    ignore_hazards: bool = False
) -> AlgorithmResult:
    """
    Custom implementation of Dijkstra's Algorithm using a Min-Heap.
    Calculates the safest, optimal route avoiding blocked roads and heavy hazards.
    
    Time Complexity: O((V + E) log V)
    Space Complexity: O(V)
    """
    start_time = time.perf_counter()

    if source not in graph:
        return AlgorithmResult("Custom Dijkstra", [], 0, 0, 0, 0, 0, [], False, f"Source '{source}' not in graph.")
    if target not in graph:
        return AlgorithmResult("Custom Dijkstra", [], 0, 0, 0, 0, 0, [], False, f"Target '{target}' not in graph.")
    if source == target:
        elapsed = (time.perf_counter() - start_time) * 1e6
        return AlgorithmResult("Custom Dijkstra", [source], 0, 0, 1.0, elapsed, 1, [source], True)

    # Priority queue stores (cost_so_far, node_id)
    pq: List[Tuple[float, str]] = [(0.0, source)]
    distances: Dict[str, float] = {node: float('inf') for node in graph.nodes()}
    distances[source] = 0.0
    previous: Dict[str, Optional[str]] = {node: None for node in graph.nodes()}
    
    visited_order: List[str] = []
    settled = set()
    nodes_explored = 0

    while pq:
        curr_cost, curr_node = heapq.heappop(pq)

        if curr_node in settled:
            continue
        settled.add(curr_node)
        visited_order.append(curr_node)
        nodes_explored += 1

        if curr_node == target:
            break

        # Explore neighbors
        for neighbor in graph.neighbors(curr_node):
            if neighbor in settled:
                continue

            edge_data = graph[curr_node][neighbor]
            # Check if road is blocked
            if edge_data.get('status') == 'blocked':
                continue

            distance = edge_data.get('distance', 1.0)
            hazard = edge_data.get('hazard_level', 1.0)
            if math.isinf(hazard):
                continue

            if ignore_hazards:
                weight = distance
            else:
                # Risk-adjusted weight
                effective_hazard = 1.0 + (hazard - 1.0) * vehicle_terrain_bias
                weight = distance * effective_hazard

            new_cost = curr_cost + weight
            if new_cost < distances[neighbor]:
                distances[neighbor] = new_cost
                previous[neighbor] = curr_node
                heapq.heappush(pq, (new_cost, neighbor))

    elapsed_us = (time.perf_counter() - start_time) * 1e6

    # Reconstruct path
    if distances[target] == float('inf'):
        return AlgorithmResult(
            "Custom Dijkstra",
            [],
            float('inf'),
            0,
            0,
            elapsed_us,
            nodes_explored,
            visited_order,
            False,
            f"No accessible route from '{source}' to '{target}'. Roads may be collapsed or blocked."
        )

    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = previous[curr]
    path.reverse()

    # Calculate physical distance and average hazard along path
    phys_dist = 0.0
    hazard_sum = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        ed = graph[u][v]
        phys_dist += ed.get('distance', 1.0)
        hazard_sum += ed.get('hazard_level', 1.0)
    avg_hazard = hazard_sum / max(1, len(path) - 1)

    return AlgorithmResult(
        "Custom Dijkstra",
        path,
        distances[target],
        phys_dist,
        avg_hazard,
        elapsed_us,
        nodes_explored,
        visited_order,
        True
    )


def a_star_search(
    graph: nx.Graph,
    source: str,
    target: str,
    vehicle_terrain_bias: float = 1.0
) -> AlgorithmResult:
    """
    A* Heuristic Search using Euclidean Distance to target as admissible heuristic h(n).
    Demonstrates AI informed search vs Dijkstra's uninformed uniform-cost exploration.
    """
    start_time = time.perf_counter()

    if source not in graph or target not in graph:
        return AlgorithmResult("A* Search", [], 0, 0, 0, 0, 0, [], False, "Invalid source or target.")
    if source == target:
        elapsed = (time.perf_counter() - start_time) * 1e6
        return AlgorithmResult("A* Search", [source], 0, 0, 1.0, elapsed, 1, [source], True)

    target_pos = graph.nodes[target].get('pos', (0.0, 0.0))

    def heuristic(node: str) -> float:
        pos = graph.nodes[node].get('pos', (0.0, 0.0))
        return math.hypot(pos[0] - target_pos[0], pos[1] - target_pos[1])

    # pq stores (f_score, g_score, node)
    pq: List[Tuple[float, float, str]] = [(heuristic(source), 0.0, source)]
    g_scores: Dict[str, float] = {node: float('inf') for node in graph.nodes()}
    g_scores[source] = 0.0
    previous: Dict[str, Optional[str]] = {node: None for node in graph.nodes()}

    settled = set()
    visited_order: List[str] = []
    nodes_explored = 0

    while pq:
        f_score, curr_g, curr_node = heapq.heappop(pq)

        if curr_node in settled:
            continue
        settled.add(curr_node)
        visited_order.append(curr_node)
        nodes_explored += 1

        if curr_node == target:
            break

        for neighbor in graph.neighbors(curr_node):
            if neighbor in settled:
                continue

            edge_data = graph[curr_node][neighbor]
            if edge_data.get('status') == 'blocked':
                continue
            hazard = edge_data.get('hazard_level', 1.0)
            if math.isinf(hazard):
                continue

            dist = edge_data.get('distance', 1.0)
            effective_hazard = 1.0 + (hazard - 1.0) * vehicle_terrain_bias
            step_cost = dist * effective_hazard

            tentative_g = curr_g + step_cost
            if tentative_g < g_scores[neighbor]:
                g_scores[neighbor] = tentative_g
                previous[neighbor] = curr_node
                f = tentative_g + heuristic(neighbor)
                heapq.heappush(pq, (f, tentative_g, neighbor))

    elapsed_us = (time.perf_counter() - start_time) * 1e6

    if g_scores[target] == float('inf'):
        return AlgorithmResult("A* Search", [], float('inf'), 0, 0, elapsed_us, nodes_explored, visited_order, False, "No route found.")

    path = []
    curr = target
    while curr is not None:
        path.append(curr)
        curr = previous[curr]
    path.reverse()

    phys_dist = 0.0
    hazard_sum = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        ed = graph[u][v]
        phys_dist += ed.get('distance', 1.0)
        hazard_sum += ed.get('hazard_level', 1.0)
    avg_hazard = hazard_sum / max(1, len(path) - 1)

    return AlgorithmResult(
        "A* Search",
        path,
        g_scores[target],
        phys_dist,
        avg_hazard,
        elapsed_us,
        nodes_explored,
        visited_order,
        True
    )


def networkx_dijkstra_benchmark(
    graph: nx.Graph,
    source: str,
    target: str,
    vehicle_terrain_bias: float = 1.0
) -> AlgorithmResult:
    """
    Standard NetworkX Dijkstra implementation for verification & benchmarking.
    """
    start_time = time.perf_counter()

    # Create a sub-view without blocked edges
    def weight_func(u, v, d):
        if d.get('status') == 'blocked' or math.isinf(d.get('hazard_level', 1.0)):
            return None
        hazard = d.get('hazard_level', 1.0)
        effective_hazard = 1.0 + (hazard - 1.0) * vehicle_terrain_bias
        return d.get('distance', 1.0) * effective_hazard

    # Create a clean graph copy with valid edge weights
    valid_graph = nx.Graph()
    for u, v, data in graph.edges(data=True):
        w = weight_func(u, v, data)
        if w is not None:
            valid_graph.add_edge(u, v, weight=w, distance=data.get('distance', 1.0), hazard_level=data.get('hazard_level', 1.0))

    try:
        path = nx.dijkstra_path(valid_graph, source, target, weight='weight')
        cost = nx.dijkstra_path_length(valid_graph, source, target, weight='weight')
        elapsed_us = (time.perf_counter() - start_time) * 1e6

        phys_dist = sum(graph[path[i]][path[i+1]]['distance'] for i in range(len(path)-1))
        avg_haz = sum(graph[path[i]][path[i+1]]['hazard_level'] for i in range(len(path)-1)) / max(1, len(path)-1)

        return AlgorithmResult(
            "NetworkX Built-in Dijkstra",
            path,
            cost,
            phys_dist,
            avg_haz,
            elapsed_us,
            len(path),
            path,
            True
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
        elapsed_us = (time.perf_counter() - start_time) * 1e6
        return AlgorithmResult("NetworkX Built-in Dijkstra", [], float('inf'), 0, 0, elapsed_us, 0, [], False, str(e))


def multi_target_triage_route(
    graph: nx.Graph,
    source: str,
    target_candidates: List[str],
    vehicle_terrain_bias: float = 1.0
) -> Optional[AlgorithmResult]:
    """
    Emergency Triage Router:
    Calculates the single closest viable emergency facility (e.g. Hospital or Shelter)
    from an affected disaster site using Dijkstra's algorithm.
    """
    best_result: Optional[AlgorithmResult] = None
    min_cost = float('inf')

    for candidate in target_candidates:
        if candidate == source or candidate not in graph:
            continue
        res = custom_dijkstra(graph, source, candidate, vehicle_terrain_bias)
        if res.success and res.total_cost < min_cost:
            min_cost = res.total_cost
            best_result = res

    return best_result


def dynamic_reroute(
    graph: nx.Graph,
    current_node: str,
    destination: str,
    blocked_edge: Tuple[str, str],
    vehicle_terrain_bias: float = 1.0
) -> AlgorithmResult:
    """
    Mid-mission reroute handler:
    Triggered when an unexpected bridge collapse or hazard surge blocks an edge
    while a rescue unit is underway.
    """
    # Temporarily or permanently block the edge
    u, v = blocked_edge
    if graph.has_edge(u, v):
        graph[u][v]['status'] = 'blocked'
        graph[u][v]['hazard_level'] = float('inf')

    # Immediately recalculate path from current vehicle location
    return custom_dijkstra(graph, current_node, destination, vehicle_terrain_bias)
