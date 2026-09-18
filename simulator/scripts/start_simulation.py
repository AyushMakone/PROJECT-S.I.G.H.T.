"""
PROJECT S.I.G.H.T. - Start Virtual UAV Simulator
Starts the background simulator engine with MAVLink UDP broadcasting on 14550.
"""

import sys
import time
import argparse
from pathlib import Path

# Add simulator root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from simulator.simulator_interface import SimulatorInterface

def main():
    parser = argparse.ArgumentParser(description="Start S.I.G.H.T. Virtual UAV Simulator")
    parser.add_argument("--port", type=int, default=14550, help="MAVLink UDP broadcast port")
    parser.add_argument("--fps", type=int, default=15, help="Camera sensor frame rate")
    args = parser.parse_args()

    print("==================================================")
    print("PROJECT S.I.G.H.T. - VIRTUAL UAV SIMULATOR (PHASE 2)")
    print("==================================================")
    print(f"[*] Initializing PX4 SITL Autopilot...")
    print(f"[*] Initializing Gazebo Proving Ground World...")
    print(f"[*] Initializing Virtual Gimbal Optical Camera...")
    
    sim = SimulatorInterface(mavlink_port=args.port, camera_fps=args.fps)
    sim.start(enable_mavlink=True)

    print(f"[+] Simulator RUNNING.")
    print(f"[+] MAVLink 2.0 Telemetry Broadcasting on UDP 127.0.0.1:{args.port}")
    print("[+] Press Ctrl+C to terminate simulator.")

    try:
        while True:
            telem = sim.get_telemetry()
            sys.stdout.write(
                f"\r[STATUS: {telem['flight_mode']}] "
                f"LAT: {telem['lat']:.5f}, LNG: {telem['lng']:.5f} | "
                f"ALT: {telem['altitude_m']}m | SPD: {telem['speed_mps']}m/s | "
                f"BATT: {telem['battery_percent']}% | ARMED: {telem['is_armed']}   "
            )
            sys.stdout.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[*] Stopping simulator...")
        sim.stop()
        print("[+] Simulator stopped successfully.")

if __name__ == "__main__":
    main()
