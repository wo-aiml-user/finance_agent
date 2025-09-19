import json
from typing import Dict, Any, Optional
from decimal import Decimal
from model_config.llm import get_slm
from prompt.finance_prompt_template import get_finance_analysis_prompt
from database.finance_memory import get_finance_memory_manager
from data.finance_profile import FinanceProfile
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_decimals_to_float(obj: Any) -> Any:
    """
    Recursively convert Decimal objects to float for MongoDB compatibility.
    
    Args:
        obj: Object that may contain Decimal values
        
    Returns:
        Object with Decimal values converted to float
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
            self.slm_client = get_slm()
        return self.slm_client
    
    def _parse_slm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse the SLM JSON response and validate structure.
        
        Args:
            response_text: Raw response from SLM
            
        Returns:
            Parsed and validated response dict
            
        Raises:
            ValueError: If response format is invalid
        """
        try:
            # Clean the response text (remove markdown formatting if present)
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Parse JSON
            parsed_response = json.loads(clean_text)
            
            # Validate required keys
            required_keys = ["FinanceProfile", "profile_summary"]
            for key in required_keys:
                if key not in parsed_response:
                    raise ValueError(f"Missing required key: {key}")
            
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
        
        Args:
            user_data: User's financial data from dt.json
            user_id: Unique identifier for the user
            
        Returns:
            Complete analysis result with profile, insights, and summary
        """
        try:
            # Convert Decimal objects to float for MongoDB compatibility
            user_data = convert_decimals_to_float(user_data)
            
            # Get SLM client
            client = self._get_slm_client()
            
            # Build the prompt with user data
            prompt = get_finance_analysis_prompt(user_data)
            
            logger.info(f"Analyzing finances for user: {user_id}")
            
            # Call SLM for analysis
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast inference model for reasoning
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
                temperature=0.4,  # Low temperature for consistent structured output
            )
            
            # Extract and parse response
            response_text = completion.choices[0].message.content
            logger.info("Received response from SLM, parsing...")
            
            # Parse the structured response
            parsed_response = self._parse_slm_response(response_text)
            
            # Validate FinanceProfile structure
            finance_profile_data = parsed_response["FinanceProfile"]
            
            # Try to create a FinanceProfile instance for validation
            try:
                finance_profile = FinanceProfile(**finance_profile_data)
                # Convert back to dict to ensure all fields are properly serialized
                validated_profile_data = finance_profile.model_dump()
            except Exception as e:
                logger.warning(f"Profile validation failed, using raw data: {e}")
                validated_profile_data = finance_profile_data
            
            # Extract additional components
            additional_insights = parsed_response.get("additional_insights", {})
            profile_summary = parsed_response.get("profile_summary", "")
            
            # Convert all data to MongoDB-compatible format
            validated_profile_data = convert_decimals_to_float(validated_profile_data)
            additional_insights = convert_decimals_to_float(additional_insights)
            
            # Store in finance memory
            doc_id = self.memory_manager.store_finance_profile(
                user_id=user_id,
                profile_data=validated_profile_data,
                additional_insights=additional_insights,
                profile_summary=profile_summary
            )
            
            logger.info(f"Stored finance profile for user {user_id} with document ID: {doc_id}")
            
            # Return complete analysis
            return {
                "user_id": user_id,
                "document_id": doc_id,
                "finance_profile": validated_profile_data,
                "additional_insights": additional_insights,
                "profile_summary": profile_summary,
                "analysis_status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing user finances: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "analysis_status": "failed"
            }
    
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored financial profile for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Stored financial profile or None if not found
        """
        return self.memory_manager.get_finance_profile(user_id)
    
    def update_user_insights(self, user_id: str, new_insights: Dict[str, Any]) -> bool:
        """
        Update additional insights for a user.
        
        Args:
            user_id: Unique identifier for the user
            new_insights: New insights to add/update
            
        Returns:
            True if update successful, False otherwise
        """
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