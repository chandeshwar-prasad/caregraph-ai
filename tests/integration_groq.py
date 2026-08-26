import os
import sys
from dotenv import load_dotenv

# Add parent directory to path so app can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm import GroqLLMService

def run_integration_test():
    load_dotenv()
    
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    print("--- CareGraph AI Groq Manual Integration Test ---")
    
    if not api_key or api_key.strip() == "your_groq_api_key_here":
        print("Error: GROQ_API_KEY is not set or contains the default placeholder.")
        print("Please configure a valid GROQ_API_KEY in your .env file to run this test.")
        return
        
    print(f"Connecting to Groq API using model: {model}...")
    
    try:
        service = GroqLLMService(api_key=api_key, model=model)
        
        # Test Query 1
        query1 = "I have a sudden high fever and bad cough since yesterday"
        print(f"\nTest 1: Intent Extraction")
        print(f"User query: '{query1}'")
        intent_info = service.extract_intent(query1)
        print(f"Extracted Intent: {intent_info.intent.value}")
        print(f"Confidence: {intent_info.confidence}")
        print(f"Extracted Entities: {intent_info.extracted_entities}")
        
        # Test Query 2
        print(f"\nTest 2: Response Generation")
        response = service.generate_response(query1, intent_info)
        print(f"Assistant Response:\n{response}")
        
        print("\n-------------------------------------------------")
        print("Manual Integration Test Completed successfully!")
        
    except Exception as e:
        print(f"\nError occurred during live API connection: {e}")
        print("Please verify your API key, billing account, and internet connectivity.")

if __name__ == "__main__":
    run_integration_test()
