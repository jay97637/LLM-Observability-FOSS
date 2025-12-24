import os
from google import genai
from dotenv import load_dotenv
from langtrace_python_sdk import langtrace
import time

# Load environment variables
load_dotenv()

# Initialize Langtrace - THIS IS THE MAGIC (1 line!)
langtrace.init(api_key=os.getenv("LANGTRACE_API_KEY"))

# Configure Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def chat_with_langtrace():
    """Same chatbot but WITH observability"""
    
    print("🤖 Chatbot (WITH Langtrace Observability)")
    print("=" * 60)
    print("Ask me anything! (type 'quit' to exit)\n")
    
    user_id = input("Enter your name: ")
    print(f"\nHello {user_id}!\n")
    
    conversation_count = 0
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            print(f"\nGoodbye {user_id}! Had {conversation_count} interactions.")
            print("📊 Check Langtrace dashboard for full analytics!")
            print("   https://app.langtrace.ai")
            break
        
        conversation_count += 1
        start_time = time.time()
        
        # Generate response
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=user_input
        )
        
        latency = time.time() - start_time
        
        # Calculate approximate metrics
        input_tokens = len(user_input.split()) * 1.3  # Rough estimate
        output_tokens = len(response.text.split()) * 1.3
        estimated_cost = (input_tokens * 0.000015) + (output_tokens * 0.00006)  # Gemini Flash pricing
        
        print(f"\nBot: {response.text}\n")
        
        # Show metrics in terminal
        print("=" * 60)
        print(f"📊 Metrics (Query #{conversation_count}):")
        print(f"   ⏱️  Latency:        {round(latency, 3)}s")
        print(f"   📝 Input tokens:   ~{int(input_tokens)}")
        print(f"   📝 Output tokens:  ~{int(output_tokens)}")
        print(f"   💰 Est. Cost:      ${round(estimated_cost, 6)}")
        
        if estimated_cost > 0.01:
            print(f"   🚨 HIGH COST ALERT! (>${0.01})")
        
        print(f"\n   ✅ Tracked in Langtrace: https://app.langtrace.ai")
        print("=" * 60)

if __name__ == "__main__":
    chat_with_langtrace()