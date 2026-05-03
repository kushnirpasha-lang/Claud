# Codex Workspace

This folder is the Codex-managed workspace for improving the assistant step by step without touching the existing Claude implementation.

## Purpose

- Keep the current Claude-based assistant stable.
- Design a cleaner next-generation architecture in parallel.
- Document decisions before changing production code.
- Add new modules only when the plan is clear and reviewable.

## Ground Rules

1. Do not modify the existing `assistant/`, `.github/workflows/`, `CLAUDE.md`, or `MEMORY.md` files unless Pavel explicitly approves it.
2. New Codex work starts inside `codex/`.
3. Secrets must stay in GitHub Secrets, server `.env`, or a secure vault. Never commit API keys, tokens, phone codes, session files, or private SSH keys.
4. Every operational feature should have a status command and a clear rollback path.
5. Production deployment remains manual or explicitly approved until the new flow is trusted.

## Current Direction

The first phase is documentation and design. After that, we can add a separate OpenAI-powered assistant module, Telegram command layer, GitHub control workflows, and content/autoposting pipeline.
