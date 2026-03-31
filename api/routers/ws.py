"""WebSocket /ws/chat — orchestrator routing with Deep Search trace support."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents.orchestrator import run_orchestrator
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
            mode = payload.get("mode", "rag")
            search_mode = payload.get("search_mode", "standard")
            role = payload.get("role", "doctor")

            if not question:
                await websocket.send_json({"error": "Empty question"})
                continue

            await websocket.send_json(
                {"type": "start", "model": model_name, "mode": mode, "search_mode": search_mode}
            )

            try:
                if search_mode == "deep":
                    # Deep search: call run_rag directly for progress callbacks
                    async def progress_callback(event: dict):
                        await websocket.send_json(event)

                    result = await run_rag(
                        question,
                        model_name=model_name,
                        role=role,
                        search_mode="deep",
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
                        "mode": mode,
                        "search_mode": "deep",
                        "intent": "",
                        "is_confident": result.get("is_confident", True),
                    })
                else:
                    # Standard: route through orchestrator for intent classification
                    result = await run_orchestrator(
                        question,
                        model_name=model_name,
                        mode=mode,
                        search_mode=search_mode,
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
                        "mode": mode,
                        "search_mode": result.get("search_mode", "standard"),
                        "intent": result.get("intent", "GENERAL"),
                        "is_confident": result.get("is_confident", True),
                    })
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": str(e)})

    except WebSocketDisconnect:
        pass
