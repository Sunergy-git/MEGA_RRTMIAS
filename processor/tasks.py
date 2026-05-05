from celery import shared_task
from processor.services import process_tick

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def process_engine_tick(self, tick: dict):
    return process_tick(tick)