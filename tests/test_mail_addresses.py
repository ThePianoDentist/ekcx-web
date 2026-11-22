from __future__ import annotations

import pytest

from app.mail.domain.addresses import normalize_recipient, validate_recipient
from app.mail.domain.errors import EmailDeliveryError


def test_normalize_recipient_accepts_display_name():
    # Setup / Run / Check:
    assert normalize_recipient("Jane <Jane.Doe@Example.COM>") == "jane.doe@example.com"


def test_validate_recipient_blocks_example_com_for_resend():
    # Setup / Run / Check:
    with pytest.raises(EmailDeliveryError, match="example.com"):
        validate_recipient("you@example.com", for_resend=True)