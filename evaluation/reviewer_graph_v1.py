"""Single-task graph adapter for the frozen reviewer component, not a new agent."""
from functools import lru_cache
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langsmith import tracing_context

from evaluation import premise_bound_review_v7 as v7, premise_bound_review_v6 as v6
from evaluation.reviewer_baseline_trial_v1 import validate_task
from harness.graph_runtime_v1 import validate_versions
from model_adapter.runtime import model_invocation_scope
from services.structured_model import structured_request


VERSION = 'reviewer-component-langgraph-adapter-v1'


class ReviewState(TypedDict, total=False):
    messages: tuple
    prediction: dict


class ReviewContext(TypedDict):
    task: dict
    client: object
    diagnostics: object


async def prepare(_state: ReviewState, runtime: Runtime[ReviewContext]):
    task = runtime.context['task']
    validate_task(task)
    return {'messages': v7.messages(task)}


async def review(state: ReviewState, runtime: Runtime[ReviewContext]):
    context = runtime.context
    value, _ = await structured_request(
        context['client'], state['messages'], v7.VERSION,
        lambda raw: v6.parse(raw, context['task']), diagnostics=context['diagnostics'],
        response_contract_version=v6.VERSION, max_corrections=1, max_message_chars=90000,
    )
    return {'prediction': value}


@lru_cache(maxsize=1)
def build_graph():
    builder = StateGraph(ReviewState, context_schema=ReviewContext)
    builder.add_node('prepare', prepare, retry_policy=[], cache_policy=None)
    builder.add_node('review', review, retry_policy=[], cache_policy=None)
    builder.add_edge(START, 'prepare')
    builder.add_edge('prepare', 'review')
    builder.add_edge('review', END)
    return builder.compile(checkpointer=None, cache=None, store=None, name=VERSION)


async def review_task(task, client, diagnostics=None):
    validate_versions()
    with model_invocation_scope(task['sample_id'], v7.VERSION, 1), tracing_context(enabled=False, parent=False):
        result = await build_graph().ainvoke(
            {}, context={'task': task, 'client': client, 'diagnostics': diagnostics},
            config={'callbacks': [], 'recursion_limit': 4},
        )
    return result['prediction']
