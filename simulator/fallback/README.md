# PROJECT S.I.G.H.T. — FALLBACK FLIGHT SIMULATOR

> **WARNING: FALLBACK / DEVELOPMENT ONLY**  
> **NOT THE PRIMARY FLIGHT SIMULATOR**

This directory contains the legacy in-memory synthetic UAV kinematic state machine and world generator.
It is retained solely as an offline development fallback when neither Cloud nor Local PX4 SITL MAVLink connections are available.

### Notice
* The primary operational simulator runs via real MAVLink (PX4 SITL / Cloud SITL).
* This fallback engine is activated only when `SIMULATOR_MODE=fallback` is explicitly set in configuration.
