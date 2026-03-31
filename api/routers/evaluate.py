"""POST /evaluate/ragas — run RAGAS evaluation and log scores to Langfuse."""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.schemas import RagasEvalRequest, RagasEvalResponse

router = APIRouter(prefix="/evaluate", tags=["evaluation"])


@router.post("/ragas", response_model=RagasEvalResponse)
async def ragas_evaluate(req: RagasEvalRequest):
    try:
        from evaluation.ragas_eval import run_ragas_eval
        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(
            None, run_ragas_eval, req.questions, req.model
        )
        return RagasEvalResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
