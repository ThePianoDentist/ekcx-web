---
name: pre-push
description: >-
  Pre-push gate: scan for secrets, scrub them from all commits if found, and
  sweep the push range for common security vulnerabilities. Use before every
  git push, when the user asks to push, or when AGENTS.md pre-push checks apply.
---

# Pre-push

Run before every `git push`. Do not push until both checks pass.

## 1. Secrets

Scan the commits about to be pushed (`git log origin/<branch>..HEAD` and their diffs), plus the working tree if dirty.

Look for (non-exhaustive):

- API keys, tokens, passwords, private keys, `.env` / credential files
- Hardcoded connection strings with credentials
- Auth cookies / session secrets
- Cloud/provider keys (`AKIA…`, `sk-…`, `ghp_…`, etc.)

If anything looks secret:

1. **Stop.** Do not push.
2. Remove secrets from the working tree (env vars, secrets store, or redacted placeholders).
3. Scrub from **all** commits that contain them (history rewrite of the affected range), not only the tip.
4. Confirm the rewritten range is clean, then push.
5. If the branch was already pushed with secrets: warn the user; rotate the exposed credentials; only force-push after explicit user approval (never force-push `main`/`master` unless they explicitly demand it).

Prefer `git filter-repo` or a targeted rebase for scrubbing. Do not leave secrets in older commits of the push range.

## 2. Security sweep

Review the same push range for common issues introduced or worsened by the changes:

- Injection (SQL, command, template/XSS)
- Authn/authz gaps (missing checks, IDOR)
- Unsafe deserialization / path traversal / SSRF
- Overly permissive CORS, debug flags, or verbose errors in prod paths
- Insecure defaults (open redirects, weak crypto, raw HTML from user input)

Fix critical/high findings before push, or stop and report them. For a deeper pass, use the repo’s security-review flow when the user wants it.

## 3. Report

Briefly tell the user: secrets clean / scrubbed; security sweep result (ok or blockers). Then push only if clear.
