"""Self-RAG — Vérifie la fidélité et la complétude après génération.

Si la réponse n'est pas fidèle aux sources ou ne répond pas à la
question, reformule et relance le pipeline (max 2 tentatives).
"""
import json
from langchain_core.prompts import ChatPromptTemplate

REFLECT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Tu es un vérificateur de réponses médicales.
Analyse la réponse générée et détermine :
1. FIDÉLITÉ : la réponse est-elle fidèle aux sources fournies ?
   (pas d'hallucination, pas d'information inventée)
2. COMPLÉTUDE : la réponse répond-elle à la question posée ?

Réponds UNIQUEMENT en JSON :
{{"faithful": true/false, "complete": true/false,
  "reason": "explication courte si false"}}"""),
    ("human", """Question : {question}
Sources : {sources}
Réponse générée : {answer}"""),
])


async def check_response(llm, question: str, sources: str, answer: str, config=None) -> dict:
    """Vérifie fidélité et complétude d'une réponse."""
    chain = REFLECT_PROMPT | llm
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "4_self_reflect"
    result = await chain.ainvoke({
        "question": question,
        "sources": sources,
        "answer": answer,
    }, config=invoke_config)
    try:
        return json.loads(result.content)
    except (json.JSONDecodeError, AttributeError):
        return {"faithful": True, "complete": True}
