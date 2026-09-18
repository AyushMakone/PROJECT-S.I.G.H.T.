"""
PROJECT S.I.G.H.T. - Reset Simulator Script
Resets the virtual UAV position, battery, and flight state to initial home baseline.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from simulator.simulator_interface import SimulatorInterface

def main():
    print("[*] PROJECT S.I.G.H.T. - Resetting Virtual UAV Simulator...")
    sim = SimulatorInterface()
    sim.reset()
    telem = sim.get_telemetry()
    print(f"[+] Simulator Reset Complete.")
    print(f"    Position: {telem['lat']:.5f}N, {telem['lng']:.5f}W (HOME)")
    print(f"    Altitude: {telem['altitude_m']}m AGL")
    print(f"    Battery:  {telem['battery_percent']}% ({telem['battery_voltage_v']}V)")
    print(f"    Mode:     {telem['flight_mode']}")

if __name__ == "__main__":
    main()
