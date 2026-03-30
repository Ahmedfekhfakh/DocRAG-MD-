"""POST /query — calls RAG agent."""
from fastapi import APIRouter, HTTPException
from api.schemas import QueryRequest, QueryResponse, SourceDoc
from agents.rag_agent import run_rag

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    try:
        result = await run_rag(req.question, model_name=req.model)
        sources = [
            SourceDoc(
                doc_id=s.get("doc_id", ""),
                title=s.get("title", ""),
                content=s.get("content", "")[:500],
                source=s.get("source", "statpearls"),
                score=float(s.get("rerank_score", s.get("score", 0.0))),
            )
            for s in result.get("sources", [])
        ]
        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            model=req.model,
            is_confident=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
