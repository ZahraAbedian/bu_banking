import requests

from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Register this bank with the payment network."

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            required=True,
            help="Bank name, for example: Team4 Bank",
        )
        parser.add_argument(
            "--registration-key",
            required=True,
            help="One-time registration key from instructor.",
        )

    def handle(self, *args, **options):
        url = f"{settings.PAYMENT_NETWORK_BASE_URL}/api/banks"

        payload = {
            "name": options["name"],
            "registration_key": options["registration_key"],
        }

        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        if response.status_code >= 400:
            raise CommandError(
                f"Registration failed: {response.status_code} {response.text}"
            )

        data = response.json()

        self.stdout.write(self.style.SUCCESS("Bank registered successfully."))
        self.stdout.write("")
        self.stdout.write("Copy these into your .env file:")
        self.stdout.write("")
        self.stdout.write(f"PAYMENT_BANK_ID={data.get('id')}")
        self.stdout.write(f"PAYMENT_API_KEY={data.get('api_key')}")