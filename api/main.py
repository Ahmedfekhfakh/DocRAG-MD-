"""FastAPI application with lifespan, CORS for React frontend."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from api.routers import health, query, ingest, ws, evaluate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up Qdrant client on startup
    try:
        from retrieval.qdrant_client import get_qdrant_client
        get_qdrant_client().get_collections()
        print("✓ Qdrant connected")
    except Exception as e:
        print(f"⚠ Qdrant not available: {e}")
    yield


app = FastAPI(
    title="Medical RAG API",
    description="RAG platform for medical knowledge (StatPearls)",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(query.router)
app.include_router(ingest.router)
app.include_router(ws.router)
app.include_router(evaluate.router)
