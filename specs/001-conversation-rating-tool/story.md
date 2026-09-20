# Quest Story: Claude Code Conversation Review & Prompt Rating Tool

## 1. Quest Title

Claude Code Conversation Review & Prompt Rating Tool

## 2. Problem Statement

Developers on the team have no way to look back at their past Claude Code conversations to see
which of their prompts led to good outcomes and which didn't. Transcripts exist only as raw local
session files, and today no review of them happens at all — good and bad prompting patterns go
unexamined, unreflected-on, and unshared across the team.

## 3. Who Is Affected / Actors

Individual developers on the team who use Claude Code, via its CLI and/or its VS Code extension,
and want to review their own past conversations. Each developer reviews only their own
conversation history — there is no shared or team-visible view built into this tool (team sharing
happens informally, outside the tool; see Scope Boundaries).

## 4. Current Behaviour

No review currently happens. Claude Code writes each conversation to a local session/transcript
JSONL file (from the CLI, and potentially in a different shape from the VS Code extension). These
files are not surfaced anywhere a developer would casually revisit, so once a conversation ends, a
developer has no practical way to look back at which prompts worked and which didn't.

## 5. Use Cases

**UC1 — Browse and rate a session's prompts**
- Actor: individual developer
- Trigger: developer opens the tool (e.g. after a coding session, or when reflecting on recent work)
- Goal: identify which of their own prompts worked well
- Flow: opens the tool → sees a list of sessions, most recent first → clicks a session → sees the
  prompts given in that session, in the order given → expands a prompt to view Claude's
  corresponding response/activity → rates the prompt on a 1–10 scale
- Alternate/failure path: if a session's content can't be fully or safely rendered (malformed
  data, unusual content), that session degrades gracefully rather than breaking the whole list

**UC2 — Review top-rated prompts**
- Actor: individual developer
- Trigger: developer wants a personal reference of their best prompts (e.g. before helping a
  teammate, or to remind themselves what works)
- Goal: see their best prompts, kept current
- Flow: switches to the "Top Rated" view → sees their own prompts sorted by rating (highest first,
  most recent breaking ties), paginated → can re-rate a prompt directly from this view so the
  ranking stays accurate over time

**UC3 — Recover from corrupted ratings data**
- Actor: individual developer
- Trigger: the local ratings file becomes invalid (e.g. an interrupted write, or drift from a
  rated session's underlying file being moved/renamed/deleted)
- Goal: get back to a working tool without hand-editing a JSON file
- Flow: tool detects invalid ratings data → interface presents a delete/reset control → developer
  deletes it → tool starts again with a fresh, empty ratings store

**UC5 — Read a session quickly (added post-implementation)**
- Actor: individual developer
- Trigger: opening a session that contains bookkeeping/empty entries and long-running responses
- Goal: see when each prompt was given, how long Claude took, and not wade through blank boxes
- Flow: each prompt is headed "Prompt N: DD/MM/YYYY HH:MM:SS" → expanding a response shows how long
  Claude worked → consecutive prompts with nothing to show collapse into "Empty prompts and
  responses (n)"; boxes are evenly spaced, matching the session list

**UC4 — View a very long conversation**
- Actor: individual developer
- Trigger: expanding a prompt whose response (or prompt itself) is very long
- Goal: view it without the page becoming heavy or slow
- Flow: long content is truncated by default behind a "show more" control, keeping the number of
  rendered DOM elements low until the developer chooses to expand it

## 6. Desired Outcomes

Developers can look back at any past Claude Code conversation, from either the CLI or the VS Code
extension, and see — prompt by prompt — what they asked and what Claude did in response. Each
developer builds a personal, rated record of their own prompts over time, which they can draw on
to reflect on their own practice and informally pass tips to teammates, contributing to a
team-wide culture of learning from and supporting each other's use of Claude Code.

## 7. Scope Boundaries

**In-Scope**:
- Listing a developer's own local Claude Code sessions (CLI and VS Code extension), most recent
  first
- Viewing, per session, the prompts given (in order) and expanding to view Claude's corresponding
  response/activity
- Rating any individual prompt on a 1–10 scale, and re-rating it later, including from the Top
  Rated view
- A separate "Top Rated" view: paginated, sorted by rating descending with recency as a tiebreaker
- Truncating long prompt/response content behind a "show more" control
- Showing each prompt's number and date/time (`DD/MM/YYYY HH:MM:SS`), how long Claude worked on a
  response, and collapsing consecutive empty prompt/response pairs into an expandable "Empty
  prompts and responses (n)" entry (added post-implementation, 2026-09-19)
- Graceful degradation when a session's content can't be fully or safely rendered
- Recovering from a corrupted local ratings file via an in-interface delete/reset control
- Running as a minimal local web server process, no account/login, suitable for VS Code's
  automatic port forwarding inside an SSH/devcontainer session, assuming only Python 3

**Out-of-Scope / Non-Goals**:
- Any account system, authentication, or multi-user/shared-server deployment
- Any built-in export/share feature for sending a prompt or rating to a teammate
- Acting on a conversation from the tool: re-running, continuing, or editing a session (browse-only)
- A shared or central store of ratings across developers (each developer's ratings file is local
  and personal)

**Adjacent Concerns**:
- Informal team sharing of rated prompts (e.g. copy-paste into Slack) happens naturally outside
  this tool and isn't designed for here
- A future cross-developer or team leaderboard view is explicitly deferred (see Dragon's Questions
  below) — today's local-file design may need revisiting if that becomes a real ask

## 8. Success Criteria

- A developer can go from opening the tool to viewing a specific past prompt and Claude's
  response, and giving it a rating, without reading or hand-editing any transcript or ratings file
- The Top Rated view reflects current ratings (sorted by score, recency tiebreak) immediately
  after any rating or re-rating
- The tool runs inside a VS Code SSH/devcontainer session with only Python 3 available, and loads
  via VS Code's automatic port forwarding with no extra configuration
- A session containing unusual or malformed content (very long responses, an interrupted/partial
  entry) still renders the rest of that session rather than failing entirely
- If the local ratings file becomes invalid, a developer can recover without external help or
  manual file editing

## 9. Assumptions & Known Unknowns

**Assumed**:
- Python 3 is available in the developer's environment (devcontainer or otherwise); no other
  runtime dependency should be required
- Claude Code CLI and VS Code extension session files are both discoverable in standard,
  predictable local file locations for a normal developer setup
- One session corresponds to one conversation transcript file

**Unknown**:
- The exact schema Claude Code CLI and VS Code extension transcripts use today, and whether the
  two differ enough to need separate parsing logic (to confirm during planning)
- Whether transcript schemas stay stable across Claude Code versions, or might change in a way
  that requires the parser to be updated (accepted as a risk, not mitigated further here)
- The realistic upper bound on conversation length or prompt/response size the tool needs to
  handle gracefully

## 10. Background / Context

This tool is part of a broader push on the team to get developers supporting and learning from
each other's use of Claude Code — turning individual prompting experience into something that can
be reviewed, reflected on, and informally shared, rather than lost in terminal scrollback or
personal habit.

## 11. Business Rules

N/A — this is a personal developer tool with no domain or business logic beyond the rating and
display mechanics described above; there are no organizational or domain rules governing its
behavior.

## 12. Constraints

- Must run with minimal technology assumptions: assume only Python 3 is installed; no other
  required runtime or toolchain
- Must run correctly inside a VS Code SSH session into a devcontainer, served by a small local web
  server whose port VS Code can auto-forward
- No accounts or authentication of any kind
- Ratings persist in a local JSON file, not a database or external service
- HTML/CSS/JS should stay light: a lightweight, semantic-HTML-friendly CSS framework, minimal DOM
  complexity, and long content truncated ("show more") to help keep the rendered DOM small
- Use the browser's built-in HTML Sanitizer API (rather than a custom sanitizer) when rendering
  conversation content that can't be trusted outright

## 13. Proposed Solutions & Solution-Neutrality Assessment

**Proposal as stated**: A personal, no-account, minimal-server web interface, run via Python 3,
viewable inside a VS Code devcontainer via automatic port forwarding. Lists Claude Code sessions
(CLI and VS Code extension) most recent first; clicking a session shows its prompts in order;
expanding a prompt shows Claude's response, truncated behind "show more" for long content,
rendered safely via the HTML Sanitizer API. Prompts are rated 1–10, with ratings stored in a local
JSON file. A separate Top Rated view shows prompts sorted by score (recency tiebreak), paginated,
with re-rating supported directly from that view. If the ratings JSON becomes invalid, the
interface offers a delete/reset control. Browse-only — no re-run/continue. Uses a light,
semantic-HTML-friendly CSS framework to keep DOM/JS complexity down.

**Classification**:
- Requirement(s): browse a developer's own Claude Code sessions (CLI + VS Code extension) most
  recent first; view prompts per session in order and expand to see Claude's response; rate any
  prompt 1–10 and be able to re-rate it later; a Top Rated view sorted by score with recency
  tiebreak, paginated; browse-only (no re-run/continue); no accounts; graceful degradation on
  unparseable/long content with a "show more" control; a recovery path (delete/reset) for a
  corrupted ratings file
- Implementation detail: serving the interface via a small Python-based local web server (rather
  than, say, a native desktop app or terminal UI); storing ratings in a flat local JSON file
  (rather than sqlite or another local store); using the browser's built-in HTML Sanitizer API
  specifically; choice of a lightweight/semantic CSS framework
- Assumption(s): Python 3 is available in the target environment; CLI and VS Code extension
  transcripts are both locally discoverable; standard developer file locations are safe to rely on
  without extra configuration
- Unnecessary constraint(s): none identified — every constraint given (Python-3-only, no
  account/server complexity, light DOM/CSS, devcontainer compatibility) is directly justified by
  the stated context (a lightweight personal tool that must run inside a remote devcontainer
  session) rather than an arbitrary restriction

## 14. Dragon's Questions

1. **[unsafe_assumption]** Challenges: relying on Claude Code CLI and VS Code-extension
   transcripts being in a stable, parseable shape today, and staying that way.
   Response: "i'm happy with the file locations as this is a standard developer environment."
   Disposition: accepted_as_risk

2. **[unexpected_input]** Challenges: transcripts may contain tool calls, thinking blocks,
   images, or a truncated/malformed entry from an interrupted session — what happens when the
   tool hits one it can't fully render?
   Response: "degrade the HTML render gracefully perhaps using built in HTML Sanitizer API
   (https://developer.mozilla.org/en-US/docs/Web/API/HTML_Sanitizer_API)."
   Disposition: changed_the_story

3. **[partial_failure]** Challenges: ratings live in a separate local JSON file keyed to
   sessions/prompts — if the underlying session file is deleted, moved, or renamed after being
   rated, does the rating become orphaned and silently corrupt the Top Rated view?
   Response: "if the json is not valid, then provide a delete button in the interface and start
   again."
   Disposition: changed_the_story

4. **[changing_requirements]** Challenges: today it's local-only, no accounts, one JSON file per
   developer — but this is part of a bigger "team learns from each other" push. If the natural
   next request becomes cross-developer visibility (e.g. a shared leaderboard), does today's
   design box this in?
   Response: "local is fine for now"
   Disposition: accepted_as_risk

## Questmaster Record

### Judgment Ledger
- **2026-09-19** · story · asserted_fact — "personal web interface no accounts, no server (ratings can just be kept in a local json file)"
  *Effect*: Fixed scope to a local-only, no-auth, single-developer tool; ratings persisted as a local JSON file rather than a database or service.

- **2026-09-19** · story · asserted_fact — "developer opens the tool, sees a list of sessions (most recent first), developer clicks a session sees a prompts they gave (first prompt first), developer clicks an expand button to view the claude activity, developer rates the prompt 1 (poor) ... 10 (great). The developer has a different view they can see all of their top rated prompts (top 10 most recent first, paginated)."
  *Effect*: Defined the core UX flow (session list -> prompt list -> expand -> rate 1-10) and a dedicated top-rated prompts view as explicit use cases.

- **2026-09-19** · story · asserted_fact — "top scores first, recent breaking ties"
  *Effect*: Set explicit sort order for the Top Rated view: rating descending, recency as tiebreaker.

- **2026-09-19** · story · asserted_fact — "it might be good to allow the developer to re-rate te prompt in this list, so that the top prompts can be maintained -- confirmed: now."
  *Effect*: Confirmed re-rating from the Top Rated view as an in-scope requirement for this build, not deferred.

- **2026-09-19** · story · asserted_fact — "browse only"
  *Effect*: Scoped interaction to browse+rate only -- no re-run, continue, or otherwise acting on a conversation from within the tool.

- **2026-09-19** · story · asserted_fact — "they live in local session/transcript JSONL files"
  *Effect*: Fixed data source to local Claude Code session/transcript JSONL files on disk, not an API or exported log format.

- **2026-09-19** · story · asserted_fact — "both the cli and vscode extension if they are different"
  *Effect*: Extended the data-source requirement to cover transcripts from both the Claude Code CLI and the VS Code extension, parsing each shape if they differ.

- **2026-09-19** · story · correction — "yes a small as possible server running, no account required, vscode should port forward the port automatically."
  *Effect*: Resolved the apparent no-server/web-interface tension: a minimal local server process is required for VS Code's automatic port forwarding, but with no accounts or backend service -- clarifying, not contradicting, the earlier no-server statement.

- **2026-09-19** · story · asserted_fact — "they can just copy and paste their prompt somewhere"
  *Effect*: Confirmed team-sharing is informal/manual (copy-paste) and out of scope as a built-in export/share feature; recorded as an Adjacent Concern rather than a requirement.

- **2026-09-19** · story · asserted_fact — "if the prompt response is really long limit the length with a show more (this should allow us to keep the number dom elements lower)."
  *Effect*: Added an explicit functional/performance requirement: truncate long prompt/response content behind a show-more expander to keep rendered DOM size low.

- **2026-09-19** · story · asserted_fact — "it is part of something bigger, getting the team to support each other and learn from each other."
  *Effect*: Established the Background/Context motivation: this tool supports a broader team initiative of peer learning and mutual support around prompting practice.

- **2026-09-19** · story · asserted_fact — "it would be good to keep the HTML complexity down, use a css framework that is light and HTML semantic friendly so that the DOM and javascript can be kept light"
  *Effect*: Added an explicit technical constraint: prefer a lightweight, semantic-HTML-friendly CSS framework and keep DOM/JS complexity low.

- **2026-09-19** · story · asserted_fact — "ideally this would run with minimum assumptions for technology, we could assume python3 is installed, i would like to beable to run this within a vscode ssh session into devcontainers"
  *Effect*: Set explicit technical constraints: assume only Python 3 as a dependency, and the tool must run correctly inside a VS Code SSH/devcontainer session.

- **2026-09-19** · dragon · dragon_response — "i'm happy with the file locations as this is a standard developer environment."
  *Effect*: Accepted as risk: no explicit mitigation added for potential schema drift between Claude Code releases or surfaces; relying on standard, discoverable file locations.

- **2026-09-19** · dragon · dragon_response — "degrade the HTML render gracefully perhaps using built in HTML Sanitizer API."
  *Effect*: Added explicit requirement: malformed/unrenderable transcript content degrades gracefully, using the browser's built-in HTML Sanitizer API rather than a custom sanitizer.

- **2026-09-19** · dragon · dragon_response — "if the json is not valid, then provide a delete button in the interface and start again."
  *Effect*: Added explicit requirement: on invalid/corrupted ratings JSON, the interface offers a delete/reset control rather than crashing or silently discarding data.

- **2026-09-19** · dragon · dragon_response — "local is fine for now"
  *Effect*: Accepted as risk: the local-file, no-accounts design may need revisiting if the team-learning initiative later calls for cross-developer visibility; deliberately deferred.

- **2026-09-19** · implement · decision_resolution — "add a vertical gap between the prompt boxes, the same gap as on the sessions page. after "Prompt #" add ": DD/MM/YYY HH:MM:SS" and show thinking time for claude's response. Some of the prompts and respones are empty (collapse them if both are empty and consequitive into a "Empty prompts and responses (n)...")"
  *Effect*: Post-implementation scope addition: UC5 and three In-Scope bullets. Recorded here because the developer changed intent after seeing the working tool.

### Comprehension

### Decisions

## 16. Story Readiness Assessment

**Status**: READY

- **Score**: 95 / 100
- **Readiness threshold**: 70
- **Unmet critical conditions**: none

## 17. Story Integrity Assessment

| Dimension | Band | Score / Weight | Evidence |
|---|---|---|---|
| Problem definition | STRONG | 15/15 | Problem Statement (§2) names the concrete gap — no review of past prompts happens, patterns go unexamined and unshared — without naming the web-interface solution; would stay true regardless of what tool eventually gets built. |
| Actors & current state | STRONG | 10/10 | §3/§4 name the actor precisely (individual team developers, own history only) and describe today's behavior concretely (raw local JSONL files, no surfacing mechanism, no review happens). |
| Use cases | STRONG | 15/15 | Four concrete use cases (§5) each with actor/trigger/goal/flow, including alternate/failure paths (graceful degradation, corrupted-ratings recovery) grounded directly in interview answers. |
| Desired outcomes | STRONG | 15/15 | §6 is phrased as a resulting state (developers can look back, build a personal rated record, informally pass tips, contribute to team learning) rather than an implementation action. |
| Scope & boundaries | STRONG | 10/10 | §7 has three genuinely distinct lists — in-scope, non-goals, and adjacent concerns (informal sharing, future leaderboard) — each traceable to a specific interview answer, not restated versions of each other. |
| Success criteria | ADEQUATE | 7/10 | §8's criteria are largely checkable independent of implementation, but one ("via the delete/reset control") names the recovery mechanism rather than only the observable outcome, so it isn't cleanly implementation-free throughout. |
| Assumptions & unknowns | STRONG | 5/5 | §9 keeps Assumed and Unknown as genuinely distinct lists; each unknown (schema differences, schema stability, size limits) would change a real decision if resolved, rather than being padding. |
| Constraints & context | STRONG | 5/5 | §10 ties the tool to a stated, real motivation (team peer-learning push); §12 lists constraints the developer explicitly asserted (Python-3-only, devcontainer/port-forward, no accounts, light DOM/CSS, Sanitizer API), not inferred ones. |
| Solution neutrality | ADEQUATE | 3/5 | §13 completes the full requirement/implementation/assumption/unnecessary-constraint classification, but because the developer specified the solution at unusually high fidelity throughout (exact rating scale, exact pagination/sort behavior), the requirement/implementation-detail line is thinner than usual and some "requirements" are close to solution-shaped. |
| Developer judgment | STRONG | 10/10 | 17 Judgment Ledger entries (§ Questmaster Record), including multiple asserted facts/corrections beyond the Dragon Pass and two Dragon Pass responses that materially changed the story (HTML Sanitizer API, delete/reset recovery UX) — well beyond mere dismissals. |

**Overall score**: 95/100 (computed by `qm-score.sh`, not hand-summed)
