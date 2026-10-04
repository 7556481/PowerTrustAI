# Deterministic generation citations and bounded real revision

Generation output v3 uses answer_units (kind, literal text, evidence_ids),
assumptions, missing_information and evidence_sufficient. Model output does not
repeat answer ID/version or produce character offsets. The program joins literal
units with exactly two LF characters and calculates Python Unicode character ranges.
Embedded newlines are preserved. Repeated sentences get distinct intervals.
Uncited technical content is still extracted and reviewed; a scope label never
establishes support or bypasses review.

The old generation v2 parser and saved AnswerDraft/CitationBinding remain readable.
New CLI generation defaults to v3. Older Python constructor callers retain v2
unless schema_version=3 is selected. Historical failures remain failures.
The archived engineering case copied source sentences into answer citation fields;
those sentences did not occur literally in the paraphrased answer. The new protocol
removes this location task, not the need for semantic review.

ModelRevisionAgent implements the existing interface. It receives frozen answer,
both independent reviews, allowed evidence and constraints. It returns answer
units, changes bound to known finding IDs, and explicit unresolved IDs. Every input
finding is accounted for. Unknown IDs/fields, invented offsets or sources fail.
Changes are proposals, not declarations that historical findings have passed.
The prompt requires correction/removal/narrowing rather than disclaimer-only edits;
whether this was achieved remains a re-review and human-review question.

LimitedRepairPolicy is explicit opt-in within the existing OfflineHarness. An
observed contradiction, insufficient evidence or domain warning can trigger one
business revision despite retained missing-input/unperformed-simulation findings.
Execution or required retrieval failures block revision. Coverage gaps remain.
The final policy never returns pass. After revision the complete extraction and
both retrieval/review paths run again at the same knowledge version.

HarnessResult.review_rounds preserves frozen drafts, extraction, both reviews and
reports. revision_outputs preserves proposed edits and unresolved historical IDs.
Later failures retain prior valid rounds. Model requests are counted directly by
ModelClient, without a duplicate Harness call charge. Each structured stage has one
initial request and at most one budgeted format correction.

Private pre-request diagnostics archive complete creation inputs and actual Evidence
records. The generation-full-input-v2 shape is reused for revision: its prompt
version identifies revision and answer_requirements includes the serialized frozen
answer/reviews/constraints actually supplied. This is a new revision input, never
reconstructed historical generation evidence. The generation-input filename is a
storage convention. SHA-256 binds input archives; literal responses, prompt/contract
versions and validation errors are also archived. Credentials/headers are excluded.

## Running

From the root, one complete PowerShell command (program privately loads root .env):

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m harness.revision_demo --db D:\PowerTrustAI\data\retrieval_local\pdf-quality\nerc-reactive-planning-2016.sqlite3 --knowledge-version k-7268b72e3f29f10bee44469b24680593116feef95c4f410680392292d19ecd55 --max-requests 25 --output D:\PowerTrustAI\data\retrieval_local\deepseek\revision-new-run.json

Optional --scenarios selects engineering-data,normal-voltage-error,quantity-unit-error.
New output paths are mandatory. The first generates a new draft. The other two
use explicitly human-constructed synthetic bad drafts with real indexed references;
no complete historical generation snapshot is invented. These are development
examples, not natural generation failures or an independent acceptance set.

Each invocation has an actual request cap. Sum calls across invocations when using
a shared trial budget. Repeated errors after one correction stop that scenario.
Independent cases may continue within the remaining budget. Ordinary tests do not
load .env or invoke paid APIs:

    & D:\PowerTrustAI\.venv\Scripts\python.exe -m unittest discover -s tests -q

No simulation, arbitrary-prose unit parser, engineering safety certification or
independent semantic validation is supplied. Rules are demonstration rules.
Review completion and traceable citation location do not establish correctness.
