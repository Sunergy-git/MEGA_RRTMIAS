from django.db import models

from django.db import models
from django.utils.timezone import now
from core.models import Engine


class EngineMetaData(models.Model):
    """
    Technical metadata associated with a real engine_id owned by a customer.
    One-to-one with CustomerEngine.
    """
    engine = models.OneToOneField(
        Engine,
        on_delete=models.CASCADE,
        related_name="metadata"
    )

    engine_name = models.CharField(max_length=128, unique=True)
    model_number = models.CharField(max_length=64, blank=True, null=True)

    rated_power_kw = models.FloatField(null=True, blank=True)
    rated_rpm = models.IntegerField(null=True, blank=True)
    cylinders = models.IntegerField(null=True, blank=True)

    fuel_type = models.CharField(max_length=64, null=True, blank=True)
    firing_order = models.CharField(max_length=64, null=True, blank=True)
    bore_mm = models.FloatField(null=True, blank=True)
    stroke_mm = models.FloatField(null=True, blank=True)
    valve_overlap_deg = models.FloatField(null=True, blank=True)
    intake_manifold_cs_area = models.FloatField(null=True, blank=True)
    exhaust_manifold_cs_area = models.FloatField(null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.engine_name} ({self.model_number})"


class ProcessedFeatures(models.Model):
    """
    Per-second tick from processor.
    """
    timestamp = models.DateTimeField(default=now, db_index=True)

    engine = models.ForeignKey(
        EngineMetaData,
        on_delete=models.CASCADE,
        related_name='processed'
    )

    rpm = models.IntegerField()

    lub_oil_pressure = models.FloatField(null=True, blank=True)
    jacket_cw_outlet_temp = models.FloatField(null=True, blank=True)
    lub_oil_flow = models.FloatField(null=True, blank=True)
    cooling_water_flow = models.FloatField(null=True, blank=True)

    boost_air_temp = models.FloatField(null=True, blank=True)
    boost_air_pressure = models.FloatField(null=True, blank=True)
    boost_air_flow_after_cooler = models.FloatField(null=True, blank=True)

    bmep = models.FloatField(null=True, blank=True)
    combustion_temp = models.FloatField(null=True, blank=True)

    exhaust_temp_c1 = models.FloatField(null=True, blank=True)
    exhaust_temp_c2 = models.FloatField(null=True, blank=True)
    exhaust_temp_c3 = models.FloatField(null=True, blank=True)
    exhaust_temp_c4 = models.FloatField(null=True, blank=True)
    exhaust_temp_c5 = models.FloatField(null=True, blank=True)
    exhaust_temp_c6 = models.FloatField(null=True, blank=True)

    fuel_temp = models.FloatField(null=True, blank=True)
    fuel_flow = models.FloatField(null=True, blank=True)
    fuel_pressure = models.FloatField(null=True, blank=True)
    fuel_pump_rack = models.FloatField(null=True, blank=True)

    exhaust_manifold_pressure = models.FloatField(null=True, blank=True)

    piston_force = models.FloatField(null=True, blank=True)
    mechanical_efficiency = models.FloatField(null=True, blank=True)
    indicated_power_kw = models.FloatField(null=True, blank=True)
    volumetric_efficiency = models.FloatField(null=True, blank=True)
    frictional_loss_kw = models.FloatField(null=True, blank=True)
    afr = models.FloatField(null=True, blank=True)
    governor_response_time_s = models.FloatField(null=True, blank=True)
    piston_speed_mps = models.FloatField(null=True, blank=True)
    bsfc_g_per_kwh = models.FloatField(null=True, blank=True)
    thermal_efficiency = models.FloatField(null=True, blank=True)

    raw_meta = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)


class AlarmFlags(models.Model):
    features = models.ForeignKey(
        ProcessedFeatures,
        on_delete=models.CASCADE,
        related_name="alarms"
    )

    lub_oil_low = models.BooleanField(default=False)
    jacket_cw_high = models.BooleanField(default=False)
    overspeed = models.BooleanField(default=False)
    high_exhaust_temp = models.BooleanField(default=False)
    low_fuel_pressure = models.BooleanField(default=False)

    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=128, null=True, blank=True)

    created_at = models.DateTimeField(default=now)


class StatisticalFeatures(models.Model):
    features = models.ForeignKey(
        ProcessedFeatures,
        on_delete=models.CASCADE,
        related_name="stats"
    )

    window_size = models.IntegerField(default=20)

    rpm_mean = models.FloatField(null=True, blank=True)
    rpm_std = models.FloatField(null=True, blank=True)

    lub_oil_pressure_mean = models.FloatField(null=True, blank=True)
    lub_oil_pressure_std = models.FloatField(null=True, blank=True)

    boost_air_pressure_mean = models.FloatField(null=True, blank=True)
    boost_air_pressure_std = models.FloatField(null=True, blank=True)

    exhaust_temp_mean = models.FloatField(null=True, blank=True)
    exhaust_temp_std = models.FloatField(null=True, blank=True)

    fuel_flow_mean = models.FloatField(null=True, blank=True)
    fuel_flow_std = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(default=now)


class PCAFeatures(models.Model):
    features = models.ForeignKey(
        ProcessedFeatures,
        on_delete=models.CASCADE,
        related_name="pca"
    )

    pc1 = models.FloatField(null=True, blank=True)
    pc2 = models.FloatField(null=True, blank=True)
    pc3 = models.FloatField(null=True, blank=True)

    loadings = models.JSONField(null=True, blank=True)
    explained_variance = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(default=now)
