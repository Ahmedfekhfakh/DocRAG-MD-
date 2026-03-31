"""LLM Router — active runtime path is Gemini only."""
import os


def get_llm(model_name: str = "gemini"):
    """Return the active Gemini LLM backend."""
    if model_name != "gemini":
        raise ValueError(f"Unsupported model for this runtime: {model_name}")

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if project:
        from langchain_google_vertexai import ChatVertexAI

        return ChatVertexAI(
            model_name="gemini-2.5-flash",
            project=project,
            location=os.getenv("GCP_LOCATION", "europe-west1"),
            temperature=0.0,
        )

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Neither GOOGLE_CLOUD_PROJECT nor GOOGLE_API_KEY is set.")

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.0,
        google_api_key=api_key,
    )
