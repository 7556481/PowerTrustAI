from dataclasses import dataclass
from typing import Mapping, Optional, Protocol, Tuple, Union

from core.models import ExecutionIssue, ExecutionStatus


JsonValue = Union[None, bool, int, float, str, Tuple["JsonValue", ...], Mapping[str, "JsonValue"]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    version: str
    description: str
    input_schema: Mapping[str, JsonValue]
    output_schema: Mapping[str, JsonValue]
    allowed_agent_roles: Tuple[str, ...]
    read_only: bool = True


@dataclass(frozen=True)
class ToolRequest:
    call_id: str
    task_id: str
    tool_name: str
    caller_role: str
    payload: Mapping[str, JsonValue]
    timeout_seconds: float


@dataclass(frozen=True)
class ToolResult:
    result_id: str
    call_id: str
    tool_name: str
    tool_version: str
    status: ExecutionStatus
    payload: Mapping[str, JsonValue]
    issue: Optional[ExecutionIssue] = None


class Tool(Protocol):
    @property
    def spec(self) -> ToolSpec: ...

    async def execute(self, request: ToolRequest) -> ToolResult: ...


class ToolExecutor(Protocol):
    async def execute(self, request: ToolRequest) -> ToolResult: ...
