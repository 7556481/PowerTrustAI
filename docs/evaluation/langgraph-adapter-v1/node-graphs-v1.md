# Optional LangGraph graphs v1

Implementation commit: `9f0e491ad41e8b1beb4d2d9bd45eff2755163d4c`. Generated locally from the compiled graph structures; no remote image renderer or live model.

## Business Harness: seven shared stages

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	validate_saved_inputs(validate_saved_inputs)
	generate(generate)
	extract_and_tools(extract_and_tools)
	prepare_review(prepare_review)
	review_pair(review_pair)
	merge_and_decide(merge_and_decide)
	revise(revise)
	__end__([<p>__end__</p>]):::last
	__start__ --> validate_saved_inputs;
	extract_and_tools --> prepare_review;
	generate -.-> __end__;
	generate -.-> extract_and_tools;
	merge_and_decide -.-> __end__;
	merge_and_decide -.-> revise;
	prepare_review --> review_pair;
	review_pair -.-> __end__;
	review_pair -.-> merge_and_decide;
	revise -.-> __end__;
	revise -.-> extract_and_tools;
	validate_saved_inputs -.-> extract_and_tools;
	validate_saved_inputs -.-> generate;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

## Separate reviewer component: prepare and review

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	prepare(prepare)
	review(review)
	__end__([<p>__end__</p>]):::last
	__start__ --> prepare;
	prepare --> review;
	review --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```
