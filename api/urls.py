from django.urls import path
from .views import ingest_engine_data
from .views import latest_engine_data

urlpatterns = [
    path('ingest/', ingest_engine_data),
    path('engine/<int:engine_id>/latest/', latest_engine_data),
]