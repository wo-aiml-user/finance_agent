# Finance Agent Memory System

## Overview

The Finance Agent Memory System is an AI-powered platform that builds structured financial memory by reading user data from the `finance_profiles` collection and storing analyzed insights in the `finance_memory` collection using Small Language Models (SLM).

## System Architecture

```
finance_profiles collection → SLM Analysis → Structured Memory → finance_memory collection
```

## Key Components

### 1. Memory Endpoint (`/memory`)
- **Single endpoint** for memory building
- Reads user data from `finance_profiles` collection by `user_id`
- Uses SLM to analyze and structure the data
- Stores results in `finance_memory` collection

### 2. SLM Integration (`services/`)
- **services/finance_chat.py**: SLM communication service for analysis/memory building
- Uses Groq's fast inference model for structured data extraction
- Handles response parsing, validation, and persistence to `finance_memory`

### 3. Database Layer (`database/`)
- **finance_memory.py**: MongoDB integration
- Manages both `finance_profiles` and `finance_memory` collections
- Supports CRUD operations with versioning

### 4. Data Models (`data/`)
- **data/finance_profile.py**: Comprehensive financial schema
- 100+ fields covering income, expenses, goals, investments, debt, etc.

### 5. Prompts (`prompt/`)
- **prompt/finance_prompt_template.py**: Centralized prompt builders
  - `get_finance_analysis_prompt()` for SLM analysis
  - `get_suggestions_prompt()` for user-facing advice

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
2. Build prompt with user data and FinanceProfile schema
3. Call Groq SLM for structured extraction
4. Parse and validate JSON response

### 3. Output Collection: `finance_memory`
Stores structured financial memory:
```json
{
  "user_id": "user_123",
  "finance_profile": {
    "user_age_years": 34,
    "income_total_yearly_amount": 1400000.00,
    "expense_total_monthly": 18000.00,
    "savings_monthly_amount": 95000.00,
    ...
  },
  "additional_insights": {
    "cash_flow_pattern": "Consistent income with stable expenses",
    "financial_health_score": "8/10",
    "recommended_actions": [...]
  },
  "profile_summary": "Comprehensive financial analysis...",
  "created_at": "2024-09-19T10:00:00Z",
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
# Test the memory endpoint logic
python test_memory_endpoint.py

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
  "message": "Memory successfully built and stored for user user_123"
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
  "suggestion": "Based on your income stability, current savings rate, and debt profile, start by..."
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
- **SLM (analysis/memory)**: Groq `llama-3.1-8b-instant`
- **LLM (suggestions)**: Google Gemini `gemini-2.5flash`
- Temperature: 0.4 (consistent structured output)
- Response format: Strict JSON for analysis; JSON with `short_msg` and `suggestion` for suggestions

## Testing

Test the memory endpoint:
```bash
python test_memory_endpoint.py
```

Tests cover:
- Database connectivity
- Test data setup in finance_profiles
- Memory endpoint logic
- Collection management

## Usage Workflow

1. **Setup**: Ensure user data exists in `finance_profiles` collection
2. **Build Memory**: POST `/memory` with `{ "user_id": "user_123" }`
3. **Generate Suggestions**: POST `/suggestions` with the same body
4. **Result**: Structured memory stored and personalized suggestions returned

## Next Steps

1. **Environment Setup**: Configure GROQ_API_KEY and MongoDB
2. **Data Preparation**: Load user data into `finance_profiles` collection
4. **Integration**: Connect with your data sources
5. **Production**: Deploy with proper security and monitoring