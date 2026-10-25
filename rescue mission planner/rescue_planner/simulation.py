"""
Emergency Fleet Dispatch and Mission Simulation Engine.
Models heterogeneous emergency vehicle profiles, patient survivability metrics,
and multi-vehicle resource allocation.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import networkx as nx
from rescue_planner.algorithms import AlgorithmResult, custom_dijkstra, a_star_search, networkx_dijkstra_benchmark


@dataclass
class VehicleProfile:
    name: str
    code: str
    base_speed_kmh: float
    terrain_sensitivity: float   # Higher = suffers more in mud/flood/debris; lower = cuts through easily
    capacity: int                # Number of patients/victims transported
    icon: str
    description: str


VEHICLE_FLEET: Dict[str, VehicleProfile] = {
    'ambulance': VehicleProfile(
        name='Advanced Life Support Ambulance',
        code='AMB-01',
        base_speed_kmh=75.0,
        terrain_sensitivity=2.5,   # Highly sensitive to rough roads & floods
        capacity=2,
        icon='🚑',
        description='Fast medical transport for critical casualties. Optimal on highways and paved roads.'
    ),
    'rescue_truck': VehicleProfile(
        name='Heavy Rescue & Extrication Truck',
        code='TRK-09',
        base_speed_kmh=45.0,
        terrain_sensitivity=0.6,   # Handles debris & rubble with ease
        capacity=8,
        icon='🚒',
        description='All-terrain vehicle equipped with hydraulic cutters and heavy winch. Clears light debris.'
    ),
    'drone': VehicleProfile(
        name='Autonomous SAR Aerial Drone',
        code='DRN-X4',
        base_speed_kmh=95.0,
        terrain_sensitivity=0.05,  # Virtually immune to ground road hazards
        capacity=1,
        icon='🚁',
        description='High-speed aerial reconnaissance & medical payload delivery. Bypasses ground blocks.'
    ),
    'boat': VehicleProfile(
        name='Amphibious Flood Rescue Craft',
        code='BOT-03',
        base_speed_kmh=35.0,
        terrain_sensitivity=0.2,   # Excels in flooded sectors
        capacity=6,
        icon='🚤',
        description='Specialized watercraft for submerged urban sectors and river rescues.'
    )
}


class MissionPlan:
    """Detailed operational dispatch plan for an emergency rescue response."""

    def __init__(
        self,
        vehicle: VehicleProfile,
        origin: str,
        destination: str,
        result: AlgorithmResult,
        graph: nx.Graph
    ):
        self.vehicle = vehicle
        self.origin = origin
        self.destination = destination
        self.result = result
        self.graph = graph

        # Compute travel time taking hazards and vehicle speed into account
        if result.success and result.physical_distance > 0:
            effective_speed = max(15.0, vehicle.base_speed_kmh / max(0.5, result.average_hazard * 0.4))
            self.eta_minutes = round((result.physical_distance / effective_speed) * 60.0, 1)
        else:
            self.eta_minutes = 0.0

        # Assess mission risk category
        if not result.success:
            self.risk_category = "IMPASSABLE"
            self.risk_color = "#e63946"
        elif result.average_hazard <= 1.3:
            self.risk_category = "LOW RISK"
            self.risk_color = "#2a9d8f"
        elif result.average_hazard <= 2.5:
            self.risk_category = "MODERATE RISK"
            self.risk_color = "#e9c46a"
        elif result.average_hazard <= 4.0:
            self.risk_category = "HIGH HAZARD"
            self.risk_color = "#f4a261"
        else:
            self.risk_category = "EXTREME HAZARD"
            self.risk_color = "#d90429"

        # Triage and victim stats at target
        target_data = graph.nodes[destination] if destination in graph else {}
        self.target_casualties = target_data.get('casualties', 0)
        self.target_severity = target_data.get('severity', 0.0)
        self.target_name = target_data.get('name', destination)

    def generate_turn_by_turn(self) -> List[str]:
        """Generates waypoint telemetry instructions for field operators."""
        if not self.result.success:
            return [f"MISSION ABORT: {self.result.error_message}"]

        instructions = [
            f"DEPART: {self.graph.nodes[self.origin].get('name', self.origin)} with {self.vehicle.name} ({self.vehicle.code})"
        ]

        for i in range(len(self.result.path) - 1):
            curr_id = self.result.path[i]
            next_id = self.result.path[i + 1]
            edge = self.graph[curr_id][next_id]
            dist = edge.get('distance', 1.0)
            status = edge.get('status', 'open').upper()
            hz = edge.get('hazard_level', 1.0)
            road_type = edge.get('road_type', 'road').replace('_', ' ').title()
            next_name = self.graph.nodes[next_id].get('name', next_id)

            instructions.append(
                f"-> Proceed {dist} km along {road_type} to '{next_name}' [Condition: {status}, Hazard: {hz}x]"
            )

        instructions.append(
            f"ARRIVE: {self.target_name} | Est. Arrival: {self.eta_minutes} mins | Patients to secure: {self.target_casualties}"
        )
        return instructions
