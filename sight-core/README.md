# S.I.G.H.T. Core Module

Future home of the S.I.G.H.T. Governor and Context Evaluation Engine.

Responsibilities:
- Mission Card parsing and validation
- Operational context engine (spatial geofences, zone classification, temporal persistence)
- Decision policy state machine: `SUPPRESS`, `RETAIN`, `EVENT`, `EVIDENCE`
- Explainability metadata generation for every decision

*Note: Frontend Command Centre displays decisions; Core evaluates them.*
