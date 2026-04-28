from decimal import Decimal
from django.db import transaction
from .models import Card, Transaction, Business
from .payment_network import respond_to_authorization


RESPONSE_APPROVED = "00"
RESPONSE_INVALID_CARD = "14"
RESPONSE_INSUFFICIENT_FUNDS = "51"
RESPONSE_INVALID_AMOUNT = "13"
RESPONSE_BANK_MISCONFIGURED = "15"
RESPONSE_GENERIC_DECLINE = "05"

def handle_authorize_request(item):
    item_id = item.get("id")
    payload = item.get("payload") or {}

    card_number = payload.get("card_number")
    merchant_id = payload.get("merchant_id") or "unknown"

    try:
        amount = Decimal(str(payload.get("amount")))
    except (InvalidOperation, TypeError, ValueError):
        return respond_to_authorization(
            item_id=item_id,
            approve=False,
            rsponse_code=RESPONSE_INVALID_AMOUNT,
        )

    if amount <= 0:
        return respond_to_authorization(
            item_id=item_id,
            approve=False,
            response_code=RESPONSE_INVALID_AMOUNT,
        )

        try: 
            card = Card.objects.select_related("account").get(
                card_number=card_number,
                active=True
            )
        except Card.DoesNotExist:
            return respond_to_authorization(
                item_id=item_id,
                approve=False,
                response_code=RESPONSE_INVALID_CARD,
            )
        
        account = card.account

        if account.starting_balance < amount:
            return respond_to_authorization(
                item_id=item_id,
                approve=False,
                response_code=RESPONSE_INSUFFICIENT_FUNDS,
            )

        with transaction.atomic():
            account.starting_balance -= amount
            account.save()

            business, _ = Business.objects.get_or_create(
                id=merchant_id,
                defaults={
                    "name": merchant_id,
                    "category": "external merchant",
                    "sanctioned": False,
                },
            )

            Transaction.objects.create(
                transaction_type="payment",
                amount=amount,
                from_account=account,
                business=business
            )

            return respond_to_authorization(
                item_id=item_id,
                approve=True,
                response_code=RESPONSE_APPROVED,
            )