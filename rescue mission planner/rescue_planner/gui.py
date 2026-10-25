"""
Interactive Desktop GUI for Rescue Mission Planner.
Combines Tkinter and Matplotlib (FigureCanvasTkAgg) for high-performance,
interactive graph visualization, dynamic road blocking, and real-time mission dispatch.
"""

import time
import math
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import networkx as nx

from rescue_planner.graph_manager import EmergencyGraphManager, NODE_TYPES, EDGE_STATUS_COLORS
from rescue_planner.algorithms import (
    custom_dijkstra,
    a_star_search,
    networkx_dijkstra_benchmark,
    multi_target_triage_route
)
from rescue_planner.simulation import VEHICLE_FLEET, MissionPlan, VehicleProfile


class RescueMissionGUI:
    """Master GUI Application for Rescue Mission Planner."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Rescue Mission Planner | Emergency Route Dispatch System")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 750)

        # Apply dark command center theme
        self.bg_dark = "#13161c"
        self.bg_panel = "#1e222d"
        self.bg_card = "#282d3c"
        self.accent_blue = "#00d2ff"
        self.accent_green = "#00ff88"
        self.accent_red = "#ff2a5f"
        self.accent_yellow = "#ffd166"
        self.fg_white = "#f0f3f8"
        self.fg_muted = "#9ba3b4"

        self.root.configure(bg=self.bg_dark)

        # State management
        self.manager = EmergencyGraphManager()
        self.active_path = []
        self.highlighted_nodes = []
        self.current_mission: Optional[MissionPlan] = None
        self.selected_vehicle_key = 'ambulance'
        self.selected_algo_key = 'custom_dijkstra'
        self.click_mode = 'origin'  # alternates between 'origin' and 'destination'

        # Configure ttk styles
        self._setup_styles()

        # Build Layout
        self._build_header()
        self._build_main_body()

        # Initial plot render and logs
        self.log_event("SYSTEM INITIALIZED", "Rescue Mission Tactical Dispatch online. Ready for tasking.", "INFO")
        self.refresh_location_dropdowns()
        self.update_plot()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground=self.bg_card, background=self.bg_card, foreground=self.fg_white)
        style.configure("TLabel", background=self.bg_panel, foreground=self.fg_white, font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.accent_blue)
        style.configure("SubHeader.TLabel", font=("Segoe UI", 9), foreground=self.fg_muted)

    def _build_header(self):
        header_frame = tk.Frame(self.root, bg="#0d1117", height=65, relief=tk.RAISED, bd=1)
        header_frame.pack(side=tk.TOP, fill=tk.X)

        title_box = tk.Frame(header_frame, bg="#0d1117")
        title_box.pack(side=tk.LEFT, padx=20, pady=8)

        lbl_title = tk.Label(
            title_box,
            text="RESCUE MISSION PLANNER",
            font=("Segoe UI", 16, "bold"),
            bg="#0d1117",
            fg=self.accent_blue
        )
        lbl_title.pack(anchor="w")

        lbl_subtitle = tk.Label(
            title_box,
            text="Autonomous Emergency Route Optimization | Dijkstra & NetworkX Engine",
            font=("Segoe UI", 9),
            bg="#0d1117",
            fg=self.fg_muted
        )
        lbl_subtitle.pack(anchor="w")

        # Top Scenario Switcher
        scenario_box = tk.Frame(header_frame, bg="#0d1117")
        scenario_box.pack(side=tk.RIGHT, padx=20, pady=12)

        tk.Label(scenario_box, text="Disaster Scenario:", font=("Segoe UI", 10, "bold"), bg="#0d1117", fg=self.fg_white).pack(side=tk.LEFT, padx=6)
        self.scenario_var = tk.StringVar(value="Urban Flash Flood Disaster")
        self.cb_scenario = ttk.Combobox(
            scenario_box,
            textvariable=self.scenario_var,
            state="readonly",
            values=[
                "Urban Flash Flood Disaster",
                "Major Earthquake & Structural Collapse",
                "Wildfire & Industrial Hazmat Threat",
                "Procedural Random Map (Stress Test)"
            ],
            width=32
        )
        self.cb_scenario.pack(side=tk.LEFT, padx=6)
        self.cb_scenario.bind("<<ComboboxSelected>>", self._on_scenario_change)

        btn_reload = tk.Button(
            scenario_box,
            text="Load Scenario",
            font=("Segoe UI", 9, "bold"),
            bg=self.accent_blue,
            fg="#0d1117",
            activebackground="#00b4db",
            relief=tk.FLAT,
            padx=10,
            command=self._on_scenario_change
        )
        btn_reload.pack(side=tk.LEFT, padx=6)

    def _build_main_body(self):
        main_frame = tk.Frame(self.root, bg=self.bg_dark)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        # Left Control Panel
        left_panel = tk.Frame(main_frame, bg=self.bg_panel, width=380, relief=tk.GROOVE, bd=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        self._populate_control_panel(left_panel)

        # Center Graph Canvas Area
        center_frame = tk.Frame(main_frame, bg=self.bg_panel, relief=tk.GROOVE, bd=1)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._populate_graph_canvas(center_frame)

        # Right / Bottom Telemetry & Analytics Dashboard
        right_panel = tk.Frame(main_frame, bg=self.bg_panel, width=360, relief=tk.GROOVE, bd=1)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)
        self._populate_telemetry_panel(right_panel)

    def _populate_control_panel(self, parent: tk.Frame):
        scroll_canvas = tk.Canvas(parent, bg=self.bg_panel, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=scroll_canvas.yview)
        inner = tk.Frame(scroll_canvas, bg=self.bg_panel)

        inner.bind(
            "<Configure>",
            lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
        )
        scroll_canvas.create_window((0, 0), window=inner, anchor="nw", width=360)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        pad_x = 14

        # Section 1: Route Endpoints
        s1 = tk.LabelFrame(inner, text="  1. Mission Endpoints  ", bg=self.bg_panel, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), bd=1)
        s1.pack(fill=tk.X, padx=pad_x, pady=(10, 8))

        lbl_instruct = tk.Label(
            s1,
            text="Tip: You can also click directly on map nodes to select origin & destination!",
            bg=self.bg_panel,
            fg=self.accent_yellow,
            font=("Segoe UI", 8),
            wraplength=320,
            justify=tk.LEFT
        )
        lbl_instruct.pack(anchor="w", padx=10, pady=(4, 6))

        tk.Label(s1, text="Origin (Depot / Base / Point):", bg=self.bg_panel, fg=self.fg_white).pack(anchor="w", padx=10)
        self.var_origin = tk.StringVar()
        self.cb_origin = ttk.Combobox(s1, textvariable=self.var_origin, state="readonly")
        self.cb_origin.pack(fill=tk.X, padx=10, pady=(2, 6))

        tk.Label(s1, text="Destination (Target / Casualty Zone):", bg=self.bg_panel, fg=self.fg_white).pack(anchor="w", padx=10)
        self.var_dest = tk.StringVar()
        self.cb_dest = ttk.Combobox(s1, textvariable=self.var_dest, state="readonly")
        self.cb_dest.pack(fill=tk.X, padx=10, pady=(2, 8))

        # Quick Triage Buttons
        btn_triage_hosp = tk.Button(
            s1,
            text="🏥 Auto-Route to Closest Hospital",
            font=("Segoe UI", 9, "bold"),
            bg="#1f4e38",
            fg=self.accent_green,
            activebackground="#2a664a",
            relief=tk.FLAT,
            command=self._triage_to_hospital
        )
        btn_triage_hosp.pack(fill=tk.X, padx=10, pady=(2, 4))

        btn_triage_shelter = tk.Button(
            s1,
            text="🏕️ Auto-Route to Closest Shelter",
            font=("Segoe UI", 9, "bold"),
            bg="#1e3a5f",
            fg="#64b5f6",
            activebackground="#2a4c7a",
            relief=tk.FLAT,
            command=self._triage_to_shelter
        )
        btn_triage_shelter.pack(fill=tk.X, padx=10, pady=(2, 8))

        # Section 2: Fleet & Vehicle Dispatch
        s2 = tk.LabelFrame(inner, text="  2. Response Vehicle Fleet  ", bg=self.bg_panel, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), bd=1)
        s2.pack(fill=tk.X, padx=pad_x, pady=8)

        self.var_vehicle = tk.StringVar(value='ambulance')
        for v_key, v_prof in VEHICLE_FLEET.items():
            r = tk.Radiobutton(
                s2,
                text=f"{v_prof.icon} {v_prof.name} ({v_prof.base_speed_kmh} km/h)",
                variable=self.var_vehicle,
                value=v_key,
                bg=self.bg_panel,
                fg=self.fg_white,
                activebackground=self.bg_panel,
                selectcolor="#2b313e",
                font=("Segoe UI", 9)
            )
            r.pack(anchor="w", padx=10, pady=2)

        # Section 3: AI Routing Algorithm
        s3 = tk.LabelFrame(inner, text="  3. Algorithm Engine  ", bg=self.bg_panel, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), bd=1)
        s3.pack(fill=tk.X, padx=pad_x, pady=8)

        self.var_algo = tk.StringVar(value='custom_dijkstra')
        algos = [
            ('custom_dijkstra', "Custom Dijkstra (Risk-Adjusted Weighting)"),
            ('a_star', "A* Heuristic Search (Euclidean Distance)"),
            ('nx_dijkstra', "NetworkX Built-in Dijkstra Benchmark")
        ]
        for a_key, a_label in algos:
            r = tk.Radiobutton(
                s3,
                text=a_label,
                variable=self.var_algo,
                value=a_key,
                bg=self.bg_panel,
                fg=self.fg_white,
                activebackground=self.bg_panel,
                selectcolor="#2b313e",
                font=("Segoe UI", 9)
            )
            r.pack(anchor="w", padx=10, pady=2)

        # Section 4: Operational Action Buttons
        s4 = tk.Frame(inner, bg=self.bg_panel)
        s4.pack(fill=tk.X, padx=pad_x, pady=10)

        btn_plan = tk.Button(
            s4,
            text="🚀 PLAN RESCUE ROUTE",
            font=("Segoe UI", 11, "bold"),
            bg=self.accent_blue,
            fg="#0d1117",
            activebackground="#00b4db",
            relief=tk.FLAT,
            height=2,
            command=self.plan_route
        )
        btn_plan.pack(fill=tk.X, pady=(0, 6))

        btn_compare = tk.Button(
            s4,
            text="⚖️ Compare All Algorithms",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg_card,
            fg=self.accent_yellow,
            activebackground="#3a4154",
            relief=tk.FLAT,
            pady=4,
            command=self.compare_all_algorithms
        )
        btn_compare.pack(fill=tk.X, pady=3)

        # Section 5: Real-Time Disaster Simulation Controls
        s5 = tk.LabelFrame(inner, text="  4. Dynamic Hazard Controls  ", bg=self.bg_panel, fg=self.accent_red, font=("Segoe UI", 10, "bold"), bd=1)
        s5.pack(fill=tk.X, padx=pad_x, pady=8)

        tk.Label(s5, text="Block a Road Segment (Simulate Collapse):", bg=self.bg_panel, fg=self.fg_white, font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(4, 2))
        self.var_edge_to_block = tk.StringVar()
        self.cb_edges = ttk.Combobox(s5, textvariable=self.var_edge_to_block, state="readonly")
        self.cb_edges.pack(fill=tk.X, padx=10, pady=(2, 6))

        edge_btn_box = tk.Frame(s5, bg=self.bg_panel)
        edge_btn_box.pack(fill=tk.X, padx=10, pady=2)

        btn_block = tk.Button(
            edge_btn_box,
            text="❌ Block Road",
            font=("Segoe UI", 8, "bold"),
            bg="#5a1827",
            fg=self.accent_red,
            activebackground="#782335",
            relief=tk.FLAT,
            command=self._block_selected_edge
        )
        btn_block.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        btn_reopen = tk.Button(
            edge_btn_box,
            text="✅ Reopen Road",
            font=("Segoe UI", 8, "bold"),
            bg="#1b4d3e",
            fg=self.accent_green,
            activebackground="#266854",
            relief=tk.FLAT,
            command=self._reopen_selected_edge
        )
        btn_reopen.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        tk.Label(s5, text="Environmental Flood/Rain Severity:", bg=self.bg_panel, fg=self.fg_white, font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(10, 2))
        self.slider_flood = tk.Scale(
            s5,
            from_=1.0,
            to=3.5,
            resolution=0.1,
            orient=tk.HORIZONTAL,
            bg=self.bg_card,
            fg=self.fg_white,
            highlightthickness=0,
            troughcolor=self.bg_panel,
            command=self._on_flood_slider_change
        )
        self.slider_flood.set(1.0)
        self.slider_flood.pack(fill=tk.X, padx=10, pady=(0, 8))

    def _populate_graph_canvas(self, parent: tk.Frame):
        # Matplotlib Figure
        self.fig = Figure(figsize=(7, 6), dpi=100, facecolor=self.bg_dark)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor(self.bg_dark)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Matplotlib Navigation Toolbar (custom styled)
        toolbar_frame = tk.Frame(parent, bg="#0d1117")
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.config(background="#0d1117")
        self.toolbar.update()

        # Connect click event on canvas
        self.canvas.mpl_connect('button_press_event', self._on_canvas_click)

    def _populate_telemetry_panel(self, parent: tk.Frame):
        pad_x = 12

        lbl_dash = tk.Label(parent, text="  MISSION TELEMETRY  ", font=("Segoe UI", 11, "bold"), bg=self.bg_panel, fg=self.accent_blue)
        lbl_dash.pack(anchor="w", padx=pad_x, pady=(10, 6))

        # Metrics Card Frame
        self.card_frame = tk.Frame(parent, bg=self.bg_card, relief=tk.FLAT, bd=1)
        self.card_frame.pack(fill=tk.X, padx=pad_x, pady=4)

        self.lbl_metric_dist = self._create_metric_row(self.card_frame, "Route Distance:", "-- km", self.accent_blue)
        self.lbl_metric_eta = self._create_metric_row(self.card_frame, "Estimated ETA:", "-- min", self.accent_green)
        self.lbl_metric_risk = self._create_metric_row(self.card_frame, "Risk Assessment:", "AWAITING MISSION", self.accent_yellow)
        self.lbl_metric_cost = self._create_metric_row(self.card_frame, "Risk-Adjusted Cost:", "--", self.fg_white)
        self.lbl_metric_time = self._create_metric_row(self.card_frame, "Algorithm Latency:", "-- us", self.accent_yellow)
        self.lbl_metric_nodes = self._create_metric_row(self.card_frame, "Nodes Explored:", "--", self.fg_white)

        # Target Site Status Box
        self.target_site_frame = tk.LabelFrame(parent, text=" Target Zone Intel ", bg=self.bg_panel, fg=self.accent_yellow, font=("Segoe UI", 9, "bold"))
        self.target_site_frame.pack(fill=tk.X, padx=pad_x, pady=8)

        self.lbl_intel_cas = tk.Label(self.target_site_frame, text="Casualties / Trapped: --", bg=self.bg_panel, fg=self.accent_red, font=("Segoe UI", 9, "bold"))
        self.lbl_intel_cas.pack(anchor="w", padx=8, pady=2)
        self.lbl_intel_sev = tk.Label(self.target_site_frame, text="Hazard Severity Level: -- / 10", bg=self.bg_panel, fg=self.fg_white, font=("Segoe UI", 9))
        self.lbl_intel_sev.pack(anchor="w", padx=8, pady=2)
        self.lbl_intel_desc = tk.Label(self.target_site_frame, text="Awaiting target destination selection.", bg=self.bg_panel, fg=self.fg_muted, font=("Segoe UI", 8), wraplength=310, justify=tk.LEFT)
        self.lbl_intel_desc.pack(anchor="w", padx=8, pady=(2, 6))

        # Real-Time Operational Log Console
        lbl_log = tk.Label(parent, text="  Operational Log Console  ", font=("Segoe UI", 10, "bold"), bg=self.bg_panel, fg=self.fg_white)
        lbl_log.pack(anchor="w", padx=pad_x, pady=(6, 2))

        self.log_text = scrolledtext.ScrolledText(
            parent,
            bg="#0d1117",
            fg="#c9d1d9",
            insertbackground="white",
            font=("Consolas", 8),
            height=16,
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=(0, 10))

    def _create_metric_row(self, parent: tk.Frame, label_text: str, default_val: str, val_color: str) -> tk.Label:
        row = tk.Frame(parent, bg=self.bg_card)
        row.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(row, text=label_text, bg=self.bg_card, fg=self.fg_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text=default_val, bg=self.bg_card, fg=val_color, font=("Segoe UI", 9, "bold"))
        val_lbl.pack(side=tk.RIGHT)
        return val_lbl

    def log_event(self, tag: str, message: str, level: str = "INFO"):
        """Appends a timestamped log entry to the mission console."""
        timestamp = time.strftime("%H:%M:%S")
        color_tag = f"tag_{level}"
        
        self.log_text.insert(tk.END, f"[{timestamp}] [{tag}] {message}\n")
        self.log_text.see(tk.END)

    def refresh_location_dropdowns(self):
        """Populates origin, destination, and edge selection dropdowns."""
        nodes = list(self.manager.graph.nodes())
        node_display_list = []
        for n in nodes:
            nd = self.manager.graph.nodes[n]
            node_display_list.append(f"{n} | {nd.get('name', n)}")

        self.cb_origin['values'] = node_display_list
        self.cb_dest['values'] = node_display_list

        # Pick smart defaults
        bases = self.manager.get_locations_by_type('base')
        affected = self.manager.get_locations_by_type('affected')

        if bases:
            self.var_origin.set(f"{bases[0]} | {self.manager.graph.nodes[bases[0]].get('name', bases[0])}")
        elif nodes:
            self.var_origin.set(node_display_list[0])

        if affected:
            self.var_dest.set(f"{affected[0]} | {self.manager.graph.nodes[affected[0]].get('name', affected[0])}")
        elif len(nodes) > 1:
            self.var_dest.set(node_display_list[1])

        # Edges for blocking
        edge_list = []
        for u, v, data in self.manager.graph.edges(data=True):
            status = data.get('status', 'open').upper()
            edge_list.append(f"{u} <-> {v} [{status}]")
        self.cb_edges['values'] = edge_list
        if edge_list:
            self.var_edge_to_block.set(edge_list[0])

    def _parse_node_id(self, combobox_value: str) -> str:
        """Extracts node ID from string format 'NODE_ID | Node Name'."""
        if not combobox_value:
            return ""
        return combobox_value.split(" | ")[0].strip()

    def _on_scenario_change(self, event=None):
        scenario = self.scenario_var.get()
        self.active_path = []
        self.current_mission = None

        if "Flash Flood" in scenario:
            self.manager.load_flash_flood_scenario()
        elif "Earthquake" in scenario:
            self.manager.load_earthquake_scenario()
        elif "Wildfire" in scenario:
            self.manager.load_wildfire_scenario()
        elif "Procedural" in scenario:
            self.manager.generate_random_scenario(num_nodes=15)

        self.refresh_location_dropdowns()
        self.update_plot()
        self.log_event("SCENARIO LOADED", f"Disaster topology active: {self.manager.scenario_name}", "INFO")

    def _on_flood_slider_change(self, val):
        mult = float(val)
        # Apply scaled hazard factor
        for u, v, data in self.manager.graph.edges(data=True):
            if data.get('status') != 'blocked':
                base_hz = data.get('hazard_level', 1.0)
                data['current_hazard'] = round(base_hz * mult, 2)
        self.update_plot()

    def _block_selected_edge(self):
        selected = self.var_edge_to_block.get()
        if not selected:
            return
        parts = selected.split(" <-> ")
        if len(parts) >= 2:
            u = parts[0].strip()
            v = parts[1].split(" [")[0].strip()
            self.manager.block_road(u, v)
            self.log_event("INFRASTRUCTURE", f"ROAD COLLAPSE / BLOCKED: {u} <-> {v}", "WARN")
            self.refresh_location_dropdowns()
            self.update_plot()

            # If current active path used this edge, trigger instant dynamic re-route!
            if self.active_path and len(self.active_path) > 1:
                path_edges = [(self.active_path[i], self.active_path[i+1]) for i in range(len(self.active_path)-1)]
                path_edges += [(self.active_path[i+1], self.active_path[i]) for i in range(len(self.active_path)-1)]
                if (u, v) in path_edges or (v, u) in path_edges:
                    self.log_event("RE-ROUTING", f"Active mission path severed by road collapse! Triggering Dijkstra detour...", "ALERT")
                    self.plan_route()

    def _reopen_selected_edge(self):
        selected = self.var_edge_to_block.get()
        if not selected:
            return
        parts = selected.split(" <-> ")
        if len(parts) >= 2:
            u = parts[0].strip()
            v = parts[1].split(" [")[0].strip()
            self.manager.unblock_road(u, v, hazard_level=1.2)
            self.log_event("ENGINEERING", f"ROAD CLEARED & REOPENED: {u} <-> {v}", "INFO")
            self.refresh_location_dropdowns()
            self.update_plot()

    def _triage_to_hospital(self):
        dest_id = self._parse_node_id(self.var_dest.get())
        if not dest_id:
            messagebox.showwarning("Selection Missing", "Please select a disaster zone or starting point first.")
            return

        hospitals = self.manager.get_locations_by_type('hospital')
        if not hospitals:
            messagebox.showwarning("No Hospital Found", "No emergency hospitals available in current network.")
            return

        v_profile = VEHICLE_FLEET.get(self.var_vehicle.get(), VEHICLE_FLEET['ambulance'])
        result = multi_target_triage_route(self.manager.graph, dest_id, hospitals, v_profile.terrain_sensitivity)

        if result and result.success:
            hosp_id = result.path[-1]
            hosp_name = self.manager.graph.nodes[hosp_id].get('name', hosp_id)
            self.log_event("TRIAGE", f"Optimal hospital for {dest_id}: '{hosp_name}' (Cost: {result.total_cost})", "SUCCESS")
            # Update origin to dest_id and target to hosp_id
            self.var_origin.set(f"{dest_id} | {self.manager.graph.nodes[dest_id].get('name', dest_id)}")
            self.var_dest.set(f"{hosp_id} | {hosp_name}")
            self.plan_route()
        else:
            messagebox.showerror("Triage Route Failed", "All routes to emergency hospitals are severed.")

    def _triage_to_shelter(self):
        dest_id = self._parse_node_id(self.var_dest.get())
        if not dest_id:
            messagebox.showwarning("Selection Missing", "Please select a starting point first.")
            return

        shelters = self.manager.get_locations_by_type('shelter')
        if not shelters:
            messagebox.showwarning("No Shelter Found", "No evacuation shelters available.")
            return

        v_profile = VEHICLE_FLEET.get(self.var_vehicle.get(), VEHICLE_FLEET['rescue_truck'])
        result = multi_target_triage_route(self.manager.graph, dest_id, shelters, v_profile.terrain_sensitivity)

        if result and result.success:
            shelter_id = result.path[-1]
            shelter_name = self.manager.graph.nodes[shelter_id].get('name', shelter_id)
            self.log_event("TRIAGE", f"Optimal shelter for {dest_id}: '{shelter_name}' (Cost: {result.total_cost})", "SUCCESS")
            self.var_origin.set(f"{dest_id} | {self.manager.graph.nodes[dest_id].get('name', dest_id)}")
            self.var_dest.set(f"{shelter_id} | {shelter_name}")
            self.plan_route()
        else:
            messagebox.showerror("Triage Route Failed", "All routes to evacuation shelters are severed.")

    def plan_route(self):
        """Calculates optimal rescue route using the selected algorithm."""
        origin_id = self._parse_node_id(self.var_origin.get())
        dest_id = self._parse_node_id(self.var_dest.get())

        if not origin_id or not dest_id:
            messagebox.showwarning("Input Error", "Please select both Origin and Destination.")
            return
        if origin_id == dest_id:
            messagebox.showinfo("Identical Endpoints", "Origin and Destination are the same location.")
            return

        v_key = self.var_vehicle.get()
        vehicle = VEHICLE_FLEET.get(v_key, VEHICLE_FLEET['ambulance'])
        algo_choice = self.var_algo.get()

        self.log_event("MISSION DISPATCH", f"Calculating route for {vehicle.name} from '{origin_id}' to '{dest_id}' via {algo_choice}...", "INFO")

        # Execute chosen algorithm
        if algo_choice == 'custom_dijkstra':
            result = custom_dijkstra(
                self.manager.graph,
                origin_id,
                dest_id,
                vehicle_terrain_bias=vehicle.terrain_sensitivity
            )
        elif algo_choice == 'a_star':
            result = a_star_search(
                self.manager.graph,
                origin_id,
                dest_id,
                vehicle_terrain_bias=vehicle.terrain_sensitivity
            )
        elif algo_choice == 'nx_dijkstra':
            result = networkx_dijkstra_benchmark(
                self.manager.graph,
                origin_id,
                dest_id,
                vehicle_terrain_bias=vehicle.terrain_sensitivity
            )
        else:
            result = custom_dijkstra(self.manager.graph, origin_id, dest_id, vehicle.terrain_sensitivity)

        if not result.success:
            self.active_path = []
            self.update_plot()
            self._update_telemetry_failure(result)
            self.log_event("MISSION FAILURE", f"Pathfinding failed: {result.error_message}", "ALERT")
            messagebox.showerror("Path Blocked", f"No accessible route found!\n\nReason: {result.error_message}\n\nTry deploying the SAR Aerial Drone (DRN-X4) or reopening roads.")
            return

        # Build Mission Plan
        mission = MissionPlan(vehicle, origin_id, dest_id, result, self.manager.graph)
        self.current_mission = mission
        self.active_path = result.path

        # Update telemetry cards
        self._update_telemetry_success(mission, result)

        # Log turn-by-turn orders
        for instr in mission.generate_turn_by_turn():
            self.log_event("NAV TELEMETRY", instr, "INFO")

        self.update_plot()

    def compare_all_algorithms(self):
        """Runs Custom Dijkstra, A*, and NetworkX Dijkstra and prints comparison metrics."""
        origin_id = self._parse_node_id(self.var_origin.get())
        dest_id = self._parse_node_id(self.var_dest.get())

        if not origin_id or not dest_id:
            messagebox.showwarning("Input Error", "Please select both Origin and Destination to compare algorithms.")
            return

        vehicle = VEHICLE_FLEET.get(self.var_vehicle.get(), VEHICLE_FLEET['ambulance'])
        bias = vehicle.terrain_sensitivity

        r_custom = custom_dijkstra(self.manager.graph, origin_id, dest_id, bias)
        r_astar = a_star_search(self.manager.graph, origin_id, dest_id, bias)
        r_nx = networkx_dijkstra_benchmark(self.manager.graph, origin_id, dest_id, bias)

        self.log_event("BENCHMARK", f"--- ALGORITHM COMPARISON FOR {origin_id} -> {dest_id} ---", "INFO")
        self.log_event("BENCHMARK", f"Custom Dijkstra  : Time={r_custom.execution_time_us} us | Explored={r_custom.nodes_explored_count} nodes | Dist={r_custom.physical_distance}km | Cost={r_custom.total_cost}", "INFO")
        self.log_event("BENCHMARK", f"A* Search (Heur) : Time={r_astar.execution_time_us} us | Explored={r_astar.nodes_explored_count} nodes | Dist={r_astar.physical_distance}km | Cost={r_astar.total_cost}", "INFO")
        self.log_event("BENCHMARK", f"NetworkX Dijkstra: Time={r_nx.execution_time_us} us | Dist={r_nx.physical_distance}km | Cost={r_nx.total_cost}", "INFO")

        # Show modal popup with summary table
        summary_msg = (
            f"Algorithm Performance Comparison:\n"
            f"From: {origin_id}  -->  To: {dest_id}\n\n"
            f"1. Custom Dijkstra:\n"
            f"   - Execution Time: {r_custom.execution_time_us:.1f} us\n"
            f"   - Nodes Explored: {r_custom.nodes_explored_count}\n"
            f"   - Path Distance : {r_custom.physical_distance} km\n"
            f"   - Risk Cost     : {r_custom.total_cost}\n\n"
            f"2. A* Heuristic Search:\n"
            f"   - Execution Time: {r_astar.execution_time_us:.1f} us\n"
            f"   - Nodes Explored: {r_astar.nodes_explored_count} (Goal-directed pruning)\n"
            f"   - Path Distance : {r_astar.physical_distance} km\n"
            f"   - Risk Cost     : {r_astar.total_cost}\n\n"
            f"3. NetworkX Built-in Dijkstra:\n"
            f"   - Execution Time: {r_nx.execution_time_us:.1f} us\n"
            f"   - Path Distance : {r_nx.physical_distance} km\n"
        )
        messagebox.showinfo("Algorithm Benchmark Summary", summary_msg)

    def _update_telemetry_success(self, mission: MissionPlan, result):
        self.lbl_metric_dist.config(text=f"{result.physical_distance} km", fg=self.accent_blue)
        self.lbl_metric_eta.config(text=f"{mission.eta_minutes} min", fg=self.accent_green)
        self.lbl_metric_risk.config(text=f"{mission.risk_category} (hz: {result.average_hazard}x)", fg=mission.risk_color)
        self.lbl_metric_cost.config(text=f"{result.total_cost}", fg=self.fg_white)
        self.lbl_metric_time.config(text=f"{result.execution_time_us} us", fg=self.accent_yellow)
        self.lbl_metric_nodes.config(text=f"{result.nodes_explored_count} / {len(self.manager.graph.nodes())}", fg=self.fg_white)

        # Target intel
        self.lbl_intel_cas.config(text=f"Casualties / Trapped: {mission.target_casualties} persons")
        self.lbl_intel_sev.config(text=f"Hazard Severity Level: {mission.target_severity} / 10")
        target_node = self.manager.graph.nodes.get(mission.destination, {})
        self.lbl_intel_desc.config(text=target_node.get('description', 'No specific Intel notes.'))

    def _update_telemetry_failure(self, result):
        self.lbl_metric_dist.config(text="BLOCKED", fg=self.accent_red)
        self.lbl_metric_eta.config(text="INF", fg=self.accent_red)
        self.lbl_metric_risk.config(text="SEVERED ROUTE", fg=self.accent_red)
        self.lbl_metric_cost.config(text="INF", fg=self.accent_red)
        self.lbl_metric_time.config(text=f"{result.execution_time_us} us", fg=self.accent_yellow)
        self.lbl_metric_nodes.config(text=f"{result.nodes_explored_count}", fg=self.fg_white)

    def _on_canvas_click(self, event):
        """Allows users to click directly on nodes on the Matplotlib canvas!"""
        if event.xdata is None or event.ydata is None:
            return

        click_x, click_y = event.xdata, event.ydata
        closest_node = None
        min_dist = float('inf')

        # Find closest node within threshold
        for node, data in self.manager.graph.nodes(data=True):
            pos = data.get('pos', (0, 0))
            d = math.hypot(click_x - pos[0], click_y - pos[1])
            if d < min_dist and d < 0.6:  # 0.6 coordinate threshold
                min_dist = d
                closest_node = node

        if closest_node:
            node_name = self.manager.graph.nodes[closest_node].get('name', closest_node)
            item_str = f"{closest_node} | {node_name}"

            if self.click_mode == 'origin':
                self.var_origin.set(item_str)
                self.click_mode = 'destination'
                self.log_event("CANVAS PICK", f"Selected ORIGIN: '{node_name}' ({closest_node}). Now click destination.", "INFO")
            else:
                self.var_dest.set(item_str)
                self.click_mode = 'origin'
                self.log_event("CANVAS PICK", f"Selected DESTINATION: '{node_name}' ({closest_node}). Ready to plan.", "INFO")
            self.update_plot()

    def update_plot(self):
        """Redraws the NetworkX graph on the embedded Matplotlib figure."""
        self.ax.clear()
        self.ax.set_facecolor(self.bg_dark)
        self.ax.set_title(
            f"Tactical Map: {self.manager.scenario_name}",
            color=self.accent_blue,
            fontsize=12,
            fontweight="bold",
            pad=12
        )

        G = self.manager.graph
        pos = {n: d.get('pos', (0, 0)) for n, d in G.nodes(data=True)}

        # 1. Draw Edges by status
        for u, v, data in G.edges(data=True):
            status = data.get('status', 'open')
            u_pos = pos[u]
            v_pos = pos[v]

            if status == 'blocked':
                # Blocked edge (dashed red)
                self.ax.plot(
                    [u_pos[0], v_pos[0]],
                    [u_pos[1], v_pos[1]],
                    color=EDGE_STATUS_COLORS['blocked'],
                    linestyle='--',
                    linewidth=2.2,
                    alpha=0.8,
                    zorder=1
                )
                # Mark 'X' at midpoint
                mid_x = (u_pos[0] + v_pos[0]) / 2.0
                mid_y = (u_pos[1] + v_pos[1]) / 2.0
                self.ax.text(mid_x, mid_y, "BLOCKED", color=self.accent_red, fontsize=7, fontweight='bold', ha='center', va='center')
            elif status == 'hazardous':
                self.ax.plot(
                    [u_pos[0], v_pos[0]],
                    [u_pos[1], v_pos[1]],
                    color=EDGE_STATUS_COLORS['hazardous'],
                    linestyle='-',
                    linewidth=2.0,
                    alpha=0.85,
                    zorder=1
                )
            elif status == 'caution':
                self.ax.plot(
                    [u_pos[0], v_pos[0]],
                    [u_pos[1], v_pos[1]],
                    color=EDGE_STATUS_COLORS['caution'],
                    linestyle='-',
                    linewidth=1.8,
                    alpha=0.75,
                    zorder=1
                )
            else:
                self.ax.plot(
                    [u_pos[0], v_pos[0]],
                    [u_pos[1], v_pos[1]],
                    color=EDGE_STATUS_COLORS['open'],
                    linestyle='-',
                    linewidth=1.6,
                    alpha=0.6,
                    zorder=1
                )

            # Draw edge distance annotation
            dist = data.get('distance', 1.0)
            mid_x = (u_pos[0] + v_pos[0]) / 2.0
            mid_y = (u_pos[1] + v_pos[1]) / 2.0
            if status != 'blocked':
                self.ax.text(mid_x, mid_y, f"{dist}km", color=self.fg_muted, fontsize=6, ha='center', va='center', bbox=dict(boxstyle="round,pad=0.1", fc=self.bg_dark, ec="none", alpha=0.6))

        # 2. Highlight Active Rescue Route (Glowing Cyan / Gold)
        if self.active_path and len(self.active_path) > 1:
            for i in range(len(self.active_path) - 1):
                u = self.active_path[i]
                v = self.active_path[i + 1]
                if u in pos and v in pos:
                    u_pos = pos[u]
                    v_pos = pos[v]
                    # Outer glow
                    self.ax.plot(
                        [u_pos[0], v_pos[0]],
                        [u_pos[1], v_pos[1]],
                        color=self.accent_blue,
                        linewidth=6.0,
                        alpha=0.4,
                        zorder=2
                    )
                    # Core highlight line
                    self.ax.plot(
                        [u_pos[0], v_pos[0]],
                        [u_pos[1], v_pos[1]],
                        color="#ffffff",
                        linewidth=2.5,
                        zorder=3
                    )
                    # Directional arrow
                    dx = v_pos[0] - u_pos[0]
                    dy = v_pos[1] - u_pos[1]
                    self.ax.annotate(
                        "",
                        xy=(v_pos[0] - dx*0.15, v_pos[1] - dy*0.15),
                        xytext=(u_pos[0] + dx*0.15, u_pos[1] + dy*0.15),
                        arrowprops=dict(arrowstyle="->", color=self.accent_yellow, lw=2.0),
                        zorder=4
                    )

        # 3. Draw Nodes categorized by emergency type
        current_origin = self._parse_node_id(self.var_origin.get())
        current_dest = self._parse_node_id(self.var_dest.get())

        for node, data in G.nodes(data=True):
            p = pos[node]
            ntype = data.get('node_type', 'checkpoint')
            type_cfg = NODE_TYPES.get(ntype, NODE_TYPES['checkpoint'])
            color = type_cfg['color']
            marker = type_cfg['marker']
            size = 280

            # Distinct sizing/halo for selected Origin and Destination
            if node == current_origin:
                self.ax.scatter([p[0]], [p[1]], s=650, color=self.accent_blue, alpha=0.35, zorder=4)
                color = self.accent_blue
            elif node == current_dest:
                self.ax.scatter([p[0]], [p[1]], s=650, color=self.accent_red, alpha=0.35, zorder=4)
                color = self.accent_red

            # Casualty sites sized proportionally to number of casualties
            cas = data.get('casualties', 0)
            if cas > 0:
                size = 320 + min(cas * 8, 400)

            self.ax.scatter(
                [p[0]], [p[1]],
                s=size,
                color=color,
                marker=marker,
                edgecolors="#ffffff",
                linewidths=1.5,
                zorder=5
            )

            # Labels
            short_label = node
            if node == current_origin:
                short_label = f"START\n({node})"
            elif node == current_dest:
                short_label = f"TARGET\n({node})"
            elif cas > 0:
                short_label = f"{node}\n({cas} victims)"

            self.ax.text(
                p[0],
                p[1] + 0.38,
                short_label,
                color=self.fg_white,
                fontsize=7.5,
                fontweight='bold',
                ha='center',
                va='bottom',
                zorder=6,
                bbox=dict(boxstyle="round,pad=0.15", fc=self.bg_card, ec=color, lw=0.8, alpha=0.85)
            )

        # Add Legend
        legend_handles = []
        legend_labels = []
        for t_key, t_info in NODE_TYPES.items():
            handle = plt.Line2D([0], [0], marker=t_info['marker'], color='w', markerfacecolor=t_info['color'], markersize=8, linestyle='None')
            legend_handles.append(handle)
            legend_labels.append(t_info['label'])

        leg = self.ax.legend(
            legend_handles,
            legend_labels,
            loc='upper left',
            facecolor="#0d1117",
            edgecolor="#282d3c",
            labelcolor=self.fg_white,
            fontsize=7,
            framealpha=0.85
        )
        leg.set_zorder(10)

        # Clean axes
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_color("#282d3c")

        self.fig.tight_layout()
        self.canvas.draw()
