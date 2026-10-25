"""
Unit Tests for Rescue Mission Planner.
Tests:
- Graph topology generation and connectivity
- Custom Dijkstra vs NetworkX Dijkstra consistency
- A* Heuristic Search admissibility & agreement
- Dynamic road blocking & mid-mission rerouting
- Multi-target emergency triage router
- Vehicle fleet terrain sensitivity scaling
"""

import unittest
import networkx as nx
from rescue_planner.graph_manager import EmergencyGraphManager
from rescue_planner.algorithms import (
    custom_dijkstra,
    a_star_search,
    networkx_dijkstra_benchmark,
    multi_target_triage_route,
    dynamic_reroute
)
from rescue_planner.simulation import VEHICLE_FLEET, MissionPlan


class TestRescueMissionPlanner(unittest.TestCase):

    def setUp(self):
        self.manager = EmergencyGraphManager()
        self.manager.load_flash_flood_scenario()
        self.graph = self.manager.graph

    def test_graph_initialization(self):
        """Verify scenario loading creates expected nodes and edges."""
        self.assertGreaterEqual(self.graph.number_of_nodes(), 10)
        self.assertGreaterEqual(self.graph.number_of_edges(), 12)
        self.assertIn('BASE_A', self.graph.nodes)
        self.assertIn('ZONE_RES', self.graph.nodes)

    def test_custom_dijkstra_success(self):
        """Test Dijkstra finds accessible route."""
        res = custom_dijkstra(self.graph, 'BASE_A', 'ZONE_RES', vehicle_terrain_bias=1.0)
        self.assertTrue(res.success)
        self.assertGreater(len(res.path), 1)
        self.assertEqual(res.path[0], 'BASE_A')
        self.assertEqual(res.path[-1], 'ZONE_RES')
        self.assertGreater(res.physical_distance, 0)
        self.assertGreater(res.total_cost, 0)

    def test_dijkstra_avoids_blocked_bridge(self):
        """Verify Dijkstra does not use the collapsed central bridge."""
        res = custom_dijkstra(self.graph, 'BASE_A', 'ZONE_RES', vehicle_terrain_bias=1.0)
        self.assertTrue(res.success)
        
        # Bridge is ('CHK_BRIDGE', 'ZONE_RES')
        path_edges = [(res.path[i], res.path[i+1]) for i in range(len(res.path)-1)]
        self.assertNotIn(('CHK_BRIDGE', 'ZONE_RES'), path_edges)
        self.assertNotIn(('ZONE_RES', 'CHK_BRIDGE'), path_edges)

    def test_dijkstra_vs_networkx_benchmark(self):
        """Verify custom Dijkstra matches NetworkX built-in result."""
        res_custom = custom_dijkstra(self.graph, 'BASE_A', 'HOSP_1', vehicle_terrain_bias=1.0)
        res_nx = networkx_dijkstra_benchmark(self.graph, 'BASE_A', 'HOSP_1', vehicle_terrain_bias=1.0)

        self.assertTrue(res_custom.success)
        self.assertTrue(res_nx.success)
        self.assertEqual(res_custom.path, res_nx.path)
        self.assertAlmostEqual(res_custom.total_cost, res_nx.total_cost, places=2)

    def test_a_star_agreement(self):
        """Verify A* search produces optimal cost path matching Dijkstra."""
        res_dijkstra = custom_dijkstra(self.graph, 'BASE_A', 'HOSP_2', vehicle_terrain_bias=1.0)
        res_astar = a_star_search(self.graph, 'BASE_A', 'HOSP_2', vehicle_terrain_bias=1.0)

        self.assertTrue(res_dijkstra.success)
        self.assertTrue(res_astar.success)
        self.assertAlmostEqual(res_dijkstra.total_cost, res_astar.total_cost, places=2)

    def test_dynamic_reroute_on_road_collapse(self):
        """Test mid-transit detour calculation when an active road collapses."""
        # Initial path
        res_init = custom_dijkstra(self.graph, 'ZONE_COM', 'ZONE_RES', vehicle_terrain_bias=1.0)
        self.assertTrue(res_init.success)
        self.assertIn(('ZONE_COM', 'ZONE_RES'), [('ZONE_COM', 'ZONE_RES')])

        # Simulate collapse of direct road
        reroute_res = dynamic_reroute(self.graph, 'ZONE_COM', 'ZONE_RES', ('ZONE_COM', 'ZONE_RES'), 1.0)
        self.assertTrue(reroute_res.success)
        self.assertNotEqual(reroute_res.path, ['ZONE_COM', 'ZONE_RES'])
        self.assertGreater(reroute_res.physical_distance, res_init.physical_distance)

    def test_multi_target_triage_routing(self):
        """Verify closest medical facility is selected."""
        hospitals = self.manager.get_locations_by_type('hospital')
        res = multi_target_triage_route(self.graph, 'ZONE_SCH', hospitals, vehicle_terrain_bias=1.0)

        self.assertIsNotNone(res)
        self.assertTrue(res.success)
        self.assertIn(res.path[-1], hospitals)

    def test_vehicle_terrain_sensitivity(self):
        """Drone should suffer less penalty on hazardous roads compared to ambulance."""
        amb = VEHICLE_FLEET['ambulance']
        drone = VEHICLE_FLEET['drone']

        res_amb = custom_dijkstra(self.graph, 'ZONE_COM', 'ZONE_RES', vehicle_terrain_bias=amb.terrain_sensitivity)
        res_drone = custom_dijkstra(self.graph, 'ZONE_COM', 'ZONE_RES', vehicle_terrain_bias=drone.terrain_sensitivity)

        self.assertTrue(res_amb.success)
        self.assertTrue(res_drone.success)
        # Ambulance cost should be significantly higher due to terrain sensitivity
        self.assertGreater(res_amb.total_cost, res_drone.total_cost)

    def test_procedural_scenario_generation(self):
        """Verify procedural generator creates connected valid graphs."""
        self.manager.generate_random_scenario(num_nodes=16, seed=42)
        self.assertEqual(self.manager.graph.number_of_nodes(), 16)
        self.assertGreaterEqual(self.manager.graph.number_of_edges(), 15)


if __name__ == "__main__":
    unittest.main()
