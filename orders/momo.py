import base64
import uuid

import requests
from django.conf import settings


class MomoConfigurationError(Exception):
    pass


class MomoRequestError(Exception):
    pass


class MomoCollectionClient:
    def _configuration_is_complete(self):
        return all((settings.MOMO_COLLECTION_SUBSCRIPTION_KEY, settings.MOMO_COLLECTION_API_USER, settings.MOMO_COLLECTION_API_KEY))

    def _token(self):
        if not self._configuration_is_complete():
            raise MomoConfigurationError("MTN MoMo sandbox credentials have not been configured.")
        credentials = f"{settings.MOMO_COLLECTION_API_USER}:{settings.MOMO_COLLECTION_API_KEY}".encode()
        response = requests.post(
            f"{settings.MOMO_BASE_URL}/collection/token/",
            headers={
                "Authorization": f"Basic {base64.b64encode(credentials).decode()}",
                "Ocp-Apim-Subscription-Key": settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
            },
            timeout=15,
        )
        if not response.ok:
            raise MomoRequestError("Unable to authenticate with MTN MoMo.")
        return response.json()["access_token"]

    def request_to_pay(self, *, amount, currency, phone_number, external_id):
        reference_id = uuid.uuid4()
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Ocp-Apim-Subscription-Key": settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
            "X-Reference-Id": str(reference_id),
            "X-Target-Environment": settings.MOMO_ENVIRONMENT,
            "Content-Type": "application/json",
        }
        if settings.MOMO_CALLBACK_URL and settings.MOMO_ENVIRONMENT != "sandbox":
            headers["X-Callback-Url"] = settings.MOMO_CALLBACK_URL
        response = requests.post(
            f"{settings.MOMO_BASE_URL}/collection/v1_0/requesttopay",
            headers=headers,
            json={
                "amount": f"{amount:.2f}", "currency": currency, "externalId": str(external_id),
                "payer": {"partyIdType": "MSISDN", "partyId": phone_number},
                "payerMessage": f"Twinpeaks order {external_id}", "payeeNote": "Twinpeaks checkout",
            },
            timeout=20,
        )
        if response.status_code != 202:
            raise MomoRequestError("MTN MoMo could not start this payment request.")
        return reference_id

    def get_status(self, reference_id):
        response = requests.get(
            f"{settings.MOMO_BASE_URL}/collection/v1_0/requesttopay/{reference_id}",
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Ocp-Apim-Subscription-Key": settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
                "X-Target-Environment": settings.MOMO_ENVIRONMENT,
            },
            timeout=15,
        )
        if not response.ok:
            raise MomoRequestError("MTN MoMo could not retrieve this payment status.")
        return response.json()
