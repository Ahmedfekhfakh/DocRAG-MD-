"""HyDE — Hypothetical Document Embedding."""
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from generation.llm_router import get_llm

_HYDE_PROMPT = PromptTemplate.from_template(
    "Write a short medical passage (2-3 sentences) that would answer this question:\n\n{question}\n\nPassage:"
)


async def generate_hypothetical_doc(question: str, model_name: str = "gemini") -> str:
    llm = get_llm(model_name)
    chain = _HYDE_PROMPT | llm | StrOutputParser()
    return await chain.ainvoke({"question": question})
