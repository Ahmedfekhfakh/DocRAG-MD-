"""Agent orchestrateur — Classifie l'intention et route vers l'agent spécialisé.

Routes :
- Symptôme / diagnostic → Agent diagnostic
- Médicament / interaction → Agent pharmacologie
- Tout le reste → Agent général
- Benchmark → Agent évaluateur
"""
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from generation.llm_router import get_llm
from typing import TypedDict, Annotated
import operator

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """Classifie la question médicale suivante dans UNE des catégories :
- DIAGNOSTIC : question sur des symptômes, diagnostic différentiel, arbres décisionnels cliniques
- PHARMACOLOGIE : question sur des médicaments, interactions, contre-indications, posologie
- GENERAL : toute autre question médicale
- BENCHMARK : demande d'évaluation ou de benchmark

Réponds UNIQUEMENT par le mot : DIAGNOSTIC, PHARMACOLOGIE, GENERAL, ou BENCHMARK."""),
    ("human", "{question}"),
])


class OrchestratorState(TypedDict):
    question: str
    model_name: str
    mode: str
    intent: str
    answer: str
    sources: list[dict]
    is_confident: bool
    messages: Annotated[list, operator.add]


async def classify_intent(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Classifie l'intention de la question."""
    llm = get_llm(state.get("model_name", "gemini"))
    chain = CLASSIFY_PROMPT | llm
    invoke_config = dict(config) if config else {}
    invoke_config["run_name"] = "1_classify_intent"
    result = await chain.ainvoke({"question": state["question"]}, config=invoke_config)
    intent = result.content.strip().upper()
    valid = {"DIAGNOSTIC", "PHARMACOLOGIE", "GENERAL", "BENCHMARK"}
    if intent not in valid:
        intent = "GENERAL"
    return {"intent": intent}


def route_to_agent(state: OrchestratorState) -> str:
    """Route vers le bon agent selon l'intention."""
    intent = state.get("intent", "GENERAL")
    return {
        "DIAGNOSTIC": "diagnosis_agent",
        "PHARMACOLOGIE": "pharmacology_agent",
        "GENERAL": "general_agent",
        "BENCHMARK": "eval_agent",
    }.get(intent, "general_agent")


async def run_diagnosis(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Agent diagnostic — spécialisé symptômes, diagnostic différentiel."""
    from agents.diagnosis_agent import run_diagnosis_pipeline
    result = await run_diagnosis_pipeline(
        state["question"], state.get("model_name", "gemini"), state.get("mode", "rag"),
        config=config,
    )
    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "is_confident": result.get("is_confident", True),
    }


async def run_pharmacology(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Agent pharmacologie — spécialisé médicaments, interactions."""
    from agents.pharmacology_agent import run_pharmacology_pipeline
    result = await run_pharmacology_pipeline(
        state["question"], state.get("model_name", "gemini"), state.get("mode", "rag"),
        config=config,
    )
    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "is_confident": result.get("is_confident", True),
    }


async def run_general(state: OrchestratorState, config: RunnableConfig) -> dict:
    """Agent général — RAG standard avec Self-RAG."""
    from agents.general_agent import run_general_pipeline
    result = await run_general_pipeline(
        state["question"], state.get("model_name", "gemini"), state.get("mode", "rag"),
        config=config,
    )
    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "is_confident": result.get("is_confident", True),
    }


async def run_eval(state: OrchestratorState) -> dict:
    """Agent évaluateur — benchmark MedMCQA."""
    from agents.eval_agent import run_evaluation
    report = await run_evaluation(n_questions=150, models=[state.get("model_name", "gemini")])
    return {"answer": report, "sources": [], "is_confident": True}


def build_orchestrator_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("classify", classify_intent)
    graph.add_node("diagnosis_agent", run_diagnosis)
    graph.add_node("pharmacology_agent", run_pharmacology)
    graph.add_node("general_agent", run_general)
    graph.add_node("eval_agent", run_eval)

    graph.set_entry_point("classify")
    graph.add_conditional_edges("classify", route_to_agent, {
        "diagnosis_agent": "diagnosis_agent",
        "pharmacology_agent": "pharmacology_agent",
        "general_agent": "general_agent",
        "eval_agent": "eval_agent",
    })

    graph.add_edge("diagnosis_agent", END)
    graph.add_edge("pharmacology_agent", END)
    graph.add_edge("general_agent", END)
    graph.add_edge("eval_agent", END)

    return graph.compile()


_orchestrator_graph = None


def get_orchestrator_graph():
    global _orchestrator_graph
    if _orchestrator_graph is None:
        _orchestrator_graph = build_orchestrator_graph()
    return _orchestrator_graph


async def run_orchestrator(question: str, model_name: str = "gemini", mode: str = "rag") -> dict:
    """Point d'entrée principal — classifie et route vers l'agent spécialisé."""
    from langchain_core.messages import HumanMessage
    from generation.observability import create_langfuse_handler
    import uuid

    graph = get_orchestrator_graph()

    config = {"run_id": uuid.uuid4()}
    handler = create_langfuse_handler()
    if handler:
        config["callbacks"] = [handler]

    result = await graph.ainvoke({
        "question": question,
        "model_name": model_name,
        "mode": mode,
        "intent": "",
        "answer": "",
        "sources": [],
        "is_confident": True,
        "messages": [HumanMessage(content=question)],
    }, config=config)

    if handler:
        try:
            handler.client.flush()
        except Exception:
            pass

    return {
        "answer": result["answer"],
        "sources": result.get("sources", []),
        "is_confident": result.get("is_confident", True),
        "intent": result.get("intent", "GENERAL"),
    }
