"""Multi-query expansion — 3 LLM-generated rephrasings."""
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from generation.llm_router import get_llm

_MQ_PROMPT = PromptTemplate.from_template(
    "Generate 3 different phrasings of the following medical question. "
    "Output ONLY the 3 questions, one per line, no numbering:\n\n{question}"
)


async def expand_query(question: str, model_name: str = "gemini") -> list[str]:
    llm = get_llm(model_name)
    chain = _MQ_PROMPT | llm | StrOutputParser()
    result = await chain.ainvoke({"question": question})
    variants = [q.strip() for q in result.strip().split("\n") if q.strip()]
    # Always include the original
    all_queries = [question] + variants[:3]
    return all_queries
