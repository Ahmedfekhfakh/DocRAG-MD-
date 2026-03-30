"""WebSocket /ws/chat — streaming responses."""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents.rag_agent import get_rag_graph
from langchain_core.messages import HumanMessage

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

            if not question:
                await websocket.send_json({"error": "Empty question"})
                continue

            await websocket.send_json({"type": "start", "model": model_name})

            try:
                graph = get_rag_graph()
                result = await graph.ainvoke({
                    "question": question,
                    "model_name": model_name,
                    "queries": [],
                    "raw_docs": [],
                    "reranked_docs": [],
                    "is_confident": True,
                    "context": "",
                    "answer": "",
                    "sources": [],
                    "messages": [HumanMessage(content=question)],
                })
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
                })
            except Exception as e:
                await websocket.send_json({"type": "error", "detail": str(e)})

    except WebSocketDisconnect:
        pass
