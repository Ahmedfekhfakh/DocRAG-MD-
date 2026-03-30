"""Agent 2 — Evaluator Agent (LangGraph).

Runs MedMCQA benchmark, compares models, reports accuracy.
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from evaluation.datasets.medmcqa import load_medmcqa_sample
from .rag_agent import run_rag
import operator
import logging

log = logging.getLogger(__name__)


class EvalState(TypedDict):
    n_questions: int
    models: list[str]
    questions: list[dict]
    results: Annotated[list, operator.add]
    report: str


async def load_dataset_node(state: EvalState) -> dict:
    questions = load_medmcqa_sample(state["n_questions"])
    return {"questions": questions}


async def run_eval_node(state: EvalState) -> dict:
    """Run all models on all questions and collect results."""
    results = []
    models = state.get("models", ["gemini"])
    for model in models:
        correct = 0
        for item in state["questions"]:
            try:
                resp = await run_rag(item["question"], model_name=model)
                answer = resp["answer"].strip().upper()
                # Extract first letter A/B/C/D from answer
                predicted = next((c for c in answer if c in "ABCD"), "")
                is_correct = predicted == item["correct"]
                correct += int(is_correct)
            except Exception as e:
                log.warning("Error on %s / %s: %s", model, item["question"][:40], e)
        accuracy = correct / len(state["questions"]) if state["questions"] else 0.0
        results.append({"model": model, "correct": correct, "total": len(state["questions"]), "accuracy": accuracy})
    return {"results": results}


def report_node(state: EvalState) -> dict:
    lines = ["# MedMCQA Evaluation Results\n", f"Questions: {state['n_questions']}\n", "| Model | Correct | Total | Accuracy |", "|-------|---------|-------|----------|"]
    for r in state["results"]:
        lines.append(f"| {r['model']} | {r['correct']} | {r['total']} | {r['accuracy']:.1%} |")
    report = "\n".join(lines)
    log.info("\n%s", report)
    return {"report": report}


def build_eval_graph() -> StateGraph:
    graph = StateGraph(EvalState)
    graph.add_node("load_dataset", load_dataset_node)
    graph.add_node("run_eval", run_eval_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("load_dataset")
    graph.add_edge("load_dataset", "run_eval")
    graph.add_edge("run_eval", "report")
    graph.add_edge("report", END)

    return graph.compile()


async def run_evaluation(n_questions: int = 150, models: list[str] | None = None) -> str:
    if models is None:
        models = ["gemini"]
    graph = build_eval_graph()
    result = await graph.ainvoke({
        "n_questions": n_questions,
        "models": models,
        "questions": [],
        "results": [],
        "report": "",
    })
    return result["report"]
