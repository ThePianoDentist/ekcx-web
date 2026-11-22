# Server upgrade (exck-web)

DigitalOcean VPS **exck-web**: Ubuntu **23.10** (EOL), multi-site nginx, apps under `/home/jdog`. DNS on DO (`209.97.142.138`). SSH key-only on **port 22**.

Reference configs in repo: `conf/etc/nginx/`, `conf/etc/systemd/`.

### Recorded inventory (2026-11-21)

| Item | Value |
|------|--------|
| Disk `/` | 11G / 24G (44%) — OK for release upgrade |
| App units (enabled) | `ekcx`, `utilityjude`, `nginx`, `fail2ban` |
| Backend listeners | nginx 80/443; `utilityjude` → `127.0.0.1:8009` (uvicorn); ekcx via gunicorn unix socket |
| Postgres | Not listening; not in enabled units |
| TLS (certbot) | `ekcx.co.uk`, `thepianodentist.co.uk`, `utilityjude.co.uk` |

**nginx `server_name` (production):** `ekcx.co.uk`, `www.ekcx.co.uk`, `kentcoast2coast.co.uk`, `www.kentcoast2coast.co.uk`, `thepianodentist.co.uk`, `www.thepianodentist.co.uk`, `utilityjude.co.uk`, `www.utilityjude.co.uk` (site file `kc2c`).

**Post-upgrade smoke URLs:**

```bash
for h in ekcx.co.uk www.ekcx.co.uk kentcoast2coast.co.uk www.kentcoast2coast.co.uk \
  thepianodentist.co.uk www.thepianodentist.co.uk utilityjude.co.uk www.utilityjude.co.uk; do
  echo -n "$h: "; curl -sS -o /dev/null -w '%{http_code}\n' "https://$h/" || echo FAIL
done
```

**Note:** `kentcoast2coast.co.uk` is not in `certbot certificates` output — check nginx `ssl_certificate` for that vhost after upgrade.

**Choose one path:**

| Path | When |
|------|------|
| [In-place upgrade](#in-place-upgrade-2310--2404) | Accept downtime; snapshot rollback is OK |
| [New droplet migration](#new-droplet-migration-archived-plan) | Safer cutover; minimal reliance on apt release upgrade |

---

## In-place upgrade (23.10 → 24.04)

**Goal:** Same droplet, Ubuntu 24.04 LTS, patched packages from `noble`.

**Rollback:** DO droplet **snapshot** taken immediately before upgrade. If broken: power off → restore snapshot (or rebuild droplet from snapshot). Expect **1–4 h** downtime.

### Before (day before, optional)

1. **Snapshot** live system (baseline).
2. DO **Networking → Domains**: set TTL **300** on all A records still pointing at this host (helps if you must revert and browsers cache hard — optional for in-place).
3. Run read-only inventory; keep output in a local note:

```bash
hostname; lsb_release -a; df -hT
sudo ss -tulpn
systemctl list-unit-files --type=service --state=enabled --no-pager
sudo nginx -T 2>/dev/null | awk '/server_name/ {print}' | sort -u
sudo certbot certificates
```

### Maintenance window — start

1. **Second snapshot** (name e.g. `pre-release-upgrade-24.04`).
2. Open **DO Droplet → Access → Launch recovery console** (or DRO Web Console). Do not rely on SSH alone.
3. Optional: stop public apps (short blank page / connection refused behind nginx if you stop nginx too):

```bash
sudo systemctl stop ekcx utilityjude
# optional: sudo systemctl stop nginx
```

4. Refresh current system:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y
```

5. Release upgrader:

```bash
sudo apt install -y update-manager-core
grep -E '^Prompt=' /etc/update-manager/release-upgrades   # usually Prompt=normal
```

6. **Dry run is not available** for `do-release-upgrade`; proceed only if snapshot exists.

```bash
sudo do-release-upgrade
```

- Accept defaults unless you understand the prompt (config file merges: prefer **keep current** for `sshd`, `nginx`, `fail2ban` when unsure).
- If asked to restart services: **yes**.
- Reboot when prompted.

7. If `do-release-upgrade` says no release found (EOL quirks):

```bash
sudo sed -i 's/^Prompt=.*/Prompt=normal/' /etc/update-manager/release-upgrades
sudo do-release-upgrade -d   # last resort; only with snapshot
```

If still blocked, use [new droplet migration](#new-droplet-migration-archived-plan) instead.

### After reboot

1. Confirm release:

```bash
lsb_release -a    # expect 24.04 noble
uname -r
```

2. Fix packages and security:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt autoremove -y
apt-cache policy nginx | head -5   # should show noble / noble-security
```

3. **SSH:** connect with `ssh -p 22 jdog@209.97.142.138`. If locked out, use the DO console.

4. **Stack check:**

```bash
sudo nginx -t && sudo systemctl restart nginx
sudo systemctl restart ekcx utilityjude
systemctl is-active nginx ekcx utilityjude fail2ban
cd ~/ekcx-web && uv sync    # refresh venv if Python major changed
```

5. **TLS:**

```bash
sudo certbot renew --dry-run
systemctl list-timers --all | grep certbot
```

6. **Smoke test** every `server_name` from pre-upgrade nginx output (browser or `curl -I https://…`).

7. **Hardening** (if not already):

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# optional: enable ufw allow 22,80,443
```

### If it fails

- Do not run `apt --fix-broken` loops for hours if services are dead and deadline matters.
- **DO → Snapshots → restore** pre-upgrade snapshot (or create new droplet from that snapshot to get back to 23.10 quickly).
- File issues / switch to [new droplet migration](#new-droplet-migration-archived-plan).

### Known risks on this host

- Several nginx vhosts and systemd units; dpkg may ask about modified configs.
- **snap certbot** may need `snap refresh` after upgrade.
- SSH is **port 22** — verify it still listens after upgrade via the console before closing the session.
- Large homedir (`~2.6G`); disk OK at ~44% used.

---

## New droplet migration (archived plan)

**Goal:** New Ubuntu **24.04** droplet; copy apps and config; cutover via **Reserved IP** or DNS A records. Old droplet kept for rollback until decommission.

**When:** In-place fails, or you want ~90%+ success without touching apt release upgrade.

### Phase 0 — IP type

- DO **Networking → Reserved IPs**: is **209.97.142.138** there?
- **Droplet → exck-web → Public IPv4**: same address?

| Type | Cutover |
|------|---------|
| Reserved IP | Assign IP to new droplet; DNS unchanged |
| Droplet public IP only | DO Domains: point all A records to `NEW_IP` |

List hostnames:

```bash
sudo nginx -T 2>/dev/null | awk '/server_name/ {for(i=2;i<=NF;i++) gsub(/;/,"",$i); print}' | tr ' ' '\n' | sort -u | grep -vE '^_|^$'
```

### Phase 1 — Old server

1. Snapshot exck-web.
2. TTL **300** on all affected domains; wait ~30 min.
3. Note enabled units: `ekcx`, `utilityjude`, nginx sites `ekcx`, `kc2c` (`kentcoast2coast.co.uk`), `thepianodentist`, `utilityjude`.

### Phase 2 — New droplet

- Ubuntu **24.04 LTS**, same region, ≥25 GB.
- SSH key for `jdog`. **Do not** restore 23.10 snapshot onto it.

```bash
sudo apt update && sudo DEBIAN_FRONTEND=noninteractive apt full-upgrade -y
sudo apt install -y nginx fail2ban unattended-upgrades rsync
sudo snap install --classic certbot
```

UFW: allow 22, 80, 443. Create `jdog`, `/var/log/ekcx`, install `uv` for `jdog`. SSH stays on **port 22**.

### Phase 3 — Copy old → new

From **old** as `jdog` (set `NEW_IP`):

```bash
NEW_IP=...
sudo rsync -aHAX --numeric-ids --exclude '.cache/' /home/jdog/ jdog@${NEW_IP}:/home/jdog/
sudo rsync -aHAX /etc/nginx/sites-available/ /etc/nginx/sites-enabled/ jdog@${NEW_IP}:/tmp/nginx/
sudo rsync -aHAX /etc/letsencrypt/ jdog@${NEW_IP}:/tmp/letsencrypt/
sudo rsync -aHAX /etc/systemd/system/*.service jdog@${NEW_IP}:/tmp/systemd/
```

On **new**: merge into `/etc/nginx`, `/etc/letsencrypt`, `/etc/systemd/system`; `nginx -t`; `uv sync` in each app dir; `daemon-reload`; `enable --now` units.

### Phase 4 — Test

```bash
curl -I --resolve 'HOST:443:NEW_IP' https://HOST/
```

`certbot renew --dry-run` on new box.

### Phase 5 — Cutover

Reserved IP → reassign to new droplet; or update all A records to `NEW_IP`. Stop nginx/apps on old when satisfied.

### Phase 6 — Decommission

After 3–7 days: final snapshot optional; **destroy** old droplet to stop billing.

### What to copy (whole VPS)

| Item | Path |
|------|------|
| Apps | `/home/jdog/` (exclude `.cache/`) |
| ekcx extra data | `/home/jdog/results` |
| nginx | `sites-available`, `sites-enabled` |
| TLS | `/etc/letsencrypt` |
| systemd | `ekcx.service`, `utilityjude.service`, others as needed |
| Skip | dev-ekcx |

---

## Post-upgrade (either path)

- `nginx` from **noble-security** via `unattended-upgrades`.
- Keep certbot on **snap**; webroot `/.well-known/acme-challenge/` on port 80 and 443 per `conf/etc/nginx/sites-available/ekcx`.
- Repo unit paths: live **ekcx** uses `/home/jdog/ekcx-web` and **uv** (update `conf/etc/systemd/system/ekcx.service` if it still says poetry).