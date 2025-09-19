"""
Main application module for finance agent with memory building from finance_profiles collection.
"""

import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from services.finance_chat import generate_finance_response
from database.finance_memory import get_finance_memory_manager
from model_config.llm import get_llm
from prompt.finance_prompt_template import get_suggestions_prompt
import logging

# Initialize FastAPI app
app = FastAPI(
    title="Finance Agent Memory API",
    description="AI-powered memory building system for financial data",
    version="1.0.0"
)

# Set up logger
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class MemoryRequest(BaseModel):
    user_id: str

class MemoryResponse(BaseModel):
    user_id: str
    memory_status: str
    document_id: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None

class SuggestionResponse(BaseModel):
    user_id: str
    short_msg: str
    suggestion: str

def _fetch_user_profile(memory_manager, user_id: str) -> dict:
    """Fetch user profile document from finance_profiles or raise 404."""
    finance_profiles_collection = memory_manager.db["finance_profiles"]
    user_profile_data = finance_profiles_collection.find_one({"user_id": user_id})
    if not user_profile_data:
        raise HTTPException(
            status_code=404,
            detail=f"No financial profile found for user_id: {user_id} in finance_profiles collection"
        )
    return user_profile_data

def _extract_financial_data(user_profile_data: dict) -> dict:
    """Return profile data excluding MongoDB/system metadata fields."""
    excluded_keys = {"_id", "user_id", "created_at", "updated_at"}
    return {k: v for k, v in user_profile_data.items() if k not in excluded_keys}

def _build_memory_response(memory_result: dict, user_id: str) -> "MemoryResponse":
    """Construct a MemoryResponse from the analysis result."""
    if memory_result.get("analysis_status") == "success":
        return MemoryResponse(
            user_id=user_id,
            memory_status="success",
            document_id=memory_result.get("document_id"),
            message=f"Memory successfully built and stored for user {user_id}"
        )
    return MemoryResponse(
        user_id=user_id,
        memory_status="failed",
        error=memory_result.get("error", "Unknown error during memory building"),
        message="Failed to build memory for user"
    )

def _get_user_finance_memory(memory_manager, user_id: str) -> dict:
    """Fetch stored finance memory document for a user or raise 404."""
    collection = memory_manager.db["finance_memory"]
    doc = collection.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"No finance memory found for user_id: {user_id}")
    return doc

def _remove_nulls(obj):
    """Recursively remove None values from dicts/lists while preserving falsy but meaningful values (0, False)."""
    if isinstance(obj, dict):
        cleaned = {k: _remove_nulls(v) for k, v in obj.items() if v is not None}
        return {k: v for k, v in cleaned.items() if not (isinstance(v, (dict, list)) and len(v) == 0)}
    if isinstance(obj, list):
        return [
            _remove_nulls(v)
            for v in obj
            if v is not None and not (isinstance(v, (dict, list)) and len(_remove_nulls(v)) == 0)
        ]
    return obj

def _build_suggestions_input(memory_doc: dict) -> dict:
    """Compose a compact, non-null finance memory payload for prompting."""
    payload = {
        "finance_profile": memory_doc.get("finance_profile", {}),
        "additional_insights": memory_doc.get("additional_insights", {}),
        "profile_summary": memory_doc.get("profile_summary", ""),
    }
    return _remove_nulls(payload)

def _parse_llm_json(text: str) -> dict:
    """Parse JSON from an LLM response, handling optional markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    return json.loads(cleaned)


@app.post("/memory", response_model=MemoryResponse)
async def build_user_memory(request: MemoryRequest):
    """
    Build structured memory for a user by reading their data from finance_profiles collection
    and storing the analyzed memory in finance_memory collection.
    
    This endpoint:
    1. Reads user financial data from finance_profiles collection by user_id
    2. Uses SLM to analyze and build structured memory
    3. Stores the memory in finance_memory collection
    4. Returns memory building status
    """
    try:
        memory_manager = get_finance_memory_manager()
        user_profile_data = _fetch_user_profile(memory_manager, request.user_id)
        user_financial_data = _extract_financial_data(user_profile_data)

        # Generate structured memory using SLM analysis
        memory_result = generate_finance_response(user_financial_data, request.user_id)

        return _build_memory_response(memory_result, request.user_id)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error occurred while building memory")
        return MemoryResponse(
            user_id=request.user_id,
            memory_status="error",
            error=str(e),
            message="Error occurred while building memory"
        )

@app.post("/suggestions", response_model=SuggestionResponse)
async def generate_suggestions(request: MemoryRequest):
    """
    Generate personalized suggestions for a user based on stored finance memory.
    - Loads user's stored memory (built via /memory)
    - Filters out null fields from the schema
    - Uses get_llm() with SUGGESTIONS_PROMPT to generate JSON {short_msg, suggestion}
    """
    try:
        memory_manager = get_finance_memory_manager()
        memory_doc = _get_user_finance_memory(memory_manager, request.user_id)
        compact_memory = _build_suggestions_input(memory_doc)

        prompt = get_suggestions_prompt(compact_memory)
        llm = get_llm()
        # For LangChain ChatGoogleGenerativeAI, invoke with a plain string prompt
        llm_response = llm.invoke(prompt)
        content = getattr(llm_response, "content", None) or str(llm_response)

        try:
            parsed = _parse_llm_json(content)
        except Exception as e:
            logger.warning(f"Failed to parse suggestions JSON, returning raw text. Error: {e}")
            # Fallback: wrap raw text as suggestion
            parsed = {"short_msg": "Personalized advice ready", "suggestion": content}

        short_msg = parsed.get("short_msg", "")
        suggestion = parsed.get("suggestion", "")
        if not suggestion:
            raise HTTPException(status_code=500, detail="LLM did not return suggestion text")

        return SuggestionResponse(user_id=request.user_id, short_msg=short_msg, suggestion=suggestion)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error generating suggestions")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )