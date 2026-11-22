# VPS deploy (GitHub Actions)

Issue: [#34](https://github.com/ThePianoDentist/ekcx-web/issues/34).

| Branch | Clone | systemd unit | URL |
|--------|-------|--------------|-----|
| `staging` | `/home/jdog/ekcx-dev` | `dev-ekcx.service` | [dev.ekcx.co.uk](https://dev.ekcx.co.uk) |
| `main` | `/home/jdog/ekcx-web` | `ekcx.service` | [ekcx.co.uk](https://ekcx.co.uk) |

Push to either branch runs [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml): SSH → `git pull --ff-only` → [`scripts/vps-deploy.sh`](../scripts/vps-deploy.sh) (`uv sync`, Alembic, `systemctl restart`).

## One-time VPS setup

### Clones

- Prod: `/home/jdog/ekcx-web` on `main`.
- Staging: `/home/jdog/ekcx-dev` on `staging`.
- Both need non-interactive `git pull` from GitHub (see deploy key below).

### GitHub read-only deploy key (on-server `git pull`)

1. On the VPS: `ssh-keygen -t ed25519 -N "" -f ~/.ssh/ekcx_github_deploy`.
2. GitHub repo → **Settings → Deploy keys → Add**: paste `~/.ssh/ekcx_github_deploy.pub`, read-only.
3. `~/.ssh/config`:

   ```
   Host github.com
     IdentityFile ~/.ssh/ekcx_github_deploy
     IdentitiesOnly yes
   ```

4. In each clone: `git remote -v` should be `git@github.com:ThePianoDentist/ekcx-web.git`; test `git fetch`.

### Actions → VPS SSH key + sudoers (local script)

From your machine (needs `gh auth login` and your normal SSH to the VPS):

```bash
REMOTE_HOST=209.97.142.138 ./local/setup-github-actions-deploy.sh
```

This generates `local/github-actions-deploy` (gitignored), appends the public key to `jdog`’s `authorized_keys`, sets `DEPLOY_HOST`, `DEPLOY_USER`, and `DEPLOY_SSH_PRIVATE_KEY`, and installs [`conf/etc/sudoers.d/ekcx-deploy`](../conf/etc/sudoers.d/ekcx-deploy) on the VPS.

Options: `--secrets-only`, `--sudoers-only`, `--regenerate-key`.

Manual equivalent: ed25519 key → `authorized_keys` → repo secrets table above; then `sudo install` + `visudo -cf` for the sudoers file.

Sudoers allows only `systemctl restart ekcx.service` and `dev-ekcx.service` as `jdog`.

### `uv`

Units expect `/home/jdog/.local/bin/uv` ([`conf/etc/systemd/system/`](../conf/etc/systemd/system/)).

## Manual deploy

Same steps as the workflow:

```bash
# staging
cd /home/jdog/ekcx-dev
git pull --ff-only origin staging
./scripts/vps-deploy.sh staging

# production
cd /home/jdog/ekcx-web
git pull --ff-only origin main
./scripts/vps-deploy.sh production
```

## First autodeploy checklist

1. Merge workflow + `vps-deploy.sh` to `staging`; configure secrets and VPS items above.
2. Push to `staging` → confirm [Actions](https://github.com/ThePianoDentist/ekcx-web/actions) and dev site.
3. Merge to `main` and repeat for production.

## Troubleshooting

- **`git pull` fails on VPS** — deploy key / `authorized_keys` / SSH config.
- **`sudo: a password is required`** — install `ekcx-deploy` sudoers fragment.
- **Wrong tree** — `vps-deploy.sh` checks cwd and branch; fix checkout in that clone.
- **Workflow SSH fails** — `DEPLOY_*` secrets, host key, and Actions public key in `authorized_keys`.

Initial nginx/systemd/bootstrap for dev is still [`local/deploy-dev-ekcx.sh`](../local/deploy-dev-ekcx.sh) (gitignored); server units live under `conf/etc/`.