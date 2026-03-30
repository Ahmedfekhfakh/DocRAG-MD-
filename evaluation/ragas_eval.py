"""RAGAS evaluation: faithfulness + answer relevancy."""
import asyncio
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from agents.rag_agent import run_rag


async def collect_samples(questions: list[str], model_name: str = "gemini") -> list[dict]:
    samples = []
    for q in questions:
        try:
            result = await run_rag(q, model_name=model_name)
            samples.append({
                "question": q,
                "answer": result["answer"],
                "contexts": [s["content"] for s in result["sources"]],
                "ground_truth": "",  # Not available for open-ended questions
            })
        except Exception as e:
            print(f"Error on '{q[:40]}': {e}")
    return samples


def run_ragas_eval(questions: list[str], model_name: str = "gemini") -> dict:
    samples = asyncio.run(collect_samples(questions, model_name))
    if not samples:
        return {}
    dataset = Dataset.from_list(samples)
    result = evaluate(dataset, metrics=[faithfulness, answer_relevancy])
    return result
