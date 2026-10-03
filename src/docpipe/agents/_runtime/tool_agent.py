"""A tool-using LangGraph agent with the production defaults already in place.

Give it a system prompt and tools; mark the tools that need a human decision. It adds:

    START -> agent --tool calls--> tools -> agent ...
                |  \\--approval needed--> approval_gate (interrupt) --approved--> tools
                |                                  \\--rejected--> END
                |  \\--loop detected--> fallback -> END
                \\--final answer--> verify (optional groundedness check) -> END

Loop guard (step budget, duplicate-call suppression, repeat cap, no-progress window), tool-call
logging and progress events, a per-node timeout, a recursion limit, checkpointing per session
(in memory, or Postgres when ``startup(database_url)`` is given) and provider-error mapping.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Annotated, Any, Callable, Dict, List, Mapping, Optional, Sequence, TypedDict, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime
from langgraph.types import Command, interrupt

from docpipe.agents._runtime.errors import (
    AgentServiceError,
    ApprovalPendingError,
    GraphUninitializedError,
    LoopBreakerError,
    NoPendingApprovalError,
    OutputHallucinationError,
    ProviderModelError,
    ToolExecutionError,
)
from docpipe.agents._runtime.guardrails.loop_guard import DUPLICATE_PREFIX, FEEDBACK_FLAG, LoopGuardrail, current_turn
from docpipe.agents._runtime.telemetry import get_logger, trace_context, tracing_callbacks
from docpipe.agents._runtime.tool_logging import ToolCallLoggingHandler

logger = get_logger(__name__)

ProgressCallback = Callable[[str, str, str], None]
ApprovalRule = Union[bool, str, Callable[[Dict[str, Any]], Optional[str]]]
Verifier = Callable[[str, Sequence[str]], List[str]]
# Builds the per-run tool callbacks from the request's progress callback (default: ``ToolCallLoggingHandler``).
CallbacksFactory = Callable[[Optional[ProgressCallback]], List[Any]]


class ToolAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    step_count: int
    loop_detected: bool
    requires_approval: bool
    pending_action: Optional[Dict[str, Any]]
    verify_attempts: int
    ungrounded_values: List[str]


class ToolAgentContext(TypedDict, total=False):
    """Per-invocation secrets and settings; never persisted in graph state."""

    api_key: str


@dataclass(frozen=True)
class AgentResult:
    response: str
    tools_executed: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    requires_approval: bool = False
    pending_action: Optional[Dict[str, Any]] = None
    extras: Mapping[str, Any] = field(default_factory=dict)


def handle_tool_error(error: Exception) -> str:
    if isinstance(error, ToolExecutionError):
        return f"Tool error ({error.tool_name}): {error.message}"
    return f"Tool error: {error}"


class ToolAgent:
    MAX_VERIFY_RETRIES: int = 1
    RECURSION_LIMIT: int = 40
    NODE_TIMEOUT_SECONDS: int = 90

    def __init__(
        self,
        *,
        system_prompt: str,
        tools: Sequence[BaseTool],
        model_factory: Optional[Callable[[str], BaseChatModel]] = None,
        llm: Optional[BaseChatModel] = None,
        approval_tools: Optional[Mapping[str, ApprovalRule]] = None,
        approval_policy: Optional[Callable[[str, Dict[str, Any]], Optional[str]]] = None,
        verifier: Optional[Verifier] = None,
        loop_guard: Optional[LoopGuardrail] = None,
        name: str = "agent",
        provider_name: str = "llm",
        callbacks_factory: Optional[CallbacksFactory] = None,
        checkpointer: Optional[Any] = None,
    ) -> None:
        if llm is None and model_factory is None:
            raise ValueError("Pass either llm or model_factory")
        self._system_prompt = system_prompt
        self._tools = list(tools)
        self._model_factory = model_factory
        self._llm = llm
        self._approval_tools = dict(approval_tools or {})
        self._approval_policy = approval_policy
        self._verifier = verifier
        write_tools = set(self._approval_tools)
        self._loop_guard = loop_guard or LoopGuardrail(write_tools=write_tools)
        self._name = name
        self._provider_name = provider_name
        self._callbacks_factory = callbacks_factory or (lambda on_progress: [ToolCallLoggingHandler(on_progress)])
        # Pass one saver to several agents so a session continues across them (e.g. one agent built per request).
        self._checkpointer: Any = checkpointer if checkpointer is not None else InMemorySaver()
        self._checkpointer_context: Any = None
        self._compiled_graph: Optional[CompiledStateGraph] = None
        self._llm_with_tools: Any = None

    # ---- lifecycle -------------------------------------------------------------------

    async def startup(self, database_url: Optional[str] = None) -> None:
        """Compile the graph; with a database URL, checkpoint to Postgres so approvals survive restarts."""
        if database_url:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

            self._checkpointer_context = AsyncPostgresSaver.from_conn_string(database_url)
            self._checkpointer = await self._checkpointer_context.__aenter__()
            try:
                await self._checkpointer.setup()
            except Exception:
                await self._checkpointer_context.__aexit__(*sys.exc_info())
                self._checkpointer_context = None
                raise
        self.compile()

    async def shutdown(self) -> None:
        if self._checkpointer_context is not None:
            await self._checkpointer_context.__aexit__(None, None, None)
            self._checkpointer_context = None

    @property
    def is_ready(self) -> bool:
        return self._compiled_graph is not None

    # ---- approval --------------------------------------------------------------------

    def approval_reason(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        if self._approval_policy is not None:
            reason = self._approval_policy(tool_name, args)
            if reason:
                return reason
        rule = self._approval_tools.get(tool_name)
        if not rule:
            return None
        if callable(rule):
            return rule(args)
        if isinstance(rule, str):
            return rule
        return f"The '{tool_name}' action requires human approval before it runs."

    # ---- nodes -----------------------------------------------------------------------

    async def _agent_node(self, state: ToolAgentState, runtime: Runtime[ToolAgentContext]) -> Dict[str, Any]:
        messages = list(state["messages"])
        turn = current_turn(messages)
        step_count = state.get("step_count", 0) + 1

        if step_count > self._loop_guard.MAX_TOTAL_STEPS or self._loop_guard.no_progress(turn):
            logger.warning("agent.loop.halted", step_count=step_count)
            return {"step_count": step_count, "loop_detected": True}

        llm_with_tools = self._llm_with_tools
        if self._llm is None:
            context = runtime.context or {}
            llm_with_tools = self._model_factory(context.get("api_key", "")).bind_tools(self._tools)  # type: ignore[misc]
        response = await llm_with_tools.ainvoke([SystemMessage(content=self._system_prompt), *messages])

        reasons: List[str] = []
        calls: List[Dict[str, Any]] = []
        for call in getattr(response, "tool_calls", None) or []:
            reason = self.approval_reason(call["name"], call["args"])
            logger.info(
                "agent.tool.requested",
                tool_name=call["name"],
                tool_call_id=call["id"],
                argument_names=sorted(str(key) for key in call["args"]),
                approval_required=bool(reason),
            )
            if self._loop_guard.would_repeat_too_often(call["name"], call["args"], turn):
                logger.warning("agent.tool.blocked", tool_name=call["name"], tool_call_id=call["id"], block_reason="loop_guard")
                return {"step_count": step_count, "loop_detected": True}
            if reason:
                reasons.append(reason)
                calls.append({"tool": call["name"], "args": call["args"], "id": call["id"]})

        return {
            "messages": [response],
            "step_count": step_count,
            "loop_detected": False,
            "requires_approval": bool(reasons),
            "pending_action": {"reasons": reasons, "calls": calls} if reasons else None,
        }

    def _fallback_node(self, state: ToolAgentState) -> Dict[str, Any]:
        logger.warning("agent.fallback.routed")
        verified: List[str] = []
        for msg in current_turn(list(state["messages"])):
            text = str(msg.content)
            if isinstance(msg, ToolMessage) and not text.startswith(DUPLICATE_PREFIX) and msg.status != "error" and text not in verified:
                verified.append(text if len(text) <= 800 else text[:800] + " ...")
        content = "I stopped because a repetitive execution pattern was detected. Please refine your query."
        if verified:
            content += "\n\nVerified information collected:\n" + "\n".join(verified)
        return {"messages": [AIMessage(content=content)], "loop_detected": False}

    def _approval_node(self, state: ToolAgentState) -> Command:
        pending = state.get("pending_action")
        logger.info("agent.approval.requested", pending=pending)
        decision = interrupt(pending)
        cleared = {"requires_approval": False, "pending_action": None}
        if decision.get("approved"):
            logger.info("agent.approval.granted")
            return Command(goto="tools", update=cleared)
        notes = decision.get("notes") or "no notes"
        logger.info("agent.approval.rejected", notes=notes)
        rejected = [
            ToolMessage(content=f"Action rejected by reviewer. Notes: {notes}", tool_call_id=c["id"], name=c["tool"], status="error")
            for c in (pending or {}).get("calls", [])
        ]
        closing = AIMessage(content=f"Action cancelled by the reviewer. Notes: {notes}")
        return Command(goto=END, update={**cleared, "messages": [*rejected, closing]})

    def _verify_node(self, state: ToolAgentState) -> Command:
        last = state["messages"][-1]
        scaffolding = [
            RemoveMessage(id=m.id) for m in current_turn(list(state["messages"])) if isinstance(m, HumanMessage) and m.additional_kwargs.get(FEEDBACK_FLAG)
        ]
        ungrounded: List[str] = []
        if self._verifier is not None:
            sources = [
                str(m.content)
                for m in state["messages"]
                if isinstance(m, ToolMessage) or (isinstance(m, HumanMessage) and not m.additional_kwargs.get(FEEDBACK_FLAG))
            ]
            ungrounded = self._verifier(str(last.content), sources)
        if not ungrounded:
            return Command(goto=END, update={"messages": scaffolding} if scaffolding else None)
        attempts = state.get("verify_attempts", 0)
        logger.warning("agent.verify.failed", ungrounded=ungrounded, attempt=attempts + 1)
        if attempts < self.MAX_VERIFY_RETRIES:
            feedback = HumanMessage(
                content=(
                    f"Verification failed: these values are not present in any tool result: {', '.join(ungrounded)}. "
                    "Rewrite your answer using only figures from tool results."
                ),
                additional_kwargs={FEEDBACK_FLAG: True},
            )
            return Command(goto="agent", update={"messages": [RemoveMessage(id=last.id), feedback], "verify_attempts": attempts + 1})
        return Command(goto=END, update={"messages": [RemoveMessage(id=last.id), *scaffolding], "ungrounded_values": ungrounded})

    # ---- graph -----------------------------------------------------------------------

    def compile(self) -> CompiledStateGraph:
        self._llm_with_tools = self._llm.bind_tools(self._tools) if self._llm is not None else None

        builder = StateGraph(ToolAgentState, context_schema=ToolAgentContext)
        builder.add_node("agent", self._agent_node, timeout=self.NODE_TIMEOUT_SECONDS)
        builder.add_node("fallback", self._fallback_node)
        builder.add_node("approval_gate", self._approval_node, destinations=("tools", END))
        builder.add_node("verify", self._verify_node, destinations=("agent", END))
        builder.add_node("tools", ToolNode(self._tools, handle_tool_errors=handle_tool_error))
        builder.add_edge(START, "agent")

        def route(state: ToolAgentState) -> str:
            if state.get("loop_detected"):
                return "fallback"
            if state.get("requires_approval"):
                return "approval_gate"
            if getattr(state["messages"][-1], "tool_calls", None):
                return "tools"
            return "verify"

        builder.add_conditional_edges("agent", route, {"fallback": "fallback", "approval_gate": "approval_gate", "tools": "tools", "verify": "verify"})
        builder.add_edge("fallback", END)
        builder.add_edge("tools", "agent")
        self._compiled_graph = builder.compile(checkpointer=self._checkpointer)
        return self._compiled_graph

    # ---- execution -------------------------------------------------------------------

    def _thread_config(self, session_id: str) -> Dict[str, Any]:
        return {"configurable": {"thread_id": session_id}, "recursion_limit": self.RECURSION_LIMIT}

    def _require_graph(self) -> CompiledStateGraph:
        if self._compiled_graph is None:
            raise GraphUninitializedError()
        return self._compiled_graph

    async def execute(
        self,
        query: str,
        session_id: str,
        trace_id: str,
        context: Optional[ToolAgentContext] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> AgentResult:
        graph = self._require_graph()
        cfg = self._thread_config(session_id)
        snapshot = await graph.aget_state(cfg)
        if snapshot.next:
            raise ApprovalPendingError(session_id)
        initial: Dict[str, Any] = {
            "messages": [HumanMessage(content=query)],
            "step_count": 0,
            "loop_detected": False,
            "requires_approval": False,
            "pending_action": None,
            "verify_attempts": 0,
            "ungrounded_values": [],
        }
        return await self._run(graph, initial, cfg, trace_id, context, progress_callback=progress_callback)

    async def resume_approval(
        self,
        session_id: str,
        approved: bool,
        notes: Optional[str],
        trace_id: str,
        context: Optional[ToolAgentContext] = None,
    ) -> AgentResult:
        graph = self._require_graph()
        cfg = self._thread_config(session_id)
        snapshot = await graph.aget_state(cfg)
        if not snapshot.next:
            raise NoPendingApprovalError(session_id)
        completed = {str(m.tool_call_id) for m in snapshot.values.get("messages", []) if isinstance(m, ToolMessage)}
        return await self._run(graph, Command(resume={"approved": approved, "notes": notes}), cfg, trace_id, context, completed_tool_call_ids=completed)

    async def _run(
        self,
        graph: CompiledStateGraph,
        graph_input: Any,
        cfg: Dict[str, Any],
        trace_id: str,
        context: Optional[ToolAgentContext],
        completed_tool_call_ids: Optional[set[str]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> AgentResult:
        session_id = cfg["configurable"]["thread_id"]
        run_config = {
            **cfg,
            "callbacks": [*tracing_callbacks(), *self._callbacks_factory(progress_callback)],
            "run_name": self._name,
        }
        try:
            with trace_context(session_id, trace_id):
                result = await graph.ainvoke(graph_input, config=run_config, context=dict(context or {}))
        except GraphRecursionError as exc:
            raise LoopBreakerError(reason=f"recursion limit of {self.RECURSION_LIMIT} reached") from exc
        except AgentServiceError:
            raise
        except Exception as exc:
            logger.error("agent.model.invocation_failed", error_type=type(exc).__name__)
            raise ProviderModelError(
                provider=self._provider_name,
                reason=f"upstream request failed ({type(exc).__name__})",
                details={"upstream_status": getattr(exc, "status_code", None)},
            ) from exc

        messages: List[BaseMessage] = result.get("messages", [])
        turn = current_turn(messages)
        tools_executed = [m.name or "tool" for m in turn if isinstance(m, ToolMessage) and not str(m.content).startswith(DUPLICATE_PREFIX)]
        tool_calls = self._tool_call_records(turn, completed_tool_call_ids)

        interrupts = result.get("__interrupt__")
        if interrupts:
            logger.info("agent.paused_for_approval", tools=tools_executed)
            return AgentResult(
                response="Action requires human approval before it can be applied.",
                tools_executed=tools_executed,
                tool_calls=tool_calls,
                requires_approval=True,
                pending_action=interrupts[0].value,
            )
        if result.get("ungrounded_values"):
            raise OutputHallucinationError(hallucinated_values=result["ungrounded_values"])
        if not messages:
            return AgentResult(response="No response generated.")
        return AgentResult(response=_text(messages[-1].content), tools_executed=tools_executed, tool_calls=tool_calls)

    @staticmethod
    def _tool_call_records(messages: List[BaseMessage], exclude_tool_call_ids: Optional[set[str]] = None) -> List[Dict[str, Any]]:
        records: Dict[str, Dict[str, Any]] = {}
        ordered_ids: List[str] = []
        for message in messages:
            if isinstance(message, AIMessage):
                for call in message.tool_calls:
                    call_id = str(call.get("id") or f"tool-{len(ordered_ids)}")
                    records[call_id] = {
                        "tool_call_id": call_id,
                        "name": str(call.get("name") or "unknown"),
                        "arguments": call.get("args") if isinstance(call.get("args"), dict) else {},
                        "status": "awaiting_approval",
                        "result": None,
                    }
                    ordered_ids.append(call_id)
            elif isinstance(message, ToolMessage):
                record = records.get(str(message.tool_call_id))
                if record is None:
                    continue
                content = str(message.content)
                if content.startswith(DUPLICATE_PREFIX):
                    record["status"] = "skipped"
                elif message.status == "error":
                    record["status"] = "failed"
                else:
                    record["status"] = "completed"
                record["result"] = content if len(content) <= 1200 else content[:1200] + " … (truncated)"
        return [records[i] for i in ordered_ids if i not in (exclude_tool_call_ids or set())]


def _text(content: Any) -> str:
    """Normalise model content (a string, or a list of text blocks) to plain text."""
    if isinstance(content, str):
        return content
    return "".join(str(b.get("text", "")) if isinstance(b, dict) else str(b) for b in content)
