"""WebSocket /ws/chat — streaming responses via orchestrator."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents.orchestrator import run_orchestrator

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
            mode = payload.get("mode", "rag")
            role = payload.get("role", "doctor")

            if not question:
                await websocket.send_json({"error": "Empty question"})
                continue

            await websocket.send_json({"type": "start", "model": model_name})

            try:
                result = await run_orchestrator(
                    question, model_name=model_name, mode=mode
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
                    "intent": result.get("intent", "GENERAL"),
                })
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": str(e)})

    except WebSocketDisconnect:
        pass
