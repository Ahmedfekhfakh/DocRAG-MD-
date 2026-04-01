"""Multi-query expansion — 3 LLM-generated rephrasings."""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from generation.llm_router import get_llm

_MQ_PROMPT = PromptTemplate.from_template(
    "Generate 3 different phrasings of the following medical question. "
    "Output ONLY the 3 questions, one per line, no numbering:\n\n{question}"
)


async def expand_query(question: str, model_name: str = "gemini", config=None) -> list[str]:
    llm = get_llm(model_name)
    chain = _MQ_PROMPT | llm | StrOutputParser()
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "deep_search_multi_query"
    result = await chain.ainvoke({"question": question}, config=invoke_config)
    variants = [q.strip() for q in result.strip().split("\n") if q.strip()]
    return [question] + variants[:3]
