import base64
import uuid

import requests
from django.conf import settings


class MomoConfigurationError(Exception):
    pass


class MomoRequestError(Exception):
    pass


class MomoAmbiguousError(MomoRequestError):
    """A request may have reached the provider. Do not issue another charge."""


class MomoCollectionClient:
    def _configuration_is_complete(self):
        return all((settings.MOMO_COLLECTION_SUBSCRIPTION_KEY, settings.MOMO_COLLECTION_API_USER, settings.MOMO_COLLECTION_API_KEY))

    def _token(self):
        if not self._configuration_is_complete():
            raise MomoConfigurationError("MTN MoMo sandbox credentials have not been configured.")
        credentials = f"{settings.MOMO_COLLECTION_API_USER}:{settings.MOMO_COLLECTION_API_KEY}".encode()
        try:
            response = requests.post(
                f"{settings.MOMO_BASE_URL}/collection/token/",
                headers={
                    "Authorization": f"Basic {base64.b64encode(credentials).decode()}",
                    "Ocp-Apim-Subscription-Key": settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise MomoRequestError('Unable to authenticate with MTN MoMo. Please retry this payment reference.') from exc
        if not response.ok:
            raise MomoRequestError("Unable to authenticate with MTN MoMo.")
        try:
            token = response.json()["access_token"]
            if not isinstance(token, str) or not token:
                raise ValueError()
            return token
        except (ValueError, KeyError, TypeError) as exc:
            raise MomoRequestError('Invalid MTN MoMo authentication response.') from exc

    def request_to_pay(self, *, amount, currency, phone_number, external_id, reference_id=None):
        reference_id = reference_id or uuid.uuid4()
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Ocp-Apim-Subscription-Key": settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
            "X-Reference-Id": str(reference_id),
            "X-Target-Environment": settings.MOMO_ENVIRONMENT,
            "Content-Type": "application/json",
        }
        if settings.MOMO_CALLBACK_URL and settings.MOMO_ENVIRONMENT != "sandbox":
            headers["X-Callback-Url"] = settings.MOMO_CALLBACK_URL
        try:
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
        except requests.RequestException as exc:
            raise MomoAmbiguousError('Payment submission is unconfirmed. Check the existing reference; do not start another payment.') from exc
        if response.status_code != 202:
            if response.status_code >= 500 or response.status_code in {408, 409, 429}:
                raise MomoAmbiguousError('Payment submission is unconfirmed. Check the existing reference; do not start another payment.')
            raise MomoRequestError("MTN MoMo could not start this payment request.")
        return reference_id

    def get_status(self, reference_id):
        try:
            response = requests.get(
                f"{settings.MOMO_BASE_URL}/collection/v1_0/requesttopay/{reference_id}",
                headers={
                    "Authorization": f"Bearer {self._token()}",
                    "Ocp-Apim-Subscription-Key": settings.MOMO_COLLECTION_SUBSCRIPTION_KEY,
                    "X-Target-Environment": settings.MOMO_ENVIRONMENT,
                },
                timeout=15,
            )
        except requests.RequestException as exc:
            raise MomoRequestError('Unable to refresh payment status. The existing payment is unchanged.') from exc
        if not response.ok:
            raise MomoRequestError("MTN MoMo could not retrieve this payment status.")
        try:
            data = response.json()
            if not isinstance(data, dict) or data.get('status') not in {'SUCCESSFUL', 'FAILED', 'REJECTED', 'TIMEOUT', 'PENDING'}:
                raise ValueError()
            return data
        except (ValueError, TypeError) as exc:
            raise MomoRequestError('Invalid MTN MoMo status response. The existing payment is unchanged.') from exc
