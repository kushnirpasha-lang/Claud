# Roadmap

## Phase 1: Safe Workspace

- Create the `codex/` folder.
- Document what exists today.
- Define safety rules and ownership boundaries.
- Avoid modifying the current Claude deployment path.

## Phase 2: Clean Architecture

- Design a separate assistant module that can use OpenAI API.
- Define configuration through environment variables only.
- Separate chat, tools, commands, and deployment concerns.
- Add a clear status and diagnostics command set.

## Phase 3: Telegram Control Layer

- Add explicit Telegram commands such as `/status`, `/tasks`, `/server`, `/logs`, and `/help`.
- Keep risky actions behind confirmation.
- Add structured command parsing before using general AI reasoning.

## Phase 4: GitHub Control Layer

- Use issues or workflow dispatch as a control surface.
- Add diagnostics that report concise results.
- Add a staging workflow for Codex-only experiments.

## Phase 5: Content And Autoposting

- Add a content queue format such as YAML or CSV.
- Validate posts before publishing.
- Add dry-run mode.
- Add separate publishing adapters for Instagram, Telegram, and other channels.

## Phase 6: Migration Or Coexistence

- Compare Claude and OpenAI behavior.
- Keep whichever path is cheaper, more reliable, and easier to maintain.
- Migrate only after tests and manual approval.
