"""LCEL generation chain: prompt | llm | parser."""
import os
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .llm_router import get_llm

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(name: str) -> PromptTemplate:
    text = (_PROMPTS_DIR / name).read_text()
    return PromptTemplate.from_template(text)


def build_chain(model_name: str, use_cot: bool = False):
    """Return an LCEL chain: prompt | llm | parser."""
    prompt_file = "cot_medical.txt" if use_cot else "clinical_qa.txt"
    prompt = _load_prompt(prompt_file)
    llm = get_llm(model_name)
    return prompt | llm | StrOutputParser()


async def generate_answer(question: str, context: str, model_name: str, use_cot: bool = False) -> str:
    chain = build_chain(model_name, use_cot)
    return await chain.ainvoke({"question": question, "context": context})
