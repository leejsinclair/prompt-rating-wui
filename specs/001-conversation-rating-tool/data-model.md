# Data Model: Claude Code Conversation Review & Rating Tool

Source: `spec.md` Key Entities (Session, Prompt, Rating), refined against the real session-file
schema documented in `research.md` §1 and §6.

## Session

A single Claude Code conversation transcript, discovered on disk (research.md §1/§2).

| Field | Type | Notes |
|---|---|---|
| `session_id` | string | The transcript's own id; equals the JSONL filename stem. |
| `file_path` | string | Absolute path to the source `.jsonl` file. Not shown to the user; used internally and stored alongside ratings (research.md §6) for orphan detection. |
| `project_path` | string | The working directory the session ran in (`cwd` on its lines), decoded from the containing directory name. |
| `started_at` | timestamp | Timestamp of the session's first real prompt (see Prompt below). |
| `last_activity_at` | timestamp | Timestamp of the session's last line. Drives "most recent first" ordering (FR-001). |
| `prompt_count` | integer | Number of real prompts in the session (for list display; not a full prompt fetch). |
| `is_parseable` | boolean | `false` if the file could not be opened/parsed at all (FR-014: the rest of the *list* must still render). |
| `parse_warnings` | list of string | Non-fatal issues hit while parsing this session (e.g. lines with an unrecognized `type`, a malformed line skipped) — surfaced only if useful for graceful-degradation messaging, never blocking. |

**Ordering**: sessions are listed by `last_activity_at` descending (FR-001), paginated per the
Session-list ↔ Top-Rated pagination clarification.

**Lifecycle**: read-only from this tool's perspective (browse-only, FR-010). A session
disappearing (deleted/moved/renamed) is not a state on this entity — it simply stops being
discoverable, which is the trigger for a Rating becoming orphaned (see Rating below, FR-015).

## Prompt

A single developer-typed instruction within a Session, plus Claude's corresponding
response/activity (research.md §1: only string-content, non-meta, non-sidechain `user` lines
qualify as Prompts).

| Field | Type | Notes |
|---|---|---|
| `prompt_id` | string | The transcript's own `promptId`. Stable identity key used by Rating (research.md §6). |
| `session_id` | string | Parent session. |
| `position` | integer | 0-based order within the session (FR-003: "in the order they were given"). Fallback identity component if `prompt_id` is ever absent (research.md §6). |
| `text` | string | The prompt's own text (the `user` line's string `message.content`). |
| `response_text` | string | Concatenation of the following assistant turn's `text` content blocks — what's shown as "Claude's corresponding response" (FR-004). |
| `activity_summary` | string (optional) | A short, non-exhaustive indicator that additional Claude activity exists beyond plain text for that turn, shown inside the same expanded view (research.md §1) — not a separate scored artifact. **Generation rule**: count the assistant turn's `tool_use` blocks (N) and note whether any `thinking` block is present; render as `"used N tools"` (N ≥ 1, no thinking), `"used N tools, with reasoning"` (N ≥ 1, with thinking), `"internal reasoning"` (N = 0, with thinking), or omit the field entirely (N = 0, no thinking — i.e. a plain text-only response). |
| `timestamp` | timestamp | The prompt line's own timestamp. |
| `duration_seconds` | integer (optional) | Seconds from this prompt's `timestamp` to the last non-sidechain assistant line before the next prompt (FR-022). Null when either timestamp is unavailable. Elapsed time, not measured thinking time — the session files record no per-block durations. |
| `is_truncated` | boolean (derived) | `true` when `text` or `response_text` exceeds ~500 words / ~2000 characters (FR-013); drives the "show more" control. Not stored — computed at render time. |
| `rating` | integer 1–10, optional | Looked up from the Rating store by `prompt_id` (falls back to `(session_id, position)` per research.md §6); absent means unrated. |

## Rating

A developer-assigned score for one Prompt, persisted locally (FR-012), independent of any
session-store schema (research.md §6).

| Field | Type | Notes |
|---|---|---|
| `prompt_id` | string | Primary key into the ratings store (research.md §6). |
| `session_id` | string | Stored redundantly so an orphan (FR-015) can still be identified/flagged even if the session file is gone. |
| `position` | integer | Stored redundantly for the same reason, and as the fallback identity key if a `prompt_id` was ever missing at rating time. |
| `value` | integer, 1–10 | FR-005. Replacing an existing value is an overwrite, not a new record (FR-006/FR-009). |
| `rated_at` | timestamp | Updated on every set/re-rate; used only as the Top Rated view's tiebreaker (FR-007: "more recently rated prompts breaking ties" — recency of *rating*, not of the original prompt). |

**Storage location**: `~/.claude/claude-rating-tool/ratings.json` — a single, fixed, global path
independent of the tool's launch directory (resolved via Plan Integrity Finding 1: session
discovery already spans every project on the machine, so the ratings store must not be scoped to
whichever directory the server happens to be started from). The directory is created if it does
not already exist; its absence is not an error condition, unlike an existing-but-invalid file
(FR-016).

**Storage shape** (`ratings.json`, one file, FR-012):

```json
{
  "<prompt_id>": { "session_id": "...", "position": 3, "value": 8, "rated_at": "2026-09-19T10:00:00Z" }
}
```

**Validation rule**: the file must parse as a JSON object whose values match the shape above with
`value` an integer 1–10. Any failure (invalid JSON, wrong shape, out-of-range value) puts the whole
store into an "invalid" state, which is what FR-016's in-interface delete/reset control responds
to — there is no partial/per-entry repair, by design (story.md Dragon's Question 3: "if the json is
not valid, then provide a delete button in the interface and start again").

**Orphan handling (FR-015)**: at read time, if a rating's `session_id` no longer resolves to a
discoverable session (or the specific `position`/`prompt_id` can no longer be found within it), the
Top Rated view marks that entry as unavailable (or omits it — a rendering choice, not a data-model
one) rather than treating the whole ratings file as invalid. This is distinct from FR-016's
whole-file corruption case (confirmed in the resolved spec Decision on FR-015).

## Relationships

```
Session 1 ──── * Prompt ──── 0..1 Rating
```

- A Session has many Prompts, ordered by `position`.
- A Prompt has at most one current Rating (re-rating replaces, never accumulates).
- A Rating can outlive its Session (orphan case, FR-015) but never outlives being explicitly
  cleared (FR-016's reset, or a future per-entry omission from display).
