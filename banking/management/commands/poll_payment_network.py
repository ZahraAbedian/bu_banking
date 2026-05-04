import time

from django.core.management.base import BaseCommand

from banking.payment_network import (
    get_pending_queue,
    acknowledge_queue_item,
    PaymentNetworkError,
)
from banking.payment_handlers import handle_authorize_request


class Command(BaseCommand):
    help = "Poll the payment network queue and process pending payment items."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=3,
            help="Seconds between queue checks.",
        )

    def handle(self, *args, **options):
        interval = options["interval"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Started payment network polling every {interval} seconds."
            )
        )

        while True:
            try:
                queue = get_pending_queue()
                items = queue.get("items", [])

                if not items:
                    self.stdout.write("No pending payment items.")

                for item in items:
                    item_id = item.get("id")
                    item_type = item.get("item_type")

                    self.stdout.write(f"Processing item {item_id}: {item_type}")

                    if item_type == "authorize_request":
                        handle_authorize_request(item)
                        acknowledge_queue_item(item_id)

                    elif item_type == "transaction_update":
                        acknowledge_queue_item(item_id)

                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Unknown queue item type: {item_type}"
                            )
                        )
                        acknowledge_queue_item(item_id)

            except PaymentNetworkError as e:
                self.stdout.write(self.style.ERROR(str(e)))

            except Exception as e:
                import traceback
                self.stdout.write(self.style.ERROR(f"Unexpected polling error: {e}"))
                traceback.print_exc()

            time.sleep(interval)