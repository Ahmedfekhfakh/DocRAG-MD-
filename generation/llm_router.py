"""LLM Router — ALL LLM access goes through here."""
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI


def get_llm(model_name: str = "gemini"):
    """Return a LangChain chat model for the given model name."""
    if model_name == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in environment.")
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            google_api_key=api_key,
        )
    if model_name == "biomistral":
        base_url = os.getenv("BIOMISTRAL_URL", "http://llama:8080/v1")
        return ChatOpenAI(
            base_url=base_url,
            api_key="not-needed",
            model="local-model",
            temperature=0.0,
            max_tokens=1024,
        )
    raise ValueError(f"Unknown model: {model_name}. Supported: 'gemini', 'biomistral'.")
