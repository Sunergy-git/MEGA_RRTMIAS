from rest_framework import serializers

class EngineDataSerializer(serializers.Serializer):
    engine_id = serializers.IntegerField()
    rpm = serializers.IntegerField()

    lub_oil_pressure = serializers.FloatField()
    jacket_cw_outlet_temp = serializers.FloatField()

    boost_air_pressure = serializers.FloatField()
    boost_air_temp = serializers.FloatField()

    fuel_flow = serializers.FloatField()
    fuel_pressure = serializers.FloatField()

    exhaust_temp = serializers.ListField(
        child=serializers.FloatField(),
        min_length=6,
        max_length=6
    )

    timestamp = serializers.CharField()