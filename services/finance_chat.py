import json
from typing import Dict, Any, Optional
from decimal import Decimal
from model_config.llm import get_slm
from prompt.finance_prompt_template import get_finance_analysis_prompt
from database.finance_memory import get_finance_memory_manager
import logging

logger = logging.getLogger(__name__)


def convert_decimals_to_float(obj: Any) -> Any:
    """
    Recursively convert Decimal objects to float for MongoDB compatibility.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals_to_float(item) for item in obj)
    else:
        return obj


class FinanceChatService:
    """
    Service for handling financial data analysis using SLM and storing results in memory.
    """
    
    def __init__(self):
        """Initialize the finance chat service."""
        self.slm_client = None
        self.memory_manager = get_finance_memory_manager()
    
    def _get_slm_client(self):
        """Get or initialize the SLM client."""
        if not self.slm_client:
            logger.info("Initializing SLM client")
            self.slm_client = get_slm()
        return self.slm_client
    
    def _parse_slm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the SLM JSON response and validate structure.
        """
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()

            parsed_response = json.loads(clean_text)

            required_keys = [
                "account_overview",
                "spending_analysis",
                "income_analysis",
                "debt_analysis",
                "risk_flags",
                "recommendations",
                "summary",
            ]
            missing = [k for k in required_keys if k not in parsed_response]
            if missing:
                raise ValueError(f"Missing required keys: {', '.join(missing)}")

            return parsed_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response from SLM: {e}")
        except Exception as e:
            logger.error(f"Error parsing SLM response: {e}")
            raise ValueError(f"Failed to parse SLM response: {e}")
    
    def analyze_user_finances(self, user_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Analyze user financial data using SLM and store results in memory.
        """
        try:
            logger.info(f"Starting analysis for user_id='{user_id}'")
            user_data = convert_decimals_to_float(user_data)
            client = self._get_slm_client()
            prompt = get_finance_analysis_prompt(user_data)
            logger.info(f"Calling SLM for analysis user_id='{user_id}', prompt_len={len(prompt)}")
            completion = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial data analyst. Always respond with valid JSON only, no additional text or explanations."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.4,
            )
            logger.info(f"SLM response received for user_id='{user_id}'")
            response_text = completion.choices[0].message.content
            logger.info(f"Parsing SLM response for user_id='{user_id}', response_len={len(response_text)}")
            parsed_response = self._parse_slm_response(response_text)
            logger.info(f"Parsed SLM response successfully for user_id='{user_id}'")
            validated_profile_data = parsed_response
            profile_summary = parsed_response.get("summary", "")
            additional_insights = {}

            validated_profile_data = convert_decimals_to_float(validated_profile_data)
            additional_insights = convert_decimals_to_float(additional_insights)
            logger.info(f"Storing analysis in finance_memory for user_id='{user_id}'")
            doc_id = self.memory_manager.store_finance_profile(
                user_id=user_id,
                profile_data=validated_profile_data,
                additional_insights=additional_insights,
                profile_summary=profile_summary
            )
            logger.info(f"Stored finance profile for user_id='{user_id}', document_id='{doc_id}'")
            return {
                "user_id": user_id,
                "document_id": doc_id,
                "finance_profile": validated_profile_data,
                "additional_insights": additional_insights,
                "profile_summary": profile_summary,
                "slm_response": validated_profile_data,
                "analysis_status": "success",
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user finances for user_id='{user_id}': {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "analysis_status": "failed"
            }
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored financial profile for a user."""
        return self.memory_manager.get_finance_profile(user_id)
    
    def update_user_insights(self, user_id: str, new_insights: Dict[str, Any]) -> bool:
        """Update additional insights for a user."""
        return self.memory_manager.update_profile_insights(user_id, new_insights)


# Global service instance
finance_chat_service = FinanceChatService()


def get_finance_chat_service() -> FinanceChatService:
    """
    Get the global finance chat service instance.
    
    Returns:
        FinanceChatService instance
    """
    return finance_chat_service


def generate_finance_response(user_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Main function to generate financial analysis response.
    Combines static finance profile template with user data via SLM analysis.
    
    Args:
        user_data: User's financial data from dt.json
        user_id: Unique identifier for the user
        
    Returns:
        Complete analysis with dynamic memory schema filled by SLM
    """
    service = get_finance_chat_service()
    return service.analyze_user_finances(user_data, user_id)