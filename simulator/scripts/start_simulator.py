"""
PROJECT S.I.G.H.T. — Start Simulator Service
Entrypoint for launching or connecting to the UAV Flight Simulator.
Supports Cloud, Local PX4 SITL, and Fallback modes.
"""

import os
import sys
import time
import asyncio
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from simulator.adapters.base_adapter import BaseSimulatorAdapter
from simulator.adapters.px4_adapter import PX4Adapter
from simulator.adapters.cloud_adapter import CloudAdapter
from simulator.adapters.fallback_adapter import FallbackAdapter
from simulator.telemetry.telemetry_manager import TelemetryManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("SIGHT.StartSimulator")


def get_adapter(mode: str, port: int, host: str, endpoint: str) -> BaseSimulatorAdapter:
    mode = mode.lower()
    if mode == "cloud":
        logger.info(f"[*] Selected PRIMARY mode: CLOUD SIMULATOR (Host: {host}:{port})")
        return CloudAdapter(host=host, port=port, mavlink_endpoint=endpoint)
    elif mode == "local":
        logger.info(f"[*] Selected mode: LOCAL PX4 SITL (Endpoint: {endpoint})")
        return PX4Adapter(connection_string=endpoint)
    elif mode == "fallback":
        logger.warning("[!] Selected mode: FALLBACK / DEVELOPMENT ONLY — NOT THE PRIMARY FLIGHT SIMULATOR")
        return FallbackAdapter(mavlink_port=port)
    else:
        logger.error(f"[!] Unknown mode '{mode}', defaulting to cloud.")
        return CloudAdapter(host=host, port=port, mavlink_endpoint=endpoint)


async def run_simulator(args):
    print("==========================================================")
    print("  PROJECT S.I.G.H.T. — REAL-TIME DRONE SIMULATOR SERVICE  ")
    print("  Silent Intelligence Gathering & Hidden Transmission     ")
    print("==========================================================")

    adapter = get_adapter(
        mode=args.mode,
        port=args.port,
        host=args.host,
        endpoint=args.endpoint
    )

    logger.info("[SIM] Connecting to simulation engine...")
    connected = await adapter.connect()

    telemetry_manager = TelemetryManager(adapter=adapter, rate_hz=args.rate)
    await telemetry_manager.start()

    print(f"\n[+] Simulator Active in mode: {adapter.mode_name.upper()}")
    print(f"[+] Telemetry streaming at {args.rate} Hz")
    print("[+] Press Ctrl+C to terminate.\n")

    try:
        while True:
            telem = await adapter.get_telemetry()
            status_line = (
                f"\r[{telem.get('flightMode', 'UNKNOWN')}] "
                f"LAT: {telem.get('lat', 0.0):.5f}, LNG: {telem.get('lng', 0.0):.5f} | "
                f"ALT: {telem.get('altitude', 0.0)}m | "
                f"SPD: {telem.get('speed', 0.0)}m/s | "
                f"HDG: {telem.get('headingDegrees', 0.0)}° ({telem.get('heading', 'N')}) | "
                f"BATT: {telem.get('battery', 0.0)}% | "
                f"LINK: {telem.get('linkStatus', 'UNKNOWN')}   "
            )
            sys.stdout.write(status_line)
            sys.stdout.flush()
            await asyncio.sleep(0.5)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n[*] Shutting down simulator...")
    finally:
        await telemetry_manager.stop()
        await adapter.disconnect()
        print("[+] Simulator stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Start S.I.G.H.T. Drone Simulator Interface")
    parser.add_argument(
        "--mode",
        type=str,
        default=os.getenv("SIMULATOR_MODE", "cloud"),
        choices=["cloud", "local", "fallback"],
        help="Simulator mode: 'cloud' (primary), 'local' (WSL/PX4), or 'fallback' (dev only)"
    )
    parser.add_argument("--host", type=str, default=os.getenv("SIMULATOR_HOST", "127.0.0.1"), help="Remote host")
    parser.add_argument("--port", type=int, default=int(os.getenv("SIMULATOR_PORT", "14550")), help="MAVLink port")
    parser.add_argument("--endpoint", type=str, default=os.getenv("MAVLINK_ENDPOINT", "udpin:0.0.0.0:14550"), help="MAVLink connection string")
    parser.add_argument("--rate", type=float, default=10.0, help="Telemetry broadcast frequency in Hz (5-20)")
    args = parser.parse_args()

    asyncio.run(run_simulator(args))


if __name__ == "__main__":
    main()
