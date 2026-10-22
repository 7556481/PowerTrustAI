"""Optional, local LangGraph routing over the existing seven Harness stages."""
from functools import lru_cache
from importlib.metadata import version
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langsmith import tracing_context

from core.models import TaskMode
from core.validation import InputError
from harness.execution import RunExecution


VERSION = 'harness-langgraph-adapter-v1'
PINNED_VERSIONS = {
    'langgraph': '1.2.16', 'langchain-core': '1.6.13',
    'langgraph-checkpoint': '4.3.0', 'langgraph-prebuilt': '1.1.1',
    'langgraph-sdk': '0.4.8', 'langsmith': '0.14.12',
}
STAGES = (
    'validate_saved_inputs', 'generate', 'extract_and_tools', 'prepare_review',
    'review_pair', 'merge_and_decide', 'revise',
)


def validate_versions():
    for name, expected in PINNED_VERSIONS.items():
        if version(name) != expected:
            raise InputError('Optional graph dependency differs from lock: ' + name)


class FlowState(TypedDict):
    business_state: str
    last_stage: str
    next_stage: str


class FlowContext(TypedDict):
    # Runtime-only resources, never checkpointed or sent as model messages.
    execution: RunExecution


def stage_node(name):
    async def node(_state: FlowState, runtime: Runtime[FlowContext]):
        execution = runtime.context['execution']
        ended = await getattr(execution, name)()
        target = ''
        if name == 'validate_saved_inputs':
            target = 'generate' if execution.request.mode == TaskMode.QUESTION_ANSWER else 'extract_and_tools'
        elif name == 'generate':
            target = END if execution.generation_only else 'extract_and_tools'
        elif name == 'review_pair':
            target = END if execution.evidence_only else 'merge_and_decide'
        elif name == 'merge_and_decide':
            target = END if ended else 'revise'
        elif name == 'revise':
            target = 'extract_and_tools' if ended else END
        return {'business_state': execution.state.value,
                'last_stage': name, 'next_stage': target}
    return node


def route(state: FlowState):
    return state['next_stage']


@lru_cache(maxsize=1)
def build_graph():
    """Cache graph structure only; each invocation receives a fresh context."""
    builder = StateGraph(FlowState, context_schema=FlowContext)
    for name in STAGES:
        builder.add_node(name, stage_node(name), retry_policy=[], cache_policy=None)
    builder.add_edge(START, 'validate_saved_inputs')
    destinations = {
        'validate_saved_inputs': ['generate', 'extract_and_tools'],
        'generate': ['extract_and_tools', END],
        'review_pair': ['merge_and_decide', END],
        'merge_and_decide': ['revise', END],
        'revise': ['extract_and_tools', END],
    }
    for source, targets in destinations.items():
        builder.add_conditional_edges(source, route, {target: target for target in targets})
    builder.add_edge('extract_and_tools', 'prepare_review')
    builder.add_edge('prepare_review', 'review_pair')
    return builder.compile(checkpointer=None, cache=None, store=None, name=VERSION)


async def run_graph(execution):
    # Disable tracing even under an outer caller's tracing context. The business
    # observer is unchanged; no LangSmith client, server, checkpoint or resume.
    with tracing_context(enabled=False, parent=False):
        await build_graph().ainvoke(
            {'business_state': execution.state.value, 'last_stage': '', 'next_stage': ''},
            context={'execution': execution},
            config={'callbacks': [], 'recursion_limit': 8 + 5 * execution.budget.max_revision_rounds},
        )
