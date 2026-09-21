from pymavlink import mavutil
import time
import math

CONNECTION = "udp:172.30.16.1:14550"

m = mavutil.mavlink_connection(
    CONNECTION,
    source_system=255
)

m.target_system = 1
m.target_component = 1

print("Connecting...")
print("Target system:", m.target_system)
print("Target component:", m.target_component)

mask = 0x05C7

print("Yaw-rate test starting...")
print("Mask:", mask, hex(mask))
print("Yaw rate: +30 deg/s")
print()

start = time.time()

while time.time() - start < 5:
    m.mav.set_position_target_local_ned_send(
        int(time.time() * 1000) & 0xffffffff,
        1,
        1,
        mavutil.mavlink.MAV_FRAME_BODY_NED,
        mask,
        0, 0, 0,
        0, 0, 0,
        0, 0, 0,
        0,
        math.radians(30)
    )

    msg = m.recv_match(
        type="ATTITUDE",
        blocking=False
    )

    if msg:
        yaw_deg = math.degrees(msg.yaw) % 360
        print(f"Yaw: {yaw_deg:6.1f} deg")

    time.sleep(0.1)

print()
print("Yaw-rate test finished.")
