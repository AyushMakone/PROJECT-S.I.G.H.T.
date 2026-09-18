# PROJECT S.I.G.H.T.
### Silent Intelligence Gathering & Hidden Transmission
**Edge-AI based Mission-Aware Communication Governance for UAVs**

---

## 🛰️ System Concept

> **"The UAV observes more information than the communication link needs to transmit."**
> **PERCEPTION ≠ COMMUNICATION DECISION**

PROJECT S.I.G.H.T. addresses the fundamental vulnerability of modern autonomous unmanned aerial vehicles (UAVs): **continuous, ungoverned RF emissions**. Continuous data transmission compromises operational stealth, consumes finite onboard energy, and saturates contested communication channels.

S.I.G.H.T. introduces a decoupled, mission-aware governance layer directly at the edge:

```
[ UAV SENSOR ]
      ↓
[  EDGE AI   ]  (YOLO / ByteTrack: Identifies what is physically present)
      ↓
[MISSION CTX ]  (Mission Card: Defines what is operational priority)
      ↓
[S.I.G.H.T. GOVERNOR] (Decides what should be communicated)
      ↓
[COMM CONTROLLER]     (Decides how and when information is transmitted)
      ↓
[GROUND COMMAND CENTRE]
```

---

## 🏛️ Governor Decision States

| Decision | Tactical Meaning | Link Action |
|---|---|---|
| **`SUPPRESS`** | Irrelevant or low-confidence detection outside mission scope | Discarded silently at edge. Zero RF emissions. |
| **`RETAIN`** | Mission-relevant target but missing zone or persistence criteria | Cached in edge NVMe/RAM. Held silent. |
| **`EVENT`** | Target satisfies all mission criteria (zone, persistence, battery) | Transmit ultra-compact metadata packet. |
| **`EVIDENCE`** | High-value target requiring verification imagery | Compressed visual clip/snapshot transmitted. |

---

## 📁 Repository Architecture

This repository is designed as a modular, decoupled system:

```
SIGHT-PROJECT/
├── command-centre/      # Operator Ground Station web interface (React + Vite + Leaflet)
├── backend/             # FastAPI REST & WebSocket communications coordinator
├── sight-core/          # Python S.I.G.H.T. Governor, Mission Context & Policy Engine
├── edge-ai/             # YOLO inference, ByteTrack object tracking & frame extractors
├── communication/       # Tactical packet codecs, link simulation & RF signature models
├── simulator/           # PX4 Autopilot SITL & Gazebo physics world integration
├── missions/            # Reusable JSON Mission Cards and tactical flight scenarios
├── tests/               # Multi-module integration, E2E and hardware-in-the-loop tests
└── docs/                # Architectural blueprints, interface protocols & metrics
```

---

## 🚀 Getting Started

### Command Centre (Operator UI)
```bash
cd command-centre
npm install
npm run dev
```

Visit `http://localhost:5173` to access the UAV Ground Command Centre.
