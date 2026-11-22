from __future__ import annotations

import httpx

from app.mail.domain.errors import EmailDeliveryError
from app.mail.domain.outbound import OutboundEmail


def send(api_key: str, from_address: str, message: OutboundEmail) -> str:
    payload: dict[str, object] = {
        "from": from_address,
        "to": [message.to],
        "subject": message.subject,
        "text": message.text,
    }
    if message.html:
        payload["html"] = message.html

    response = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )
    if response.status_code >= 400:
        detail = response.text.strip() or response.reason_phrase
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("message"):
                detail = str(body["message"])
        except ValueError:
            pass
        raise EmailDeliveryError(f"Resend API {response.status_code}: {detail}")

    body = response.json()
    message_id = body.get("id")
    if not message_id:
        raise RuntimeError(f"Resend API returned no id: {body!r}")
    return str(message_id)