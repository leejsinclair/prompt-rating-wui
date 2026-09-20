---

description: "Task list for feature implementation"
---

# Tasks: Claude Code Conversation Review & Rating Tool

**Input**: Design documents from `/specs/001-conversation-rating-tool/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/http-api.md, quickstart.md

**Tests**: Unit tests are included for the three Foundational modules (discovery, parsing,
ratings) — plan.md's Structure Decision explicitly justifies splitting them into separate modules
"so each can be unit-tested in isolation," so the task list now delivers on that (T007–T009).
Contract tests (`tests/contract/`) and integration tests (`tests/integration/`) were not
explicitly requested in spec.md/story.md and are not generated here; quickstart.md's scenarios are
instead exercised manually as the Polish-phase validation task (T028).

**Organization**: Tasks are grouped by user story (spec.md) to enable independent implementation
and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single project (plan.md Structure Decision): `src/`, `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure (plan.md Project Structure)

- [X] T001 Create project directory structure per plan.md: `src/discovery/`, `src/parsing/`, `src/ratings/`, `src/server/`, `src/web/`, `tests/contract/`, `tests/integration/`, `tests/unit/` (each Python package with `__init__.py`)
- [X] T002 [P] Vendor a classless CSS stylesheet (in the spirit of Pico.css/water.css) into `src/web/static/style.css`, served locally rather than linked from a CDN (research.md §4)
- [X] T003 [P] Create the static frontend shell in `src/web/static/index.html` and `src/web/static/app.js`: semantic HTML skeleton with placeholders for the session list view, session detail view, and Top Rated view

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Implement session discovery in `src/discovery/discovery.py`: scan `~/.claude/projects/<sanitized-cwd>/*.jsonl` across every project directory on the machine, returning candidate session file paths (research.md §1-2)
- [X] T005 [P] Implement the Session/Prompt domain models and JSONL parser in `src/parsing/parser.py`: per-line tolerant parsing that distinguishes real prompts (string-content `user` lines, excluding `isMeta`/`isSidechain`) from tool-result/list-content lines, extracts `promptId`/`timestamp`/`text`, and concatenates the following assistant turn's `text` blocks into `response_text`; unrecognized `type` values and malformed lines are skipped per-line, not per-file (data-model.md Session & Prompt; research.md §1)
- [X] T006 [P] Implement the ratings store in `src/ratings/store.py`: read/write/validate `~/.claude/claude-rating-tool/ratings.json` keyed by `prompt_id` (creating the directory on first use), treat any shape/JSON/range violation as a whole-file "invalid" state, and provide a `reset()` that deletes the file (data-model.md Rating; research.md §6; FR-012, FR-015, FR-016)
- [X] T007 [P] Unit tests for session discovery in `tests/unit/test_discovery.py`: cover no-sessions-found, single project, and multiple-project scanning against a fixture directory tree (depends on T004)
- [X] T008 [P] Unit tests for the JSONL parser in `tests/unit/test_parser.py`: cover string-content vs. list-content `user` lines, `isMeta`/`isSidechain` exclusion, `promptId`/`timestamp`/`text` extraction, assistant `text`-block concatenation into `response_text`, and per-line tolerance of malformed/unrecognized-`type` lines (depends on T005)
- [X] T009 [P] Unit tests for the ratings store in `tests/unit/test_store.py`: cover a read/write round-trip, directory-creation-on-first-use, whole-file "invalid" detection for bad JSON/shape/out-of-range values, and `reset()` (depends on T006)
- [X] T010 Implement the base HTTP server in `src/server/server.py`: binds to `127.0.0.1:5148` only — never `0.0.0.0` — using stdlib `http.server`, prints `Serving on http://127.0.0.1:5148` on startup, with request routing dispatch, a JSON response helper, and the uniform `{"error": "..."}` shape for all non-2xx responses (FR-020; contracts/http-api.md Error shape)
- [X] T011 Implement the `GET /` static-asset handler in `src/server/server.py` serving `src/web/static/*` (depends on T003, T010)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Browse a session and rate its prompts (Priority: P1) 🎯 MVP

**Goal**: List sessions, open one, view its prompts in order, expand a prompt to see Claude's
response, and assign/replace a 1–10 rating.

**Independent Test**: Open the tool against a machine with at least one existing session, open
that session, expand a prompt, and assign it a rating — delivers standalone value.

### Implementation for User Story 1

- [X] T012 [US1] Implement `GET /api/sessions` handler in `src/server/handlers/sessions.py`: list sessions (via T004 discovery + T005 parser) sorted by `last_activity_at` descending, paginated by `page`, with an empty-state-friendly `{sessions: [], has_more: false}` shape (contracts/http-api.md; FR-001, FR-002)
- [X] T013 [US1] Implement `GET /api/sessions/{session_id}` handler in `src/server/handlers/sessions.py`: return that session's prompts in order, each truncated server-side to ~500 words/~2000 characters with `is_truncated`, 404 on unknown `session_id`, and an `is_parseable: false` + top-level `error` path (with `prompts: []`) when the underlying file can't be parsed at all, without breaking the session list (contracts/http-api.md; FR-003, FR-013, FR-014)
- [X] T014 [US1] Implement `GET /api/sessions/{session_id}/prompts/{prompt_id}` handler in `src/server/handlers/sessions.py`: return the full untruncated `text`/`response_text`/`activity_summary`/`rating`, 404 on an unknown session/prompt pair (contracts/http-api.md; FR-004)
- [X] T015 [US1] Implement `PUT /api/ratings/{prompt_id}` handler in `src/server/handlers/ratings.py`: set or replace a rating via the T006 ratings store, storing `session_id`/`position` alongside it, 400 when `value` isn't an integer 1–10 (contracts/http-api.md; FR-005, FR-006)
- [X] T016 [US1] Wire the session and rating routes into the server dispatch in `src/server/server.py` (depends on T010, T012, T013, T014, T015)
- [X] T017 [US1] Implement the session list view in `src/web/static/app.js`/`index.html`: render the paginated, most-recent-first session list, with an explicit empty-state message when no sessions exist (FR-001; Clarifications Q4)
- [X] T018 [US1] Implement the session detail view in `src/web/static/app.js`: render prompts in order with an expand/collapse control revealing Claude's response/activity, a "show more" control for truncated content, rendering transcript-derived text via the browser's HTML Sanitizer API with a `textContent` fallback (FR-003, FR-004, FR-013; research.md §5)
- [X] T019 [US1] Implement the 1–10 rating control in `src/web/static/app.js`, wired to `PUT /api/ratings/{prompt_id}`, reflecting the saved value and updating in place when changed (FR-005, FR-006)

**Checkpoint**: User Story 1 is fully functional and independently testable

---

## Phase 4: User Story 2 - Review and maintain a personal list of top-rated prompts (Priority: P2)

**Goal**: A paginated Top Rated view across all sessions, sorted by rating (then recency), with
inline re-rating.

**Independent Test**: Rate several prompts across at least two sessions, open the Top Rated view,
confirm ordering and pagination, then re-rate a prompt from within that view and confirm the list
re-orders without navigating away.

### Implementation for User Story 2

- [X] T020 [US2] Implement `GET /api/top-rated` handler in `src/server/handlers/top_rated.py`: read all ratings (T006), resolve each against currently-discoverable sessions/prompts to detect orphans, sort by `value` descending then `rated_at` descending, paginate by `page`, mark unresolved entries `is_orphaned: true` with no `text`, and use an empty-state-friendly `{prompts: [], has_more: false}` shape (contracts/http-api.md; FR-007, FR-008, FR-015)
- [X] T021 [US2] Wire the top-rated route into the server dispatch in `src/server/server.py` (depends on T010, T020)
- [X] T022 [US2] Implement the Top Rated view in `src/web/static/app.js`/`index.html`: paginated list in contract sort order, explicit empty-state message when nothing has been rated yet, orphaned entries clearly flagged rather than silently dropped (FR-007, FR-008, FR-015; Clarifications Q4)
- [X] T023 [US2] Wire inline re-rating from the Top Rated view to `PUT /api/ratings/{prompt_id}` in `src/web/static/app.js`, re-sorting and re-rendering the list in place (FR-009)

**Checkpoint**: User Stories 1 AND 2 both work independently

---

## Phase 5: User Story 3 - Recover from invalid local rating data (Priority: P3)

**Goal**: Detect an invalid/corrupted `ratings.json` and offer an in-interface delete/reset path
back to a working, empty-ratings state.

**Independent Test**: Deliberately corrupt the local ratings file, open the tool, and confirm it
offers a working recovery path instead of failing outright.

### Implementation for User Story 3

- [X] T024 [US3] Implement `POST /api/ratings/reset` handler in `src/server/handlers/ratings.py`: delete `ratings.json` via the T006 store, succeeding whenever the file can be removed regardless of whether it was currently invalid (contracts/http-api.md; FR-016)
- [X] T025 [US3] Wire the reset route into the server dispatch in `src/server/server.py` (depends on T010, T024)
- [X] T026 [US3] Surface invalid-ratings detection and a delete/reset control in `src/web/static/app.js`: when any ratings-touching API response indicates an invalid store, show a clear reset control that calls `POST /api/ratings/reset` and returns the UI to a normal, empty-ratings working state with no manual file editing (FR-016; SC-006)

**Checkpoint**: All three user stories are independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation and hardening that spans multiple user stories

- [X] T027 [P] Verify no response body from `src/server/server.py`/`src/server/handlers/*` ever includes a stack trace or internal filesystem path, only the `{"error": "..."}` shape (contracts/http-api.md Error shape; FR-020)
- [X] T028 Run all 6 `quickstart.md` validation scenarios end-to-end (browse & rate, Top Rated, empty states, corrupted-ratings recovery, long-content truncation, malformed-session degradation) and fix any discrepancies found

---

## Phase 7: Post-Implementation Changes (2026-09-19)

**Purpose**: Developer feedback after seeing the working tool (spec.md FR-021–FR-024). Appended
after implementation; all completed in the same session.

- [X] T029 [US1] Add `duration_seconds` to the Prompt model and parser in `src/parsing/parser.py` (prompt timestamp to last assistant activity before the next prompt; null if unavailable), with unit tests in `tests/unit/test_parser.py` (FR-022)
- [X] T030 [US1] Add `timestamp` and `has_response` to session-detail prompts and `duration_seconds` to the prompt-detail response in `src/server/handlers/sessions.py`, with an integration test in `tests/integration/test_quickstart.py`; document in `contracts/http-api.md` (FR-021, FR-022, FR-023)
- [X] T031 [US1] Change the prompt heading in `src/web/static/app.js` to `Prompt N: DD/MM/YYYY HH:MM:SS` (local time) (FR-021)
- [X] T032 [US1] Show "Claude worked for …" in the expanded response in `src/web/static/app.js` (FR-022; superseded by T035)
- [X] T033 [US1] Wrap session-detail prompt boxes in a `.stack` grid with the same 0.6rem gap as the session list in `src/web/static/app.js` and `src/web/static/style.css` (FR-024)
- [X] T034 [US1] Collapse consecutive prompts whose rendered text and response are both empty into an expandable "Empty prompts and responses (n)" group in `src/web/static/app.js` and `src/web/static/style.css` (FR-023)

- [X] T035 [US1] Add `activity_summary` and `duration_seconds` to session-detail prompts in `src/server/handlers/sessions.py` (with an assertion in `tests/integration/test_quickstart.py` and a note in `contracts/http-api.md`), and move both into the "Claude's response" heading line in `src/web/static/app.js` as `Claude's response - Claude worked for <time> - Claude used <n> tools, with reasoning` (parts omitted when unknown), removing the duplicate lines from the expanded body (FR-022)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends only on Foundational
- **User Story 2 (Phase 4)**: Depends only on Foundational; re-uses the same `PUT /api/ratings/{prompt_id}` endpoint US1 builds (T015), but is independently testable once ratings exist
- **User Story 3 (Phase 5)**: Depends only on Foundational (specifically the T006 ratings store)
- **Polish (Phase 6)**: Depends on whichever user stories are complete

### Within Each User Story

- Handlers before route wiring before frontend wiring (e.g., T012–T015 before T016 before T017–T019)

### Known coupling — route dispatch (do not parallelize)

T016, T021, and T025 each add routes to the same dispatch block in `src/server/server.py`. Even
though the surrounding handler/frontend work for US1/US2/US3 is independent and can be built in
parallel, these three specific tasks touch the same file and must be applied one at a time
(append routes, don't overwrite a sibling story's additions) — whoever finishes their story's
dispatch-wiring task first should land it before the next one starts, or the two edits must be
manually merged.

### Parallel Opportunities

- T002 and T003 can run in parallel (Setup)
- T004, T005, T006 can run in parallel (Foundational — separate modules, no shared files)
- T007, T008, T009 (their respective unit tests) can each run in parallel with each other, once their sibling implementation task (T004/T005/T006) lands
- Once Foundational (Phase 2) completes, User Stories 1, 2, and 3 can proceed in parallel if staffed — except for the route-dispatch tasks noted above

---

## Parallel Example: Foundational Phase

```bash
Task: "Implement session discovery in src/discovery/discovery.py"
Task: "Implement the Session/Prompt domain models and JSONL parser in src/parsing/parser.py"
Task: "Implement the ratings store in src/ratings/store.py"
```

```bash
# Once the above land, their unit tests can run in parallel too:
Task: "Unit tests for session discovery in tests/unit/test_discovery.py"
Task: "Unit tests for the JSONL parser in tests/unit/test_parser.py"
Task: "Unit tests for the ratings store in tests/unit/test_store.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: run quickstart.md scenario 1 (and scenario 3's empty-state case) independently

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate (MVP: browse and rate)
3. User Story 2 → validate (Top Rated view)
4. User Story 3 → validate (corrupted-ratings recovery)
5. Polish → run full quickstart.md suite
