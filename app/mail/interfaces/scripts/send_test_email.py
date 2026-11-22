"""Smoke-test outbound mail (log or Resend)."""
from __future__ import annotations

import argparse
import logging
import sys

from app.mail.config import get_default_from, get_email_mode
from app.mail.domain.delivery import EmailDeliveryError, send_email
from app.mail.domain.outbound import OutboundEmail


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a test email via configured mail backend.")
    parser.add_argument(
        "--to",
        required=True,
        help="Real recipient (not you@example.com); try delivered@resend.dev while testing",
    )
    parser.add_argument(
        "--subject",
        default="EKCX mail smoke test",
        help="Subject line",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    mode = get_email_mode()
    from_addr = get_default_from()
    text = (
        f"This is a test message from ekcx-web (EKCX_EMAIL_MODE={mode}).\n"
        "If you received this via Resend, outbound mail is configured."
    )
    try:
        message_id = send_email(
            OutboundEmail(
                to=args.to.strip(),
                subject=args.subject,
                text=text,
            )
        )
    except EmailDeliveryError as exc:
        print(exc, file=sys.stderr)
        return 1

    if message_id:
        print(f"sent id={message_id} to={args.to} from={from_addr}")
    else:
        print(f"log/disabled mode: message recorded for {args.to} (no API call)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())