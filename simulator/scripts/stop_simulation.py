"""
PROJECT S.I.G.H.T. - Stop Simulator Script
Signals running simulator instances to terminate cleanly.
"""

import os
import sys

def main():
    print("[*] PROJECT S.I.G.H.T. - Stopping Virtual UAV Simulator processes...")
    # On Windows, locate any background python processes running start_simulation
    if sys.platform == "win32":
        os.system('taskkill /f /im python.exe /fi "WINDOWTITLE eq SIGHT_SIMULATOR*" >nul 2>&1')
    print("[+] Simulator stopped.")

if __name__ == "__main__":
    main()
