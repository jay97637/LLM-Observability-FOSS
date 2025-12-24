import os
from google import genai
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
import time

# Load environment variables
load_dotenv()

# Setup OpenTelemetry
resource = Resource(attributes={
    "service.name": "gemini-chatbot",
    "service.version": "1.0.0"
})

# Create tracer provider
provider = TracerProvider(resource=resource)

# Add console exporter (prints traces to terminal)
console_exporter = ConsoleSpanExporter()
provider.add_span_processor(BatchSpanProcessor(console_exporter))

# Set as global tracer
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# Configure Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def chat_with_opentelemetry():
    """Chatbot with manual OpenTelemetry instrumentation"""
    
    print("🤖 Chatbot (WITH OpenTelemetry Manual Instrumentation)")
    print("=" * 60)
    print("Watch the traces appear below!\n")
    
    user_id = input("Enter your name: ")
    
    print(f"\nHello {user_id}! Ask me anything! (type 'quit' to exit)\n")
    
    conversation_count = 0
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            print(f"\n✅ Goodbye {user_id}! Had {conversation_count} interactions.")
            break
        
        conversation_count += 1
        
        # 🎯 Create a trace span for the entire interaction
        with tracer.start_as_current_span("chat-interaction") as span:
            # Add attributes to the span
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.input", user_input)
            span.set_attribute("conversation.number", conversation_count)
            
            start_time = time.time()
            
            # 🎯 Create a nested span for LLM generation
            with tracer.start_as_current_span("llm-generation") as llm_span:
                llm_span.set_attribute("llm.model", "gemini-2.0-flash-exp")
                llm_span.set_attribute("llm.provider", "google")
                llm_span.set_attribute("llm.input_length", len(user_input))
                
                try:
                    # Generate response
                    response = client.models.generate_content(
                        model='gemini-2.0-flash-exp',
                        contents=user_input
                    )
                    
                    latency = time.time() - start_time
                    
                    # Add output attributes
                    llm_span.set_attribute("llm.output_length", len(response.text))
                    llm_span.set_attribute("llm.latency_seconds", round(latency, 3))
                    llm_span.set_attribute("llm.success", True)
                    
                    print(f"\nBot: {response.text}\n")
                    print(f"⏱️  Latency: {round(latency, 3)}s")
                    
                except Exception as e:
                    llm_span.set_attribute("llm.success", False)
                    llm_span.set_attribute("error.message", str(e))
                    print(f"\n❌ Error: {e}\n")
            
            print("-" * 60)

if __name__ == "__main__":
    chat_with_opentelemetry()