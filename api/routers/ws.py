"""WebSocket /ws/chat — final answer plus Deep Search trace events."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents.rag_agent import run_rag

router = APIRouter()


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            question = payload.get("question", "")
            model_name = payload.get("model", "gemini")
            search_mode = payload.get("search_mode") or payload.get("mode") or "standard"
            role = payload.get("role", "doctor")

            if not question:
                await websocket.send_json({"error": "Empty question"})
                continue

            await websocket.send_json(
                {"type": "start", "model": model_name, "search_mode": search_mode}
            )

            try:
                async def progress_callback(event: dict):
                    await websocket.send_json(event)

                result = await run_rag(
                    question,
                    model_name=model_name,
                    role=role,
                    search_mode=search_mode,
                    progress_callback=progress_callback,
                )
                sources = [
                    {
                        "doc_id": s.get("doc_id", ""),
                        "title": s.get("title", ""),
                        "content": s.get("content", "")[:300],
                        "source": s.get("source", "statpearls"),
                    }
                    for s in result.get("sources", [])
                ]
                await websocket.send_json({
                    "type": "answer",
                    "answer": result["answer"],
                    "sources": sources,
                    "model": model_name,
                    "search_mode": result.get("search_mode", search_mode),
                    "is_confident": result.get("is_confident", True),
                })
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": str(e)})

    except WebSocketDisconnect:
        pass
