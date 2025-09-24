# Finance Agent Memory System

## Overview

The Finance Agent Memory System is an AI-powered platform that builds structured financial memory by reading user data from the `finance_profiles` collection and storing analyzed insights in the `finance_memory` collection using a Groq-hosted SLM.

## System Architecture

```
finance_profiles collection → SLM Analysis → Structured Memory → finance_memory collection
```

## Data Flow

### 1. Input Collection: `finance_profiles`
Stores raw financial data per user:
```json
{
  "user_id": "user_123",
  "Person": {"PersonID": 1, "FirstName": "John", ...},
  "Account": {"CurrentBalance": 250000.75, ...},
  "Transaction": [{"Amount": 50000, "TransactionType": "Credit", ...}],
  "Loan": {"LoanAmount": 3000000, "InterestRate": 7.0, ...}
}
```

### 2. Processing: SLM Analysis
1. Read user data from `finance_profiles` by `user_id`
2. Build an analysis prompt with user banking data (no hard-coded Pydantic schema)
3. Call Groq SLM (`openai/gpt-oss-120b`) for structured extraction
4. Parse and validate JSON response against the expected prompt schema

### 3. Output Collection: `finance_memory`
Stores structured financial memory. The `finance_profile` field stores the entire SLM analysis object:
```json
{
  "user_id": "user_123",
  "finance_profile": {
    "account_overview": {
      "total_balance": 152345.75,
      "monthly_income_avg": 85000,
      "monthly_expense_avg": 62000,
      "net_cash_flow_monthly": 23000,
      "savings_rate_pct": 27.06
    },
    "spending_analysis": {
      "by_category": [{ "category": "groceries", "monthly_avg": 9000, "share_pct": 14.5 }],
      "top_merchants": [{ "merchant": "Amazon", "amount": 12000, "count": 6 }],
      "recurring_payments": [{ "name": "Netflix", "amount": 499, "frequency": "monthly", "next_expected_date": "2025-10-01" }]
    },
    "income_analysis": {
      "sources": [{ "name": "Employer", "monthly_avg": 85000, "regularity_score": 0.95 }],
      "volatility_pct": 5.2,
      "trend": "stable"
    },
    "debt_analysis": {
      "total_debt": 350000,
      "dti_ratio_pct": 28.4,
      "accounts": [{ "type": "credit_card", "balance": 25000, "apr_pct": 24.0, "min_payment": 2500, "status": "current" }]
    },
    "risk_flags": ["high_credit_card_apr"],
    "recommendations": ["Prioritize paying down high-APR balances"],
    "summary": "Cash flow is positive with manageable DTI; reduce high-APR debt to improve resilience."
  },
  "additional_insights": {},
  "profile_summary": "Cash flow is positive with manageable DTI; reduce high-APR debt to improve resilience.",
  "created_at": "2025-09-23T10:00:00Z",
  "version": 1
}
```

## Quick Start

### 1. Load Data into Database
```bash
# Load financial profiles from dt.json into finance_profiles collection
python load_finance_profiles.py
```

### 2. Check Database Status
```bash
# Verify data is loaded correctly
python check_database.py
```

### 3. Start the Server
```bash
# Start the FastAPI server
uvicorn main:app --reload
```

### 4. Test the Memory Endpoint
```bash
# Test with API call
python test_memory_api.py

# Or use curl
curl -X POST "http://localhost:8000/memory" \
     -H "Content-Type: application/json" \
     -d '{"user_id": "user_1"}'
```

## Installation & Setup

### 1. Install Dependencies
```bash
cd c:\Users\DESK0046\Documents\finance_agent
.\env\Scripts\Activate.ps1  # Activate virtual environment
pip install -r requirements.txt
```

### 2. Environment Configuration
Create `.env` and configure:
```bash
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
MONGO_URI=mongodb://127.0.0.1:27017
DATABASE_NAME=finance_agent
```

### 3. Run the System
```bash
# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Build User Memory
```bash
POST /memory
{
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "user_id": "user_123",
  "memory_status": "success",
  "document_id": "507f1f77bcf86cd799439011",
  "message": "Memory successfully built and stored for user user_123",
  "slm_response": {
    "account_overview": { "total_balance": 152345.75, "monthly_income_avg": 85000, "monthly_expense_avg": 62000, "net_cash_flow_monthly": 23000, "savings_rate_pct": 27.06 },
    "spending_analysis": { "by_category": [], "top_merchants": [], "recurring_payments": [] },
    "income_analysis": { "sources": [], "volatility_pct": 0, "trend": "stable" },
    "debt_analysis": { "total_debt": 0, "dti_ratio_pct": 0, "accounts": [] },
    "risk_flags": [],
    "recommendations": [],
    "summary": "..."
  }
}
```

### Generate Personalized Suggestions
```bash
POST /suggestions
{
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "user_id": "user_123",
  "short_msg": "Tighten monthly cash flow and build a 3‑month emergency fund",
  "suggestion": [
    "Increase monthly savings auto-transfer by ₹5,000 to reach a 3‑month emergency fund in 6 months.",
    "Refinance or pay down the highest-APR credit card to cut interest costs.",
    "Set merchant-level caps for online shopping categories where spend is trending up."
  ]
}
```

## Directory Structure

```
c:\Users\DESK0046\Documents\finance_agent\
├── data/
│   ├── dt.json                    # Sample banking data
│   └── finance_profile.py         # Pydantic profile model
├── database/
│   └── finance_memory.py          # MongoDB integration
├── model_config/
│   └── llm.py                     # SLM configuration
├── prompt/
│   └── finance_prompt_template.py # Prompt templates (analysis & suggestions)
├── services/
│   └── finance_chat.py            # SLM communication service
├── main.py                        # FastAPI app with /memory and /suggestions endpoints
├── test_memory_endpoint.py        # Memory endpoint tests
├── requirements.txt               # Dependencies
└── .env.example                   # Environment template
```

## Key Functions

### `/memory` Endpoint Workflow
1. **Read**: Gets user data from `finance_profiles` collection by `user_id`
2. **Analyze**: Uses SLM to build structured financial memory
3. **Store**: Saves analyzed memory in `finance_memory` collection
4. **Return**: Provides status and document ID

### Model Integration
- **SLM (analysis/memory)**: Groq `openai/gpt-oss-120b`
- **LLM (suggestions)**: Google Gemini `gemini-2.5-flash`
- Temperature: 0.4 (consistent structured output)
- Response format:
  - Analysis: strict JSON with keys `account_overview`, `spending_analysis`, `income_analysis`, `debt_analysis`, `risk_flags`, `recommendations`, `summary`
  - Suggestions: JSON with `short_msg` (string) and `suggestion` (list of strings)


## Usage Workflow

1. **Setup**: Ensure user data exists in `finance_profiles` collection
2. **Build Memory**: POST `/memory` with `{ "user_id": "user_123" }`
3. **Generate Suggestions**: POST `/suggestions` with the same body
4. **Result**: Structured memory stored and personalized suggestions returned

## Next Steps

1. **Environment Setup**: Configure GROQ_API_KEY and MongoDB
2. **Data Preparation**: Load user data into `finance_profiles` collection
4. **Integration**: Connect with your data sources
