# Current State

This document summarizes the existing system as observed in the repository. It avoids secrets and operational credentials.

## Existing System

- A Telegram bot is the main user interface.
- A Telethon user client can send Telegram messages after explicit confirmation.
- A Flask web interface runs on the VPS.
- Trello integration is connected to the HairLove workflow.
- GitHub Actions are used for server checks, Telegram auth diagnostics, and deployment.
- Server diagnostics are reported through GitHub issues/comments.
- The current assistant brain is implemented through Claude/Anthropic API code.

## What Works

- Repository access is readable by Codex.
- The `Claud` repository contains a functioning assistant structure.
- Telegram authorization and Trello diagnostics have been exercised through GitHub workflows.
- The existing implementation has a useful memory/context pattern in `CLAUDE.md` and `MEMORY.md`.

## Main Risks

- Operational details and sensitive context are too close to committed documentation.
- GitHub workflows contain several diagnostic paths that should be simplified before production hardening.
- The current assistant and deployment flow are tightly coupled.
- There is no separate staging lane for a Codex/OpenAI-based version yet.

## Principle

Do not replace the current working Claude path until a separate Codex path is documented, tested, and approved.
