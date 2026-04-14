import json

def sse_event(event_name: str, data: dict) -> str:
    """
    Formats a dict as an SSE event.
    """
    return f"event: {event_name}\ndata: {json.dumps(data, default=str)}\n\n"

