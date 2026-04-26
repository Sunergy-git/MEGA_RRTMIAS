import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MEGA_RRTMIAS.settings')

app = Celery('MEGA_RRTMIAS')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()