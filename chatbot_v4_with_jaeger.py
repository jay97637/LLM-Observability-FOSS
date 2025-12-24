import os
from google import genai
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
import time

# Load environment variables
load_dotenv()

# Setup OpenTelemetry with Resource attributes
resource = Resource(attributes={
    "service.name": "gemini-chatbot",
    "service.version": "1.0.0",
    "deployment.environment": "demo"
})

# Create tracer provider
provider = TracerProvider(resource=resource)

# Configure OTLP exporter to send to Jaeger
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4318/v1/traces",
)

# Add span processor
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Set as global tracer
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

# Configure Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def chat_with_jaeger():
    """Chatbot with OpenTelemetry sending traces to Jaeger"""
    
    print("🤖 Chatbot (OpenTelemetry → Jaeger)")
    print("=" * 60)
    print("📊 View traces at: http://localhost:16686")
    print("=" * 60)
    
    user_id = input("\nEnter your name: ")
    session_id = f"session-{int(time.time())}"
    
    print(f"\nHello {user_id}! Ask me anything! (type 'quit' to exit)")
    print(f"Session ID: {session_id}\n")
    
    conversation_count = 0
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == 'quit':
            print(f"\n✅ Goodbye {user_id}! Had {conversation_count} interactions.")
            print(f"🔍 Check Jaeger UI for full trace: http://localhost:16686")
            print(f"   Search for service: 'gemini-chatbot'")
            break
        
        conversation_count += 1
        
        # Create a trace span for the entire interaction
        with tracer.start_as_current_span(
            "chat-interaction",
            attributes={
                "user.id": user_id,
                "session.id": session_id,
                "conversation.number": conversation_count,
            }
        ) as span:
            
            # Add user input as event
            span.add_event("user_message_received", {
                "message.length": len(user_input)
            })
            
            start_time = time.time()
            
            # Create nested span for LLM call
            with tracer.start_as_current_span(
                "llm-generation",
                attributes={
                    "llm.model": "gemini-2.0-flash-exp",
                    "llm.provider": "google",
                    "llm.request.type": "chat.completion",
                }
            ) as llm_span:
                
                llm_span.add_event("llm_request_start")
                
                try:
                    # Generate response
                    response = client.models.generate_content(
                        model='gemini-2.0-flash-exp',
                        contents=user_input
                    )
                    
                    latency = time.time() - start_time
                    
                    # Add success attributes
                    llm_span.set_attribute("llm.input.length", len(user_input))
                    llm_span.set_attribute("llm.output.length", len(response.text))
                    llm_span.set_attribute("llm.latency.seconds", round(latency, 3))
                    llm_span.set_attribute("llm.success", True)
                    
                    llm_span.add_event("llm_response_received", {
                        "output.length": len(response.text),
                        "latency": round(latency, 3)
                    })
                    
                    print(f"\nBot: {response.text}\n")
                    print(f"⏱️  Latency: {round(latency, 3)}s | 📝 Trace sent to Jaeger!")
                    
                except Exception as e:
                    llm_span.set_attribute("llm.success", False)
                    llm_span.set_attribute("error.type", type(e).__name__)
                    llm_span.set_attribute("error.message", str(e))
                    llm_span.add_event("error_occurred", {
                        "error.type": type(e).__name__
                    })
                    print(f"\n❌ Error: {e}\n")
            
            print("-" * 60)
    
    # Ensure all spans are sent
    trace.get_tracer_provider().force_flush()

if __name__ == "__main__":
    chat_with_jaeger()