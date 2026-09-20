# Implementation Plan: Claude Code Conversation Review & Rating Tool

**Branch**: `001-conversation-rating-tool` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-conversation-rating-tool/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

A developer-facing, single-user local web tool for browsing their own past Claude Code
conversations (CLI and VS Code extension sessions, which research confirms share one on-disk
store) and rating individual prompts 1–10, plus a paginated "Top Rated" view sorted by score with
recency as a tiebreaker. Implemented as a single Python 3 standard-library process (no pip
install, no framework) that discovers and parses local session JSONL files read-only, serves a
small localhost-only HTTP API (`contracts/http-api.md`) to a light, vendored-CSS, semantic-HTML
frontend, and persists ratings in a single local `ratings.json` file with an in-interface
delete/reset recovery path.

## Technical Context

**Language/Version**: Python 3.9+ (standard library only — no `pip install` step; research.md §3)

**Primary Dependencies**: None (backend uses `http.server`/`wsgiref`, `json`, `pathlib` from the
standard library; frontend is plain HTML/CSS/JS plus one vendored, locally-served classless CSS
stylesheet — research.md §4 — and the browser's built-in HTML Sanitizer API with a plain-text
fallback — research.md §5)

**Storage**: A single local `ratings.json` file at the fixed global path
`~/.claude/claude-rating-tool/ratings.json` (data-model.md § Rating; created if the directory
doesn't yet exist), read/written by the server process — global rather than per-project, since
session discovery already spans every project on the machine. Session data itself is read-only
source data, never written by this tool (browse-only, FR-010) — see
`~/.claude/projects/**/*.jsonl` in research.md §1.

**Testing**: `unittest` (standard library) — chosen over `pytest` specifically to keep the
zero-install posture consistent across running *and* testing the tool (research.md §3 rationale
extended to the test toolchain).

**Target Platform**: A developer's own machine, including inside a VS Code remote-SSH/devcontainer
session (FR-017), reached through a standard modern browser at a `127.0.0.1` URL.

**Project Type**: Single small web application — one local process serving both the HTTP API and
the static frontend; not a separately-deployable frontend/backend pair.

**Performance Goals**: SC-001 (<30s from opening the tool to viewing a specific past prompt) and
SC-003 (no perceptible delay reflecting a new/changed rating) — met by localhost, single-developer,
sequential-request traffic against already-paginated and already-truncated data; no additional
performance engineering is warranted at this scale (research.md §7).

**Constraints**: Server binds to `127.0.0.1` only, never `0.0.0.0` (FR-020). This is compatible with
FR-017's "no manual port configuration" requirement: VS Code's automatic port-forwarding (both
remote-SSH and devcontainers) runs its detection/tunneling agent inside the same host/container
network namespace as the listening process, so a `127.0.0.1`-bound port is forwarded correctly and
looks like localhost to the browser on the client side. Binding to `0.0.0.0` would only be needed
for Docker's separate `appPort`/published-port mechanism, which this plan does not use (Plan
Integrity Finding 4). No outbound network calls at runtime — no CDN-fetched assets (research.md
§4) — since a devcontainer may have no internet access, and SC-005 requires the tool to "just
work" once forwarded. No account/auth (FR-011). No in-tool export/share (FR-018). No
cross-developer data exposure (FR-019).

**Scale/Scope**: One developer's local session history: realistically tens to low-thousands of
session files, tens to low-hundreds of prompts per session, prompt/response text typically under
the ~2000-character truncation threshold (FR-013) with occasional larger outliers already covered
by that same truncation rule (research.md §7).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` in this project is still the unfilled template — every principle
placeholder (`[PRINCIPLE_1_NAME]`, etc.) is unresolved and no version has been ratified. There are
therefore no concrete, ratified principles for this plan to be gated against. Treating this as a
**PASS by absence of gates**, not as a license to skip scrutiny: the design choices in this plan
(no dependencies, no speculative abstraction, single small process, plain data formats) were made
to be conservative and simple by default regardless, consistent with the kind of principles this
template is clearly meant to hold (simplicity, minimal footprint) once filled in. If
`/speckit-constitution` is run later and introduces real gates, this plan should be re-checked
against them before implementation proceeds.

**Post-Phase-1 re-check**: unchanged — Phase 1 design (data-model.md, contracts/http-api.md,
quickstart.md) introduced no new dependencies, no additional runtime processes, and no deviation
from the stdlib-only, localhost-only posture established above. Still PASS by absence of gates.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── discovery/     # find candidate session .jsonl files under ~/.claude/projects/** (research.md §1-2)
├── parsing/       # turn raw JSONL lines into Session/Prompt domain objects (data-model.md); per-line
│                  # tolerant so one bad session/line degrades gracefully (FR-014) instead of failing
├── ratings/       # ratings.json read/write/validate + reset (FR-012, FR-015, FR-016)
├── server/        # stdlib HTTP server + handlers implementing contracts/http-api.md, binds 127.0.0.1 (FR-020)
└── web/           # static frontend: semantic HTML, minimal JS, one vendored classless CSS file (research.md §4)

tests/
├── contract/      # one test per contracts/http-api.md endpoint (request/response shape, status codes)
├── integration/   # quickstart.md scenarios end-to-end against fixture session files
└── unit/          # parsing edge cases, ratings store validation, sort/pagination/truncation logic
```

**Structure Decision**: Single project (not a split frontend/backend pair) — this is one small
local process that serves both its own HTTP API and its own static frontend to a single developer.
`discovery/`, `parsing/`, `ratings/`, and `server/` are kept as separate modules specifically so
each can be unit-tested in isolation (e.g. parsing against fixture `.jsonl` files with no server
running) without implying they'll ever ship or deploy separately.

## Complexity Tracking

Not applicable — the Constitution Check above found no ratified gates to violate, and this plan
introduces no additional projects, services, or indirection layers beyond the single project
structure documented above.

## Post-Implementation Amendments (2026-09-19)

Driven by developer feedback on the working tool (spec.md FR-021–FR-024). No new dependencies,
processes or modules; all changes sit inside the existing structure.

- **Parser** (`src/parsing/parser.py`): each Prompt gains `duration_seconds` — seconds from the
  prompt's timestamp to the last non-sidechain assistant line before the next prompt (research §1
  records no per-thinking-block duration, so elapsed time is the only available measure). `None`
  when either timestamp is missing.
- **API** (`contracts/http-api.md`): session-detail prompts gain `timestamp`, `has_response`,
  `activity_summary` and `duration_seconds` (the last two so the response heading line can show
  them without an extra fetch on expand); the prompt-detail response also returns
  `duration_seconds`.
- **Frontend** (`src/web/static/app.js`, `style.css`): prompt heading `Prompt N: DD/MM/YYYY
  HH:MM:SS` (local time); the response `<summary>` reads `Claude's response - Claude worked for … -
  Claude used … tools, with reasoning` (parts omitted when unknown), replacing the earlier lines
  inside the expanded body; prompt boxes wrapped
  in a `.stack` grid using the same 0.6rem gap as the session list; runs of consecutive empty
  prompts collapse into a `<details>` "Empty prompts and responses (n)".
- **Design decision — what counts as "empty"**: decided client-side by measuring the *rendered*
  (post-Sanitizer-API) text of the prompt plus `has_response`, not by inspecting the raw string.
  Reason: bookkeeping prompts such as `<command-name>/compact</command-name>` carry raw text but the
  sanitizer strips the unknown tags, so the box is visibly blank; the developer's notion of
  "empty" is what they see.

## Questmaster Record

### Judgment Ledger
- **2026-09-19** · comprehension · comprehension_answer — "i'm questioning unittest over pytest, however i see why it might be chosen as it doesn't need an install. I think that maybe it might need to bind to 0.0.0.0 from vscode to work"
  *Effect*: Recorded as a Round 1 comprehension prediction (most-likely-wrong): flags a real technical question about whether 127.0.0.1 binding is sufficient for VS Code port-forwarding; routed to the independent Plan Integrity assessment for verification against FR-017/FR-020.

- **2026-09-19** · comprehension · comprehension_answer — "its really lean"
  *Effect*: Recorded as a Round 1 comprehension prediction (what-to-cut): developer sees no single component of the plan worth cutting given its current leanness.

- **2026-09-19** · comprehension · comprehension_answer — "HTML sanatization"
  *Effect*: Recorded as a Round 1 comprehension prediction (breaks-first): developer expects HTML sanitization (research.md §5, browser Sanitizer API + fallback) to be the first thing to break, under a changing-requirements or edge-case lens.

- **2026-09-19** · plan · decision_resolution — "~/.claude/claude-rating-tool/ratings.json (this may need to be created if it doesn't exist)"
  *Effect*: Resolved Plan Integrity Finding 1 (ratings.json storage location, UNJUSTIFIED_DRIFT/medium): fixed as a single global path, created on first use, independent of the tool's launch directory. Applied to plan.md Storage, data-model.md, and quickstart.md.

### Comprehension
**Round 1 · 2026-09-19** — Initial Comprehension Checkpoint after first /speckit-plan pass

- *most_likely_wrong*: "i'm questioning unittest over pytest, however i see why it might be chosen as it doesn't need an install. I think that maybe it might need to bind to 0.0.0.0 from vscode to work"
- *what_to_cut*: "its really lean"
- *breaks_first*: "HTML sanatization"

### Decisions
- **2026-09-19** — Plan Integrity Finding 4 (127.0.0.1-vs-0.0.0.0 binding compatibility with VS Code auto-forwarding, low severity): resolved by adding an explicit justification to the plan's Constraints section, closing out the round-1 Comprehension prediction on the same question.
  <!-- qm-record:decision status=resolved resolved_by=questmaster resolved_date=2026-09-19 -->
  <!-- qm-record:evidence Verified against VS Code devcontainers documentation ('Forwarding or publishing a port'): automatic port-forwarding runs in-namespace and treats forwarded ports as localhost to the app; 0.0.0.0 only applies to Docker's separate appPort/publish mechanism, unused here. No developer judgment call was required beyond adding the explanation. -->
