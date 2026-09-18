"""
PROJECT S.I.G.H.T. - Automated Mission Execution Script
Arms virtual UAV, executes predefined waypoint flight plan, logs telemetry & camera targets, and lands.
"""

import sys
import os
import time
import argparse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from simulator.simulator_interface import SimulatorInterface

def main():
    parser = argparse.ArgumentParser(description="Execute S.I.G.H.T. UAV Autonomous Mission")
    parser.add_argument(
        "--mission",
        type=str,
        default=str(Path(__file__).resolve().parent.parent / "missions" / "perimeter_mission.json"),
        help="Path to mission JSON file"
    )
    parser.add_argument("--save-frames", action="store_true", help="Save camera snapshots during mission")
    args = parser.parse_args()

    print("==================================================")
    print("PROJECT S.I.G.H.T. - VIRTUAL UAV MISSION RUNNER")
    print("==================================================")
    print(f"[*] Mission File: {args.mission}")

    sim = SimulatorInterface(mavlink_port=14550)
    sim.start(enable_mavlink=True)
    time.sleep(0.5)

    try:
        # 1. Load mission
        sim.load_mission(args.mission)
        print(f"[+] Waypoint mission loaded successfully.")

        # 2. Arm
        print(f"[*] Arming virtual UAV...")
        if sim.arm():
            print(f"[+] SIGHT-UAV-01 ARMED.")
        else:
            print(f"[-] Arming failed.")
            return

        # 3. Takeoff
        print(f"[*] Executing Autonomous Takeoff to 84.0m AGL...")
        sim.takeoff(altitude_m=84.0)

        # 4. Start mission navigation
        sim.run_mission()
        print(f"[+] Flight Mode set to AUTO_MISSION. Navigating waypoints...")

        # Monitor loop
        mission_finished = False
        start_time = time.time()
        last_log = 0.0

        while not mission_finished and time.time() - start_time < 90.0:
            telem = sim.get_telemetry()
            now = time.time()

            if now - last_log >= 1.0:
                last_log = now
                targets = sim.get_visible_targets()
                target_desc = f" | TARGETS IN FOV: {[t['class'] for t in targets]}" if targets else ""

                print(
                    f"[T+{int(now - start_time):02d}s | {telem['flight_mode']}] "
                    f"WP: {telem['current_waypoint']}/{telem['total_waypoints']} | "
                    f"ALT: {telem['altitude_m']}m | "
                    f"SPD: {telem['speed_mps']}m/s | "
                    f"HDG: {telem['heading_deg']}deg | "
                    f"BATT: {telem['battery_percent']}%"
                    f"{target_desc}"
                )

                if args.save_frames and targets:
                    frame = sim.capture_frame()
                    out_dir = Path(__file__).resolve().parent.parent / "output"
                    out_dir.mkdir(exist_ok=True)
                    sim.camera.save_snapshot(str(out_dir / f"frame_{int(now)}.jpg"))

            if telem["flight_mode"] == "LANDED":
                print("[+] Mission Complete: UAV has landed safely at HOME.")
                mission_finished = True
                break

            time.sleep(0.1)

        print("\n==================================================")
        print("MISSION SUMMARY")
        print("==================================================")
        final_telem = sim.get_telemetry()
        print(f"Final Mode: {final_telem['flight_mode']}")
        print(f"Final Battery: {final_telem['battery_percent']}%")
        print(f"Landing Position: {final_telem['lat']:.5f}N, {final_telem['lng']:.5f}W")
        print(f"Flight Duration: {int(time.time() - start_time)} seconds")
        print("==================================================")

    finally:
        sim.stop()
        print("[+] Simulator stopped.")

if __name__ == "__main__":
    main()
