"""LLM Router — ALL LLM access goes through here."""
import os
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(model_name: str = "gemini"):
    """Return a LangChain chat model. Currently only Gemini is supported."""
    if model_name == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in environment.")
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            google_api_key=api_key,
        )
    raise ValueError(f"Unknown model: {model_name}. Only 'gemini' is supported.")
