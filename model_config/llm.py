
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from groq import Groq
from dotenv import load_dotenv

load_dotenv('.env')


def get_llm():
    """
    Initialize and return the Google Gemini LLM instance
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5flash",
        google_api_key=google_api_key
    )
    return llm


def get_slm():
    """
    Initialize and return the Groq SLM (Small Language Model) instance
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required")
    
    client = Groq(api_key=groq_api_key)
    return client


