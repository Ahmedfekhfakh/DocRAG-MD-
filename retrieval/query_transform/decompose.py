"""Question decomposition for deep search."""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from generation.llm_router import get_llm

_DECOMPOSE_PROMPT = PromptTemplate.from_template(
    "Break the following medical question into up to 3 focused sub-questions that would help "
    "retrieve better evidence.\n"
    "Return one sub-question per line with no numbering.\n\n"
    "Question: {question}"
)


async def decompose_question(question: str, model_name: str = "gemini", config=None) -> list[str]:
    llm = get_llm(model_name)
    chain = _DECOMPOSE_PROMPT | llm | StrOutputParser()
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "deep_search_decomposition"
    result = await chain.ainvoke({"question": question}, config=invoke_config)
    parts = [
        line.strip("-* \t")
        for line in result.splitlines()
        if line.strip("-* \t")
    ]
    return parts[:3]
