"""LLM Router — Tous les appels LLM passent par ici."""
import os
from langchain_openai import ChatOpenAI


def get_llm(model_name: str = "gemini"):
    """Factory pour obtenir le bon LLM selon le choix utilisateur."""
    if model_name == "biomistral":
        return ChatOpenAI(
            base_url=os.getenv("BIOMISTRAL_URL", "http://llama-cpp:8080/v1"),
            api_key="not-needed",
            model="biomistral",
            temperature=0.0,
            max_tokens=1024,
        )
    elif model_name in ("gemini", "gemini-pro"):
        vertex_model = "gemini-2.5-pro" if model_name == "gemini-pro" else "gemini-2.5-flash"
        project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if project:
            from langchain_google_vertexai import ChatVertexAI
            return ChatVertexAI(
                model_name=vertex_model,
                project=project,
                location=os.getenv("GCP_LOCATION", "europe-west1"),
                temperature=0.0,
            )
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Neither GOOGLE_CLOUD_PROJECT nor GOOGLE_API_KEY is set.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=vertex_model,
            temperature=0.0,
            google_api_key=api_key,
        )
    elif model_name == "gpt4o":
        return ChatOpenAI(
            model="gpt-4o",
            temperature=0.0,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
    raise ValueError(f"Unknown model: {model_name}")
