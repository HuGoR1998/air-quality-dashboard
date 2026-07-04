from django.core.management.base import BaseCommand

from data_api.services import fetch_and_store_all


class Command(BaseCommand):
    help = "Fetch current air quality for all configured locations (AQ_LOCATIONS) and store them."

    def handle(self, *args, **options):
        summary = fetch_and_store_all()

        for reading in summary["created"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Stored {reading.city}, {reading.country}: "
                    f"AQI(US)={reading.aqi_us} ({reading.category}), "
                    f"temp={reading.temperature_c}C @ {reading.source_ts:%Y-%m-%d %H:%M} UTC"
                )
            )

        for err in summary["errors"]:
            self.stdout.write(self.style.ERROR(f"Error: {err}"))

        self.stdout.write(
            self.style.NOTICE(
                f"Done. {len(summary['created'])} stored, {len(summary['errors'])} failed."
            )
        )
