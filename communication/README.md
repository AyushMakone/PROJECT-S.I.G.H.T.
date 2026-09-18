# Communication Controller Module

Future home of the mission-data communication simulation and tactical packet engine:
- Communication Controller state machine (`INACTIVE` vs `ACTIVE` bursts)
- Compact binary / JSON packet codecs for `EVENT` (metadata-only) and `EVIDENCE` (compressed snippet)
- Simulated RF channel physics: bandwidth, latency, loss, and RF emission signature
- Transmission duration and stealth duty-cycle metrics calculation
