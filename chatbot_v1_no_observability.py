import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini with new SDK
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def chat_without_observability():
    """Simple chatbot without any observability"""
    
    print("🤖 Chatbot (No Observability)")
    print("=" * 50)
    print("Ask me anything! (type 'quit' to exit)\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        
        # Generate response with new SDK
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=user_input
        )
        print(f"\nBot: {response.text}\n")
        print("-" * 50)

if __name__ == "__main__":
    chat_without_observability()