from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils.timezone import now

from .serializers import EngineDataSerializer
from processor.models import EngineMetaData, ProcessedFeatures
from django.http import JsonResponse




@api_view(['POST'])
def ingest_engine_data(request):
    serializer = EngineDataSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    data = serializer.validated_data

    try:
        engine = EngineMetaData.objects.get(id=data["engine_id"])
    except EngineMetaData.DoesNotExist:
        return Response({"error": "Invalid engine_id"}, status=404)

    exh = data["exhaust_temp"]

    pf = ProcessedFeatures.objects.create(
        timestamp=now(),
        engine=engine,
        rpm=data["rpm"],
        lub_oil_pressure=data["lub_oil_pressure"],
        jacket_cw_outlet_temp=data["jacket_cw_outlet_temp"],
        boost_air_pressure=data["boost_air_pressure"],
        boost_air_temp=data["boost_air_temp"],
        fuel_flow=data["fuel_flow"],
        fuel_pressure=data["fuel_pressure"],
        exhaust_temp_c1=exh[0],
        exhaust_temp_c2=exh[1],
        exhaust_temp_c3=exh[2],
        exhaust_temp_c4=exh[3],
        exhaust_temp_c5=exh[4],
        exhaust_temp_c6=exh[5],
        raw_meta={"source": "api"},
    )

    return Response({"status": "stored", "id": pf.id})
def latest_engine_data(request, engine_id):
    obj = ProcessedFeatures.objects.filter(
        engine_id=engine_id
    ).order_by('-id').first()

    if not obj:
        return JsonResponse({})

    return JsonResponse({
        "rpm": obj.rpm,
        "lub_oil_pressure": obj.lub_oil_pressure,
        "jacket_cw_outlet_temp": obj.jacket_cw_outlet_temp
    })
