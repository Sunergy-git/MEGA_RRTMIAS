from django.urls import path
from .views import ingest_engine_data

urlpatterns = [
    path('ingest/', ingest_engine_data),
]