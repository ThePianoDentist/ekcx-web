from __future__ import annotations

import pytest

from app.mail.domain.delivery import send_email
from app.mail.domain.errors import EmailDeliveryError
from app.mail.domain.outbound import OutboundEmail


def test_send_email_log_mode(monkeypatch: pytest.MonkeyPatch):
    # Setup:
    monkeypatch.setenv("EKCX_EMAIL_MODE", "log")
    calls: list[object] = []

    def _fail_send(*_args, **_kwargs):
        calls.append(True)
        raise AssertionError("resend should not be called")

    monkeypatch.setattr("app.mail.domain.delivery.resend_api.send", _fail_send)

    # Run:
    result = send_email(
        OutboundEmail(
            to="admin@ekcx.test",
            subject="hello",
            text="body",
        )
    )

    # Check:
    assert result is None
    assert not calls


def test_send_email_resend_mode_calls_api(monkeypatch: pytest.MonkeyPatch):
    # Setup:
    monkeypatch.setenv("EKCX_EMAIL_MODE", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EKCX_EMAIL_FROM", "EKCX <noreply@mail.ekcx.co.uk>")
    captured: list[tuple[str, str, OutboundEmail]] = []

    def _fake_send(api_key: str, from_address: str, message: OutboundEmail) -> str:
        captured.append((api_key, from_address, message))
        return "msg_123"

    monkeypatch.setattr("app.mail.domain.delivery.resend_api.send", _fake_send)

    # Run:
    result = send_email(
        OutboundEmail(
            to="delivered@resend.dev",
            subject="invite",
            text="welcome",
        )
    )

    # Check:
    assert result == "msg_123"
    assert len(captured) == 1
    assert captured[0][0] == "re_test"
    assert captured[0][1] == "EKCX <noreply@mail.ekcx.co.uk>"
    assert captured[0][2].to == "delivered@resend.dev"


def test_send_email_resend_requires_key(monkeypatch: pytest.MonkeyPatch):
    # Setup:
    monkeypatch.setenv("EKCX_EMAIL_MODE", "resend")
    monkeypatch.setenv("EKCX_EMAIL_FROM", "noreply@test.local")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    # Run / Check:
    with pytest.raises(EmailDeliveryError, match="RESEND_API_KEY"):
        send_email(
            OutboundEmail(
                to="user@example.com",
                subject="x",
                text="y",
            )
        )