import requests
from django.conf import settings

class PaymentNetworkError(Exception):
    pass

def _headers():
    # add the key into the headers

    if not settings.PAYMENT_API_KEY:
        raise PaymentNetworkError("PAYMENT_API_KEY is not configured")

    return {
        "X-API-Key": settings.PAYMENT_API_Key,
        "Content-Type": "application/json",
    }


def get_pending_queue():
    # call the api to get the pending queue
    
    url = f"{settings.PAYMENT_NETWORK_BASE_URL}/api/queue/pending"
    response = requests.get(url, headers=_headers(), timeout=10)

    if response.status_code >= 400:
        raise PaymentNetworkError(f"failed to fetch pending queue: {response.status_code} - {response.text}")
    
    return response.json()


def respond_to_authorization(item_id, approve, response_code):
    # call the api to respond to the authorization

    url = f"{settings.PAYMENT_NETWORK_BASE_URL}/api/queue/authorize/{item_id}/respond"
    payload = {
        "approve": approve,
        "response_code": response_code,
    }
    response = requests.post(url, json=payload, headers=_headers(), timeout=10)

    if response.status_code >= 400:
        raise PaymentNetworkError(
            f"Failed to respond to authorization: {response.status_code} {response.text}"
        )

    return response.json()


def acknowledge_queue_item(item_id):
    # call the api to acknowledge the queue item
    
    url = f"{settings.PAYMENT_NETWORK_BASE_URL}/api/queue/ack/{item_id}"
    response = requests.post(url, headers=_headers(), timeout=10)

    if response.status_code >= 400:
        raise PaymentNetworkError(
            f"Failed to acknowledge queue item {item_id}: {response.status_code} {response.text}"
        )

    return response.json()