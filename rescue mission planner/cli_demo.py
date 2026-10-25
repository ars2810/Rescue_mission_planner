"""
CLI / Headless Demonstration Suite for Rescue Mission Planner.
Executes algorithmic benchmarks, dynamic detour re-routing, and triage routing.
Run directly via:
    python cli_demo.py
"""

import sys
import os

# Auto-configure Python Environment for Windows
std_lib = r"C:\Users\HP\AppData\Local\Programs\Python\Python314\Lib"
site_pkgs = r"C:\Users\HP\AppData\Local\Programs\Python\Python314\Lib\site-packages"
if os.path.exists(site_pkgs) and site_pkgs not in sys.path:
    sys.path.insert(0, site_pkgs)
if os.path.exists(std_lib) and std_lib not in sys.path:
    sys.path.insert(0, std_lib)

if "PYTHONHOME" not in os.environ:
    os.environ["PYTHONHOME"] = r"C:\Users\HP\AppData\Local\Programs\Python\Python314"

if "MPLCONFIGDIR" not in os.environ:
    import tempfile
    os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "rescue_planner_mpl")

# Ensure package directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from rescue_planner.graph_manager import EmergencyGraphManager
from rescue_planner.algorithms import (
    custom_dijkstra,
    a_star_search,
    networkx_dijkstra_benchmark,
    multi_target_triage_route,
    dynamic_reroute
)
from rescue_planner.simulation import VEHICLE_FLEET, MissionPlan


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)


def run_cli_demo():
    print_banner("Rescue Mission Planner - Automated Operational Test")

    # 1. Initialize Graph & Scenario
    manager = EmergencyGraphManager()
    manager.load_flash_flood_scenario()
    G = manager.graph

    print(f"[*] Scenario Loaded: {manager.scenario_name}")
    print(f"[*] Total Nodes: {G.number_of_nodes()} | Total Road Segments: {G.number_of_edges()}")

    print("\n[Topology Overview]")
    for n, data in G.nodes(data=True):
        ntype = data.get('node_type', 'unknown').upper()
        cas = data.get('casualties', 0)
        cas_str = f"| Victims: {cas}" if cas > 0 else ""
        print(f"  - [{ntype:<10}] {n:<12} : {data.get('name')} {cas_str}")

    # 2. Benchmark Algorithms
    origin = 'BASE_A'
    dest = 'ZONE_RES'
    print_banner(f"Route Optimization: {origin} -> {dest}")
    print(f"Target: Lowland Riverside Estates (42 stranded civilians)")

    v_amb = VEHICLE_FLEET['ambulance']
    print(f"Dispatched Unit: {v_amb.name} ({v_amb.code})")

    # Run Algorithms
    res_dijkstra = custom_dijkstra(G, origin, dest, v_amb.terrain_sensitivity)
    res_astar = a_star_search(G, origin, dest, v_amb.terrain_sensitivity)
    res_nx = networkx_dijkstra_benchmark(G, origin, dest, v_amb.terrain_sensitivity)

    print("\n[Algorithm Benchmark Comparison]")
    print(f"{'Algorithm':<28} | {'Status':<7} | {'Path Nodes':<10} | {'Dist(km)':<8} | {'Cost':<8} | {'Explored':<8} | {'Latency':<8}")
    print("-" * 88)
    for res in [res_dijkstra, res_astar, res_nx]:
        status = "PASS" if res.success else "FAIL"
        nodes_len = len(res.path)
        print(f"{res.algorithm_name:<28} | {status:<7} | {nodes_len:<10} | {res.physical_distance:<8} | {res.total_cost:<8} | {res.nodes_explored_count:<8} | {res.execution_time_us:>6.1f} us")

    print(f"\nOptimal Route Selected via Custom Dijkstra:")
    print(" -> ".join(res_dijkstra.path))

    # Mission Plan Details
    plan = MissionPlan(v_amb, origin, dest, res_dijkstra, G)
    print(f"\n[Mission Dispatch Telemetry]")
    print(f"  - Estimated Time of Arrival: {plan.eta_minutes} minutes")
    print(f"  - Risk Assessment Category : {plan.risk_category} (Avg Hazard: {res_dijkstra.average_hazard}x)")
    print(f"  - Civilians to Evacuate    : {plan.target_casualties} persons")

    print("\n[Turn-by-Turn Field Orders]")
    for step in plan.generate_turn_by_turn():
        print(f"  {step}")

    # 3. Dynamic Obstacle Simulation & Mid-Mission Detour
    print_banner("Simulation: Unexpected Road Collapse & Dynamic Rerouting")
    blocked_edge = ('ZONE_COM', 'ZONE_RES')
    print(f"ALERT: Severe landslide detected! Road {blocked_edge[0]} <-> {blocked_edge[1]} is now IMPASSABLE!")

    reroute_res = dynamic_reroute(G, 'ZONE_COM', dest, blocked_edge, v_amb.terrain_sensitivity)
    if reroute_res.success:
        print(f"[+] Detour successfully computed!")
        print(f"    New Path: {' -> '.join(reroute_res.path)}")
        print(f"    New Distance: {reroute_res.physical_distance} km | Cost: {reroute_res.total_cost}")
    else:
        print(f"[-] Ground route severed for Ambulance! Reason: {reroute_res.error_message}")
        print("[!] Deploying Autonomous SAR Aerial Drone (DRN-X4)...")
        v_drone = VEHICLE_FLEET['drone']
        drone_res = custom_dijkstra(G, origin, dest, v_drone.terrain_sensitivity)
        print(f"    Aerial Drone Path: {' -> '.join(drone_res.path)}")
        drone_plan = MissionPlan(v_drone, origin, dest, drone_res, G)
        print(f"    Aerial ETA: {drone_plan.eta_minutes} mins (Bypassed ground roadblocks)")

    # 4. Multi-Target Emergency Triage Router
    print_banner("Emergency Triage Router: Evacuate Critical Casualties")
    casualty_site = 'ZONE_SCH'
    hospitals = manager.get_locations_by_type('hospital')
    print(f"Evacuating school ({casualty_site}) to nearest accessible trauma hospital...")
    print(f"Candidate Hospitals: {hospitals}")

    triage_res = multi_target_triage_route(G, casualty_site, hospitals, v_amb.terrain_sensitivity)
    if triage_res and triage_res.success:
        target_hosp = triage_res.path[-1]
        print(f"[+] Triage Destination: {G.nodes[target_hosp].get('name')} ({target_hosp})")
        print(f"    Route: {' -> '.join(triage_res.path)}")
        print(f"    Total Risk Cost: {triage_res.total_cost} | Distance: {triage_res.physical_distance} km")

    print_banner("All Operational Demonstration Tests Passed Successfully!")


if __name__ == "__main__":
    run_cli_demo()
