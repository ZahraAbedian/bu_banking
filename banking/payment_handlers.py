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
    print("AUTHORIZE ITEM:", item)

    item_id = item.get("id")
    payload = item.get("payload") or {}

    print("PAYLOAD:", payload)

    card_number = payload.get("card_number")
    merchant_id = payload.get("merchant_id") or "unknown"

    print("CARD NUMBER:", card_number)
    print("MERCHANT ID:", merchant_id)
    


    try:
        amount = Decimal(str(payload.get("amount")))
        print("AMOUNT:", amount)
    except (InvalidOperation, TypeError, ValueError):
        print("DECLINED: invalid amount could not parse")
        return respond_to_authorization(
            item_id=item_id,
            approve=False,
            rsponse_code=RESPONSE_INVALID_AMOUNT,
        )

    if amount <= 0:
        print("DECLINED: invalid amount - non-positive")
        return respond_to_authorization(
            item_id=item_id,
            approve=False,
            response_code=RESPONSE_INVALID_AMOUNT,
        )

    print("ABOUT TO LOOK UP CARD...")

    try: 
        card = Card.objects.select_related("account").get(
            card_number=card_number,
            active=True
        )
        print("CARD FOUND:", card.id, card.card_number)

    except Card.DoesNotExist:
        print("DECLINED: invalid card")
        print("CARDS IN DATABASE:", list(Card.objects.values_list("card_number", "active")))
        return respond_to_authorization(
                item_id=item_id,
                approve=False,
                response_code=RESPONSE_INVALID_CARD,
            )
        
    account = card.account
    print("ACCOUNT:", account.id, account.name, account.starting_balance)

    if account.starting_balance < amount:
        print("DECLINED: insufficient funds")
        return respond_to_authorization(
            item_id=item_id,
            approve=False,
            response_code=RESPONSE_INSUFFICIENT_FUNDS,
            )  

    print("APPROVED! Creating transaction")
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


from decimal import Decimal
from .models import Card, Transaction, Business


def handle_transaction_update(item):
    payload = item.get("payload") or item

    card_number = payload.get("card_number")
    amount = Decimal(str(payload.get("amount", "0")))
    merchant_id = payload.get("merchant_id") or "unknown"
    status_value = payload.get("status")

    print("TRANSACTION UPDATE:", payload)

    if status_value not in ["authorized", "approved", "settled"]:
        print("Ignoring non-approved transaction update:", status_value)
        return

    try:
        card = Card.objects.select_related("account").get(
            card_number=card_number,
            active=True,
        )
    except Card.DoesNotExist:
        print("Transaction update ignored: card not found")
        return

    account = card.account

    account.starting_balance -= amount
    account.save()

    business, _ = Business.objects.get_or_create(
        id=merchant_id,
        defaults={
            "name": merchant_id,
            "category": "External Merchant",
            "sanctioned": False,
        },
    )

    Transaction.objects.create(
        transaction_type="payment",
        amount=amount,
        from_account=account,
        business=business,
    )

    print("Local transaction saved from transaction_update")