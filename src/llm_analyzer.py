from functools import lru_cache
from langchain_openai import ChatOpenAI
from src.config import LLM_MODEL_NAME, TEMPERATURE
from src.schemas import CallAnalysisResponse
from src.prompts import SYSTEM_PROMPT
from src.rag_engine import query_knowledge_base


@lru_cache(maxsize=1)
def get_structured_llm():
    llm = ChatOpenAI(model=LLM_MODEL_NAME, temperature=TEMPERATURE, max_retries=1)
    return llm.with_structured_output(CallAnalysisResponse)


def analyze_transcript(call_id: str, transcript: str) -> dict:
    """
    Main function to analyze transcripts and return structured JSON.

    1. Queries vector DB for relevant SOP procedures[cite: 1].
    2. Passes prompt + SOP context + transcript to LLM[cite: 1].
    3. Returns validated structured JSON dictionary matching schema[cite: 1].
    """
    # 1. Retrieve relevant company procedures via RAG[cite: 1]
    sop_context = query_knowledge_base(query_text=transcript, k=2)

    # 2. Build the message context
    user_message = f"""
Relevant Operating Procedures (RAG Context):
{sop_context if sop_context else "No specific SOP retrieved."}

---
Transcript to Analyze:
Call ID: {call_id}
Transcript: "{transcript}"
"""

    response: CallAnalysisResponse = get_structured_llm().invoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ])

    # 5. Return as a plain Python dictionary[cite: 1]
    return response.model_dump()
