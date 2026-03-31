"""Langfuse observability — optional. No-ops if keys are not set."""
import os
import uuid


def langfuse_enabled() -> bool:
    return bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))


def create_langfuse_handler():
    """Create a NEW CallbackHandler per request with a unique trace_id."""
    if not langfuse_enabled():
        return None
    from langfuse.langchain import CallbackHandler
    trace_id = uuid.uuid4().hex  # 32 lowercase hex chars
    return CallbackHandler(trace_context={"trace_id": trace_id})
