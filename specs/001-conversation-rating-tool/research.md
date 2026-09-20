# Phase 0 Research: Claude Code Conversation Review & Rating Tool

**Input**: `spec.md` (FR-001–FR-020), `story.md` §9 Assumptions & Known Unknowns, §12 Constraints,
§13 Solution-Neutrality Assessment (implementation-detail bucket), §14 Dragon's Questions.

Method note: rather than guessing at the Claude Code session file format, this research phase
inspected real, local Claude Code CLI session data on the developer's own machine
(`~/.claude/projects/**/*.jsonl`) and real VS Code extension installation artifacts on the same
machine. Findings below are evidence-based, not assumed — file paths and field names are recorded
so a future re-check is trivial.

## 1. Where session data actually lives, and in what shape

**Decision**: Discover sessions by scanning `~/.claude/projects/<sanitized-cwd>/*.jsonl`, where
`<sanitized-cwd>` is the absolute working-directory path with every `/` replaced by `-` (verified:
`/home/lee/Projects/personal-website` → directory `-home-lee-Projects-personal-website`, and the
JSONL filename equals the session's `sessionId`, e.g. `51755f29-cd0d-...jsonl`).

Each line is a standalone JSON object (JSON Lines). Relevant `type` values observed in real
sessions: `user`, `assistant`, `system`, `mode`, `permission-mode`, `bridge-session`,
`file-history-snapshot`, `ai-title`, `attachment`, `cost-state`, `last-prompt`. Only `user` and
`assistant` carry conversation content; the rest are session metadata/bookkeeping and MUST be
skipped by the parser (this is the concrete mechanism behind FR-014's graceful degradation — an
unrecognized `type` is simply not conversation content, not a parse failure).

For a `user`-typed line:
- `message.content` is a **plain string** for a genuine developer-typed prompt.
- `message.content` is a **list of blocks** (observed block types: `text`, `tool_result`, `image`)
  when the line is actually a tool result being fed back to the model, not something the developer
  typed. **Only string-content `user` lines are real prompts** for FR-003's "prompts they gave, in
  the order given." List-content `user` lines are Claude's own tool activity and belong to the
  "expand to view Claude's response/activity" side (FR-004), not the prompt list.
- Lines with `isMeta: true` or `isSidechain: true` are not developer-facing prompts either
  (meta/bookkeeping and sub-agent side-conversations respectively) and are excluded from the
  primary prompt list for the same reason.
- Each real prompt line carries a stable `promptId`, a `timestamp` (ISO 8601 UTC), and `uuid` /
  `parentUuid` linking it into the session's turn sequence.

For an `assistant`-typed line, `message.content` is always a list of blocks; observed types:
`text` (what the developer reads as "Claude's response"), `thinking`, and `tool_use`. FR-004's
"Claude's corresponding response/activity" maps to the concatenation of `text` blocks for display,
with `tool_use`/`thinking` blocks folded into the same expanded view as supporting activity rather
than shown as separate top-level prompts.

**Alternatives considered**: Parsing via an undocumented private API or a hypothetical export
command — rejected; no such interface exists, and reading the same JSONL files Claude Code itself
writes is the simplest option consistent with "browse-only" (FR-010) and "no additional
installation" (story §12 Constraints).

## 2. CLI vs. VS Code extension: one store, not two

**Decision**: Treat the CLI and the VS Code "Claude Code" extension as writing to the **same**
session store (`~/.claude/projects/...`), not two different formats, based on direct evidence: the
installed VS Code extension (`anthropic.claude-code`, confirmed present under
`~/.config/Code/CachedExtensionVSIXs/`) has no separate per-workspace session storage under VS
Code's own `workspaceStorage/` — it is a thin wrapper around the same underlying engine that
produces the JSONL files inspected in §1. FR-002's "source sessions from both the CLI and the VS
Code extension" is therefore satisfied by a single discovery path, not two parsers.

**Residual risk (carried from story.md's Known Unknowns, disposition `accepted_as_risk`)**: this
was verified on one real machine/version combination, not guaranteed to hold across every OS,
extension version, or future Claude Code release. Rather than hard-coding that assumption, the
discovery/parsing modules are still structured as a small abstraction (a discovery step producing
a list of candidate session file paths, and a parser step that tolerates unrecognized `type`
values and malformed lines per-line, not per-file) so a future divergence degrades a single session
(FR-014) instead of breaking the whole tool. This is a design posture, not new scope.

## 3. Runtime and dependency choice

**Decision**: Python 3 standard library only — `http.server`/`wsgiref` for the local web server,
`json` for both parsing transcripts and reading/writing the ratings store, `pathlib` for file
discovery. No `pip install` step, no `requirements.txt`.

**Rationale**: story.md §12 Constraints states "assume only Python 3 is installed; no other
required runtime or toolchain," and FR-017 requires the tool to be usable inside a VS Code
remote-SSH/devcontainer session with no manual configuration beyond what the editor already
provides. A devcontainer is not guaranteed to have outbound internet access to run `pip install`
at first launch, so a stdlib-only server removes an entire class of first-run failure.

**Alternatives considered**: Flask/FastAPI — rejected; they are a materially nicer developer
experience but reintroduce exactly the dependency-install step the constraint is written to avoid.
If this becomes a real friction point during implementation, revisit as a documented exception, not
a silent addition.

## 4. Frontend delivery: no CDN dependency

**Decision**: Ship the "lightweight, semantic-HTML-friendly CSS" (story §12 Constraints) as a
single small stylesheet **vendored into the project and served locally** by the same process,
rather than linked from a public CDN.

**Rationale**: the same offline-first reasoning as §3 applies — a devcontainer opened over
remote-SSH may have no outbound internet access, and a tool whose UI silently loses its styling (or
worse, its JS) the moment a CDN is unreachable would fail SC-005 ("reach it in their browser
without needing help beyond what their devcontainer setup already provides"). A vendored,
classless/semantic stylesheet in the spirit of frameworks like Pico.css/water.css keeps markup
close to plain HTML (supporting the "keep HTML complexity down" goal) without an external fetch.

**Alternatives considered**: Linking a CSS framework from a public CDN — rejected for the offline
reason above. Writing custom CSS from scratch — viable fallback if no existing classless stylesheet
is suitable to vendor; either way, the requirement is "vendored, not fetched," not a specific
library name.

## 5. Content rendering safety

**Decision**: Use the browser's built-in HTML Sanitizer API (per story §12 Constraints) when
rendering any transcript-derived text as HTML, with a plain-text (`textContent`) fallback path when
the API is unavailable in the developer's browser, so a missing/older-browser API degrades safely
rather than blocking rendering (consistent with FR-014's graceful-degradation intent applied to the
rendering layer, not just the parsing layer).

**Alternatives considered**: A custom/hand-rolled sanitizer — rejected per the story's explicit
preference for the platform API over reinventing one.

## 6. Ratings storage shape and identity key

**Decision**: One local JSON file (`ratings.json`) storing a flat map keyed by `promptId` (the
stable id observed in real session data, §1) to a rating record `{value, rated_at, session_id,
position}`. `session_id` + `position` are stored alongside `promptId` (not used as the primary key)
specifically to support FR-015: if a session file is later missing, the stored `session_id` is
still enough to detect and flag the orphan in the Top Rated view without needing to re-open the
(now-gone) file.

**Alternatives considered**: Keying by `(file_path, position)` instead of `promptId` — rejected as
primary key because a renamed/moved session file (explicitly named as a risk in FR-015) would break
that key even though the conversation content hasn't changed; `promptId` is stable independent of
where the file currently lives.

## 7. Performance and scale posture

**Decision**: No special-cased performance engineering; SC-001/SC-003's "under 30 seconds" /
"no perceptible delay" targets are easily met by localhost, single-developer, sequential-request
traffic against paginated, truncated data (FR-001/FR-008/FR-013 already bound per-request work).
Session and prompt listing pagination (already specified) is the sole scaling mechanism needed; no
caching layer, background indexing, or database is warranted at this scale.

**Scale assumption carried into Technical Context**: realistically tens to low-thousands of session
files per developer, tens to low-hundreds of prompts per session, individual prompt/response text
typically well under the ~2000-character truncation threshold (FR-013) with occasional larger
outliers (e.g. large tool output) that the truncation rule already covers.

## Summary of resolved unknowns

| Unknown (from Technical Context / story.md §9) | Resolution |
|---|---|
| Session file location/format | `~/.claude/projects/<cwd-with-/-replaced-by-->/<sessionId>.jsonl`, JSON Lines, §1 |
| CLI vs. VS Code extension schema difference | Same store in practice; parser still defensive per-line, §2 |
| Runtime/framework | Python 3 stdlib only (`http.server`, `json`, `pathlib`), §3 |
| CSS framework | Vendored local classless stylesheet, not CDN-linked, §4 |
| Sanitization | Browser HTML Sanitizer API with plain-text fallback, §5 |
| Ratings key / orphan detection | `promptId`-keyed JSON map with embedded `session_id`, §6 |
| Performance approach | None needed beyond existing pagination/truncation, §7 |
