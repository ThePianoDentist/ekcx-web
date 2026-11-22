# Email / Resend — pickup notes

Personal ops checklist (not required for running the app). Code lives under `app/mail/`.

## Done

| Item | Detail |
|------|--------|
| Resend account | Created; MCP OAuth in Cursor works |
| Sending domain | `mail.ekcx.co.uk` in Resend |
| DMARC | Use `_dmarc.mail.ekcx.co.uk` for `From: *@mail.ekcx.co.uk` |
| Server secrets | `scripts/server-ekcx-env.sh` → `/etc/ekcx/environment` + systemd drop-ins |

## Server env (after `git pull`)

```bash
sudo ./scripts/server-ekcx-env.sh install
sudo ./scripts/server-ekcx-env.sh set RESEND_API_KEY
sudo ./scripts/server-ekcx-env.sh set EKCX_EMAIL_FROM 'EKCX <noreply@mail.ekcx.co.uk>'
sudo ./scripts/server-ekcx-env.sh set EKCX_EMAIL_MODE resend
sudo ./scripts/server-ekcx-env.sh set EKCX_SESSION_SECRET "$(openssl rand -hex 32)"
sudo ./scripts/server-ekcx-env.sh show
```

Until DNS is green in Resend, keep using their sandbox `From` for smoke tests (see Resend domain page).

## App env vars

| Variable | Purpose |
|----------|---------|
| `RESEND_API_KEY` | Required when `EKCX_EMAIL_MODE=resend` |
| `EKCX_EMAIL_FROM` | e.g. `EKCX <noreply@mail.ekcx.co.uk>` |
| `EKCX_EMAIL_MODE` | `log` (default), `resend`, or `disabled` |

## Local testing

**0. Local env** (repo-root `.env`, gitignored — template is `.env_sample`):

```bash
cp .env_sample .env   # or ./local/setup-env.sh (migrates old local/shell.env)
chmod +x local/setup-shell-env.sh local/generate-session-secret.sh local/send-test-email.sh
./local/generate-session-secret.sh   # if placeholder secret in .env
./local/setup-shell-env.sh           # Resend API key
set -a && source .env && set +a      # or source ~/.zshrc if block installed
./local/send-test-email.sh jbknight07@gmail.com   # not you@example.com
```

**1. Default (no API key)** — safe for pytest and day-to-day dev:

```bash
# EKCX_SESSION_SECRET and EKCX_EMAIL_MODE come from `.env` when the app runs
uv run python -m app.mail.interfaces.scripts.send_test_email --to YOUR_REAL_INBOX@...
```

Stdout / app logs show the message; nothing hits Resend.

**2. Real send from laptop**

```bash
export RESEND_API_KEY=re_...
export EKCX_EMAIL_MODE=resend
export EKCX_EMAIL_FROM='EKCX <noreply@mail.ekcx.co.uk>'   # or onboarding@resend.dev pre-verify
uv run python -m app.mail.interfaces.scripts.send_test_email --to your-real-inbox@...
```

**3. Automated tests**

```bash
make test   # mail tests use log mode; no network
```

**4. Resend test recipients** (no own domain yet): see [Resend test addresses](https://resend.com/docs/knowledge-base/what-email-addresses-to-use-for-testing).

## Backend (implemented)

- `app/mail/config.py` — mode, from, API key
- `app/mail/domain/outbound.py` — `OutboundEmail`
- `app/mail/domain/delivery.py` — `send_email()`
- `app/mail/data/resend_api.py` — HTTP to Resend
- `app/mail/interfaces/scripts/send_test_email.py` — CLI smoke test

## Not wired yet (product)

- [ ] Send one-time password when `create_admin` runs (or separate “invite” flow)
- [ ] Password reset (token + link + template)
- [ ] React Email templates for branded HTML
- [ ] Webhooks / bounce handling if we mail the public

## DNS quick reference

- SPF/DKIM: on **`mail.ekcx.co.uk`** per Resend dashboard
- DMARC: **`_dmarc.mail.ekcx.co.uk`** (not only apex) when From is `@mail.ekcx.co.uk`