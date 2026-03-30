"""Langfuse observability — optional. No-ops if keys are not set."""
import os

_handler = None


def get_langfuse_handler():
    """Return a Langfuse CallbackHandler if keys are configured, else None.

    Langfuse v3 reads LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
    from environment variables automatically.
    """
    global _handler
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return None
    if _handler is None:
        from langfuse.langchain import CallbackHandler
        _handler = CallbackHandler()
    return _handler
