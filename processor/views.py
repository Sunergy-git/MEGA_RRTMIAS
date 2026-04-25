from django.shortcuts import render

from django.shortcuts import render
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from .models import ProcessedFeatures, AlarmFlags
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404
from django.shortcuts import render

def dashboard(request):
    return render(request, "processor/dashboard.html")

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
def timeseries_latest(request, limit=200):
    """
    Return last `limit` processed feature rows (chronological)
    """
    limit = int(request.GET.get('limit', limit))
    rows = ProcessedFeatures.objects.order_by('-ts')[:limit]
    rows = list(reversed(list(rows)))
    data = []
    for r in rows:
        data.append({
            "ts": r.ts.isoformat(),
            "rpm_mean": r.rpm_mean,
            "rpm_max": r.rpm_max,
            "lub_oil_pressure_mean": r.lub_oil_pressure_mean,
            "jacket_cw_outlet_temp_mean": r.jacket_cw_outlet_temp_mean,
            "lub_oil_flow_mean": r.lub_oil_flow_mean,
            "cooling_water_flow_mean": r.cooling_water_flow_mean,
            "boost_air_temp_mean": r.boost_air_temp_mean,
            "boost_air_pressure_mean": r.boost_air_pressure_mean,
            "bmep_mean": r.bmep_mean,
            "combustion_temp_mean": r.combustion_temp_mean,
            "exhaust_temp_mean": r.exhaust_temp_mean,
        })
    return Response(data)

@api_view(['GET'])
def alarms_active(request):
    rows = AlarmFlags.objects.filter(cleared=False).order_by('-ts')[:200]
    data = [{"id": r.id, "ts": r.ts.isoformat(), "title": r.title, "severity": r.severity, "details": r.details} for r in rows]
    return Response(data)

@api_view(['POST'])
def alarm_reset(request):
    alarm_id = request.data.get('alarm_id')
    if not alarm_id:
        return Response({"ok": False, "reason": "alarm_id required"}, status=400)
    alarm = get_object_or_404(AlarmFlags, id=alarm_id)
    alarm.cleared = True
    alarm.cleared_at = timezone.now()
    # cleared_by left null in API (if you want, link to request.user)
    alarm.save()
    return Response({"ok": True})

