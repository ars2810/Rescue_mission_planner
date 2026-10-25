"""
Main Entry Point for Rescue Mission Planner.
Run this script to launch the interactive Tkinter + Matplotlib Desktop GUI:
    python run_planner.py
"""

import os
import sys

# 1. Auto-configure Python Environment (portable — works on any Python installation)
_python_home = os.path.dirname(sys.executable)
_std_lib = os.path.join(_python_home, "Lib")
_site_pkgs = os.path.join(_python_home, "Lib", "site-packages")
if os.path.exists(_site_pkgs) and _site_pkgs not in sys.path:
    sys.path.insert(0, _site_pkgs)
if os.path.exists(_std_lib) and _std_lib not in sys.path:
    sys.path.insert(0, _std_lib)

# Configure matplotlib cache directory safely
if "MPLCONFIGDIR" not in os.environ:
    import tempfile
    os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "rescue_planner_mpl")

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def main():
    try:
        import tkinter as tk
        from rescue_planner.gui import RescueMissionGUI

        print("[*] Initializing Rescue Mission Tactical Dispatch UI...")
        root = tk.Tk()
        app = RescueMissionGUI(root)
        print("[*] GUI window running. Close the window to exit.")
        root.mainloop()
    except tk.TclError as e:
        print(f"\n[Notice] Graphical window error ({e}).")
        print("Switching to automated Terminal / CLI demonstration mode:\n")
        from cli_demo import run_cli_demo
        run_cli_demo()
    except Exception as e:
        print(f"\n[Error] Encountered unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
