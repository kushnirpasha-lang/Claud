# Security Notes

## Rules

- Do not commit API keys, bot tokens, SSH keys, phone codes, session files, or private identifiers.
- Use GitHub Secrets for CI/CD credentials.
- Use server `.env` for runtime configuration.
- Keep production deploys explicit and reviewable.
- Rotate any credential that may have appeared in chat, logs, commits, screenshots, or issue comments.

## Items To Review

- GitHub Actions secrets and repository permissions.
- VPS `.env` contents.
- Telegram bot token and Telethon session handling.
- Trello token permissions.
- Any old API keys referenced in documentation or diagnostics.

## Safer Operating Model

- `main` holds stable code.
- New Codex experiments live under `codex/`.
- Production-impacting changes should go through a named branch and PR.
- Diagnostics should redact secrets and personal data by default.
