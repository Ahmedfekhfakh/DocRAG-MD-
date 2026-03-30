"""POST /ingest — trigger ingestion pipeline."""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from api.schemas import IngestRequest, IngestResponse
from ingestion.pipeline import run as run_pipeline

router = APIRouter()
_ingest_running = False


@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest, background_tasks: BackgroundTasks):
    global _ingest_running
    if _ingest_running:
        raise HTTPException(status_code=409, detail="Ingestion already in progress")
    _ingest_running = True

    def _run():
        global _ingest_running
        try:
            run_pipeline(limit=req.limit)
        finally:
            _ingest_running = False

    background_tasks.add_task(_run)
    return IngestResponse(status="started", chunks_ingested=0)
