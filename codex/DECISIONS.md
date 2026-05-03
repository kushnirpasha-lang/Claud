# Decisions

## 2026-05-03: Create A Separate Codex Workspace

Decision: create a new `codex/` folder for all Codex-managed planning and future implementation.

Reason: the existing Claude-based assistant may be useful and should not be disrupted while a better system is designed.

Implications:

- Existing production files are not changed by default.
- New designs, docs, and experiments go under `codex/`.
- Any migration from Claude to OpenAI must be deliberate and reversible.
