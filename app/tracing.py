"""Runtime Tracing for LangGraph execution."""

import os
import datetime
import uuid
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage


class RuntimeTracer(BaseCallbackHandler):
    """Custom callback handler to trace execution to a local file."""

    def __init__(self, run_id: Optional[str] = None):
        super().__init__()
        # Ensure runtime/traces directory exists
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.trace_dir = os.path.join(base_dir, "runtime", "traces")
        os.makedirs(self.trace_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = run_id or str(uuid.uuid4())[:8]
        self.filename = os.path.join(self.trace_dir, f"trace_{timestamp}_{self.run_id}.log")
        
        self.log(f"--- TRACE STARTED AT {datetime.datetime.now().isoformat()} ---")
        self.log(f"Run ID: {self.run_id}")

    def log(self, message: str):
        """Append a formatted message to the trace file."""
        with open(self.filename, "a", encoding="utf-8") as f:
            f.write(message + "\n")

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        formatted = []
        for msg in messages:
            role = msg.type.upper()
            content = msg.content
            if isinstance(content, str):
                formatted.append(f"[{role}]: {content.strip()}")
            else:
                formatted.append(f"[{role}]: {json.dumps(content)}")
        return "\n".join(formatted)

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> Any:
        self.log("\n[EVENT: LLM START]")
        for prompt in prompts:
            self.log(prompt)

    def on_chat_model_start(
        self, serialized: Dict[str, Any], messages: List[List[BaseMessage]], **kwargs: Any
    ) -> Any:
        self.log("\n[EVENT: CHAT MODEL START]")
        for message_list in messages:
            self.log(self._format_messages(message_list))

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        self.log("\n[EVENT: LLM END]")
        for generation in response.generations:
            for gen in generation:
                self.log(f"Output: {gen.text}")
                # Log tool calls if present
                if hasattr(gen, "message") and hasattr(gen.message, "tool_calls"):
                    if gen.message.tool_calls:
                        self.log(f"Tool Calls: {json.dumps(gen.message.tool_calls, indent=2)}")

    def on_llm_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> Any:
        self.log(f"\n[EVENT: LLM ERROR]\nError: {str(error)}")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> Any:
        tool_name = serialized.get("name", "UnknownTool")
        self.log(f"\n[EVENT: TOOL START] Tool: {tool_name}")
        self.log(f"Input: {input_str}")

    def on_tool_end(self, output: Any, **kwargs: Any) -> Any:
        self.log("\n[EVENT: TOOL END]")
        self.log(f"Output: {str(output)}")

    def on_tool_error(
        self, error: BaseException, *, run_id: UUID, parent_run_id: Optional[UUID] = None, **kwargs: Any
    ) -> Any:
        self.log(f"\n[EVENT: TOOL ERROR]\nError: {str(error)}")

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> Any:
        # LangGraph nodes often trigger chain events
        name = serialized.get("name", "")
        # Filter out noisy internal Langchain chains if necessary, 
        # but capturing everything is good for tracing.
        self.log(f"\n[EVENT: CHAIN/NODE START] Name: {name}")
        # Log keys of inputs to avoid huge state dumps
        if isinstance(inputs, dict):
            self.log(f"Input Keys: {list(inputs.keys())}")
        else:
            self.log(f"Inputs: {str(inputs)[:200]}...")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> Any:
        self.log("\n[EVENT: CHAIN/NODE END]")
