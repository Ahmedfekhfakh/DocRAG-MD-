"""LCEL generation chain: prompt | llm | parser."""
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .llm_router import get_llm

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> PromptTemplate:
    text = (_PROMPTS_DIR / name).read_text()
    return PromptTemplate.from_template(text)


def build_chain(model_name: str, use_cot: bool = False, mode: str = "rag"):
    """Return an LCEL chain: prompt | llm | parser."""
    if mode in ("graph", "hybrid"):
        prompt = _load_prompt("graph_qa.txt")
    elif use_cot:
        prompt = _load_prompt("cot_medical.txt")
    else:
        prompt = _load_prompt("clinical_qa.txt")
    llm = get_llm(model_name)
    return prompt | llm | StrOutputParser()


async def generate_answer(question: str, context: str, model_name: str, use_cot: bool = False, mode: str = "rag", config=None) -> str:
    chain = build_chain(model_name, use_cot, mode=mode)
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "3_generate_answer"
    return await chain.ainvoke({"question": question, "context": context}, config=invoke_config)
