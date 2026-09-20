# Feature Specification: Claude Code Conversation Review & Rating Tool

**Feature Branch**: `001-conversation-rating-tool`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "" (no text was supplied to `/speckit-specify` directly — this specification is derived from the Quest Story produced by `/speckit-questmaster-story`, `.specify/extensions/questmaster/pending-story.md`, which is treated as the authoritative source per this project's spec-template addendum)

## Clarifications

### Session 2026-09-19

- Q: Should the tool's local web server only accept connections from the developer's own machine (bind to localhost), or does it need to be reachable from other devices on the network? → A: Localhost-only (127.0.0.1) — reachable only via the developer's own machine or VS Code's port-forward
- Q: How long should a prompt or response be before the tool truncates it behind "show more"? → A: Roughly 500 words (~2000 characters)
- Q: Roughly how many past sessions should the tool handle smoothly before the session list needs its own pagination or scrolling strategy? → A: Paginate the session list too, same pattern as the Top Rated view
- Q: What should a developer see the very first time they open the tool, before they've rated anything — an empty session list message, or something else entirely? → A: Explicit empty-state message in both the session list and the Top Rated view when there's nothing to show

### Session 2026-09-19 (post-implementation review)

- Q: How should prompt boxes be laid out in a session? → A: With the same vertical gap between boxes as the session list
- Q: What should the prompt heading show? → A: The prompt number followed by the date and time it was given, formatted `DD/MM/YYYY HH:MM:SS` in the developer's local time (e.g. `Prompt 3: 19/09/2026 12:01:04`)
- Q: What does "thinking time" for Claude's response mean? → A: Elapsed time from the prompt to Claude's last activity for that prompt (session files record no per-thinking-block duration), shown in the expanded response
- Q: Where should Claude's response time and activity summary appear? → A: In the "Claude's response" heading line itself, visible without expanding, joined with " - " (e.g. `Claude's response - Claude worked for 2m 33s - Claude used 19 tools, with reasoning`); a part is omitted when it is unknown
- Q: What should happen to prompts that show nothing? → A: Consecutive prompts with no visible prompt text and no response text collapse into one "Empty prompts and responses (n)" group that can be expanded

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Browse a session and rate its prompts (Priority: P1)

A developer opens the tool and sees their own Claude Code sessions listed, most recent first.
They open a session, see the prompts they gave in that session in order, expand any prompt to see
Claude's corresponding response, and rate that prompt on a 1–10 scale.

**Why this priority**: This is the entire reason the tool exists — without it, nothing else in
this feature has anything to operate on. It delivers the core value (being able to look back and
judge what worked) on its own.

**Independent Test**: Can be fully tested by opening the tool against a machine that has at least
one existing Claude Code session, opening that session, expanding a prompt, and assigning it a
rating — delivers standalone value even with no other feature in this set built yet.

**Acceptance Scenarios**:

1. **Given** a developer has one or more past Claude Code sessions on their machine, **When** they
   open the tool, **Then** they see those sessions listed with the most recent one first.
2. **Given** a developer has opened a session, **When** they view it, **Then** they see the
   prompts they gave, in the order they gave them.
3. **Given** a developer is viewing a prompt, **When** they expand it, **Then** they see Claude's
   corresponding response/activity for that prompt.
4. **Given** a developer is viewing a prompt, **When** they assign it a rating from 1 to 10,
   **Then** that rating is saved and is visible the next time they view that prompt.
5. **Given** a prompt already has a rating, **When** the developer sets a new rating for it,
   **Then** the previous rating is replaced by the new one.
6. **Given** a developer has no Claude Code sessions on their machine yet, **When** they open the
   tool, **Then** they see an explicit empty-state message rather than a blank or broken screen.
7. **Given** a developer is viewing a session, **When** they look at a prompt, **Then** its heading
   shows the prompt number and the date/time it was given as `DD/MM/YYYY HH:MM:SS`, and prompt
   boxes are separated by the same vertical gap used between entries in the session list.
8. **Given** a developer is viewing a prompt with a response, **When** the session records when
   Claude finished and what activity it used, **Then** the "Claude's response" heading line shows
   `Claude's response - Claude worked for <time> - Claude used <n> tools, with reasoning`, without
   the developer needing to expand it.
9. **Given** a session contains consecutive prompts that have no visible prompt text and no
   response text, **When** the developer views the session, **Then** those prompts appear as a
   single collapsed "Empty prompts and responses (n)" entry that expands to show them.

---

### User Story 2 - Review and maintain a personal list of top-rated prompts (Priority: P2)

A developer switches to a "Top Rated" view to see their best prompts across all sessions, sorted
by rating (highest first, most recent breaking ties), and can re-rate a prompt directly from this
view to keep the list accurate over time.

**Why this priority**: This turns individual ratings into a reusable personal reference — the
part of the tool a developer returns to later, and the part they'd draw on when informally sharing
tips with teammates. It depends on User Story 1 existing (there must be ratings to show) but is
independently testable and valuable once ratings exist.

**Independent Test**: Can be fully tested by rating several prompts across different sessions,
opening the Top Rated view, and confirming the ordering and pagination — then changing a rating
from within that view and confirming the list updates accordingly.

**Acceptance Scenarios**:

1. **Given** a developer has rated prompts across multiple sessions, **When** they open the Top
   Rated view, **Then** prompts appear ordered by rating from highest to lowest, with more
   recently rated prompts appearing first among ties.
2. **Given** there are more rated prompts than fit on one screen, **When** the developer views the
   Top Rated view, **Then** the list is paginated rather than shown all at once.
3. **Given** a developer is viewing the Top Rated view, **When** they change a prompt's rating
   from within that view, **Then** the list re-orders to reflect the new rating.
4. **Given** a developer has not rated any prompts yet, **When** they open the Top Rated view,
   **Then** they see an explicit empty-state message rather than a blank or broken view.

---

### User Story 3 - Recover from invalid local rating data (Priority: P3)

If the developer's locally stored ratings become invalid or corrupted for any reason, the
developer can clear them from within the interface and start again, without needing to find or
edit any file by hand.

**Why this priority**: This is a reliability safety net rather than day-to-day value, but it
prevents a corrupted local file from silently locking a developer out of the tool entirely. It's
independently testable and shippable on its own.

**Independent Test**: Can be fully tested by deliberately corrupting the local ratings data,
opening the tool, and confirming it offers a working recovery path instead of failing outright.

**Acceptance Scenarios**:

1. **Given** the developer's local rating data is invalid or unreadable, **When** they open the
   tool, **Then** the interface offers a clear way to delete/reset that data from within the UI.
2. **Given** the developer uses that reset control, **When** the reset completes, **Then** the
   tool is usable again with an empty rating history, and no manual file editing was required.

---

### Edge Cases

- What happens when a session's underlying data can't be fully or safely rendered (e.g. unusual
  content, an interrupted/partial write)? The rest of that session must still be viewable — a
  single problematic session must not break the session list or the rest of that session's
  content.
- How does the system handle a prompt or a response that is very long? Content over roughly 500
  words (~2000 characters) is shown in a shortened form by default with a way to reveal the rest,
  so viewing it doesn't make the page heavy or slow.
- What happens if a session that was previously rated is later deleted, moved, or renamed on the
  developer's machine? The corresponding entry is omitted or clearly marked as unavailable in the
  Top Rated view rather than breaking that view.
- How does the system handle sessions coming from two different sources (the Claude Code CLI and
  the Claude Code VS Code extension) if they don't describe a conversation in quite the same way?
  Both are expected to be shown consistently in the same session list and prompt view; a session
  from either source that can't be interpreted falls under the graceful-degradation behavior above.
- What does a developer see before any sessions exist, or before any prompt has been rated? Both
  the session list and the Top Rated view show an explicit empty-state message rather than a
  blank or broken screen.
- What if several consecutive prompts show nothing (for example, slash-command bookkeeping lines
  with no visible text, and no response)? They are grouped into one collapsed "Empty prompts and
  responses (n)" entry instead of a run of blank boxes; a prompt with a response is never
  collapsed, even if its own text is blank.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let a developer view a list of their own Claude Code conversation
  sessions, ordered most recent first, paginated the same way as the top-rated view so the list
  stays light regardless of how much session history has accumulated.
- **FR-002**: System MUST source sessions from both the Claude Code CLI and the Claude Code VS
  Code extension.
- **FR-003**: System MUST let a developer open a session and view the prompts within it, in the
  order they were given.
- **FR-004**: System MUST let a developer expand any prompt to view Claude's corresponding
  response/activity for that prompt.
- **FR-005**: System MUST let a developer assign a rating from 1 to 10 to any individual prompt.
- **FR-006**: System MUST let a developer change a prompt's rating at any time after it was first
  set.
- **FR-007**: System MUST provide a separate view listing a developer's rated prompts sorted by
  rating, highest first, with more recently rated prompts breaking ties.
- **FR-008**: That top-rated view MUST be paginated rather than shown all at once.
- **FR-009**: System MUST let a developer re-rate a prompt directly from the top-rated view.
- **FR-010**: System MUST be browse-only — it MUST NOT allow re-running, continuing, or otherwise
  acting on a conversation from within the tool.
- **FR-011**: System MUST NOT require any account, login, or authentication.
- **FR-012**: System MUST persist a developer's ratings locally on their own machine, independent
  of any shared or remote service, so that ratings survive restarting the tool.
- **FR-013**: When a prompt or its corresponding response exceeds approximately 500 words
  (~2000 characters), System MUST show a shortened version by default with a control to reveal
  the full content.
- **FR-014**: When a session contains content the system cannot fully or safely render, System
  MUST still show the rest of that session's content rather than failing the entire session or the
  session list.
- **FR-015**: When previously rated content is no longer available (e.g. the underlying session
  was deleted, moved, or renamed), System MUST omit or clearly flag that entry rather than
  breaking the top-rated view.
- **FR-016**: If a developer's locally stored rating data becomes invalid, System MUST offer a way
  from within the interface to clear it and start fresh, without requiring manual file editing.
- **FR-017**: System MUST be usable by a developer working inside a VS Code remote-SSH/devcontainer
  session without the developer needing to perform manual network/port configuration beyond what
  their editor already provides.
- **FR-018**: System MUST NOT provide any built-in feature for exporting or sending a prompt or
  rating to another person; sharing happens outside the tool.
- **FR-019**: System MUST NOT expose one developer's sessions or ratings to another developer —
  each developer's data is local and personal to them.
- **FR-020**: System's local server MUST accept connections only from the developer's own
  machine (not from other devices on the network), so conversation content is never reachable
  beyond the developer's own machine and their editor's own port-forwarding.

- **FR-021**: System MUST show each prompt's number followed by the date and time it was given,
  formatted `DD/MM/YYYY HH:MM:SS` in the developer's local time.
- **FR-022**: System MUST show, in each prompt's "Claude's response" heading line (visible without
  expanding it), how long Claude worked on the prompt (elapsed time from the prompt to Claude's
  last activity for it) and a summary of Claude's activity (e.g. "Claude used 19 tools, with
  reasoning"), each separated by " - " and each omitted when it cannot be determined.
- **FR-023**: System MUST collapse a run of consecutive prompts that have no visible prompt text
  and no response text into a single expandable "Empty prompts and responses (n)" entry, where n
  is the number of prompts in the run; expanding it MUST show each prompt as normal.
- **FR-024**: System MUST separate prompt boxes within a session by the same vertical gap used
  between entries in the session list.

### Key Entities

- **Session**: A single Claude Code conversation, sourced from either the CLI or the VS Code
  extension, made up of an ordered sequence of prompts and Claude's corresponding activity for
  each; has a recency ordering relative to other sessions.
- **Prompt**: A single instruction a developer gave within a session; has its position within the
  session, the time it was given, Claude's corresponding response/activity (including how long
  Claude worked on it and a summary of its activity), and an optional rating.
- **Rating**: A developer-assigned score from 1 to 10 attached to a specific prompt; replaceable
  at any time; belongs to the developer who set it and is never shared with other developers by
  this tool.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can go from opening the tool to viewing a specific past prompt and
  Claude's response in under 30 seconds, without reading or editing any file by hand.
- **SC-002**: A developer can rate or re-rate a prompt in three actions or fewer from wherever
  they're currently looking at it (session view or top-rated view).
- **SC-003**: The top-rated view reflects a new or changed rating with no perceptible delay after
  it's given.
- **SC-004**: A session containing unusually long or unrenderable content still allows every other
  prompt in that session to be reviewed, rather than the whole session failing to display.
- **SC-005**: Every developer on the team can start the tool inside their own VS Code devcontainer
  session and reach it in their browser without needing help beyond what their devcontainer setup
  already provides.
- **SC-006**: If a developer's local rating data becomes invalid, they can get back to a working
  tool using only the interface, in under a minute, without needing anyone else's help.

## Assumptions

- Each developer runs the tool against their own machine's local Claude Code session data; there
  is no multi-developer or shared-server deployment in this feature.
- The developer's environment already provides whatever lightweight runtime the tool needs; no
  additional heavyweight installation is treated as in-scope work for this feature (the specific
  runtime is a planning decision, not a specification concern).
- Claude Code CLI and VS Code extension sessions are both discoverable in standard locations on a
  normal developer machine, without custom configuration.
- One session corresponds to exactly one conversation transcript.
- Sharing a rated prompt with a teammate happens informally outside this tool (e.g. copy-paste
  into chat); no in-tool export/share mechanism is part of this feature.
- Whether the CLI and VS Code extension describe a session's data identically, or differently
  enough to need separate handling, is not yet confirmed and is left for investigation during
  planning; this feature assumes both can be presented through the same session/prompt/rating
  model described above.

## Questmaster Record

### Judgment Ledger
- **2026-09-19** · spec · asserted_fact — "1 -- keep FR-015 as written"
  *Effect*: Resolved spec-integrity Finding 1 (FR-015 flagged as DISCOVERED, not explicitly approved in the story): developer confirmed the automatic per-entry omit/flag behavior for an orphaned rating should stand as specified, rather than folding it into the whole-file delete/reset flow (FR-016).

- **2026-09-19** · implement · decision_resolution — "add a vertical gap between the prompt boxes, the same gap as on the sessions page. after "Prompt #" add ": DD/MM/YYY HH:MM:SS" and show thinking time for claude's response. Some of the prompts and respones are empty (collapse them if both are empty and consequitive into a "Empty prompts and responses (n)...")"
  *Effect*: Added FR-021–FR-024, acceptance scenarios 7–9 and an edge case. Interpretations made without further questions: "DD/MM/YYY" read as `DD/MM/YYYY`; "thinking time" read as elapsed prompt-to-last-activity time; "empty" read as visibly empty after sanitizing.

### Comprehension

### Decisions
