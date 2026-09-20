# Plan Integrity Assessment

**Assessed**: 2026-09-19 · **Against**: story.md, spec.md
**Assessment context**: INDEPENDENT
**Source digests**: story.md `sha256:200d3ed3d6ab1547454184c64c3e5b32a915207b0d65a6ceefc11bf22f44900b`, spec.md `sha256:b33ed7bbc7dd1cfcfb743fd974a2b8522bb3dda62332ac256f3b50b724e504b7`, plan.md `sha256:2f9b682817448e4742db072e74614a3d72416839584af6150b3782fe8892bb35`

## Decisions for you (2)

1. **ratings.json storage location is unspecified** → *Where does ratings.json actually live — a fixed path (e.g. ~/.claude-rating-tool/ratings.json), or something relative to the server's launch directory? Given session discovery spans all projects, should the ratings store be single and global rather than per-project?* `UNJUSTIFIED_DRIFT` · medium · see Finding 1
2. **127.0.0.1-only binding's compatibility with VS Code auto-forwarding is asserted, not justified in the plan text** → *Should plan.md's Constraints section cite VS Code's forward-vs-publish distinction so the 127.0.0.1-sufficiency claim is defensible from the plan alone, and should the empty round-1 Comprehension Decisions entry be filled in to formally close this out?* `CLARIFIED` · low · see Finding 4

## Outstanding accepted risk (0)

No outstanding accepted risk.

## Integrity

intent_preservation **STRONG** 20/20 · specification_coverage **ADEQUATE** 10/15 · constraint_preservation **STRONG** 15/15 · proportionality **STRONG** 15/15 · legibility **ADEQUATE** 10/15 · risk_management **ADEQUATE** 7/10 · test_strategy **STRONG** 5/5 · traceability **STRONG** 5/5 → **87/100**

| Dimension | Band | Score | Evidence |
|---|---|---|---|
| intent_preservation | STRONG | 20/20 | plan.md Summary directly threads every element back to story.md §6 Desired Outcomes and UC1/UC2: 'A developer-facing, single-user local web tool for browsing their own past Claude Code conversations (CLI and VS Code extension sessions, which research confirms share one on-disk store) and rating individual prompts 1–10, plus a paginated Top Rated view sorted by score with recency as a tiebreaker.' A reader can explain exactly why this plan solves the story's problem without inference. |
| specification_coverage | ADEQUATE | 10/15 | All 20 FRs have a traceable plan/contract element (e.g. FR-001->GET /api/sessions pagination, FR-013->is_truncated/500-word threshold, FR-015 vs FR-016 kept distinct, FR-020->'binds to 127.0.0.1 only, never 0.0.0.0'). Gap: FR-012's local persistence is never given an actual file path/location, despite session discovery spanning multiple projects. |
| constraint_preservation | STRONG | 15/15 | All six story §12 constraints are explicitly visible: Python-3-only/no-install, devcontainer/SSH compatibility, no accounts, local JSON ratings, light DOM/CSS (vendored classless stylesheet), and the HTML Sanitizer API with fallback. |
| proportionality | STRONG | 15/15 | Every module is explicitly justified (discovery/parsing/ratings/server kept separate 'so each can be unit-tested in isolation... without implying they'll ever ship or deploy separately'); Complexity Tracking states no additional projects/services/indirection are introduced; unittest-over-pytest and vendored-CSS-over-CDN are both argued from FR-017/story §12, not asserted bare. |
| legibility | ADEQUATE | 10/15 | research.md's Decision/Rationale/Alternatives-considered structure and inline FR citations are followable by a newcomer, but the 127.0.0.1-vs-0.0.0.0 compatibility claim (FR-020 vs FR-017) is asserted with zero supporting reasoning in the plan text itself — exactly the gap that produced the developer's own Comprehension Checkpoint doubt. |
| risk_management | ADEQUATE | 7/10 | 3 of 4 story §14 Dragon's Questions are explicitly mitigated with citations (schema drift tolerance, Sanitizer API + fallback, is_orphaned vs whole-file reset). Gap: the Comprehension round-1 prediction about 0.0.0.0-vs-127.0.0.1 is never resolved anywhere in plan.md — its own '### Decisions' subsection is empty — even though the underlying technical claim is correct per independent verification. |
| test_strategy | STRONG | 5/5 | tests/{contract,integration,unit} map directly to contracts/http-api.md endpoints, quickstart.md scenarios, and parsing/ratings edge cases; quickstart.md's 6 validation scenarios explicitly cover User Story 3 (corrupted-ratings recovery) and spec.md's Edge Cases. |
| traceability | STRONG | 5/5 | Nearly every non-trivial line in plan.md/research.md/data-model.md/contracts/http-api.md cites the specific FR or story section it satisfies. |

## Drift Classification summary

11 elements compared: **1 PRESERVED**, **5 REFINED**, **2 CLARIFIED**, **2 DISCOVERED**, **1 UNJUSTIFIED_DRIFT**.
Per-element table: appendix below.

Partially agree on 'most_likely_wrong': the unittest-vs-pytest half of the worry is largely unfounded (fully justified by the stdlib-only rationale, STRONG proportionality), but the 0.0.0.0-vs-127.0.0.1 half was a sharp, worthwhile catch — after independent research against VS Code's own devcontainers documentation, the plan's 127.0.0.1-only claim is actually CORRECT (automatic forwarding runs in-namespace and treats forwarded ports as localhost to the app; 0.0.0.0 only matters for Docker's separate appPort/publish mechanism, unused here), but the plan never states this reasoning and its own Decisions section left the question open. Agree fully on 'what-to-cut, nothing': proportionality review found no untraceable complexity — the one real gap found (unspecified ratings.json location) is a missing detail, not excess to cut. Partially agree on 'breaks-first, HTML sanitization': the plan already pre-empts the most obvious sanitizer failure mode with a textContent fallback; a more likely actual first break is the accepted-as-risk transcript-schema drift across future Claude Code versions, which has no fallback beyond per-line tolerance.

### Finding 1: ratings.json storage location unspecified
- **Source artifact**: spec.md FR-012 / data-model.md Rating storage shape
- **Destination artifact**: plan.md Technical Context (Storage), data-model.md, quickstart.md
- **Original intent**: FR-012: System MUST persist ratings locally so they survive restarting the tool. Session discovery scans ~/.claude/projects/** across all of a developer's projects, not one repo.
- **New behaviour**: Every artifact refers to 'a single local ratings.json file' as self-evident, but none states where on disk it lives, risking inconsistent visibility if launched from different working directories.
- **Classification**: UNJUSTIFIED_DRIFT · **Severity**: medium
- **Evidence**: data-model.md: 'Storage shape (ratings.json, one file, FR-012)' — no path given anywhere; quickstart.md scenario 4 also omits a path.
- **Question for the developer**: Where does ratings.json actually live, and should it be single/global rather than per-project given cross-project session discovery?

### Finding 2: promptId as rating identity key
- **Source artifact**: research.md §1 (real session file inspection), §6
- **Destination artifact**: data-model.md Rating, contracts/http-api.md PUT /api/ratings/{prompt_id}
- **Original intent**: spec.md describes Rating only abstractly, with no stated identity/keying mechanism.
- **New behaviour**: Plan concretely keys ratings by the transcript's own stable promptId field, discovered via real file inspection, with session_id/position stored redundantly for FR-015 orphan detection.
- **Classification**: DISCOVERED · **Severity**: low
- **Evidence**: research.md §6: promptId chosen specifically because it 'is stable independent of where the file currently lives.'
- **Question for the developer**: None required — sound, well-justified discovery.

### Finding 3: HTML Sanitizer API fallback for unsupported browsers
- **Source artifact**: story.md §12 Constraints / Dragon's Question 2
- **Destination artifact**: research.md §5, plan.md Primary Dependencies
- **Original intent**: Story mandates the Sanitizer API but says nothing about unsupported browsers.
- **New behaviour**: Plan adds a plain-text fallback when the API is unavailable, extending FR-014's graceful-degradation intent to rendering.
- **Classification**: DISCOVERED · **Severity**: low
- **Evidence**: research.md §5: fallback path 'so a missing/older-browser API degrades safely rather than blocking rendering.'
- **Question for the developer**: None required — sound addition.

### Finding 4: 127.0.0.1-only binding vs VS Code auto-port-forwarding compatibility, asserted without justification
- **Source artifact**: plan.md Comprehension round 1 (most_likely_wrong prediction); plan.md Decisions (empty)
- **Destination artifact**: plan.md Constraints / Technical Context
- **Original intent**: FR-017 requires no manual network/port configuration; FR-020 requires localhost-only binding. Developer explicitly flagged uncertainty about compatibility.
- **New behaviour**: plan.md asserts compatibility without explaining why, and the Comprehension Checkpoint's own Decisions subsection meant to resolve this is empty.
- **Classification**: CLARIFIED · **Severity**: low
- **Evidence**: Verified against VS Code devcontainers docs ('Forwarding or publishing a port'): automatic forwarding runs in-namespace and forwarded ports 'look like localhost to the application'; 0.0.0.0 only matters for Docker's separate appPort/publish mechanism, unused here. The plan's claim is correct but unexplained in-document.
- **Question for the developer**: Should the plan cite this reasoning explicitly and close out the round-1 Decision?

## Appendix — full per-element classification

| Element | Classification | Notes |
|---|---|---|
| Python 3 stdlib-only, no pip install | REFINED | spec.md Assumptions left the runtime open; plan makes the concrete, justified choice consistent with story §12. |
| unittest over pytest | REFINED | Extends the stdlib-only principle to the test toolchain with stated rationale. |
| Vendored CSS instead of CDN | CLARIFIED | Resolves the story's underspecified CSS-framework constraint, justified against devcontainer offline-access risk. |
| promptId-based rating identity key | DISCOVERED | Concrete schema fact learned from real session-file inspection; not knowable from story/spec text alone. |
| Single-project structure (one process serves API + frontend) | REFINED | Elaborates story's 'as small as possible server' correction into a concrete architecture. |
| discovery/parsing/ratings/server/web module split | REFINED | Implementation-level decomposition for isolated unit testing; explicitly not implying separate deployment. |
| localhost-only (127.0.0.1) binding | PRESERVED | Directly carries forward spec.md's Clarifications decision and FR-020 verbatim. |
| HTTP API contract's endpoint set | REFINED | Concrete REST interface fulfilling multiple FRs at a level of detail spec.md doesn't specify but doesn't contradict. |
| Sanitizer API fallback (textContent when unavailable) | DISCOVERED | Browser-compatibility edge case identified during planning research. |
| Session-list pagination reusing Top-Rated pattern | CLARIFIED | Directly carries forward spec.md Clarifications Q3 into FR-001 and the /api/sessions contract. |
| ratings.json storage path (cwd vs home dir vs XDG) | UNJUSTIFIED_DRIFT | Never specified despite being load-bearing for FR-012 persistence; a silent gap, not a recorded Decision. |

## Advisory note

This assessment does not block, modify, or reject the plan (FR-022). All findings require developer judgment.
