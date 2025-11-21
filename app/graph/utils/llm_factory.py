# llm_factory.py

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.config import (
    LLM_PROVIDER,
    LOCAL_LLM_MODEL,
    OPENAI_MODEL,
    OPENAI_API_KEY,
    ANTHROPIC_MODEL,
    ANTHROPIC_API_KEY,
    GEMINI_MODEL,
    GEMINI_API_KEY,
    LOCAL_EMBED_MODEL,
)


# =============================================================================
# Core LLM Factory
# =============================================================================

def get_llm(temperature=0):
    """Return an LLM according to environment variable LLM_PROVIDER."""
    
    # --------------------- Local (Ollama) ---------------------
    if LLM_PROVIDER == "local":
        return ChatOllama(
            model=LOCAL_LLM_MODEL,
            temperature=temperature,
        )

    # --------------------- OpenAI -----------------------------
    if LLM_PROVIDER == "openai":
        return ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=temperature,
        )

    # --------------------- Anthropic --------------------------
    if LLM_PROVIDER == "anthropic":
        return ChatAnthropic(
            model=ANTHROPIC_MODEL,
            api_key=ANTHROPIC_API_KEY,
            temperature=temperature,
        )

    # --------------------- Google Gemini ----------------------
    if LLM_PROVIDER == "gemini":
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=temperature,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


# =============================================================================
# Structured Output LLM Factory
# =============================================================================

def get_structured_llm(schema, temperature=0):
    """
    Wrap LLM with structured output using schema.
    e.g., JSONPatchOperation, ToxicityUpdateSchema
    """
    llm = get_llm(temperature=temperature)
    return llm.with_structured_output(schema, method="function_calling")


# =============================================================================
# Embedding model factory
# =============================================================================

def get_embedder():
    """
    Currently we only use local embedding models (Ollama).
    Extend here if cloud embeddings logic is needed.
    """
    return OllamaEmbeddings(model=LOCAL_EMBED_MODEL)