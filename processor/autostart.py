import threading
from django.apps import apps

# Import our new Django-ORM processor loop
from .services import start_processor_loop


def _run():
    """
    Internal wrapper to ensure Django is fully loaded
    before starting the processor loop.
    """
    # optional safety: wait until models are ready
    apps.check_apps_ready()

    print("🔵 Processor autostart: starting main processor loop...")
    start_processor_loop()      # infinite loop (while True)


def start_background_thread():
    """
    Called from AppConfig.ready() to automatically launch
    the processor in a daemon thread when Django boots.
    """

    print("🟢 Launching processor background thread...")

    thread = threading.Thread(
        target=_run,
        name="processor-thread",
        daemon=True
    )
    thread.start()
