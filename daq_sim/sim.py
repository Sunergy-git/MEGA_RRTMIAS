"""
DAQ Simulator (Engine digital twin)
- In-process tick generator for processor.services to import and consume.
- Integer RPM, consequential anomalies, engine_id included.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MEGA_RRTMIAS.settings")
django.setup()

import time
import json
import random
from datetime import datetime, timezone
from processor.models import EngineMetaData

# -------------------------
# CONFIG
# -------------------------
RATED_RPM = 750
OVERSPEED_RPM = int(RATED_RPM * 1.10)   # 825

LOW_LO_PRESSURE = 2.5
HIGH_JW_TEMP = 90.0

# Tick interval (seconds)
TICK_INTERVAL = 1.0

# Anomaly parameters
ANOMALY_START_PROB = 1.0 / 500.0   # chance per tick to start a new anomaly
ANOMALY_STEP_MIN = 0.005
ANOMALY_STEP_MAX = 0.02
ANOMALY_MAX = 1.0

# Engine identifier emitted in every tick (must match EngineMetaData.id in DB)
ENGINE_ID = 2

# -------------------------
# INITIAL SMOOTH STATE
# -------------------------
_state = {
    # integer rpm
    "rpm": RATED_RPM,
    # pressures / temps / flows
    "lub_oil_pressure": 5.2,           # bar
    "jacket_cw_outlet_temp": 78.0,     # C
    "lub_oil_flow": 127.0,             # L/min (example)
    "cooling_water_flow": 532.0,       # L/min
    "boost_air_temp": 56.0,            # C
    "boost_air_pressure": 1.6,         # bar
    "bmep": 11.2,                      # bar
    "combustion_temp": 575.0,          # C
    "exhaust_temp": [300.0, 310.0, 290.0, 320.0, 295.0, 305.0],  # 6 cyl

    # --- Fuel system (new)
    "fuel_temp": 60.0,                 # degC
    "fuel_flow": 220.0,                # LPH
    "fuel_pressure": 320.0,            # bar (injection line)
    "fuel_pump_rack": 55.0,            # %

    # --- Turbo / manifold (new)
    "exhaust_manifold_pressure": 2.4,  # bar (turbine inlet side)
    "boost_air_flow": 4.8               # kg/s (air cooler outlet)
}

# -------------------------
# ANOMALY STATE MACHINE
# -------------------------
_anom = {
    "oil_leak": {"active": False, "progress": 0.0},
    "cw_blockage": {"active": False, "progress": 0.0},
    "turbo_issue": {"active": False, "progress": 0.0},
    "overspeed_event": {"active": False, "progress": 0.0},
}

_ticks_since_last_anom = 0


# -------------------------
# UTILS
# -------------------------
def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _maybe_start_anomaly():
    global _ticks_since_last_anom
    _ticks_since_last_anom += 1
    if random.random() < ANOMALY_START_PROB:
        choice = random.choice(list(_anom.keys()))
        if not _anom[choice]["active"]:
            _anom[choice]["active"] = True
            _anom[choice]["progress"] = random.uniform(0.02, 0.06)


def _progress_anomalies():
    for v in _anom.values():
        if v["active"]:
            v["progress"] += random.uniform(ANOMALY_STEP_MIN, ANOMALY_STEP_MAX)
            if v["progress"] >= ANOMALY_MAX or random.random() < 0.002:
                v["active"] = False
                v["progress"] = 0.0


# -------------------------
# CAUSAL UPDATE FUNCTIONS
# -------------------------
def _update_rpm():
    jitter = random.randint(-2, 2)
    _state["rpm"] += jitter

    ao = _anom["overspeed_event"]
    if ao["active"]:
        increment = int(ao["progress"] * 120)
        _state["rpm"] += increment

    _state["rpm"] = int(max(0, min(900, _state["rpm"])))


def _update_boost_and_bmeps():
    rp = _state["rpm"]
    boost_base = 1.6 + (rp - RATED_RPM) * 0.0008 + (_state["exhaust_manifold_pressure"] - 2.4) * 0.12
    boost_noise = random.uniform(-0.03, 0.03)
    _state["boost_air_pressure"] = round(max(0.4, min(3.5, boost_base + boost_noise)), 2)

    _state["boost_air_temp"] = round(max(40.0, min(380.0, 90.0 + (_state["boost_air_pressure"] - 1.6) * 40.0 + random.uniform(-1.0, 1.0))), 1)

    bmep_base = 10.5 + (rp - RATED_RPM) * 0.003 + (_state["boost_air_pressure"] - 1.6) * 1.2
    _state["bmep"] = round(max(4.0, min(25.0, bmep_base + random.uniform(-0.15, 0.15))), 2)

    baf = _state["boost_air_pressure"] * 2.5 + (rp - RATED_RPM) * 0.002 + (_state["exhaust_manifold_pressure"] - 2.4) * 1.2
    _state["boost_air_flow"] = round(max(0.5, min(50.0, baf + random.uniform(-0.2, 0.2))), 2)


def _update_fuel_and_manifold():
    bmep = _state["bmep"]
    rp = _state["rpm"]
    rack_delta = (bmep - 11.2) * 1.8
    _state["fuel_pump_rack"] = max(0.0, min(100.0, _state["fuel_pump_rack"] + rack_delta * 0.02 + random.uniform(-0.3, 0.3)))

    _state["fuel_flow"] = round(max(10.0, min(2000.0,
        50.0 + _state["fuel_pump_rack"] * 3.0 + (bmep - 10.0) * 8.0 + (_state["rpm"] - RATED_RPM) * 0.05 + random.uniform(-3.0, 3.0)
    )), 1)

    _state["fuel_pressure"] = round(max(50.0, min(1000.0,
        200.0 + (_state["fuel_pump_rack"] - 50.0) * 2.0 + (_state["fuel_flow"] - 200.0) * 0.6 + (_state["rpm"] - RATED_RPM) * 0.02 + (bmep - 10.0) * 1.0 + random.uniform(-5.0, 5.0)
    )), 1)

    _state["fuel_temp"] = round(max(-10.0, min(120.0,
        30.0 + (_state["fuel_flow"] - 200.0) * 0.03 + (_state["fuel_pump_rack"] - 50.0) * 0.05 + (bmep - 10.0) * 0.6 + random.uniform(-0.6, 0.6)
    )), 1)

    emp = 0.5 + (bmep - 10.0) * 0.18 + (rp - RATED_RPM) * 0.0012
    tt = _anom["turbo_issue"]
    if tt["active"]:
        emp += tt["progress"] * 0.8
    _state["exhaust_manifold_pressure"] = round(max(0.2, min(6.0, emp + random.uniform(-0.05, 0.05))), 2)


def _update_lube_and_flows():
    pump_contrib = _state["lub_oil_pressure"] + (_state["rpm"] - RATED_RPM) * 0.002
    _state["lub_oil_pressure"] = round(max(0.2, min(12.0, pump_contrib + random.uniform(-0.06, 0.06))), 2)

    _state["lub_oil_flow"] = round(max(20.0, min(350.0, 120.0 + (_state["rpm"] - RATED_RPM) * 0.2 + (_state["lub_oil_pressure"] - 3.2) * 18.0 + random.uniform(-2.0, 2.0))), 1)

    _state["cooling_water_flow"] = round(max(20.0, min(2000.0, _state["cooling_water_flow"] + random.uniform(-8.0, 8.0))), 1)

    flow_effect = (600.0 - _state["cooling_water_flow"]) * 0.02
    rpm_effect = (_state["rpm"] - RATED_RPM) * 0.01
    _state["jacket_cw_outlet_temp"] = round(max(20.0, min(160.0, 78.0 + flow_effect + rpm_effect + random.uniform(-0.4, 0.6))), 1)


def _update_combustion_and_exhaust():
    _state["combustion_temp"] = round(max(250.0, min(1100.0, 510.0 + (_state["bmep"] - 10.0) * 35.0 + random.uniform(-5.0, 5.0))), 1)

    for i in range(len(_state["exhaust_temp"])):
        scatter = random.uniform(-5.0, 5.0)
        base = _state["combustion_temp"] * 0.56
        _state["exhaust_temp"][i] = round(max(220.0, min(1200.0, base + scatter + random.uniform(-3.0, 3.0))), 1)


# -------------------------
# ANOMALY EFFECTS (consequential)
# -------------------------
def _apply_anomaly_effects():
    al = _anom["oil_leak"]
    if al["active"]:
        prog = al["progress"]
        _state["lub_oil_pressure"] = round(max(0.1, _state["lub_oil_pressure"] - prog * 1.8), 2)
        _state["lub_oil_flow"] = round(max(10.0, _state["lub_oil_flow"] - prog * 80.0), 1)
        _state["jacket_cw_outlet_temp"] = round(min(300.0, _state["jacket_cw_outlet_temp"] + prog * 6.0), 1)
        _state["combustion_temp"] = round(min(1300.0, _state["combustion_temp"] + prog * 12.0), 1)
        _state["fuel_pressure"] = round(max(30.0, _state["fuel_pressure"] - prog * 5.0), 1)

    cb = _anom["cw_blockage"]
    if cb["active"]:
        prog = cb["progress"]
        _state["cooling_water_flow"] = round(max(5.0, _state["cooling_water_flow"] * (1.0 - prog * 0.6)), 1)
        _state["jacket_cw_outlet_temp"] = round(min(300.0, _state["jacket_cw_outlet_temp"] + prog * 28.0), 1)
        for i in range(len(_state["exhaust_temp"])):
            _state["exhaust_temp"][i] = round(min(1500.0, _state["exhaust_temp"][i] + prog * 10.0), 1)
        _state["fuel_temp"] = round(min(150.0, _state["fuel_temp"] + prog * 2.5), 1)

    tt = _anom["turbo_issue"]
    if tt["active"]:
        prog = tt["progress"]
        _state["boost_air_pressure"] = round(max(0.2, _state["boost_air_pressure"] - prog * 1.2), 2)
        _state["boost_air_temp"] = round(min(900.0, _state["boost_air_temp"] + prog * 30.0), 1)
        _state["exhaust_temp"][0] = round(min(2000.0, _state["exhaust_temp"][0] + prog * 45.0), 1)
        _state["exhaust_temp"][1] = round(min(2000.0, _state["exhaust_temp"][1] + prog * 30.0), 1)
        _state["exhaust_manifold_pressure"] = round(min(12.0, _state["exhaust_manifold_pressure"] + prog * 0.9), 2)
        _state["boost_air_flow"] = round(max(0.1, _state["boost_air_flow"] - prog * 1.5), 2)
        _state["fuel_pressure"] = round(min(1200.0, _state["fuel_pressure"] + prog * 8.0), 1)

    os_ev = _anom["overspeed_event"]
    if os_ev["active"]:
        prog = os_ev["progress"]
        _state["lub_oil_pressure"] = round(min(12.0, _state["lub_oil_pressure"] + prog * 0.6), 2)
        _state["lub_oil_flow"] = round(min(800.0, _state["lub_oil_flow"] + prog * 30.0), 1)
        _state["boost_air_flow"] = round(min(60.0, _state["boost_air_flow"] + prog * 2.5), 2)
        _state["fuel_flow"] = round(min(5000.0, _state["fuel_flow"] + prog * 25.0), 1)


# -------------------------
# ALARM EVALUATION (for inclusion in tick)
# -------------------------
def _eval_alarms_for_tick():
    return {
        "lub_oil_low": True if _state["lub_oil_pressure"] < LOW_LO_PRESSURE else False,
        "jacket_cw_high": True if _state["jacket_cw_outlet_temp"] > HIGH_JW_TEMP else False,
        "overspeed": True if _state["rpm"] > OVERSPEED_RPM else False
    }


# -------------------------
# TICK GENERATOR (dict and json)
# -------------------------
def generate_tick_dict():
    _maybe_start_anomaly()
    _progress_anomalies()

    _update_rpm()
    _update_boost_and_bmeps()
    _update_fuel_and_manifold()
    _update_lube_and_flows()
    _update_combustion_and_exhaust()

    _apply_anomaly_effects()

    tick = {
        "timestamp": _now_iso(),
        "engine_id": ENGINE_ID,
        "rpm": int(_state["rpm"]),
        "lub_oil_pressure": round(_state["lub_oil_pressure"], 2),
        "jacket_cw_outlet_temp": round(_state["jacket_cw_outlet_temp"], 1),
        "lub_oil_flow": round(_state["lub_oil_flow"], 1),
        "cooling_water_flow": round(_state["cooling_water_flow"], 1),
        "boost_air_temp": round(_state["boost_air_temp"], 1),
        "boost_air_pressure": round(_state["boost_air_pressure"], 2),
        "bmep": round(_state["bmep"], 2),
        "combustion_temp": round(_state["combustion_temp"], 1),
        "exhaust_temp": [round(x, 1) for x in _state["exhaust_temp"]],
        "fuel_temp": round(_state["fuel_temp"], 1),
        "fuel_flow": round(_state["fuel_flow"], 1),
        "fuel_pressure": round(_state["fuel_pressure"], 1),
        "fuel_pump_rack": round(_state["fuel_pump_rack"], 2),
        "exhaust_manifold_pressure": round(_state["exhaust_manifold_pressure"], 2),
        "boost_air_flow": round(_state["boost_air_flow"], 2),
        "alarms": _eval_alarms_for_tick()
    }
    return tick


def generate_tick_json():
    return json.dumps(generate_tick_dict())


# -------------------------
# Manual CLI test
# -------------------------
if __name__ == "__main__":
    from processor.tasks import process_engine_tick

    print("Starting Celery simulator... Ctrl+C to stop")

    try:
        while True:
            tick = generate_tick_dict()
            process_engine_tick.delay(tick)
            time.sleep(TICK_INTERVAL)
    except KeyboardInterrupt:
        print("Simulator stopped")