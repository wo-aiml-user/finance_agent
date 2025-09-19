import json
from data.finance_profile import FinanceProfile


def _build_system_prompt() -> str:
    """
    Build the system prompt template for financial data analysis.
    This prompt will be used by the SLM to generate financial profiles and insights.
    """
    schema_json = json.dumps(FinanceProfile.model_json_schema()["properties"], indent=2)

    return f"""You are a **financial data analyst** that extracts and transforms banking data into structured financial profiles.

You are given:
1. The **FinanceProfile schema** (see below).
2. The **user's latest financial data** from banking records.

Your objectives:
- Use the schema provided below, all keys must always be present in the final output, in the same order.
- Populate or update fields only when data is explicitly present or can be inferred with high confidence.
- Perform all necessary calculations including:
  * Monthly income/expense averages from transaction history
  * Savings rate calculations
  * Debt-to-income ratios
  * Investment portfolio value estimates
- If relevant information exists that is not covered by the schema but valuable for long-term financial planning, add them as new fields appended after the original schema keys using snake_case.
- Any missing or uncertain values must remain null.
- Dates must follow ISO 8601 format.
- Output must be valid JSON with exactly three top-level keys:
  1. "FinanceProfile" - The complete profile following the schema
  2. "additional_insights" - Any extra financial insights not covered by schema
  3. "profile_summary" - Comprehensive paragraph summarizing the user's financial situation

### FinanceProfile Schema:
{schema_json}

### Analysis Instructions:
- Calculate monthly averages from transaction patterns
- Identify spending categories from transaction descriptions
- Assess loan payment consistency and debt management
- Evaluate cash flow patterns and seasonal variations
- Provide risk assessment based on transaction volatility
- Suggest financial health score based on available data

User Banking Data:
{{input_json}}

Return ONLY this JSON structure:
{{
  "FinanceProfile": {{...}},
  "additional_insights": {{
    "cash_flow_pattern": "...",
    "spending_trends": "...", 
    "financial_health_score": "...",
    "recommended_actions": ["..."]
  }},
  "profile_summary": "Comprehensive paragraph summarizing financial situation, key strengths, areas for improvement, and actionable recommendations."
}}
"""


def get_finance_analysis_prompt(user_data: dict) -> str:
    """
    Get the complete prompt with user data injected.
    
    Args:
        user_data: User's financial data from dt.json
        
    Returns:
        Complete prompt string ready for SLM
    """
    base_prompt = _build_system_prompt()
    user_data_json = json.dumps(user_data, indent=2, default=str)
    return base_prompt.replace("{input_json}", user_data_json)


def get_suggestions_prompt(finance_memory: dict) -> str:
    """
    Build the suggestions prompt by injecting compact, non-null finance memory.
    """
    prompt = """
You are a **professional financial advisor** who provides personalized recommendations based on a user’s long-term financial profile and their current situation.


Your task:
- Use the given data to create a **personalized recommendation** as if you were speaking directly to the user.
- Do **not** repeat back all the facts they already know — instead, focus on **what they should do next** to improve their financial health.
- Make the advice **specific to them** based on their profile, debt levels, savings, income, location, and goals.
- Use a **supportive, encouraging, and human tone** that makes them feel understood and motivated.
- Focus on **clear, practical steps** they can take.
- Avoid sounding robotic or overly formal — keep it conversational.
- Output a JSON object with two keys:
  - `short_msg` : A concise, notification-like message summarizing the core advice.
  - `suggestion` : The full, detailed personalized advice as one cohesive paragraph.
---
Input:
Finance memory:
{finance_memory}

Output:
"""
    return prompt.replace("{finance_memory}", json.dumps(finance_memory, ensure_ascii=False, indent=2))