"""
Ultimate Unified Observability Chatbot - FIXED VERSION
Demonstrates ALL observability frameworks simultaneously on the same LLM calls
"""

import os
import time
from google import genai
from dotenv import load_dotenv

# Langtrace
from langtrace_python_sdk import langtrace

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# OpenLLMetry
from traceloop.sdk import Traceloop

# Load environment variables
load_dotenv()

# ============================================================================
# INITIALIZATION - All frameworks at once
# ============================================================================

print("🚀 Initializing Unified Observability Stack...")
print("=" * 70)

# 1. Langtrace Setup
print("📊 [1/4] Initializing Langtrace...")
try:
    langtrace.init(api_key=os.getenv("LANGTRACE_API_KEY"))
    print("    ✅ Langtrace ready: https://app.langtrace.ai")
    LANGTRACE_ENABLED = True
except Exception as e:
    print(f"    ❌ Langtrace failed: {e}")
    LANGTRACE_ENABLED = False

# 2. OpenTelemetry Setup (sends to Jaeger)
print("📊 [2/4] Initializing OpenTelemetry → Jaeger...")
try:
    resource = Resource(attributes={
        "service.name": "unified-chatbot",
        "service.version": "2.0.0",
        "demo.type": "unified-observability"
    })
    otel_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
    otel_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(otel_provider)
    otel_tracer = trace.get_tracer("unified-chatbot")
    print("    ✅ OpenTelemetry ready: http://localhost:16686")
    OTEL_ENABLED = True
except Exception as e:
    print(f"    ❌ OpenTelemetry failed: {e}")
    OTEL_ENABLED = False
    otel_tracer = None

# 3. OpenLLMetry Setup (also uses OpenTelemetry)
print("📊 [3/4] Initializing OpenLLMetry...")
try:
    Traceloop.init(
        app_name="unified-chatbot-openllmetry",
        api_endpoint="http://localhost:4318/v1/traces"
    )
    print("    ✅ OpenLLMetry ready (sends to Jaeger)")
    OPENLLMETRY_ENABLED = True
except Exception as e:
    print(f"    ⚠️  OpenLLMetry initialization issue: {e}")
    OPENLLMETRY_ENABLED = False

# 4. Opik Setup - Simplified
print("📊 [4/4] Initializing Opik...")
OPIK_ENABLED = False
opik_client = None

try:
    import opik
    
    api_key = os.getenv("OPIK_API_KEY")
    workspace = os.getenv("OPIK_WORKSPACE")
    
    if api_key and workspace:
        opik.configure(api_key=api_key, workspace=workspace)
        opik_client = opik.Opik()
        OPIK_ENABLED = True
        print("    ✅ Opik ready: https://www.comet.com/opik")
    else:
        print("    ⚠️  Opik keys not found in .env (skipping)")
        
except ImportError:
    print("    ⚠️  Opik not installed (pip install opik)")
except Exception as e:
    print(f"    ⚠️  Opik not configured: {e}")

print("=" * 70)
enabled_count = sum([LANGTRACE_ENABLED, OTEL_ENABLED, OPENLLMETRY_ENABLED, OPIK_ENABLED])
print(f"✅ {enabled_count}/4 frameworks initialized!\n")

# Configure Gemini
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ============================================================================
# UNIFIED CHAT FUNCTION - All instrumentation in one place
# ============================================================================

def unified_chat_response(user_input: str, user_id: str, conversation_num: int):
    """
    Single function that instruments with ALL frameworks simultaneously
    """
    
    print(f"\n{'='*70}")
    print(f"📝 Processing Query #{conversation_num}")
    print(f"{'='*70}\n")
    
    # Start timing
    start_time = time.time()
    
    response_text = None
    
    # ========================================================================
    # OpenTelemetry Manual Instrumentation (if enabled)
    # ========================================================================
    if OTEL_ENABLED and otel_tracer:
        with otel_tracer.start_as_current_span("unified-chat-interaction") as otel_span:
            otel_span.set_attribute("user.id", user_id)
            otel_span.set_attribute("user.input", user_input)
            otel_span.set_attribute("conversation.number", conversation_num)
            otel_span.set_attribute("framework", "OpenTelemetry")
            
            with otel_tracer.start_as_current_span("llm-generation") as llm_span:
                llm_span.set_attribute("llm.model", "gemini-2.0-flash-exp")
                llm_span.set_attribute("llm.provider", "google")
                
                try:
                    # ========================================================
                    # THE ACTUAL LLM CALL
                    # (Langtrace auto-instruments this!)
                    # (OpenLLMetry auto-instruments this!)
                    # ========================================================
                    
                    response = client.models.generate_content(
                        model='gemini-2.0-flash-exp',
                        contents=user_input
                    )
                    
                    response_text = response.text
                    latency = time.time() - start_time
                    
                    # Calculate metrics
                    input_tokens = len(user_input.split()) * 1.3
                    output_tokens = len(response_text.split()) * 1.3
                    estimated_cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)
                    
                    # Add OpenTelemetry attributes
                    llm_span.set_attribute("llm.input_tokens", int(input_tokens))
                    llm_span.set_attribute("llm.output_tokens", int(output_tokens))
                    llm_span.set_attribute("llm.latency_seconds", round(latency, 3))
                    llm_span.set_attribute("llm.estimated_cost_usd", round(estimated_cost, 6))
                    llm_span.set_attribute("llm.success", True)
                    
                    if estimated_cost > 0.01:
                        llm_span.add_event("high_cost_warning", {
                            "cost_usd": estimated_cost,
                            "threshold": 0.01
                        })
                    
                except Exception as e:
                    llm_span.set_attribute("llm.success", False)
                    llm_span.set_attribute("error.message", str(e))
                    print(f"❌ Error: {e}")
                    return None
    else:
        # If OTEL not enabled, still make the LLM call
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=user_input
            )
            response_text = response.text
            latency = time.time() - start_time
            input_tokens = len(user_input.split()) * 1.3
            output_tokens = len(response_text.split()) * 1.3
            estimated_cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    # ========================================================================
    # Opik Manual Tracking (if enabled)
    # ========================================================================
    if OPIK_ENABLED and opik_client:
        try:
            opik_client.trace(
                name="unified-chat-interaction",
                input={"query": user_input, "user": user_id},
                output={"response": response_text},
                metadata={
                    "model": "gemini-2.0-flash-exp",
                    "latency_seconds": round(latency, 3),
                    "estimated_cost_usd": round(estimated_cost, 6),
                    "conversation_number": conversation_num,
                    "input_tokens": int(input_tokens),
                    "output_tokens": int(output_tokens)
                },
                tags=["gemini", "unified-demo", f"user-{user_id}"]
            )
        except Exception as e:
            print(f"    ⚠️  Opik logging failed: {e}")
    
    # ========================================================================
    # Print Results with Framework Status
    # ========================================================================
    print(f"🤖 Bot Response:")
    print(f"   {response_text}\n")
    
    print(f"📊 Observability Status:")
    if LANGTRACE_ENABLED:
        print(f"   ✅ Langtrace:      Auto-instrumented (check dashboard)")
    else:
        print(f"   ❌ Langtrace:      Not enabled")
        
    if OTEL_ENABLED:
        print(f"   ✅ OpenTelemetry:  Manual spans added (check Jaeger)")
    else:
        print(f"   ❌ OpenTelemetry:  Not enabled")
        
    if OPENLLMETRY_ENABLED:
        print(f"   ✅ OpenLLMetry:    Auto-instrumented (check Jaeger)")
    else:
        print(f"   ❌ OpenLLMetry:    Not enabled")
        
    if OPIK_ENABLED:
        print(f"   ✅ Opik:           Logged (check Opik dashboard)")
    else:
        print(f"   ⚠️  Opik:           Not configured")
    
    print(f"\n⏱️  Metrics:")
    print(f"   Latency:        {round(latency, 3)}s")
    print(f"   Input tokens:   ~{int(input_tokens)}")
    print(f"   Output tokens:  ~{int(output_tokens)}")
    print(f"   Est. Cost:      ${round(estimated_cost, 6)}")
    
    if estimated_cost > 0.01:
        print(f"\n   🚨 HIGH COST ALERT! (>${0.01})")
    
    return response_text

# ============================================================================
# MAIN CHAT LOOP
# ============================================================================

def main():
    """
    Main chat interface - one bot, all frameworks watching
    """
    
    print("\n" + "="*70)
    print("🎯 UNIFIED OBSERVABILITY CHATBOT v2.0")
    print("="*70)
    print("\n🔍 Active frameworks monitoring your queries:")
    
    if LANGTRACE_ENABLED:
        print("   ✅ Langtrace (auto)")
    if OTEL_ENABLED:
        print("   ✅ OpenTelemetry (manual)")
    if OPENLLMETRY_ENABLED:
        print("   ✅ OpenLLMetry (auto)")
    if OPIK_ENABLED:
        print("   ✅ Opik (manual)")
    
    print("\n📊 Check your dashboards:")
    if LANGTRACE_ENABLED:
        print("   • Langtrace:  https://app.langtrace.ai")
    if OTEL_ENABLED or OPENLLMETRY_ENABLED:
        print("   • Jaeger:     http://localhost:16686")
    if OPIK_ENABLED:
        print("   • Opik:       https://www.comet.com/opik")
    
    print("\n" + "="*70)
    
    user_id = input("\n👤 Enter your name: ")
    print(f"\nHello {user_id}! Each question will be traced by all active frameworks.")
    print("Type 'quit' to exit and view dashboards.\n")
    
    conversation_count = 0
    
    while True:
        user_input = input(f"\n[Q{conversation_count + 1}] You: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n" + "="*70)
            print(f"👋 Goodbye {user_id}! You had {conversation_count} interactions.")
            print("="*70)
            print("\n📊 Now check your dashboards to compare frameworks:")
            
            if LANGTRACE_ENABLED:
                print(f"\n   1. Langtrace:  https://app.langtrace.ai")
                print(f"      → See auto-instrumented traces with costs")
            
            if OTEL_ENABLED or OPENLLMETRY_ENABLED:
                print(f"\n   2. Jaeger:     http://localhost:16686")
                print(f"      → Service: 'unified-chatbot'")
                print(f"      → Compare OpenTelemetry vs OpenLLMetry spans")
            
            if OPIK_ENABLED:
                print(f"\n   3. Opik:       https://www.comet.com/opik")
                print(f"      → See evaluation and monitoring data")
            
            print(f"\n💡 TIP: Look for conversation #{conversation_count} in each dashboard")
            print("="*70)
            break
        
        conversation_count += 1
        unified_chat_response(user_input, user_id, conversation_count)
    
    # Flush all traces
    print("\n🔄 Flushing traces...")
    if OTEL_ENABLED:
        trace.get_tracer_provider().force_flush()
    if OPIK_ENABLED and opik_client:
        try:
            opik_client.flush()
        except:
            pass
    print("✅ All traces sent!\n")

if __name__ == "__main__":
    main()