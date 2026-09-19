"""
PROJECT S.I.G.H.T. — Simulator Telemetry & Health Monitor
Live terminal dashboard inspecting vehicle kinematics, link status, and governor health.
"""

import sys
import time
import argparse
import requests
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def monitor(api_url: str = "http://127.0.0.1:8000"):
    print("==========================================================")
    print("  PROJECT S.I.G.H.T. — VEHICLE & MISSION STATUS MONITOR   ")
    print("==========================================================")
    print(f"[*] Querying Backend Gateway at {api_url}...")

    try:
        while True:
            try:
                t_resp = requests.get(f"{api_url}/api/v1/telemetry", timeout=1.0)
                h_resp = requests.get(f"{api_url}/api/v1/health", timeout=1.0)
                c_resp = requests.get(f"{api_url}/api/v1/comm/state", timeout=1.0)

                t = t_resp.json() if t_resp.ok else {}
                h = h_resp.json() if h_resp.ok else {}
                c = c_resp.json() if c_resp.ok else {}

                sys.stdout.write("\033[2J\033[H") # Clear screen ANSI
                print("==========================================================")
                print(f"  S.I.G.H.T. LIVE MONITOR | SYSTEM: {h.get('status', 'OFFLINE')} | UPTIME: {h.get('uptime_s', 0)}s")
                print("==========================================================")
                print(f" [UAV FLIGHT STATE]")
                print(f"  Mode:        {t.get('flight_mode', 'UNKNOWN')} | Armed: {t.get('is_armed', False)}")
                print(f"  Position:    Lat {t.get('lat', 0.0):.6f}, Lng {t.get('lng', 0.0):.6f}")
                print(f"  Altitude:    {t.get('altitude_m', 0.0):.1f} m AGL")
                print(f"  Speed:       {t.get('speed_mps', 0.0):.1f} m/s | Heading: {t.get('heading_deg', 0.0):.1f}°")
                print(f"  Battery:     {t.get('battery_percent', 0.0):.1f}% ({t.get('battery_voltage_v', 0.0):.1f}V)")
                print(f"  Attitude:    Roll: {t.get('roll_deg', 0.0):.1f}°, Pitch: {t.get('pitch_deg', 0.0):.1f}°, Yaw: {t.get('yaw_deg', 0.0):.1f}°")
                print("----------------------------------------------------------")
                print(f" [COMMUNICATION CONTROLLER]")
                print(f"  State:       {c.get('state', 'UNKNOWN')} | Link Available: {c.get('link_available', False)}")
                print(f"  Packets Tx:  {c.get('packets_sent', 0)} | Bytes Tx: {c.get('bytes_transmitted', 0)} B")
                print(f"  Events Tx:   {c.get('events_transmitted', 0)} | Evidence Tx: {c.get('evidence_transmitted', 0)}")
                print(f"  Suppressed:  {c.get('suppressed', 0)} | Retained: {c.get('retained', 0)}")
                print("==========================================================")
                print(" Press Ctrl+C to exit monitor.")

            except requests.exceptions.RequestException:
                sys.stdout.write("\r[!] Waiting for S.I.G.H.T. Backend to become reachable...")
                sys.stdout.flush()

            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n[*] Monitor stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor S.I.G.H.T. Telemetry and Flight State")
    parser.add_argument("--url", type=str, default="http://127.0.0.1:8000", help="FastAPI backend URL")
    args = parser.parse_args()
    monitor(args.url)
