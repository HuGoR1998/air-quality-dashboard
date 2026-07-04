import os
import sys

from django.apps import AppConfig


class DataApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "data_api"

    def ready(self):
        # Only run the background scheduler under the dev server, not during
        # migrate / shell / other management commands.
        if "runserver" not in sys.argv:
            return
        # Under the autoreloader, ready() runs in both the watcher and the child;
        # only start the scheduler in the child (RUN_MAIN=="true"). With
        # --noreload, RUN_MAIN is unset, so we start once.
        run_main = os.environ.get("RUN_MAIN")
        if run_main is not None and run_main != "true":
            return

        from data_api import scheduler

        scheduler.start()
