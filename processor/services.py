"""
Processor service (Django ORM version)
- Uses daq_sim.sim.generate_tick_dict()
- Computes engineered features, rolling stats, alarms, PCA
"""

import time
import numpy as np
from collections import deque
from datetime import datetime

from django.db import transaction
from django.utils.timezone import now
from django.db.models import Max

# Django models
from processor.models import (
    EngineMetaData,
    ProcessedFeatures,
    StatisticalFeatures,
    AlarmFlags,
    PCAFeatures,
)

# simulator
from daq_sim.sim import generate_tick_dict, TICK_INTERVAL

# ---------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------
RATED_RPM = 750
OVERSPEED_RPM = int(RATED_RPM * 1.10)
ROLLING_WINDOW = 20
LOW_LOP_PRESSURE = 2.5
HIGH_EXH_TEMP = 450
LOW_FUEL_PRESSURE = 2.5

# Rolling buffers
stats_buffer = {
    "rpm": deque(maxlen=ROLLING_WINDOW),
    "lub_oil_pressure": deque(maxlen=ROLLING_WINDOW),
    "boost_air_pressure": deque(maxlen=ROLLING_WINDOW),
    "fuel_flow": deque(maxlen=ROLLING_WINDOW),
    "exhaust_temps": deque(maxlen=ROLLING_WINDOW),
}


# ---------------------------------------------------------------------
# ENGINEERED FEATURES (exact formulas you gave)
# ---------------------------------------------------------------------
def compute_engineered_features(raw, meta):
    rpm = raw.get("rpm", 0)
    bmep = raw.get("bmep", 0.0)
    fuel_flow = raw.get("fuel_flow", 0.0)
    boost_air_pressure = raw.get("boost_air_pressure", 0.0)

    stroke_mm = meta.stroke_mm if meta.stroke_mm else 300.0
    bore_mm = meta.bore_mm if meta.bore_mm else 300.0
    cylinders = meta.cylinders if meta.cylinders else 6

    stroke_m = stroke_mm / 1000.0
    piston_speed = 2 * stroke_m * (rpm / 60.0)

    displacement = ((bore_mm / 1000.0) ** 2) * np.pi * stroke_m * cylinders

    indicated_power = (bmep * displacement * rpm) / 60_000 if bmep else 0.0

    mechanical_eff = 0.95
    brake_power = indicated_power * mechanical_eff
    friction_loss = indicated_power - brake_power

    afr = (boost_air_pressure / fuel_flow) if fuel_flow else None

    fuel_energy_rate = (fuel_flow * 42000.0) if fuel_flow else 0.0
    thermal_eff = (brake_power / fuel_energy_rate) if fuel_energy_rate else None

    bsfc = (fuel_flow * 1000.0 / brake_power) if brake_power else None

    governor_response = abs(rpm - RATED_RPM) * 0.015

    return {
        "piston_force": float(bmep * displacement if bmep else 0.0),
        "mechanical_efficiency": float(mechanical_eff),
        "indicated_power_kw": float(indicated_power),
        "volumetric_efficiency": float(boost_air_pressure / 2.0 if boost_air_pressure else 0.0),
        "frictional_loss_kw": float(friction_loss),
        "afr": float(afr) if afr is not None else None,
        "governor_response_time_s": float(governor_response),
        "piston_speed_mps": float(piston_speed),
        "bsfc_g_per_kwh": float(bsfc) if bsfc is not None else None,
        "thermal_efficiency": float(thermal_eff) if thermal_eff is not None else None,
    }


# ---------------------------------------------------------------------
# ROLLING STATS
# ---------------------------------------------------------------------
def compute_rolling_stats(pf):
    stats_buffer["rpm"].append(pf.rpm)
    stats_buffer["lub_oil_pressure"].append(pf.lub_oil_pressure)
    stats_buffer["boost_air_pressure"].append(pf.boost_air_pressure)
    stats_buffer["fuel_flow"].append(pf.fuel_flow)

    exh_avg = np.mean([
        pf.exhaust_temp_c1 or 0.0,
        pf.exhaust_temp_c2 or 0.0,
        pf.exhaust_temp_c3 or 0.0,
        pf.exhaust_temp_c4 or 0.0,
        pf.exhaust_temp_c5 or 0.0,
        pf.exhaust_temp_c6 or 0.0,
    ])
    stats_buffer["exhaust_temps"].append(exh_avg)

    def safe_mean(arr): return float(np.mean(arr)) if len(arr) else None
    def safe_std(arr): return float(np.std(arr)) if len(arr) else None

    StatisticalFeatures.objects.create(
        features=pf,
        window_size=ROLLING_WINDOW,
        rpm_mean=safe_mean(stats_buffer["rpm"]),
        rpm_std=safe_std(stats_buffer["rpm"]),
        lub_oil_pressure_mean=safe_mean(stats_buffer["lub_oil_pressure"]),
        lub_oil_pressure_std=safe_std(stats_buffer["lub_oil_pressure"]),
        boost_air_pressure_mean=safe_mean(stats_buffer["boost_air_pressure"]),
        boost_air_pressure_std=safe_std(stats_buffer["boost_air_pressure"]),
        fuel_flow_mean=safe_mean(stats_buffer["fuel_flow"]),
        fuel_flow_std=safe_std(stats_buffer["fuel_flow"]),
        exhaust_temp_mean=safe_mean(stats_buffer["exhaust_temps"]),
        exhaust_temp_std=safe_std(stats_buffer["exhaust_temps"]),
    )


# ---------------------------------------------------------------------
# ALARMS
# ---------------------------------------------------------------------
def compute_alarms(pf):
    max_egt = max([
        pf.exhaust_temp_c1 or 0.0,
        pf.exhaust_temp_c2 or 0.0,
        pf.exhaust_temp_c3 or 0.0,
        pf.exhaust_temp_c4 or 0.0,
        pf.exhaust_temp_c5 or 0.0,
        pf.exhaust_temp_c6 or 0.0,
    ])

    AlarmFlags.objects.create(
        features=pf,
        lub_oil_low=pf.lub_oil_pressure is not None and pf.lub_oil_pressure < LOW_LOP_PRESSURE,
        jacket_cw_high=pf.jacket_cw_outlet_temp is not None and pf.jacket_cw_outlet_temp > 92,
        overspeed=pf.rpm > OVERSPEED_RPM,
        high_exhaust_temp=max_egt > HIGH_EXH_TEMP,
        low_fuel_pressure=pf.fuel_pressure is not None and pf.fuel_pressure < LOW_FUEL_PRESSURE,
    )


# ---------------------------------------------------------------------
# PCA
# ---------------------------------------------------------------------
def compute_pca(pf):
    recent = (
        ProcessedFeatures.objects.order_by("-id")[:ROLLING_WINDOW]
    )

    if recent.count() < 5:
        return

    matrix = []
    ids = []

    for r in recent:
        vec = [
            r.rpm or 0.0,
            r.lub_oil_pressure or 0.0,
            r.jacket_cw_outlet_temp or 0.0,
            r.boost_air_pressure or 0.0,
            r.boost_air_temp or 0.0,
            r.fuel_flow or 0.0,
            r.fuel_pressure or 0.0,
            r.piston_speed_mps or 0.0,
            r.indicated_power_kw or 0.0,
            r.thermal_efficiency or 0.0,
        ]
        matrix.append(vec)
        ids.append(r.id)

    X = np.nan_to_num(np.array(matrix))

    from sklearn.decomposition import PCA
    pca = PCA(n_components=3)
    scores = pca.fit_transform(X)

    if pf.id not in ids:
        return

    idx = ids.index(pf.id)

    PCAFeatures.objects.create(
        features=pf,
        pc1=float(scores[idx, 0]),
        pc2=float(scores[idx, 1]),
        pc3=float(scores[idx, 2]),
        loadings=pca.components_.tolist(),
        explained_variance=pca.explained_variance_ratio_.tolist(),
    )


# ---------------------------------------------------------------------
# Task for Celery worker
# ---------------------------------------------------------------------
def process_tick(raw):
    engine_id = raw.get("engine_id")

    if engine_id is None:
        print("No engine_id in tick")
        return

    try:
        meta = EngineMetaData.objects.get(
        engine__engine_id=engine_id
    )
    except EngineMetaData.DoesNotExist:
        print(f"No EngineMetaData linked to Engine id={engine_id}")
        return

    engineered = compute_engineered_features(raw, meta)
    exh = raw.get("exhaust_temp", [None] * 6)

    with transaction.atomic():
        pf = ProcessedFeatures.objects.create(
            timestamp=now(),
            engine=meta,
            rpm=int(raw.get("rpm") or 0),
            lub_oil_pressure=raw.get("lub_oil_pressure"),
            jacket_cw_outlet_temp=raw.get("jacket_cw_outlet_temp"),
            lub_oil_flow=raw.get("lub_oil_flow"),
            cooling_water_flow=raw.get("cooling_water_flow"),
            boost_air_temp=raw.get("boost_air_temp"),
            boost_air_pressure=raw.get("boost_air_pressure"),
            boost_air_flow_after_cooler=raw.get("boost_air_flow"),
            bmep=raw.get("bmep"),
            combustion_temp=raw.get("combustion_temp"),
            exhaust_temp_c1=exh[0],
            exhaust_temp_c2=exh[1],
            exhaust_temp_c3=exh[2],
            exhaust_temp_c4=exh[3],
            exhaust_temp_c5=exh[4],
            exhaust_temp_c6=exh[5],
            fuel_temp=raw.get("fuel_temp"),
            fuel_flow=raw.get("fuel_flow"),
            fuel_pressure=raw.get("fuel_pressure"),
            fuel_pump_rack=raw.get("fuel_pump_rack"),
            exhaust_manifold_pressure=raw.get("exhaust_manifold_pressure"),
            **engineered,
            raw_meta={"source": "sim"},
        )

    compute_rolling_stats(pf)
    compute_alarms(pf)
    compute_pca(pf)

    print(f"Processed tick for engine {engine_id}")