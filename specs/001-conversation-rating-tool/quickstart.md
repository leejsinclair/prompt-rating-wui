# Quickstart: Claude Code Conversation Review & Rating Tool

Validates the feature end-to-end against the acceptance scenarios in `spec.md`. Uses only
Python 3's standard library (research.md §3) — no install step.

## Prerequisites

- Python 3.9+ available (`python3 --version`).
- At least one real Claude Code CLI session already exists on the machine under
  `~/.claude/projects/**/*.jsonl` (research.md §1). If validating inside a fresh devcontainer with
  no prior history, use the "empty state" scenario below instead, or copy a sample `.jsonl` fixture
  into that location first.

## Run it

```bash
python3 -m src.server
```

Expected: a single line of output naming the bound address: `Serving on http://127.0.0.1:5148`
(FR-020: localhost-only — never `0.0.0.0`; port fixed at 5148).

- **Local machine**: open the printed URL directly in a browser.
- **VS Code remote-SSH / devcontainer**: VS Code auto-detects the listening port and offers to
  forward it (FR-017); open the forwarded URL it surfaces, with no manual port configuration.

## Validation scenarios

1. **Browse and rate (User Story 1, primary)**
   - Open the tool → confirm sessions are listed, most recent first.
   - Open a session → confirm prompts appear in the order they were given.
   - Expand a prompt → confirm Claude's response/activity is shown.
   - Rate it 1–10 → reload the page → confirm the rating is still shown (FR-005, FR-012).
   - Change that rating → confirm the new value replaces the old one, not adds to it (FR-006).

2. **Top Rated view (User Story 2)**
   - Rate several prompts across at least two different sessions with different values.
   - Open the Top Rated view → confirm ordering is highest rating first, and that two equal
     ratings are ordered by most-recently-rated first (FR-007).
   - With enough rated prompts to exceed one page, confirm pagination controls appear (FR-008).
   - Re-rate a prompt from within this view → confirm the list re-orders without navigating away
     (FR-009).

3. **Empty states (Clarifications 2026-09-19, Q4)**
   - Against a `ratings.json`-free, session-history-free environment: confirm both the session list
     and the Top Rated view show an explicit empty-state message, not a blank page or an error.

4. **Recovery from corrupted ratings (User Story 3)**
   - Stop the server, overwrite `~/.claude/claude-rating-tool/ratings.json` with invalid content
     (e.g. `not json`), restart.
   - Confirm the interface detects this and offers a delete/reset control (FR-016), and that using
     it returns the tool to a normal, empty-ratings working state without hand-editing any file.

5. **Long content truncation (Edge Cases)**
   - Find or construct a session containing a prompt/response over ~500 words / ~2000 characters.
   - Confirm it renders truncated by default with a working "show more" control (FR-013).

6. **Graceful degradation on unusual session content (Edge Cases)**
   - Point the tool at a session directory containing one deliberately malformed `.jsonl` file
     alongside normal ones.
   - Confirm the session list still renders every other session, and that the malformed one either
     doesn't block the list or is clearly indicated as unavailable rather than erroring the whole
     page (FR-014).

## Contract reference

See `contracts/http-api.md` for the exact request/response shapes exercised implicitly by the
scenarios above (e.g. `GET /api/sessions`, `PUT /api/ratings/{prompt_id}`).

## Data model reference

See `data-model.md` for how a raw session `.jsonl` line maps to the Session/Prompt/Rating entities
used throughout these scenarios.
