# Development guide

## Branching

Checkout a new branch for each feature or fix. Don't commit straight to `main`.

## PRDs

For anything more than a minor change or small fix, write an AI-generated PRD before coding.

- Put it in [`docs/PRDs/`](PRDs/), named after the GitHub issue (e.g. `123-rider-normalisation.md`).
- Reference the issue number in the PRD.

Skip a PRD for typos, tiny copy tweaks, and similarly small fixes.

## Shipping

1. Test locally (`make run`, exercise the change).
2. Open a pull request.
3. Ask for review if you're unsure.
5. Check tests pass
  - Will try and automate this
4. Merging without review (yolo) is fine when you're confident (or not)
    - I feel like especially with AI-coding, gating everything behind needing reviews is inefficient.
    - People can review post-merge and suggest followups
    - Reviews much more important when project is live and runing with users, and not greenfield any more
    - We'll do a tidying sweep before making big refactor live

## AI agents

If you notice AI make the same mistake multiple times, prod it to add a concise rule to [`AGENTS.md`](../AGENTS.md).
