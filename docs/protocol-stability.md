# Scoped review and execution stability

This is protocol/observability work, not new factual or engineering capabilities.
The four existing agents, Harness, Retriever, BM25 and legacy project remain.
Historical generation/review contracts and failed archives remain readable and failed.

## Contracts

Evidence Verification v8.2 makes one independent-claim request and a separate
request per original citation. Each request receives only its allowed Evidence
fragments. Original citation calls never receive independently retrieved body
candidates; independent calls never receive old original-only body candidates.
Each wire quote_id binds answer ID/version/text hash, knowledge version, purpose,
check/citation and protocol version, plus its exact source candidate. IDs from other
scopes/versions and old canonical IDs are rejected. The program performs an exact
lookup into that request's directory, not a similar-ID/text replacement.

The model sees one whole-fragment candidate per Evidence, with raw text, interval,
source metadata and quality warnings. Original contents/conditions are retained.
Internal canonical catalogs and Evidence validation are unchanged. Snapshot
projection retains input context/presence/metadata but does not deliver old review
JSON or unavailable snapshot body text as independent candidates. Such projections
cannot prove absent document content or actual computation.

Independent findings and original citation reviews have separate output schemas.
Findings may include actual dimension observations; citations cannot echo those
fields, component IDs or program binding/coverage diagnostics. Canonical required
dimensions use jurisdiction, not region. Complete legal examples and allowed
field lists are supplied. No illegal field is silently discarded.

Domain output v2 discriminates by status: warning/not_assessable require the
missing_prerequisites array; no_issue/not_applicable forbid that model field, with
the program binding [] as the defined schema projection. Other checks still
retain missing engineering inputs. This does not turn unavailable inputs into
completed studies. Rules remain explicitly demonstration rules with their source,
scope and version, and simulation_boundary stays not_assessable.

Revision v2 provides a program finding_catalog instead of nested full audit outputs
and their duplicated Evidence/candidate/request records. Conditions, reasons,
claim qualifiers, applicable rules, citation concerns and consistency checks are
preserved. Raw allowed Evidence is separately delivered once. The model returns
exactly one finding_actions item per finding ID: modified, retained or unresolved,
with explanation. Unknown IDs, duplicates, missing rows and unknown fields fail.
Program projections generate RevisionChange and explicit nonmodified IDs.
Accounting completeness never means resolution; re-extraction/re-review are independent.

The newest protocols are selected by revision_demo --stable-protocols.
Older Python defaults preserve older contracts; ordinary regression tests remain
offline. No paid API call is made by importing these modules or running tests.

## Isolation boundaries

An entire finding/check is atomic, including all local bases, component indexes,
conditions and semantic judgments. A bad basis rejects that whole finding; supported
components in the same invalid finding are not cherry-picked. Other complete,
strictly validated findings/checks remain. A missing check is explicitly unexecuted
and not_assessable, never inferred supported.

Unknown/ambiguous root bindings, answer/version/snapshot inconsistency and global
structure failures form a whole-response boundary. Duplicate item IDs invalidate
all corresponding duplicates; no arbitrary first item wins. Previously validated
items may survive a later format/transport failure only for the same immutable
input and request scope. The diagnostic records retained IDs and response attempt.

After merging, the full existing core validators run again, including cross-field
projections, immutable Evidence, quote intervals, claim coverage and citation
coverage. If a global invariant cannot hold, no invalid merged result is accepted.
Any rejected/missing required item creates an execution issue, blocks revision or
overall completion gates as appropriate, and can never produce an overall pass.
First reviews remain independent and do not see the peer's judgments.

One initial request plus at most one budgeted format correction per scoped request.
Corrections include all detected paths, constraints and legal processing options.
Harness counts actual model requests, including partial/failed requests. Synchronous
SQLite and transport keep their existing bounded thread behavior; timeout cannot
forcibly stop underlying threads, and delayed/unknown billing is not fabricated.

## Diagnostics and overhead

ModelCallRecord now includes actual message characters, delivered candidate count,
delivered/unique source-text characters and scope IDs. Input/output tokens and
duration are service/runtime observations, not character-to-token guesses.
Response text, prompt/contract version, validation errors and scoped catalog
are saved only under ignored data/retrieval_local. No key or request header is saved.

Whole-fragment delivery removes duplicated text/context windows within a request;
the complete original fragment remains available. Two independent reviewers and
re-review still repeat legitimate reads. Separate original-citation calls increase
call count. Format correction resends the initial input and rejected output.
Older archives lacking request counters cannot support an exact historical
character-total comparison. This work does not optimize BM25 or add caching.

## Commands

New paths required; each invocation has its own actual request cap. Add counts
across invocations to enforce the round's 20-request maximum. Program loads root
.env privately for authentication.

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m harness.revision_demo --stable-protocols --scenarios normal-voltage-error --max-requests 10 --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 --knowledge-version k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55 --output D:\PowerTrustAI\data\retrieval_local\deepseek\stability-new-minimal.json

The minimal answer is explicitly human-constructed synthetic_fixture with one
false assertion and no invented original citation. Other scenarios are gated on
minimal_execution_complete, which is execution only, not audit pass.

To re-extract and re-review an already saved revision without regenerating or
revising it again, use the existing Harness assess-existing mode through the demo:

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m harness.revision_demo --stable-protocols --review-saved-revision D:\PowerTrustAI\data\retrieval_local\deepseek\stability-minimal-v2.json --max-requests 6 --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 --knowledge-version k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55 --output D:\PowerTrustAI\data\retrieval_local\deepseek\stability-new-rereview.json

The new artifact links the earlier first reviews/revision by file SHA-256; it does
not rewrite the historical failed re-review as success.

After the gate is satisfied, a future authorized round can select
--scenarios engineering-data,quantity-unit-error and
--first-success D:\PowerTrustAI\data\retrieval_local\deepseek\stability-minimal-v3-rereview.json,
using a new output path and available budget. This turn used 19/20 requests and
did not start those scenarios with only one request remaining.

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q

## Remaining limits

Final offline inspection also tightened domain protocol v2 inputs: saved indexed
references are kept for original-citation review, snapshot lookup and revision,
but are not automatically copied into the current domain-review evidence set.
Only current domain retrieval and explicitly marked user references are delivered.
Legacy protocol v1 remains compatible. This final delivery change has an offline
integration regression; the paid artifacts precede it and are not presented as
real-service validation of this additional change.

Atomic structure and execution completeness do not establish semantic correctness.
The repaired answer expanded into QV and missing-input statements, creating more
claims and review cost. Method limitations and region qualifications still require
human review. No simulation, production domain rules, engineering certification,
additional Agent, frontend or general resume scheduler was added.
