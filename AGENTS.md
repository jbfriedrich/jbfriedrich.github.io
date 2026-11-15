# AGENTS.md — working in the friedrich.uk repo

The friedrich.uk hub: a Hugo site that aggregates the author's feeds. Read the
[README](README.md) first; reasons are in [docs/decisions.md](docs/decisions.md) and
**[docs/todo.md](docs/todo.md) holds every open task** — add new ones there and delete
them when done.

## Rules

- **Public repo: name private repos, don't link them.** This repository is public. Its
  docs may mention a private repository or a document in one by name, but never link to
  it — the link is a 404 for everyone else — and never copy infrastructure details out of
  it: no host or VM names, addresses, ports, user names, home paths or secret-manager item
  names.
- **No Node.** Hugo is pinned to a range that still runs the Tailwind standalone binary
  (README, *Hugo version*); don't add npm or a `package.json`.
- **Tests fetch live feeds** (`./tests/run.sh`) and assert structure, not named content.
  The overlay `tests/hugo.test.yaml` repeats the real sources; edit it alongside
  `hugo.yaml`.
- **A push to `master` publishes the site.** Ask before pushing. Commits only when asked;
  no `Co-Authored-By` or other AI attribution.
