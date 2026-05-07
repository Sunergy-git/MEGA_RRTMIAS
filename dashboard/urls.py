from django.urls import path
from .views import home
from .views import home, live_engine

urlpatterns = [
    path('', home, name='home'),
    path('engine/<int:engine_id>/', live_engine, name='live_engine'),
]