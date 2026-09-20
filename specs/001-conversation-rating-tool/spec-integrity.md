# Specification Integrity Assessment

**Assessed**: 2026-09-19 · **Against**: story.md
**Assessment context**: INDEPENDENT
**Source digests**: story.md `sha256:200d3ed3d6ab1547454184c64c3e5b32a915207b0d65a6ceefc11bf22f44900b`, spec.md `sha256:30c9843bfeccbacd9347e22883865ec168d9e8a22c4b57c80503e67c13107c86`

## Decisions for you (1)

1. **Per-entry orphaned-rating handling (FR-015) was never explicitly approved by you** → *Should an orphaned rating (its session file moved/renamed/deleted, while the ratings JSON stays valid) be silently omitted, visibly flagged, or instead handled via the same whole-file delete/reset flow you already approved for corrupted ratings data?* `DISCOVERED` · medium · see Finding 1

## Outstanding accepted risk (0)

No outstanding accepted risk.

## Integrity

story_fidelity **STRONG** 20/20 · requirement_completeness **STRONG** 15/15 · requirement_testability **ADEQUATE** 10/15 · scope_discipline **ADEQUATE** 13/20 · traceability **STRONG** 10/10 · handling_of_ambiguity **WEAK** 3/10 · internal_consistency **STRONG** 10/10 → **81/100**

| Dimension | Band | Score | Evidence |
|---|---|---|---|
| story_fidelity | STRONG | 20/20 | Story UC1 maps directly onto spec User Story 1 and its acceptance scenarios; the peer-learning/team-sharing outcome from story S6 reappears in spec User Story 2's rationale. No solution-language drift: spec's Assumptions explicitly defer runtime choice to planning. |
| requirement_completeness | STRONG | 15/15 | All four story use cases and every Scope In-Scope item map to at least one FR (UC1->FR-001-006, UC2->FR-007-009, UC3->FR-016, UC4->FR-013, degradation->FR-014, constraints->FR-011/FR-017). |
| requirement_testability | ADEQUATE | 10/15 | Most FRs pair with concrete Given/When/Then scenarios, but FR-013's 'very long' and SC-004's degradation trigger leave size thresholds unquantified, and SC-003's 'no perceptible delay' is subjective as written. |
| scope_discipline | ADEQUATE | 13/20 | 18 of 19 FRs plus all Assumptions trace cleanly to story content. FR-015 (automatic per-entry orphan omit/flag) is DISCOVERED: it elaborates Dragon Question 3's scenario beyond what the developer's recorded response (whole-file delete/reset) actually committed to. |
| traceability | STRONG | 10/10 | Requirements are numbered FR-001-FR-019 and each maps one-to-one to an identifiable story clause, e.g. FR-007 traces directly to the Judgment Ledger's 'top scores first, recent breaking ties'. |
| handling_of_ambiguity | WEAK | 3/10 | Of story's three stated Unknowns, only the CLI/VS-Code schema-shape question is carried into spec Assumptions. Schema stability across Claude Code versions, and the realistic size upper bound, are never mentioned anywhere in spec.md. |
| internal_consistency | STRONG | 10/10 | No requirement contradicts another requirement or a stated non-goal; FR-015 and FR-016 address distinct failure modes (orphaned-but-valid data vs. structurally invalid data) without conflicting. |

## Drift Classification summary

25 elements compared: **23 PRESERVED**, **1 REFINED**, **0 CLARIFIED**, **1 DISCOVERED**.
Per-element table: appendix below.

### Finding 1: Automatic per-entry orphan omit/flag in Top Rated view
- **Source artifact**: story.md
- **Destination artifact**: spec.md
- **Original intent**: Dragon's Question 3 raised the scenario of a rated session's underlying file being deleted/moved/renamed, but the developer's recorded response only committed to a whole-file delete/reset control for when the ratings JSON itself becomes invalid.
- **New behaviour**: FR-015 and its matching Edge Case mandate automatic detection and omission/flagging of an individual orphaned entry in the Top Rated view -- a more granular, distinct recovery mechanism than the whole-file delete/reset the developer actually approved.
- **Classification**: DISCOVERED · **Severity**: medium
- **Evidence**: story.md Dragon's Question 3 response: "if the json is not valid, then provide a delete button in the interface and start again." vs spec.md FR-015: "System MUST omit or clearly flag that entry rather than breaking the top-rated view."
- **Question for the developer**: Should an orphaned rating be silently omitted, visibly flagged, or handled via the same whole-file delete/reset flow you already approved -- rather than a new automatic per-entry mechanism?

## Appendix — full per-element classification

| Element | Classification | Notes |
|---|---|---|
| FR-001 | PRESERVED | Sessions list, most-recent-first -- matches Scope item 1 and UC1. |
| FR-002 | PRESERVED | Source sessions from CLI + VS Code extension -- matches actors and Scope item 1. |
| FR-003 | PRESERVED | Open session, view prompts in order -- matches Scope item 2 / UC1. |
| FR-004 | PRESERVED | Expand prompt to view Claude's response -- matches UC1 flow exactly. |
| FR-005 | PRESERVED | Rate 1-10 -- matches Scope item 3 / UC1 exactly. |
| FR-006 | PRESERVED | Re-rate later -- matches Scope item 3. |
| FR-007 | PRESERVED | Top Rated view, rating desc / recency tiebreak -- matches Scope item 4 and Ledger. |
| FR-008 | PRESERVED | Paginated -- matches Scope item 4. |
| FR-009 | PRESERVED | Re-rate from Top Rated view -- matches UC2 and Ledger confirming in-scope now. |
| FR-010 | PRESERVED | Browse-only, no re-run/continue -- matches Out-of-Scope item 3 / Ledger 'browse only'. |
| FR-011 | PRESERVED | No account/login -- matches Out-of-Scope item 1 and Constraints. |
| FR-012 | PRESERVED | Persist ratings locally, survive restart -- JSON-file detail correctly dropped per story's own solution-neutrality split. |
| FR-013 | PRESERVED | Truncate long content behind 'show more' -- matches Scope item 5 / UC4. |
| FR-014 | PRESERVED | Graceful degradation on unrenderable content -- matches Scope item 6 / Dragon Q2, Sanitizer-API detail correctly excluded. |
| FR-015 | DISCOVERED | Per-entry omit/flag is a reasonable elaboration of Dragon Q3's scenario, but developer's response only approved whole-file delete/reset (FR-016). |
| FR-016 | PRESERVED | Delete/reset invalid ratings data -- matches Scope item 7 / UC3 / Dragon Q3 response exactly. |
| FR-017 | PRESERVED | Usable via VS Code auto port-forwarding without manual config -- Python-3-specific detail appropriately abstracted as a planning concern. |
| FR-018 | PRESERVED | No built-in export/share -- matches Out-of-Scope item 2 and Adjacent Concerns. |
| FR-019 | PRESERVED | No cross-developer exposure -- matches actors section and Out-of-Scope item 4. |
| Assumption: own-machine, no shared/server deployment | PRESERVED | Matches Out-of-Scope item 1 and Assumed context directly. |
| Assumption: environment provides needed lightweight runtime, specific runtime left to planning | REFINED | Generalizes story's specific 'Python 3' assumption into a technology-neutral runtime assumption, per story's own solution-neutrality reasoning. |
| Assumption: CLI/VS Code sessions discoverable in standard locations | PRESERVED | Matches Assumed item 2 verbatim in substance. |
| Assumption: one session = one transcript | PRESERVED | Matches Assumed item 3 verbatim. |
| Assumption: sharing happens informally outside the tool | PRESERVED | Matches Adjacent Concerns and Out-of-Scope item 2; reframed from non-goal to assumption, same intent. |
| Assumption: CLI/VS Code schema-identity unconfirmed, deferred to planning | PRESERVED | Matches Unknown item 1 near-verbatim, including the 'confirm during planning' framing. |

## Advisory note

This assessment does not block, modify, or reject spec.md. All findings require developer judgment before or during /speckit-plan.
