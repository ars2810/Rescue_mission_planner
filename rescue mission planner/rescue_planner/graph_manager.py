"""
Graph Modeling & Emergency Topology Manager for Rescue Mission Planner.
Uses NetworkX to model urban road networks, disaster zones, and medical infrastructure.
"""

import math
import random
import networkx as nx
from typing import Dict, List, Tuple, Any, Optional

NODE_TYPES = {
    'base': {'color': '#00d2ff', 'marker': 's', 'label': 'Rescue Depot / Base'},
    'hospital': {'color': '#00ff88', 'marker': 'P', 'label': 'Emergency Hospital'},
    'shelter': {'color': '#3a86ff', 'marker': '^', 'label': 'Evacuation Shelter'},
    'affected': {'color': '#ff0055', 'marker': 'o', 'label': 'Casualty / Disaster Zone'},
    'checkpoint': {'color': '#ffbe0b', 'marker': 'D', 'label': 'Transit Checkpoint'}
}

EDGE_STATUS_COLORS = {
    'open': '#2a9d8f',       # Clear, safe road (green-teal)
    'caution': '#e9c46a',    # Minor debris/rain (yellow)
    'hazardous': '#f4a261',  # Flood/severe damage (orange)
    'blocked': '#e76f51'     # Impassable / destroyed (red dashed)
}


class EmergencyGraphManager:
    """Manages the NetworkX graph representation of the disaster area."""

    def __init__(self):
        self.graph = nx.Graph()
        self.scenario_name = "Default Emergency Scenario"
        self.load_flash_flood_scenario()

    def clear(self):
        """Clears the current network."""
        self.graph.clear()

    def add_location(
        self,
        node_id: str,
        name: str,
        node_type: str,
        pos: Tuple[float, float],
        casualties: int = 0,
        severity: float = 0.0,
        description: str = ""
    ):
        """Adds a location node with disaster metadata."""
        if node_type not in NODE_TYPES:
            node_type = 'checkpoint'
        self.graph.add_node(
            node_id,
            name=name,
            node_type=node_type,
            pos=pos,
            casualties=casualties,
            severity=severity,
            description=description
        )

    def add_road(
        self,
        u: str,
        v: str,
        distance: float,
        road_type: str = 'local_road',
        hazard_level: float = 1.0,
        status: str = 'open',
        elevation_risk: float = 1.0
    ):
        """
        Adds a road connection between two locations.
        hazard_level: 1.0 (clear) to 10.0 (extreme), or float('inf') for impassable.
        """
        self.graph.add_edge(
            u,
            v,
            distance=round(distance, 2),
            road_type=road_type,
            hazard_level=hazard_level,
            status=status,
            elevation_risk=elevation_risk
        )

    def block_road(self, u: str, v: str):
        """Marks a road as completely blocked / collapsed."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]['status'] = 'blocked'
            self.graph[u][v]['hazard_level'] = float('inf')

    def unblock_road(self, u: str, v: str, hazard_level: float = 1.0):
        """Reopens a previously blocked road."""
        if self.graph.has_edge(u, v):
            self.graph[u][v]['status'] = 'open' if hazard_level <= 1.2 else 'caution'
            self.graph[u][v]['hazard_level'] = hazard_level

    def update_road_hazard(self, u: str, v: str, hazard: float):
        """Updates road condition dynamically based on sensor/disaster telemetry."""
        if not self.graph.has_edge(u, v):
            return
        if math.isinf(hazard) or hazard >= 999:
            self.block_road(u, v)
        else:
            if hazard <= 1.2:
                status = 'open'
            elif hazard <= 2.5:
                status = 'caution'
            else:
                status = 'hazardous'
            self.graph[u][v]['status'] = status
            self.graph[u][v]['hazard_level'] = hazard

    def get_locations_by_type(self, node_type: str) -> List[str]:
        """Returns all node IDs matching a given type."""
        return [
            node for node, data in self.graph.nodes(data=True)
            if data.get('node_type') == node_type
        ]

    def get_edge_risk_adjusted_weight(self, u: str, v: str, vehicle_terrain_bias: float = 1.0) -> float:
        """
        Calculates the effective traversal cost combining physical distance
        and environmental hazards.
        """
        edge = self.graph[u][v]
        hazard = edge.get('hazard_level', 1.0)
        if math.isinf(hazard) or edge.get('status') == 'blocked':
            return float('inf')
        
        distance = edge.get('distance', 1.0)
        # Vehicle terrain bias scales how heavily rough terrain affects it
        effective_hazard = 1.0 + (hazard - 1.0) * vehicle_terrain_bias
        return distance * effective_hazard

    # ------------------ PRE-CONFIGURED DISASTER SCENARIOS ------------------ #

    def load_flash_flood_scenario(self):
        """
        Scenario 1: Urban Flash Flood
        River has broken banks. Central Transit Bridge is submerged.
        Lowland residential zones are flooded with stranded civilians.
        """
        self.clear()
        self.scenario_name = "Urban Flash Flood Disaster"

        # Key Nodes
        self.add_location('BASE_A', 'North Rescue Depot Alpha', 'base', (2.0, 9.0), 0, 0.0, "Main rescue command center")
        self.add_location('BASE_B', 'East Airbase & Helipad', 'base', (9.0, 7.5), 0, 0.0, "Aerial operations command")
        self.add_location('HOSP_1', 'Metropolitan Trauma Center', 'hospital', (1.5, 5.0), 0, 0.0, "Level 1 Trauma Hospital (High Ground)")
        self.add_location('HOSP_2', 'St. Jude Community Hospital', 'hospital', (8.5, 2.5), 0, 0.0, "Secondary Emergency Care Unit")
        self.add_location('SHELTER_1', 'Highland Community Shelter', 'shelter', (3.0, 1.5), 0, 0.0, "Evacuation center on elevated terrain")

        # Affected Zones (Casualties & Flood levels)
        self.add_location('ZONE_RES', 'Lowland Riverside Estates', 'affected', (5.0, 6.0), 42, 8.5, "Rising flood water, 42 stranded residents")
        self.add_location('ZONE_SCH', 'Riverside Academy / School', 'affected', (4.5, 3.5), 28, 7.0, "Ground floor submerged, 28 students/staff")
        self.add_location('ZONE_COM', 'Old Town Commercial Market', 'affected', (7.0, 5.5), 15, 6.0, "Flash flood current, debris in streets")

        # Transit Checkpoints / Intersections
        self.add_location('CHK_BRIDGE', 'Central River Bridge', 'checkpoint', (5.0, 8.0), 0, 9.0, "Bridge structure threatened by river surge")
        self.add_location('CHK_WEST', 'West Outer Bypass', 'checkpoint', (1.0, 7.5), 0, 1.0, "Clear elevated highway")
        self.add_location('CHK_EAST', 'East River Highway Junction', 'checkpoint', (8.0, 6.0), 0, 3.0, "Moderate water runoff")
        self.add_location('CHK_SOUTH', 'South levee Junction', 'checkpoint', (5.5, 1.8), 0, 4.0, "Water seepage near river delta")

        # Roads and Hazards
        self.add_road('BASE_A', 'CHK_WEST', 3.2, 'highway', hazard_level=1.0, status='open')
        self.add_road('CHK_WEST', 'HOSP_1', 4.0, 'highway', hazard_level=1.0, status='open')
        self.add_road('BASE_A', 'CHK_BRIDGE', 3.0, 'arterial', hazard_level=1.8, status='caution')
        
        # Bridge is completely submerged/blocked
        self.add_road('CHK_BRIDGE', 'ZONE_RES', 2.8, 'bridge', hazard_level=float('inf'), status='blocked')
        
        self.add_road('BASE_B', 'CHK_EAST', 2.5, 'arterial', hazard_level=1.2, status='open')
        self.add_road('CHK_EAST', 'ZONE_COM', 2.0, 'local_road', hazard_level=2.2, status='caution')
        self.add_road('ZONE_COM', 'ZONE_RES', 3.1, 'local_road', hazard_level=3.5, status='hazardous')
        self.add_road('ZONE_RES', 'ZONE_SCH', 2.9, 'local_road', hazard_level=4.0, status='hazardous')
        self.add_road('HOSP_1', 'ZONE_SCH', 3.8, 'arterial', hazard_level=2.5, status='caution')
        self.add_road('ZONE_SCH', 'SHELTER_1', 2.7, 'local_road', hazard_level=1.5, status='caution')
        self.add_road('SHELTER_1', 'CHK_SOUTH', 3.0, 'local_road', hazard_level=2.0, status='caution')
        self.add_road('CHK_SOUTH', 'HOSP_2', 3.5, 'arterial', hazard_level=1.2, status='open')
        self.add_road('ZONE_COM', 'HOSP_2', 4.2, 'arterial', hazard_level=1.5, status='open')
        self.add_road('HOSP_1', 'SHELTER_1', 4.5, 'highway', hazard_level=1.0, status='open')

    def load_earthquake_scenario(self):
        """
        Scenario 2: Major Earthquake & Structural Collapse
        Severe ground rupture, collapsed overpasses, power outage in central hub.
        """
        self.clear()
        self.scenario_name = "Major Earthquake & Structural Collapse"

        self.add_location('BASE_NORTH', 'Northern Rescue Headquarters', 'base', (2.5, 9.2), 0, 0.0, "Primary response fleet")
        self.add_location('BASE_SOUTH', 'Southern Tactical Station', 'base', (7.5, 1.2), 0, 0.0, "Heavy clearing machinery")
        self.add_location('HOSP_METRO', 'Metro General Hospital', 'hospital', (1.0, 3.5), 0, 0.0, "Surgical ICU available")
        self.add_location('HOSP_EAST', 'East Valley Hospital', 'hospital', (9.2, 5.0), 0, 0.0, "Emergency Field Hospital")
        self.add_location('SHELTER_PARK', 'Olympic Park Evacuation Camp', 'shelter', (5.0, 9.0), 0, 0.0, "Open field tent sanctuary")

        # Affected Sites
        self.add_location('ZONE_DOWNTOWN', 'Downtown High-Rise Corridor', 'affected', (4.5, 5.5), 65, 9.5, "Multiple collapsed structures, gas leaks")
        self.add_location('ZONE_STATION', 'Central Metro Transit Station', 'affected', (3.5, 7.0), 34, 8.0, "Roof collapse, underground entrapment")
        self.add_location('ZONE_PLAZA', 'Civic Arts Plaza', 'affected', (6.5, 4.0), 18, 5.5, "Fallen masonry, triage in progress")

        # Intersections
        self.add_location('INT_NORTH', 'North Radial Highway Overpass', 'checkpoint', (3.0, 8.0), 0, 1.2, "Clear road")
        self.add_location('INT_CENTRAL', 'Central Flyover Interchange', 'checkpoint', (5.0, 6.8), 0, 9.9, "Flyover collapsed, rubble impassable")
        self.add_location('INT_EAST', 'East Foothills Tunnel', 'checkpoint', (8.0, 6.5), 0, 3.8, "Rockfall debris inside tunnel")
        self.add_location('INT_SOUTH', 'South Industrial Causeway', 'checkpoint', (4.0, 2.5), 0, 1.5, "Minor cracks, passible")

        # Roads
        self.add_road('BASE_NORTH', 'INT_NORTH', 2.0, 'highway', hazard_level=1.1, status='open')
        self.add_road('INT_NORTH', 'SHELTER_PARK', 2.4, 'arterial', hazard_level=1.0, status='open')
        self.add_road('INT_NORTH', 'ZONE_STATION', 1.8, 'local_road', hazard_level=3.2, status='caution')
        
        # Central Flyover collapsed
        self.add_road('INT_NORTH', 'INT_CENTRAL', 2.2, 'highway', hazard_level=float('inf'), status='blocked')
        self.add_road('INT_CENTRAL', 'ZONE_DOWNTOWN', 1.5, 'highway', hazard_level=float('inf'), status='blocked')

        self.add_road('ZONE_STATION', 'ZONE_DOWNTOWN', 2.5, 'local_road', hazard_level=4.8, status='hazardous')
        self.add_road('ZONE_STATION', 'HOSP_METRO', 4.5, 'arterial', hazard_level=2.2, status='caution')
        self.add_road('HOSP_METRO', 'INT_SOUTH', 3.8, 'arterial', hazard_level=1.3, status='open')
        self.add_road('INT_SOUTH', 'ZONE_DOWNTOWN', 4.0, 'local_road', hazard_level=3.0, status='caution')
        self.add_road('ZONE_DOWNTOWN', 'ZONE_PLAZA', 2.6, 'local_road', hazard_level=2.8, status='caution')
        self.add_road('ZONE_PLAZA', 'INT_EAST', 3.0, 'arterial', hazard_level=3.6, status='hazardous')
        self.add_road('INT_EAST', 'HOSP_EAST', 2.3, 'arterial', hazard_level=1.4, status='open')
        self.add_road('BASE_SOUTH', 'INT_SOUTH', 3.9, 'highway', hazard_level=1.0, status='open')
        self.add_road('BASE_SOUTH', 'ZONE_PLAZA', 3.7, 'arterial', hazard_level=1.6, status='open')
        self.add_road('BASE_SOUTH', 'HOSP_EAST', 5.2, 'highway', hazard_level=1.1, status='open')

    def load_wildfire_scenario(self):
        """
        Scenario 3: Wildfire & Industrial Evacuation
        Spreading forest fire threatens chemical plant and peri-urban settlements.
        Smoke corridors and shifting thermal winds.
        """
        self.clear()
        self.scenario_name = "Wildfire & Industrial Hazmat Threat"

        self.add_location('BASE_AIR', 'Fire & Aviation Command Center', 'base', (1.5, 8.5), 0, 0.0, "Air tankers and helitack teams")
        self.add_location('BASE_CITY', 'Municipal Fire Station 1', 'base', (8.5, 8.5), 0, 0.0, "Structural engines and pumpers")
        self.add_location('HOSP_BURN', 'Regional Burn & Toxicology Institute', 'hospital', (8.5, 2.0), 0, 0.0, "Specialized inhalation and burn care")
        self.add_location('SHELTER_LAKE', 'Clearwater Lake Campsite', 'shelter', (1.0, 2.5), 0, 0.0, "Safe perimeter water barrier shelter")

        # Hazards
        self.add_location('ZONE_IND', 'Petrochemical Processing Complex', 'affected', (5.0, 5.0), 55, 9.8, "Volatile fuel tanks, heavy chemical smoke")
        self.add_location('ZONE_FOREST', 'Pine Ridge Mountain Village', 'affected', (3.5, 7.0), 22, 8.8, "Active fire front, perimeter breached")
        self.add_location('ZONE_VALLEY', 'Greenwood Residential Valley', 'affected', (6.5, 3.5), 37, 7.2, "Heavy embers and zero-visibility smoke")

        # Corridors
        self.add_location('WAY_RIDGE', 'Ridge Crest Lookout Pass', 'checkpoint', (3.0, 8.5), 0, 4.5, "Smoke across roadway")
        self.add_location('WAY_HIGHWAY', 'Cross-Valley Expressway', 'checkpoint', (5.5, 8.0), 0, 1.2, "Open 4-lane expressway")
        self.add_location('WAY_CREEK', 'Cedar Creek Bridge', 'checkpoint', (3.5, 3.5), 0, 2.0, "Clear firebreak route")

        self.add_road('BASE_AIR', 'WAY_RIDGE', 2.0, 'local_road', hazard_level=2.5, status='caution')
        self.add_road('WAY_RIDGE', 'ZONE_FOREST', 2.1, 'local_road', hazard_level=float('inf'), status='blocked')  # Road trapped by fire
        self.add_road('BASE_AIR', 'WAY_HIGHWAY', 4.2, 'highway', hazard_level=1.1, status='open')
        self.add_road('WAY_HIGHWAY', 'BASE_CITY', 3.2, 'highway', hazard_level=1.0, status='open')
        self.add_road('WAY_HIGHWAY', 'ZONE_FOREST', 2.9, 'arterial', hazard_level=3.5, status='hazardous')
        self.add_road('WAY_HIGHWAY', 'ZONE_IND', 3.4, 'highway', hazard_level=3.0, status='caution')
        self.add_road('ZONE_IND', 'ZONE_VALLEY', 2.7, 'local_road', hazard_level=5.0, status='hazardous')
        self.add_road('ZONE_FOREST', 'WAY_CREEK', 4.1, 'offroad', hazard_level=2.8, status='caution')
        self.add_road('WAY_CREEK', 'SHELTER_LAKE', 3.0, 'arterial', hazard_level=1.0, status='open')
        self.add_road('WAY_CREEK', 'ZONE_IND', 3.2, 'offroad', hazard_level=3.8, status='hazardous')
        self.add_road('ZONE_VALLEY', 'HOSP_BURN', 3.1, 'arterial', hazard_level=2.1, status='caution')
        self.add_road('BASE_CITY', 'HOSP_BURN', 6.8, 'highway', hazard_level=1.0, status='open')

    def generate_random_scenario(self, num_nodes: int = 14, seed: Optional[int] = None):
        """
        Procedurally generates a realistic, connected disaster network grid.
        Great for dynamic testing and algorithmic stress tests.
        """
        if seed is not None:
            random.seed(seed)
        self.clear()
        self.scenario_name = f"Procedural Disaster Map ({num_nodes} Nodes)"

        coords: Dict[str, Tuple[float, float]] = {}
        for i in range(num_nodes):
            node_id = f"LOC_{i+1}"
            x = round(random.uniform(1.0, 9.5), 2)
            y = round(random.uniform(1.0, 9.5), 2)
            coords[node_id] = (x, y)

        # Assign Roles
        node_ids = list(coords.keys())
        random.shuffle(node_ids)

        base_count = max(1, num_nodes // 5)
        hosp_count = max(1, num_nodes // 5)
        shelter_count = max(1, num_nodes // 6)
        affected_count = max(2, num_nodes // 3)

        bases = node_ids[:base_count]
        hosps = node_ids[base_count:base_count+hosp_count]
        shelters = node_ids[base_count+hosp_count:base_count+hosp_count+shelter_count]
        affected = node_ids[base_count+hosp_count+shelter_count:base_count+hosp_count+shelter_count+affected_count]
        checkpoints = node_ids[base_count+hosp_count+shelter_count+affected_count:]

        for nid, (x, y) in coords.items():
            if nid in bases:
                self.add_location(nid, f"Rescue Base {nid}", 'base', (x, y), 0, 0.0, "Operational depot")
            elif nid in hosps:
                self.add_location(nid, f"Hospital {nid}", 'hospital', (x, y), 0, 0.0, "Medical trauma station")
            elif nid in shelters:
                self.add_location(nid, f"Shelter {nid}", 'shelter', (x, y), 0, 0.0, "Civilian gathering site")
            elif nid in affected:
                cas = random.randint(10, 60)
                sev = round(random.uniform(4.0, 9.5), 1)
                self.add_location(nid, f"Disaster Site {nid}", 'affected', (x, y), cas, sev, f"{cas} trapped victims")
            else:
                self.add_location(nid, f"Waypoint {nid}", 'checkpoint', (x, y), 0, 1.0, "Road intersection")

        # Connect nodes using a k-nearest neighbor planar-like topology
        nodes = list(self.graph.nodes())
        for i, u in enumerate(nodes):
            u_pos = self.graph.nodes[u]['pos']
            distances = []
            for j, v in enumerate(nodes):
                if u != v:
                    v_pos = self.graph.nodes[v]['pos']
                    d = math.hypot(u_pos[0] - v_pos[0], u_pos[1] - v_pos[1])
                    distances.append((d, v))
            distances.sort()
            
            # Connect to 2 to 3 nearest neighbors
            k = min(len(distances), random.randint(2, 4))
            for d, v in distances[:k]:
                if not self.graph.has_edge(u, v):
                    hazard_roll = random.random()
                    if hazard_roll < 0.12:
                        # Blocked road
                        self.add_road(u, v, d, 'local_road', hazard_level=float('inf'), status='blocked')
                    elif hazard_roll < 0.35:
                        # Hazardous
                        hz = round(random.uniform(2.5, 5.0), 1)
                        self.add_road(u, v, d, 'local_road', hazard_level=hz, status='hazardous')
                    elif hazard_roll < 0.60:
                        hz = round(random.uniform(1.3, 2.2), 1)
                        self.add_road(u, v, d, 'arterial', hazard_level=hz, status='caution')
                    else:
                        self.add_road(u, v, d, 'highway', hazard_level=1.0, status='open')

        # Ensure the whole graph (ignoring blocked edges) remains connected
        temp_g = nx.Graph()
        for u, v, data in self.graph.edges(data=True):
            if data['status'] != 'blocked':
                temp_g.add_edge(u, v)
        for n in self.graph.nodes():
            if n not in temp_g:
                temp_g.add_node(n)
        
        components = list(nx.connected_components(temp_g))
        if len(components) > 1:
            for c_idx in range(len(components) - 1):
                u = random.choice(list(components[c_idx]))
                v = random.choice(list(components[c_idx + 1]))
                u_pos = self.graph.nodes[u]['pos']
                v_pos = self.graph.nodes[v]['pos']
                dist = math.hypot(u_pos[0] - v_pos[0], u_pos[1] - v_pos[1])
                self.add_road(u, v, dist, 'highway', hazard_level=1.0, status='open')
