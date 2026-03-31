"""RAGAS evaluation: faithfulness + answer relevancy.

Judge LLM : Gemini 2.5 Flash (follows structured JSON schemas reliably).
RAG model : controlled by the `model` param — "biomistral" or "gemini".
Results   : printed to console + logged as a trace+scores in Langfuse.
"""
import asyncio
import os
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.run_config import RunConfig
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from agents.rag_agent import run_rag


def _get_ragas_llm():
    """Gemini 2.5 Flash as RAGAS judge — reliably follows structured JSON schemas."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        google_api_key=api_key,
    )
    return LangchainLLMWrapper(llm)


def _get_ragas_embeddings():
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    emb = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key,
    )
    return LangchainEmbeddingsWrapper(emb)


async def collect_samples(questions: list[str], model_name: str = "gemini") -> list[dict]:
    samples = []
    for q in questions:
        try:
            result = await run_rag(q, model_name=model_name)
            samples.append({
                "question": q,
                "answer": result["answer"],
                "contexts": [s["content"] for s in result["sources"]],
                "ground_truth": "",
            })
        except Exception as e:
            print(f"Error on '{q[:40]}': {e}")
    return samples


def _safe_score(val) -> float:
    import math
    if isinstance(val, list):
        valid = [v for v in val if v is not None and not (isinstance(v, float) and math.isnan(v))]
        return round(sum(valid) / len(valid), 4) if valid else 0.0
    try:
        v = float(val)
        return 0.0 if math.isnan(v) else round(v, 4)
    except Exception:
        return 0.0


def _log_to_langfuse(scores: dict, model_name: str, n_samples: int) -> str | None:
    import requests
    import uuid
    host = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    if not public_key or not secret_key:
        print("⚠ Langfuse keys not set, skipping.")
        return None
    try:
        trace_id = str(uuid.uuid4())
        requests.post(
            f"{host}/api/public/traces",
            auth=(public_key, secret_key),
            json={"id": trace_id, "name": "ragas_eval", "metadata": {"model": model_name, "n_samples": n_samples}},
            timeout=10,
        ).raise_for_status()
        for name, value in scores.items():
            requests.post(
                f"{host}/api/public/scores",
                auth=(public_key, secret_key),
                json={"traceId": trace_id, "name": name, "value": float(value), "dataType": "NUMERIC"},
                timeout=10,
            ).raise_for_status()
        print(f"✓ RAGAS scores logged to Langfuse (trace: {trace_id})")
        return trace_id
    except Exception as e:
        print(f"⚠ Langfuse logging failed: {e}")
        return None


def run_ragas_eval(questions: list[str], model_name: str = "gemini") -> dict:
    """Run RAGAS evaluation. model_name controls which RAG model answers the questions."""
    samples = asyncio.run(collect_samples(questions, model_name))
    if not samples:
        return {}

    judge_llm = _get_ragas_llm()
    judge_emb = _get_ragas_embeddings()

    for metric in [faithfulness, answer_relevancy]:
        metric.llm = judge_llm
    answer_relevancy.embeddings = judge_emb

    dataset = Dataset.from_list(samples)
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        raise_exceptions=False,
        run_config=RunConfig(max_workers=1, timeout=120),
    )

    scores = {
        "faithfulness": _safe_score(result["faithfulness"]),
        "answer_relevancy": _safe_score(result["answer_relevancy"]),
    }

    print(f"\n=== RAGAS Results ({model_name}) ===")
    for k, v in scores.items():
        print(f"  {k}: {v:.4f}")
    print("=====================================\n")

    trace_id = _log_to_langfuse(scores, model_name, len(samples))

    return {
        "scores": scores,
        "n_samples": len(samples),
        "model": model_name,
        "langfuse_trace_id": trace_id,
    }
