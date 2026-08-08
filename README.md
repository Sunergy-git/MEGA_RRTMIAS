# MEGA-RRTMIS

## Marine Equipment Gateway Architecture for Remote Real-Time Monitoring, Intelligence & Simulation

> A modular, simulation-driven and physics-informed architecture for real-time monitoring, engineering reasoning, diagnostics, and digital twin development in marine propulsion and power systems.

---

## Project Vision

MEGA-RRTMIS explores the convergence of marine engineering, industrial automation, physics-based modelling, and operational intelligence.

The project is designed as a **decentralised, edge-deployable engineering software architecture** that can operate alongside existing onboard automation systems such as Power Management Systems (PMS), Alarm Monitoring Systems (AMS), engine controllers, PLCs, and other industrial control systems.

The system does not replace certified onboard control systems. Instead, it observes their data and builds an engineering understanding of the physical plant through:

- measured operating states
- first-principles physics
- inferred physical states
- measurement integrity assessment
- residual analysis
- causal reasoning
- engineering memory
- contextual diagnostics
- human-readable engineering assistance

The central philosophy is:

> **Physics discovers. Context reasons. Engineering memory preserves. LLMs explain.**

---

# System Philosophy

MEGA-RRTMIAS separates **measurement, physics, reasoning, memory, and language generation**.

The architecture follows:

```text
Marine Engine / PMS / AMS / PLC
                │
                ▼
        Industrial Connectivity
                │
                ▼
           EngineState
        (measured reality)
                │
                ▼
      Measurement Integrity
        / Sensor Validation
                │
                ▼
      Validated EngineState
                │
                ▼
        Reduced-Order Physics
              Engine
                │
                ▼
          InferredState
     (hidden physical states)
                │
                ▼
       Hypothesis / Residual
             Analysis
                │
                ▼
         Context Engine
                │
                ▼
       Engineering Memory
                │
                ▼
        LLM / User Interface
```

Each layer has a distinct responsibility and should remain independently testable.

---

# Core Architectural Principles

## 1. Physics Engine First

The reduced-order physics engine is the core engineering component.

It represents the physical behaviour of the engine using:

- conservation of energy
- conservation of mass
- thermodynamic relations
- fluid mechanics
- heat-transfer relationships
- pressure-flow relationships
- rotational dynamics
- kinematic relationships
- validated engineering correlations

The physics engine should remain independent of:

- Django
- databases
- REST APIs
- Modbus
- MQTT
- OPC UA
- LLMs
- dashboards

It must be executable as a standalone Python package.

---

## 2. EngineState Represents Measured Reality

`EngineState` represents what is actually observed from the physical system at a particular timestamp.

It should contain measured and externally supplied operating variables such as:

- timestamp
- engine RPM
- load
- fuel flow
- fuel rack position
- boost pressure
- boost temperature
- exhaust temperatures
- lubricating oil pressure
- lubricating oil temperature
- jacket-water temperature
- cooling-water flow
- other available PMS/AMS/engine-controller measurements

The simulator and industrial connectivity layer both produce `EngineState`.

### Important rule

> **The simulator and industrial IO must produce the same type of state.**

Today:

```text
Simulator
    ↓
EngineState
```

Later:

```text
PMS / AMS / PLC / Engine Controller
    ↓
Industrial IO
    ↓
EngineState
```

The rest of the system does not need to know where the state came from.

---

# 3. Simulator Is Not the Physics Engine

The simulator exists to provide a controlled representation of a running engine for development, testing, and anomaly injection.

Its responsibility is to generate:

```text
EngineState(t)
```

at the required timestep.

The simulator should not depend on Django models or write directly to the database.

### Simulator responsibilities

```text
engine_simulator.py
        │
        ├── Generate normal engine behaviour
        │
        └── Advance simulation state

anomaly.py
        │
        └── Inject physical disturbances / degraded conditions

scheduler.py
        │
        └── Execute the simulation timestep
```

The simulator should eventually exercise the same physics engine used for real-time inference wherever practical.

---

# 4. Industrial IO

Industrial IO provides the bridge between the physical vessel and MEGA-RRTMIAS.

Potential interfaces include:

- Modbus TCP/IP
- Ethernet TCP/IP
- OPC UA
- CAN Bus
- other supported industrial interfaces

Its job is to:

1. acquire raw data
2. map tags/registers to engineering variables
3. validate basic communication integrity
4. timestamp the data
5. normalise units and types
6. construct `EngineState`

Industrial IO should not perform engineering diagnosis.

---

# 5. Measurement Integrity Layer

Before physics inference, MEGA-RRTMIAS determines whether measured values are internally credible.

This layer addresses:

- sensor spikes
- impossible values
- communication corruption
- inconsistent measurements
- sensor drift
- sensor failure
- conflicting instrumentation

It can use:

- physical plausibility
- cross-sensor relationships
- rate-of-change limits
- redundant measurements
- historical behaviour
- engineering memory

Example:

```text
Lub Oil Pressure ↓

Oil Flow ↓
Oil Temperature ↑
Cooling behaviour consistent

        ↓

Measurements are mutually consistent
        ↓

Proceed to physical inference
```

Whereas:

```text
Lub Oil Pressure ↓

Oil Flow unchanged
Oil Temperature unchanged
RPM unchanged
No supporting physical response

        ↓

Measurement integrity concern
```

### Important rule

> **Do not use the physics engine to recreate a measured variable merely because it can be estimated.**

A reliably measured variable remains a measured variable.

The physics engine primarily infers **hidden physical states and causes**.

---

# 6. Reduced-Order Physics Engine

The physics engine transforms validated measured operating conditions into estimates of physical quantities that are not directly measured or are impractical to measure continuously.

The objective is not to reproduce every sensor.

The objective is to expose the hidden physical behaviour connecting them.

For example, from:

```text
RPM
Load
Fuel Flow
Boost Pressure
Boost Temperature
Oil Pressure
Oil Temperature
Cooling-Water Conditions
```

the engine may infer:

```text
Heat Release
Combustion Efficiency
Pump Head
Pump Hydraulic Efficiency
Heat Transfer Rate
Cooler Effectiveness
Oil Viscosity
Bearing Heat Generation
Turbocharger Efficiency
Mechanical Losses
Thermal Loads
```

These form the `InferredState`.

---

# 7. Physics Modules

The physics engine should be divided into physically meaningful modules.

Initial target structure:

```text
physics/
│
├── core/
│   ├── state.py
│   ├── scheduler.py
│   ├── integrator.py
│   ├── constants.py
│   └── units.py
│
├── combustion.py
├── engine.py
├── lubrication.py
├── cooling.py
├── turbo.py
├── fuel.py
├── governor.py
└── generator.py
```

Each module should have:

```text
Inputs
   ↓
Physical relations
   ↓
Internal states
   ↓
Outputs / inferred quantities
```

Every equation should be traceable to:

- a conservation law
- a thermodynamic relation
- a fluid/mechanical law
- an engineering correlation
- or a clearly documented modelling assumption

---

# 8. InferredState

`InferredState` contains quantities derived from the validated `EngineState` through the reduced-order physics engine.

It is not a duplicate of `EngineState`.

For example:

```text
EngineState
    └── Lub Oil Pressure = 3.8 bar

InferredState
    ├── Pump Head
    ├── Pump Efficiency
    ├── Oil Flow
    ├── Oil Viscosity
    ├── Bearing Heat
    └── Cooler Heat Rejection
```

The physics engine should prefer inferring **hidden physical states** rather than re-estimating variables that are already reliably measured.

---

# 9. Residual Analysis

Residual analysis has two distinct purposes.

## Operational Residuals

Measured values are compared against:

- manufacturer operating limits
- configured alarm thresholds
- normal operating envelopes
- load-dependent limits
- engine-specific operating standards

Example:

```text
Measured Oil Temperature = 92 °C
Allowed at current condition = 90 °C

        ↓

Operational residual / deviation
        ↓

Potential alarm
```

Even when the value remains within limits, the deviation should be recorded against the corresponding `EngineState` instance.

---

## Inferred-State Residuals

Inferred physical quantities can be compared against their expected or healthy reference behaviour.

Example:

```text
Normal inferred pump efficiency = 96 %

Current inferred pump efficiency = 82 %

        ↓

Degradation residual
```

This can provide evidence of an underlying problem before a conventional alarm occurs.

### Important principle

> **Measured variables are not unnecessarily re-inferred simply to create residuals.**

Measured values are evaluated against their operational standards.

Hidden physical quantities are evaluated against their expected physical/reference behaviour.

---

# 10. Hypothesis Generation

Physics inference and diagnosis are different problems.

The physics engine may infer:

```text
Pump Head ↓
Oil Flow ↓
Bearing Cooling ↓
Oil Heat Load ↑
```

A hypothesis layer can then generate possible physical causes:

```text
Oil pump wear
Pump internal leakage
Suction restriction
Oil viscosity change
Pump drive problem
```

The system should retain multiple hypotheses rather than immediately declaring one cause.

---

# 11. Context Engine

The Context Engine combines:

- EngineState history
- InferredState
- operational residuals
- inferred-state residuals
- measurement integrity
- operating mode
- load changes
- time relationships
- causal relationships
- previous events
- engineering memory

Its purpose is to construct the most plausible engineering interpretation.

Example:

```text
Oil Pressure ↓
        │
        ├── Oil Flow ↓
        │
        ├── Pump Head ↓
        │
        ├── Cooling degradation
        │
        └── Oil temperature ↑

Historical behaviour:
Pump efficiency has been declining for 14 days

        ↓

Context Engine

Most probable:
Oil pump degradation

Alternative:
Suction restriction
```

The Context Engine should continuously update this reasoning as new states arrive.

---

# 12. Engineering Memory

Engineering Memory is the structured representation of what the system has learned about a particular engine and its operating history.

It is not simply a raw database dump.

It is enriched by the Context Engine.

A memory record may contain:

```python
{
    "engine_id": "...",
    "start_time": "...",
    "end_time": "...",

    "measured_state": {...},
    "inferred_state": {...},

    "operational_deviations": {...},
    "physics_deviations": {...},

    "measurement_integrity": {...},

    "operating_context": {...},

    "causal_chain": [...],

    "probable_causes": [...],

    "confidence": {...},

    "supporting_evidence": [...],

    "recommended_checks": [...]
}
```

The memory should preserve the temporal relationship between events.

For example:

```text
10:21  Pump efficiency begins declining
10:27  Oil flow begins declining
10:31  Oil temperature begins rising
10:36  Oil pressure begins declining
10:42  Operational alarm occurs
```

This allows the system to determine:

> **What changed first, how the effect propagated, and when the problem became observable.**

---

# 13. LLM / Engineering Interface

LLMs are not the primary physics or diagnostic engine.

They consume structured engineering memory and contextual information to generate human-readable outputs.

Possible outputs include:

- problem explanation
- probable causes
- evidence supporting each cause
- timeline of degradation
- recommended inspections
- troubleshooting procedure
- references to engineering documentation
- operator summaries
- shift reports
- maintenance reports

The LLM should not invent the underlying physical state.

The structured engineering layers should provide the facts and reasoning that the LLM converts into language.

---

# Repository Structure

The architecture should evolve toward:

```text
MEGA-RRTMIAS/
│
├── shared/
│   ├── state.py
│   ├── types.py
│   ├── units.py
│   └── interfaces.py
│
├── physics/
│   ├── core/
│   │   ├── scheduler.py
│   │   ├── integrator.py
│   │   ├── constants.py
│   │   └── parameters.py
│   │
│   ├── combustion.py
│   ├── engine.py
│   ├── lubrication.py
│   ├── cooling.py
│   ├── turbo.py
│   ├── fuel.py
│   ├── governor.py
│   └── generator.py
│
├── simulator/
│   ├── engine_simulator.py
│   ├── anomaly.py
│   └── scheduler.py
│
├── industrial_io/
│   ├── modbus/
│   ├── opcua/
│   ├── can/
│   └── mapping/
│
├── integrity/
│   ├── validation.py
│   ├── plausibility.py
│   └── sensor_health.py
│
├── processor/
│   ├── residuals.py
│   ├── hypotheses.py
│   └── persistence.py
│
├── context/
│   ├── engine.py
│   ├── causal_graph.py
│   └── memory.py
│
├── knowledge/
│   ├── engineering_memory/
│   ├── manuals/
│   └── procedures/
│
├── llm/
│   ├── prompts/
│   ├── retrieval/
│   └── interface/
│
├── api/
├── dashboard/
├── visualization/
├── documentation/
├── examples/
└── research/
```

The exact names may evolve during implementation, but the separation of responsibilities should remain.

---

# Data Flow

## Development / Simulation

```text
engine_simulator
        │
        ▼
EngineState
        │
        ▼
Measurement Integrity
        │
        ▼
Physics Engine
        │
        ▼
InferredState
        │
        ▼
Residual / Hypothesis Analysis
        │
        ▼
Context Engine
        │
        ▼
Engineering Memory
```

## Real Vessel

```text
Engine / PMS / AMS / PLC
        │
        ▼
Industrial IO
        │
        ▼
EngineState
        │
        ▼
Measurement Integrity
        │
        ▼
Physics Engine
        │
        ▼
InferredState
        │
        ▼
Context / Diagnostics
        │
        ▼
Engineering Memory
```

The rest of the system should behave the same regardless of whether the source is a simulator or a real vessel.

---

# Development Strategy

The first implementation should **not** attempt to model the complete engine.

Build one physically coherent module at a time.

### Phase 1 — Physics Core

```text
EngineState
InferredState
Physics scheduler
ODE integrator
Physical parameters
```

### Phase 2 — Lubrication

Model:

- oil thermal balance
- oil flow
- pump head
- pressure losses
- viscosity
- cooler heat rejection

### Phase 3 — Cooling

Couple:

```text
Engine heat
      ↓
Jacket water
      ↓
Heat exchanger
      ↓
Sea water
```

### Phase 4 — Engine Thermodynamics

Couple:

```text
Fuel
 ↓
Combustion
 ↓
Heat release
 ↓
Mechanical power
 ↓
Exhaust energy
```

### Phase 5 — Turbocharging

Couple:

```text
Exhaust energy
      ↓
Turbocharger
      ↓
Boost pressure
      ↓
Air mass flow
      ↓
Combustion
```

### Phase 6 — Diagnostic Reasoning

Add:

- measurement integrity
- operational residuals
- inferred-state residuals
- hypothesis generation
- causal reasoning
- engineering memory

### Phase 7 — Edge Deployment

Connect the same physics and reasoning stack to:

- Modbus TCP/IP
- Ethernet
- OPC UA
- CAN
- onboard PMS/AMS/PLC data

---

# Technology Stack

## Engineering

- Marine propulsion systems
- Power Management Systems
- Dynamic Positioning
- Marine electrical systems
- Thermodynamics
- Heat transfer
- Fluid mechanics
- Rotational dynamics
- Control systems

## Core Software

- Python
- NumPy
- SciPy
- Pandas
- Docker
- Linux

## Industrial Connectivity

- Modbus TCP/IP
- OPC UA
- CAN
- MQTT

## Analytics / AI

- Scikit-Learn
- PyTorch
- LLM interfaces

## Application Layer

- ASP.NET Core
- REST APIs
- PostgreSQL
- Dashboard / visualization layer

---

# Research Philosophy

MEGA-RRTMIS is built around a strict separation between **measurement, physical inference, engineering reasoning, and language generation**.

The project does not aim to create an opaque AI system that predicts failures from sensor data alone.

Instead:

```text
Measured Reality
      ↓
Measurement Integrity
      ↓
First-Principles Physics
      ↓
Hidden-State Inference
      ↓
Residuals & Hypotheses
      ↓
Causal Context
      ↓
Engineering Memory
      ↓
Human Explanation
```

The objective is to preserve engineering traceability:

> **Every important conclusion should be explainable through measurements, physical relationships, historical evidence, or documented engineering knowledge.**

---

# Current Development Focus

The immediate development focus is:

1. Decouple the simulator from Django.
2. Establish `EngineState` as the shared data contract.
3. Build the standalone reduced-order physics core.
4. Replace heuristic simulator relationships with physically meaningful models.
5. Implement the first complete lubrication/cooling physics module.
6. Develop measurement integrity and residual analysis.
7. Build the context and engineering-memory pipeline.
8. Connect the architecture to real industrial IO.

---

# Current Principle

> **The simulator generates the physical world.  
> Industrial IO observes the real world.  
> EngineState represents what was measured.  
> The physics engine infers what cannot be directly observed.  
> Integrity validates whether measurements can be trusted.  
> Residual analysis identifies deviations.  
> The context engine connects causes and consequences.  
> Engineering memory preserves the evolving engineering understanding.  
> LLMs explain that understanding to humans.**

---

# Disclaimer

MEGA-RRTMIS is an independent engineering research and development project intended for learning, simulation, and architectural exploration.

The repository does not represent certified marine control software and should not be used for operational vessel control.

