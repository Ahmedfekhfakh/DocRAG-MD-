"""HyDE — Hypothetical Document Embedding."""
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from generation.llm_router import get_llm

_HYDE_PROMPT = PromptTemplate.from_template(
    "Write a short medical passage (2-3 sentences) that would answer this question:\n\n{question}\n\nPassage:"
)


async def generate_hypothetical_doc(question: str, model_name: str = "gemini", config=None) -> str:
    llm = get_llm(model_name)
    chain = _HYDE_PROMPT | llm | StrOutputParser()
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "2_hyde_query_transform"
    return await chain.ainvoke({"question": question}, config=invoke_config)
