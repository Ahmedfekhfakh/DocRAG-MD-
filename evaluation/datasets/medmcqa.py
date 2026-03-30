"""Load MedMCQA sample from HuggingFace datasets.

cop field: 0→A, 1→B, 2→C, 3→D
"""
from datasets import load_dataset

_COP_MAP = {0: "A", 1: "B", 2: "C", 3: "D"}


def load_medmcqa_sample(n: int = 150, split: str = "validation") -> list[dict]:
    """Return n questions formatted for evaluation."""
    ds = load_dataset("openlifescienceai/medmcqa", split=split, streaming=True)
    questions = []
    for item in ds:
        q = item.get("question", "")
        opa = item.get("opa", "")
        opb = item.get("opb", "")
        opc = item.get("opc", "")
        opd = item.get("opd", "")
        cop = item.get("cop", 0)
        correct = _COP_MAP.get(cop, "A")
        formatted = (
            f"{q}\n"
            f"A) {opa}\n"
            f"B) {opb}\n"
            f"C) {opc}\n"
            f"D) {opd}\n"
            f"Answer with only the letter (A/B/C/D)."
        )
        questions.append({"question": formatted, "correct": correct, "raw": item})
        if len(questions) >= n:
            break
    return questions
