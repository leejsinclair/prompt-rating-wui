# Contract: Local HTTP API

This tool's only external interface is the local HTTP server (FR-020: localhost-only) that its own
browser frontend talks to. There is no other consumer — this contract exists to keep the frontend
and backend independently buildable/testable against a fixed shape, and to give contract tests
something concrete to check.

All responses are JSON unless noted. All endpoints are read-only with respect to session data
(browse-only, FR-010) — the only writes this API performs are to the local ratings store.

## GET /api/sessions

List sessions, most recent first, paginated (FR-001).

**Query params**: `page` (integer, default 1)

**200 response**:
```json
{
  "page": 1,
  "has_more": true,
  "sessions": [
    {
      "session_id": "51755f29-...",
      "last_activity_at": "2026-09-19T10:00:00Z",
      "prompt_count": 12,
      "is_parseable": true
    }
  ]
}
```

**Empty state**: `sessions: []`, `has_more: false` — the frontend renders the explicit empty-state
message (Clarifications session 2026-09-19, Q4) rather than treating this as an error.

## GET /api/sessions/{session_id}

The prompts within one session, in order (FR-003).

**200 response**:
```json
{
  "session_id": "51755f29-...",
  "prompts": [
    {
      "prompt_id": "78edc450-...",
      "position": 0,
      "text": "...",
      "is_truncated": false,
      "rating": null
    }
  ]
}
```
`text` here is already truncated server-side to the ~500-word/~2000-character threshold when
`is_truncated` is `true` (FR-013); the full text is fetched via the endpoint below on "show more."

**404**: unknown `session_id`.

**200 with `is_parseable: false` semantics**: if the underlying file could not be parsed at all,
`prompts` is `[]` and a top-level `error` string explains why — the session list entry (from
`GET /api/sessions`) still exists and the rest of the tool keeps working (FR-014).

## GET /api/sessions/{session_id}/prompts/{prompt_id}

The full, untruncated prompt text and response/activity for one prompt (FR-004, and the "show
more" control from FR-013).

**200 response**:
```json
{
  "prompt_id": "78edc450-...",
  "text": "...",
  "response_text": "...",
  "activity_summary": "used 2 tools",
  "rating": 8
}
```

**404**: unknown `session_id`/`prompt_id` pair.

## GET /api/prompts/search

Search prompt text across parseable sessions, limited to prompts from the last seven days.

**Query params**:
- `q` (required, non-empty string)
- `page` (integer, default 1)

Search matching uses visible prompt text (presentation markup is ignored for matching). Returned
`text` remains the humanized/truncated prompt text used by the UI.

**200 response**:
```json
{
  "page": 1,
  "has_more": false,
  "query": "needle",
  "prompts": [
    {
      "prompt_id": "78edc450-...",
      "session_id": "51755f29-...",
      "position": 0,
      "timestamp": "2026-09-19T10:00:00Z",
      "project_path": "/work/project",
      "session_title": "Initial prompt preview",
      "text": "...",
      "is_truncated": false
    }
  ]
}
```

Only prompts with parseable timestamps in the last 7 days are included.

**400**: missing/empty `q` (`{"error": "q is required."}`).

## PUT /api/ratings/{prompt_id}

Set or replace a prompt's rating (FR-005, FR-006, FR-009).

**Body**: `{"value": 8, "session_id": "51755f29-...", "position": 0}`

`session_id`/`position` are included so the server can record them alongside the rating for later
orphan detection (data-model.md § Rating) even though `prompt_id` is the lookup key.

**200 response**: the updated rating record. **400**: `value` not an integer 1–10.

## GET /api/top-rated

Paginated, rating-sorted view across all sessions (FR-007, FR-008).

**Query params**: `page` (integer, default 1)

**200 response**:
```json
{
  "page": 1,
  "has_more": false,
  "prompts": [
    {
      "prompt_id": "78edc450-...",
      "session_id": "51755f29-...",
      "value": 9,
      "rated_at": "2026-09-19T09:00:00Z",
      "text": "...",
      "is_orphaned": false
    }
  ]
}
```

Sort: `value` descending, `rated_at` descending as tiebreaker (FR-007). An entry whose session/
prompt can no longer be found is included with `is_orphaned: true` and no `text` (FR-015) rather
than being silently dropped or breaking the response — the frontend decides whether to still list
it (clearly flagged) or omit it, per FR-015's "omit or clearly flag."

**Empty state**: `prompts: []` — explicit empty-state message (Clarifications, Q4).

## PUT /api/ratings/{prompt_id} → re-rating from the Top Rated view

Same endpoint as above; the Top Rated view calls it directly to satisfy FR-009 without a separate
route.

## POST /api/ratings/reset

Delete/reset the entire local ratings store when it's invalid (FR-016).

**200 response**: `{"reset": true}`. This endpoint always succeeds if the file can be removed;
it does not require the store to currently be invalid (a developer-initiated reset is also
reasonable, though the primary trigger is the frontend detecting a load failure).

## Implementation additions (added during /speckit-implement)

- `GET /api/sessions` entries also carry `project_path` and `title` (first-prompt preview) so
  sessions are identifiable in the list.
- `GET /api/top-rated` entries also carry `position` and, for non-orphans, `is_truncated`.
- Invalid ratings store (FR-016): `GET /api/top-rated` and `PUT /api/ratings/{prompt_id}` return
  **409** `{"error": "...", "ratings_invalid": true}`; session and prompt reads still return 200
  with `rating: null` and a top-level `"ratings_invalid": true`.
- `GET /api/sessions/{session_id}` prompts also carry `timestamp` (ISO 8601, may be null),
  `has_response` (true when Claude produced any response text), `activity_summary` (e.g.
  `"used 2 tools, with reasoning"`, or null) and `duration_seconds` (or null) — FR-021, FR-022,
  FR-023.
- `GET /api/sessions/{session_id}/prompts/{prompt_id}` also returns `duration_seconds` (integer
  seconds from the prompt to Claude's last activity for it, or null) — FR-022.
- Requests whose `Host` or `Origin` is not localhost/127.0.0.1 are rejected with 403.

## Error shape (all endpoints)

Non-2xx responses use:
```json
{"error": "human-readable message"}
```
No stack traces or internal paths are ever included in a response body — this is a local tool but
still only binds to localhost (FR-020) and should not casually leak filesystem layout to whatever
is rendering the page.

## GET /

Serves the static frontend shell (HTML/CSS/JS) described in `plan.md` Project Structure. Not a
JSON endpoint.
